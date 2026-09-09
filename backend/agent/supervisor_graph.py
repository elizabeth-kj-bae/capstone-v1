"""
Supervisor 패턴 기반 Multi-agent Graph.
"""
import asyncio
from typing import TypedDict, Annotated, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI  
from langchain.agents import create_agent
from .mcp_client import get_mcp_tools
from schemas.error import ToolError, OrchestrationError, CapstoneError, ErrorLayer


class SupervisorState(TypedDict):
    """
    Supervisor graph의 state.
    
    본 capstone의 결정:
    - messages: 대화 이력 (기존 단일 agent와 동일)
    - plan: Supervisor가 수립한 계획
    - tasks: 분해된 task 목록 (각 task의 상태 포함)
    - current_task_index: 현재 진행 중인 task
    """
    messages: Annotated[list[BaseMessage], add_messages]

    # Routing
    route: Optional[Literal["simple", "complex"]]  # Routing 결정
    route_reasoning: Optional[str]  # 결정 근거 (LangSmith trace에 기록)

    # Base
    plan: str
    tasks: list[dict]  # [{id, description, agent, status, result}, ...]
    current_task_index: int

    # Dynamic Planning
    replan_rounds: int                   # Replan 횟수 추적
    replan_decision: Optional[dict]      # 최근 replan 결정 정보

    # Validation
    draft_response: Optional[str]        # Writing의 응답 
    validation_result: Optional[dict]    # Validator 결정 결과
    writing_attempts: int                # 재시도 추적 (0부터 시작)
    validation_feedback: Optional[str]   # 재시도 시 Writing에 전달
    validation_attempts: int             # Validator 실행 횟수 (무한 루프 방어용)


class RoutingDecision(BaseModel):
    """Supervisor의 routing 결정."""
    route: Literal["simple", "complex"] = Field(
        description="질문의 복잡도. simple: 인사·메타질문·단순한 정보 요청. complex: 정보 수집·통합·분석이 필요한 작업"
    )
    reasoning: str = Field(
        description="결정 근거를 한 문장으로"
    )


class TaskSpec(BaseModel):
    """Planner가 분해한 단일 task."""
    description: str = Field(description="task가 수행할 작업 설명")
    agent: Literal["research", "analysis", "writing"] = Field(
        description=(
            '담당 sub-agent. '
            '"research": 정보 검색, '
            '"analysis": 수집 정보 분석/가공, '
            '"writing": 최종 응답 작성'
        )
    )


class PlanDecision(BaseModel):
    """Supervisor의 계획 수립 결과 (structured output)."""
    plan: str = Field(description="전체 진행 계획 (자연어 2-3문장)")
    needs_analysis: bool = Field(
        description=(
            "별도 analysis 단계가 필요한지 여부. "
            "True: 패턴 식별·비교/분류·여러 source 통합·우선순위화·근본원인 분석 등 "
            "수집 정보에 대한 가공/추론이 필요한 경우. "
            "False: 단순 검색·필터·나열·요약 등 수집 결과를 거의 그대로 전달하면 되는 경우."
        )
    )
    tasks: list[TaskSpec] = Field(
        description="실행할 task 목록. 순서는 research → (analysis) → writing"
    )


class ReplanDecision(BaseModel):
    """
    Research 결과를 평가하여 추가 정보 수집이 필요한지 판단 (평가 전용).

    Dynamic Planning:
    - is_sufficient: Research 결과가 사용자 의도를 충족하는지
    - reasoning: 판단 근거 (LangSmith trace에 기록)
    실제 plan/tasks 갱신은 별도 replan_node가 수행한다.
    """
    is_sufficient: bool = Field(
        description=(
            "현재까지의 Research 결과가 사용자 질문에 답하기에 충분한지. "
            "True: 추가 검색 불필요, 다음 단계 진행. "
            "False: 추가 정보 수집이 필요"
        )
    )
    reasoning: str = Field(
        description="판단 근거를 1-2 문장으로"
    )


class ReplanPlanDecision(BaseModel):
    """Replan 시 Supervisor가 갱신한 plan과 추가 research task."""
    plan: str = Field(
        description=(
            "갱신된 plan (직전 plan을 보강한 형태). "
            "이미 수집된 raw material은 재수집하지 말고, 부족한 부분만 명시적으로 보강."
        )
    )
    additional_research_tasks: list[TaskSpec] = Field(
        description=(
            "추가로 실행할 research task 목록. "
            "기존 task와 중복되지 않는 새 키워드/source 사용. "
            "agent는 반드시 'research' (analysis/writing은 이후 단계에서 처리)."
        )
    )


async def build_supervisor_graph(checkpointer: BaseCheckpointSaver):
    """
    Supervisor 기반 multi-agent graph 생성.

    Cost & Latency 최적화: 
    - Planning : 빠르고 저렴한 모델 (단순 분류/구조화 task)
    - Writing : 고품질 모델 (정보 추출 + 응답 생성 품질 중요)

    Session 관리 강화:
    - checkpointer를 외부에서 주입 받음 
    - Agent 코드는 checkpointer 구현체와 분리함

    Routing 추가: Simple vs Complex Response 
    """
    # 기존 버전 - 동일 모델 적용 
    # llm = ChatOpenAI(model="gpt-4o", temperature=0)


    # 단계별 모델 분리
    fast_llm = ChatOpenAI(
        model="gpt-4o-mini",  # 빠르고 저렴
        temperature=0,
    )
    
    quality_llm = ChatOpenAI(
        model="gpt-4o",  # 품질 우선
        temperature=0,
    )

    
    # Sub-agent 1: Research Agent (MCP tools 사용)
    mcp_tools = await get_mcp_tools()
    research_agent = create_agent(
        model=quality_llm,
        tools=mcp_tools,
        system_prompt=(
            "당신은 Research Agent입니다. "
            "주어진 task에 대해 적절한 tool을 호출하여 정보를 수집하세요. "
            "수집된 정보를 명확하게 요약하여 반환하세요."
        ),
    )
    
    # Sub-agent 2: Writing Agent (LLM만)
    writing_agent = create_agent(
        model=quality_llm,
        tools=[],
        system_prompt=(
            "당신은 Writing Agent입니다. "
            "Research Agent가 수집한 정보를 받아 사용자가 이해하기 쉬운 형태로 "
            "통합된 답변을 작성하세요."
        ),
    )

    # Sub-agent 3: Analysis Agent
    analysis_agent = create_agent(
        model=quality_llm,
        tools=[],
        system_prompt=(
            "당신은 Analysis Agent입니다. "
            "Research Agent가 수집한 정보를 분석하는 것이 책임입니다.\n\n"
            "다음 중 적절한 분석 활동을 수행하세요:\n"
            "- 패턴 식별: 데이터에서 반복되는 패턴, 추세 발견\n"
            "- 비교/분류: 정보를 카테고리로 분류하거나 비교\n"
            "- 통합: 여러 source의 정보를 일관된 형태로 통합\n"
            "- 우선순위화: 중요도/긴급도 기반 순위 부여\n\n"
            "Writing Agent와 달리, 사용자에게 직접 전달할 응답이 아닌 "
            "Writing Agent가 활용할 분석 결과를 작성하세요. "
            "구조화된 형태(목록, 표, 카테고리)로 표현하면 좋습니다."
        ),
    )

    # Validator Agent
    validator_llm = quality_llm    # 품질 평가는 quality 모델 사용

    class ValidationResult(BaseModel):
        """Validator의 평가 결과."""
        is_acceptable: bool = Field(
            description="응답을 사용자에게 그대로 전달할 수 있는 품질인지 (True/False)"
        )
        score: float = Field(
            description="0.0-1.0 점수. 0.7 이상을 acceptable의 기준으로 권장",
            ge=0.0,
            le=1.0,
        )
        reasoning: str = Field(
            description="판단 근거를 2-3 문장으로"
        )
        feedback: Optional[str] = Field(
            default=None,
            description="재시도가 필요할 때 Writing agent에게 전달할 구체적 개선 지시. is_acceptable이 False일 때만 작성"
        )

    
    # Routing Node 
    async def routing_node(state: SupervisorState) -> dict:
        """
        사용자 질문의 복잡도를 판단하여 경로 결정.
        
        - simple: Supervisor가 LLM 한 번으로 직접 답변
        - complex: 기존 multi-agent flow (Planning → Research → Writing)
        """
        user_msg = state["messages"][-1].content
        
        routing_prompt = f"""\
다음 사용자 질문을 분석하여 처리 경로를 결정하세요.

사용자 질문: {user_msg}

판단 기준:
- simple: 인사, 메타 질문, 단일 LLM 호출로 답변 가능한 단순 정보 요청
  예: "안녕하세요", "당신은 누구인가요?", "어떻게 사용하나요?"
- complex: 정보 수집(검색), 통합, 분석이 필요한 작업
  예: "DB 다운 시 대응 절차와 incident를 종합해 가이드 작성"

route와 reasoning을 응답하세요.
"""
        # Structured output으로 안정성 확보
        decision = await fast_llm.with_structured_output(RoutingDecision).ainvoke([
            SystemMessage(content="You are a routing classifier."),
            HumanMessage(content=routing_prompt),
        ])
        
        return {
            "route": decision.route,
            "route_reasoning": decision.reasoning,
        }

    # Routing - Simple Response Node
    async def simple_response_node(state: SupervisorState) -> dict:
        """
        단순 질문에 LLM 한 번 호출로 직접 답변.
        Plan, Task list 없이 바로 응답.
        """
        user_msg = state["messages"][-1].content
        
        system_prompt = (
            "당신은 ICT 운영 지원 AI 어시스턴트입니다. "
            "사용자의 질문에 친절하고 정확하게 답변하세요. "
            "복잡한 정보 수집이 필요한 경우 별도 안내가 가능하다고 알려주세요."
        )
        
        response = await quality_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ])
        
        return {
            "messages": [AIMessage(content=response.content)],
        }

    # Routing - 복잡도 결정에 따른 분기 함수
    def route_by_complexity(state: SupervisorState) -> Literal["simple_response", "planning"]:
        """
        routing_node가 채운 state["route"]에 따라 처리 경로 결정.

        - route == "simple"  → simple_response (LLM 1회 직접 응답)
        - route == "complex" → planning (multi-agent flow)
        """
        return "simple_response" if state.get("route") == "simple" else "planning"

    # Routing - Planning 후 분기 함수 
    def route_after_planning(state: SupervisorState) -> Literal["execute_research", "execute_analysis", "execute_writing"]:
        """
        Planning 결과에 따라 첫 task 실행 경로 결정.
        
        - research task가 있으면 research부터
        - research 없이 analysis만 있으면 analysis부터 (드문 경우)
        - 둘 다 없으면 writing으로 (단순 응답의 경우, 이론적)
        
        실제로는 거의 항상 research → analysis → writing 순서.
        """
        tasks = state.get("tasks", [])
        has_research = any(t["agent"] == "research" for t in tasks)
        has_analysis = any(t["agent"] == "analysis" for t in tasks)
        
        if has_research:
            return "execute_research"
        if has_analysis:
            return "execute_analysis"
        return "execute_writing"

    # Routing - Research 완료 후 분기 함수 
    def route_after_research(state: SupervisorState) -> Literal["execute_analysis", "execute_writing"]:
        """
        Research 완료 후 다음 단계 결정.
        
        - Analysis task가 있으면 → execute_analysis
        - 없으면 → execute_writing (기존과 동일한 흐름)
        """
        tasks = state.get("tasks", [])
        has_analysis = any(t["agent"] == "analysis" for t in tasks)
        
        return "execute_analysis" if has_analysis else "execute_writing"

    # Validator - 검증 결과에 따른 분기 함수
    def route_after_validation(state: SupervisorState) -> Literal["retry_writing", "finalize"]:
        """
        Validator 결과에 따라 다음 step 결정.
    
        - is_acceptable=True → finalize (응답 확정)
        - is_acceptable=False AND writing_attempts < 2 → retry_writing (재시도)
        - is_acceptable=False AND writing_attempts >= 2 → finalize (재시도 한계, graceful degradation)
        """
        validation = state.get("validation_result", {})
        is_acceptable = validation.get("is_acceptable", True)
        attempts = state.get("writing_attempts", 0)
        validation_rounds = state.get("validation_attempts", 0)

        MAX_WRITING_ATTEMPTS = 2   # 최초 1회 + 재시도 1회
        MAX_VALIDATION_ROUNDS = 3  # 방어적 hard stop: 카운터가 깨져도 무한 루프 차단

        if is_acceptable:
            return "finalize"

        # 방어적 안전장치: validator가 과도하게 반복되면 무조건 종료
        if validation_rounds >= MAX_VALIDATION_ROUNDS:
            return "finalize"

        if attempts >= MAX_WRITING_ATTEMPTS:
            # 재시도 한계 도달, graceful degradation
            return "finalize"

        # Validation 실패 + 재시도 여유 있음 → 재시도
        return "retry_writing"

    # Routing - Replan 결과에 따른 분기 함수
    def route_after_replan(state: SupervisorState) -> Literal["replan", "execute_analysis", "execute_writing"]:
        """
        Replan 평가 결과에 따라 다음 step 결정.

        - is_sufficient=True → 다음 단계 (analysis 또는 writing)
        - is_sufficient=False AND replan_rounds <= MAX → replan (Supervisor가 plan 재수립)
        - 재계획 한계 도달 → 다음 단계 (graceful degradation)
        """
        replan = state.get("replan_decision", {})
        is_sufficient = replan.get("is_sufficient", True)
        rounds = state.get("replan_rounds", 0)

        MAX_REPLAN_ROUNDS = 1  # 초기 + 1회 추가 = 최대 2번 research 단계

        # 충분하거나 재계획 한계 도달 → 다음 단계로 (graceful degradation)
        if is_sufficient or rounds > MAX_REPLAN_ROUNDS:
            tasks = state.get("tasks", [])
            has_analysis = any(t["agent"] == "analysis" for t in tasks)
            return "execute_analysis" if has_analysis else "execute_writing"

        # Plan 재수립 단계로 분기
        return "replan"


    # Supervisor의 Planning 함수
    async def planning_node(state: SupervisorState) -> dict:
        """
        Supervisor: 사용자 요청을 받아 plan을 수립하고 task로 분해.
        """
        user_msg = state["messages"][-1].content
        
        planning_prompt = f"""\
사용자 요청을 분석하여 진행 계획(plan), analysis 필요 여부(needs_analysis), task 목록(tasks)을 작성하세요.

사용자 요청: {user_msg}

[Agent 종류]
- "research": MCP tool로 정보 검색 (운영 매뉴얼, ticket, 시스템 상태 등)
- "analysis": 수집된 정보를 분석/가공 (패턴 식별, 비교/분류, 통합, 우선순위화, 근본원인)
- "writing": 최종 응답을 사용자 친화적으로 작성 (항상 마지막에 1개)

[needs_analysis 판단 기준]
- False (analysis 불필요): 검색 결과를 필터/나열/요약해 거의 그대로 전달하면 되는 단순 요청
  예) "critical 등급 incident ticket을 모두 검색해 목록으로 알려주세요" → research → writing
  예) "DB 백업 절차 문서를 찾아 알려주세요" → research → writing
- True (analysis 필요): 수집 정보에 대한 가공·추론이 필요한 요청
  예) "최근 incident 3건의 공통 근본원인을 비교 분석해 주세요" → research → analysis → writing
  예) "운영 매뉴얼과 과거 incident를 종합해 DB 다운 대응 가이드를 만드세요" → research → analysis → writing

[Task 설계 규칙]
- needs_analysis=False이면 tasks에 analysis를 절대 포함하지 마세요.
- needs_analysis=True이면 research 다음, writing 이전에 analysis를 1개 배치하세요.
- writing task는 항상 마지막에 정확히 1개.
"""
        decision = await fast_llm.with_structured_output(PlanDecision).ainvoke([
            SystemMessage(content="You are a planning supervisor."),
            HumanMessage(content=planning_prompt),
        ])

        # needs_analysis를 권위 있는 게이트로 사용:
        # 모델이 규칙을 어기고 analysis task를 끼워 넣어도, needs_analysis=False면 제거.
        spec_tasks = decision.tasks
        if not decision.needs_analysis:
            spec_tasks = [t for t in spec_tasks if t.agent != "analysis"]

        # task에 id와 status 추가
        tasks = [
            {
                "id": f"task_{i+1}",
                "description": t.description,
                "agent": t.agent,
                "status": "pending",
                "result": None,
            }
            for i, t in enumerate(spec_tasks)
        ]

        return {
            "plan": decision.plan,
            "tasks": tasks,
            "current_task_index": 0,
        }
    
    # Task 병렬 실행 -- Research 
    async def execute_all_research_tasks_node(state: SupervisorState) -> dict:
        """
        Research task들을 병렬 실행.
    
        Cost/Latency 최적화:
        - 기존 순차 실행 → 병렬 실행
        - Research task들은 서로 독립적이므로 병렬 가능
        - Writing task는 모든 research 결과 필요하므로 별도 실행

        Dynamic Planning 위한 변경 :
        - pending 상태의 research task만 실행
        - 이미 completed인 task는 건너뜀 (replan으로 추가된 task만 새로 실행)
        """
        tasks = state["tasks"].copy()
    
        # pending 상태의 research task indices만 추출
        research_indices = [
            i for i, t in enumerate(tasks) if t["agent"] == "research" and t.get("status") == "pending"
        ]

        if not research_indices:
            # 새로 실행할 task 없음 (이미 모두 완료된 경우)
            return {
                "tasks": tasks,
                "current_task_index" : state.get("current_task_index", 0) 
            }
    
        # 각 research task를 in_progress로 표시
        for i in research_indices:
            tasks[i] = {**tasks[i], "status": "in_progress"}
    
        # 병렬 실행
        async def run_single_task(idx: int) -> tuple[int, dict]:
            """단일 task 실행. 결과를 (index, updated_task) 형태로 반환."""
            task = tasks[idx]
            try:
                result = await research_agent.ainvoke(
                    {"messages": [HumanMessage(content=task["description"])]},
                )
                result_text = result["messages"][-1].content
                return idx, {
                    **task,
                    "status": "completed",
                    "result": result_text,
                }
            except ToolError as e:
                return idx, {
                    **task,
                    "status": "failed",
                    "result": None,
                    "error_code": e.error.code,
                    "error_message": e.error.user_message or "도구 사용 중 오류 발생",
                }
            except Exception as e:
                return idx, {
                    **task,
                    "status": "failed",
                    "result": None,
                    "error_code": "UNEXPECTED_ERROR",
                    "error_message": "예상치 못한 오류가 발생했습니다",
                }
    
        # asyncio.gather로 병렬 실행
        results = await asyncio.gather(*[
            run_single_task(idx) for idx in research_indices
        ])
    
        # 결과 반영
        for idx, updated_task in results:
            tasks[idx] = updated_task
    
        # current_task_index를 모든 research task가 끝난 다음으로 점프
        new_index = max(research_indices) + 1 if research_indices else 0
    
        return {
            "tasks": tasks,
            "current_task_index": new_index,
        }

    # Dynamic Planning - Replan Check 
    async def replan_check_node(state: SupervisorState) -> dict:
        """
        Research 결과를 평가하여 추가 task가 필요한지 판단.
        
        Dynamic Planning :
        - 현재까지의 research 결과를 종합
        - Supervisor LLM이 사용자 의도와 비교
        - 충분/부족 결정 + 부족 시 추가 task 제안
        """
        user_msg = ""
        for msg in state["messages"]:
            if hasattr(msg, "type") and msg.type == "human":
                user_msg = msg.content
                break
        
        plan = state.get("plan", "")
        tasks = state["tasks"].copy()
        
        # 완료된 research task들의 결과 종합
        completed_research = [
            t for t in tasks
            if t["agent"] == "research" 
            and t.get("status") == "completed"
            and t.get("result")
        ]
        
        research_summary = "\n\n".join([
            f"- Task: {t['description']}\n  결과: {t['result'][:1000]}{'...' if len(t.get('result', '')) > 1000 else ''}"
            for t in completed_research
        ])

        # 결정적 단락은 '판단 자체가 무의미한' degenerate 케이스에만 한정.
        # research 결과의 '의미적 충분성'은 결정론으로 알 수 없으므로 LLM이 판단.
        research_tasks = [t for t in tasks if t["agent"] == "research"]
        failed_research = [t for t in research_tasks if t.get("status") == "failed"]
        
        if not research_tasks:
            # 평가할 research task 자체가 없음 → 다음 단계로 진행
            return {
                "tasks": tasks,
                "replan_rounds": state.get("replan_rounds", 0) + 1,
                "replan_decision": {
                    "is_sufficient": True,
                    "reasoning": "평가할 research task가 없어 추가 검색 불필요.",
                    "added_task_count": 0,
                },
            }

        # 실패한 research가 있으면 LLM 판단의 신호로 제공
        failed_research_context = ""
        if failed_research:
            failed_research_context = "\n\n[실패한 Research]\n" + "\n".join(
                f"- {t['description']}: {t.get('error_message', '사유 미상')}"
                for t in failed_research
            )
        
        # 이미 실행된 task들의 description (중복 방지용)
        existing_task_descriptions = [t["description"] for t in tasks]
        
        replan_prompt = f"""\
Research 결과가 사용자 질문에 답하기에 충분한지 판단하세요.

[사용자 질문]
{user_msg}

[수립된 Plan]
{plan}

[현재까지 실행된 Task]
{chr(10).join(f"- {desc}" for desc in existing_task_descriptions)}

[Research 결과 종합]
{research_summary}{failed_research_context}

[Research의 책임 — 핵심 전제]
Research는 'raw material(원자료)'을 수집하는 단계입니다.
사용자가 요청하는 가이드/요약/답변/보고서/분석/제안 등 **최종 산출물**은 이후 Writing/Analysis 단계가 만듭니다.
따라서 is_sufficient는 "raw material이 충분히 모였는가"만 봅니다. 최종 산출물이 결과에 들어있는지는 판단 기준이 아닙니다.

[판단 절차]
1. 사용자 질문에서 Research가 수집해야 할 'raw material 항목'만 추출하세요.
   (가이드/요약/답변/보고서/분석/제안 같은 합성·가공 산출물은 Research 항목에서 제외)
2. 각 raw material 항목이 위 Research 결과로 실제로 다뤄지는지 항목별로 확인하세요.
3. raw material 항목 중 하나라도 결과에서 다뤄지지 않으면 is_sufficient=False.
   모든 raw material 항목이 다뤄지면 is_sufficient=True.

[유의]
- 추가 Research(replan)는 지연·비용을 유발합니다. "더 자세할 수 있다 / 사례가 더 있을 수 있다"
  같은 한계적·미관상 사유로는 False로 판단하지 마세요. 구체적으로 요청된 raw material이 빠졌을 때만 False.
- 답변 분량·형식 제약(예: '50자 이내')은 Research 충분성과 무관합니다. 판단에서 제외하세요.
- "DB 다운 가이드", "incident 종합 보고서" 같은 최종 산출물 표현은 Writing이 합성할 것이므로
  Research 항목으로 카운트하지 마세요.
- 실패한 Research로 특정 raw material이 비었다면, 다른 키워드/source로 재시도할 가치가 있는지 고려하세요.

[예시]
- 질문 "운영 매뉴얼과 incident를 검색해 DB 다운 가이드를 만드세요" / 결과에 매뉴얼·incident 모두 존재
  → raw material = [매뉴얼, incident] ('가이드'는 writing의 산출물이라 제외).
    두 항목 모두 충족 → is_sufficient=True
- 질문 "장애 사례 3건을 비교 분석해 주세요" / 결과에 장애 사례 5건 존재
  → raw material = [장애 사례] ('비교 분석'은 analysis의 작업이라 제외).
    충족 → is_sufficient=True
- 질문 "DB 백업 절차와 복구 절차를 알려줘" / 결과에 백업 절차만 있고 복구 절차 없음
  → raw material = [백업 절차, 복구 절차]. '복구 절차' 누락 → is_sufficient=False
"""
        
        # replan 판단은 'research의 역할 vs writing의 산출물' 메타 추론이라 quality 모델 사용.
        # 호출 빈도는 complex 1회/요청으로 비용 영향 제한적.
        decision = await quality_llm.with_structured_output(ReplanDecision).ainvoke([
            SystemMessage(content="You are a planning evaluator who decides if more research is needed."),
            HumanMessage(content=replan_prompt),
        ])
        
        # 평가 결과만 반환. plan/tasks 갱신은 replan_node에서 수행.
        current_rounds = state.get("replan_rounds", 0)

        return {
            "replan_rounds": current_rounds + 1,
            "replan_decision": {
                "is_sufficient": decision.is_sufficient,
                "reasoning": decision.reasoning,
                "added_task_count": 0,  # replan_node가 실제로 추가하면 그쪽에서 갱신 
            },
        }

    # Supervisor의 Re-Planning 노드 (replan_check가 insufficient로 판단 시 실행)
    async def replan_node(state: SupervisorState) -> dict:
        """
        Supervisor가 plan을 재수립.

        - 직전 plan + 완료된 research 결과 + insufficient 사유를 종합
        - 갱신된 plan + 추가 research task를 생성
        - state['plan']을 갱신하고, 새 research task를 state['tasks']에 append
        """
        user_msg = ""
        for msg in state["messages"]:
            if hasattr(msg, "type") and msg.type == "human":
                user_msg = msg.content
                break

        previous_plan = state.get("plan", "")
        tasks = state["tasks"].copy()

        # 완료된 research 결과 요약
        completed_research = [
            t for t in tasks
            if t["agent"] == "research"
            and t.get("status") == "completed"
            and t.get("result")
        ]
        research_summary = "\n\n".join([
            f"- Task: {t['description']}\n  결과: {t['result'][:1000]}{'...' if len(t.get('result', '')) > 1000 else ''}"
            for t in completed_research
        ])

        # 중복 방지를 위한 기존 task description
        existing_task_descriptions = [t["description"] for t in tasks]

        insufficient_reason = state.get("replan_decision", {}).get("reasoning", "")

        replan_plan_prompt = f"""\
직전 plan을 보강하여 갱신된 plan과 추가 research task를 작성하세요.

[사용자 요청]
{user_msg}

[직전 Plan]
{previous_plan}

[완료된 Research 결과 요약]
{research_summary}

[기존 task description (중복 방지)]
{chr(10).join(f"- {desc}" for desc in existing_task_descriptions)}

[부족 판정 사유 (replan_check)]
{insufficient_reason}

[작성 지침]
- 새 plan은 직전 plan을 보강한 형태로 작성하세요.
  (이미 수집된 raw material은 다시 수집하지 말고, 부족한 부분만 명시적으로 보강)
- additional_research_tasks에는 추가로 필요한 research task만 포함하세요.
  (analysis/writing은 이후 단계에서 별도 처리되므로 포함 금지)
- 각 task는 기존 task description과 중복되지 않는 새 키워드 또는 새 source를 사용하세요.
"""

        decision = await quality_llm.with_structured_output(ReplanPlanDecision).ainvoke([
            SystemMessage(content="You are a re-planning supervisor who revises the plan based on partial research results."),
            HumanMessage(content=replan_plan_prompt),
        ])

        # 새 research task들을 기존 task 목록 끝에 append (완료된 task는 보존)
        new_tasks_added = []
        for spec in decision.additional_research_tasks:
            # 방어적 필터: research가 아닌 task는 무시
            if spec.agent != "research":
                continue
            new_task = {
                "id": f"task_{len(tasks) + len(new_tasks_added) + 1}",
                "description": spec.description,
                "agent": spec.agent,
                "status": "pending",
                "result": None,
            }
            tasks.append(new_task)
            new_tasks_added.append(new_task)

        return {
            "plan": decision.plan,  # plan 갱신
            "tasks": tasks,
            "replan_decision": {
                **state.get("replan_decision", {}),
                "added_task_count": len(new_tasks_added),
            },
        }

    # Task 병렬 실행 -- Writing (re-update)
    async def execute_writing_task_node(state: SupervisorState) -> dict:
        """
        Writing task 실행. Validator feedback이 있으면 재시도.
    
        - draft_response state에 응답 저장 (아직 사용자에게 노출 안 함)
        - validation_feedback이 있으면 재시도 시 context로 활용
        - writing_attempts 카운터 증가
        """
        tasks = state["tasks"].copy()

        # Writing task를 인덱스가 아닌 명시적 탐색으로 지정.
        # 재시도 재진입 시 current_task_index가 이미 전진해 있어도 동일 writing task를 재실행.
        writing_idx = next(
            (i for i, t in enumerate(tasks) if t["agent"] == "writing"),
            None,
        )

        if writing_idx is None:
            # Writing task 자체가 없는 경우만 통과 (재시도 재진입과 명확히 구분)
            return {"current_task_index": state["current_task_index"]}

        idx = writing_idx
        task = tasks[idx]
        tasks[idx] = {**task, "status": "in_progress"}

        # Research 결과 통합 (writing task 자신의 직전 거절 응답이 재투입되지 않도록 research만)
        previous_results = "\n\n".join([
            f"- {t['description']}\n  결과: {t['result']}"
            for t in tasks
            if t["agent"] == "research" and t.get("result") is not None and t.get("status") == "completed"
        ])
        failed_tasks = [t for t in tasks if t.get("status") == "failed"]
        failed_context = ""
        if failed_tasks:
            failed_context = "\n\n다음 task는 실패로 정보 수집 불가:\n" + "\n".join([
                f"- {t['description']}: {t.get('error_message', '알 수 없는 사유')}"
                for t in failed_tasks
            ])
        
        # 재시도 시 Validator feedback을 context에 포함 
        feedback = state.get("validation_feedback")
        feedback_context = ""
        if feedback:
            feedback_context = (
                f"\n\n[중요] 직전 응답이 다음 이유로 재작성이 필요합니다:\n{feedback}\n"
                f"위 피드백을 반영하여 응답을 개선하세요.\n"
            )

        task_context = (
            f"이전 task의 수집 결과:\n{previous_results}\n{failed_context}{feedback_context}\n\n"
            f"위 정보를 바탕으로: {task['description']}"
        )
    
        # 시도 횟수는 성공/실패와 무관하게 증가시켜야 종료 안전장치가 동작 (무한 루프 방지)
        current_attempts = state.get("writing_attempts", 0)

        try:
            result = await writing_agent.ainvoke(
                {"messages": [HumanMessage(content=task_context)]},
            )
            result_text = result["messages"][-1].content
            tasks[idx] = {**tasks[idx], "status": "completed", "result": result_text}

            # draft_response에 저장 (아직 사용자에게 노출 안 함)
            return {
                "tasks": tasks,
                "current_task_index": idx + 1,
                "draft_response": result_text,
                "writing_attempts": current_attempts + 1,
                "validation_feedback": None,  # feedback 사용 완료, 비움
            }

        except Exception as e:
            tasks[idx] = {
                **tasks[idx],
                "status": "failed",
                "result": None,
                "error_message": "응답 생성 중 오류가 발생했습니다",
            }

        return {
            "tasks": tasks,
            "current_task_index": idx + 1,
            "draft_response": None,
            "writing_attempts": current_attempts + 1,
            "validation_feedback": None,
        }

    # Task 실행 -- Analysis
    async def execute_analysis_tasks_node(state: SupervisorState) -> dict:
        """
        Analysis task들을 실행.
        
        - Research 결과를 context로 받음
        - 여러 analysis task가 있으면 병렬 실행 (Research와 같은 패턴)
        - Analysis 결과는 Writing이 활용
        """
        tasks = state["tasks"].copy()
        
        # Analysis task indices 추출
        analysis_indices = [
            i for i, t in enumerate(tasks) if t["agent"] == "analysis"
        ]
        
        # Analysis task가 없으면 통과
        if not analysis_indices:
            return {"tasks": tasks}
        
        # Research 결과 context 준비
        research_results = "\n\n".join([
            f"- {t['description']}\n  결과: {t['result']}"
            for t in tasks
            if t["agent"] == "research"
            and t.get("status") == "completed"
            and t.get("result")
        ])
        
        # 각 analysis task를 in_progress로 표시
        for i in analysis_indices:
            tasks[i] = {**tasks[i], "status": "in_progress"}
        
        # 병렬 실행
        async def run_single_analysis(idx: int) -> tuple[int, dict]:
            task = tasks[idx]
            
            analysis_context = (
                f"[Research 결과]\n{research_results}\n\n"
                f"[분석 task]\n{task['description']}\n\n"
                f"위 Research 결과를 바탕으로 분석 task를 수행하세요."
            )
            
            try:
                result = await analysis_agent.ainvoke(
                    {"messages": [HumanMessage(content=analysis_context)]},
                )
                result_text = result["messages"][-1].content
                return idx, {
                    **task,
                    "status": "completed",
                    "result": result_text,
                }
            except Exception as e:
                return idx, {
                    **task,
                    "status": "failed",
                    "result": None,
                    "error_message": "분석 중 오류가 발생했습니다",
                }
        
        results = await asyncio.gather(*[
            run_single_analysis(idx) for idx in analysis_indices
        ])
        
        for idx, updated_task in results:
            tasks[idx] = updated_task
        
        return {"tasks": tasks}

    # Validator 실행 
    async def validator_node(state: SupervisorState) -> dict:
        """
        Writing agent의 응답을 검증하는 sub-agent.
    
        - 응답 품질을 4가지 기준으로 평가
        - 품질 미달 시 재시도용 feedback 생성
        """
        user_question = ""
        for msg in state["messages"]:
            if hasattr(msg, "type") and msg.type == "human":
                user_question = msg.content
                break
    
        draft = state.get("draft_response", "")
        plan = state.get("plan", "")
        tasks = state.get("tasks", [])
    
        # Task 결과들 종합
        task_summary = "\n".join([
            f"- {t['description']} → {t.get('result', '실패')[:200] if t.get('result') else '실패'}"
            for t in tasks if t["agent"] == "research"
        ])
    
        validation_prompt = f"""\
다음 AI 응답을 평가하세요.

[사용자 질문]
{user_question}

[수립된 Plan]
{plan}

[수집된 정보 (Research 결과 요약)]
{task_summary}

[AI 응답 (검증 대상)]
{draft}

[평가 기준]
1. Relevance: 응답이 사용자 질문에 답하는가
2. Completeness: 수집된 정보(Research 결과)를 충분히 활용했는가
3. Clarity: 응답이 구조적이고 명확한가
4. Domain Appropriateness: ICT 운영 도메인의 전문성을 보이는가

[판단]
- 위 4가지 기준을 모두 충분히 만족하면 is_acceptable=True
- 하나라도 명확히 부족하면 is_acceptable=False
- is_acceptable=False인 경우 feedback에 구체적 개선 지시를 작성
  (예: "X에 대한 정보가 응답에 빠져 있음. 추가 필요" 또는 "응답 구조가 모호함. 단계별로 정리 필요")
"""
    
        result = await validator_llm.with_structured_output(ValidationResult).ainvoke([
            SystemMessage(content="You are a quality validator for AI agent responses."),
            HumanMessage(content=validation_prompt),
        ])
    
        return {
            "validation_result": {
                "is_acceptable": result.is_acceptable,
                "score": result.score,
                "reasoning": result.reasoning,
                "feedback": result.feedback,
            },
            "validation_feedback": result.feedback if not result.is_acceptable else None,
            "validation_attempts": state.get("validation_attempts", 0) + 1,
        }

    # 최종 응답 생성 -- Update
    async def finalize_node(state: SupervisorState) -> dict:
        """
        최종 응답을 사용자에게 반환: 
        - draft_response를 최종 응답으로 사용
        - Validation 실패 후 한계 도달한 경우 사용자에게 한계 안내 (graceful degradation)

        Graceful Degradation:
        - Writing task가 성공했다고 그 결과를 반환
        - Writing task도 실패했다면 partial result로 fallback 응답 생성 
        """
        draft = state.get("draft_response")
        validation = state.get("validation_result", {})
        attempts = state.get("writing_attempts", 0)
    
        if draft is None:
            # Writing 자체가 실패한 경우
            partial_results = [
                f"- {t['description']}: {t['result']}"
                for t in state["tasks"]
                if t.get("status") == "completed" and t.get("result") and t["agent"] == "research"
            ]
            if partial_results:
                final_response = (
                    "일부 정보 수집은 성공했으나 응답 생성에 어려움이 있었습니다. "
                    "수집된 정보를 그대로 전달합니다:\n\n" + "\n".join(partial_results)
                )
            else:
                final_response = (
                    "죄송합니다. 요청을 처리하는 중 여러 단계에서 문제가 발생했습니다. "
                    "잠시 후 다시 시도해 주세요."
                )
        elif not validation.get("is_acceptable", True) and attempts >= 2:
            # Validation 한계 도달 (graceful degradation)
            final_response = (
                draft +
                "\n\n---\n*응답을 두 차례 작성했으나 자체 품질 기준에 완전히 도달하지 못했습니다. "
                "필요하시면 추가 질문을 통해 더 자세한 정보를 요청해 주세요.*"
            )
        else:
            # 정상 경로: validation 통과
            final_response = draft
    
        return {
            "messages": [AIMessage(content=final_response)],
        }
    

    # Graph 구성
    workflow = StateGraph(SupervisorState)

    workflow.add_node("routing", routing_node)
    workflow.add_node("simple_response", simple_response_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("execute_research", execute_all_research_tasks_node)
    workflow.add_node("replan_check", replan_check_node)
    workflow.add_node("replan", replan_node)
    workflow.add_node("execute_writing", execute_writing_task_node)
    workflow.add_node("execute_analysis", execute_analysis_tasks_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("finalize", finalize_node)
    
    # Routing
    workflow.add_edge(START, "routing")
    workflow.add_conditional_edges(
        "routing",
        route_by_complexity,
        {
            "simple_response": "simple_response",
            "planning": "planning",
        }
    )
    workflow.add_edge("simple_response", END)  # Simple 경로는 바로 종료

    # Complex 
    workflow.add_conditional_edges(
        "planning",
        route_after_planning,
        {
            "execute_research": "execute_research",
            "execute_analysis": "execute_analysis",
            "execute_writing": "execute_writing",
        },
    )

    # Replan Check
    workflow.add_edge("execute_research", "replan_check")
    workflow.add_conditional_edges(
        "replan_check",
        route_after_replan,
        {
            "replan": "replan",                       # Plan 재수립
            "execute_analysis": "execute_analysis",
            "execute_writing": "execute_writing",
        }
    )
    workflow.add_edge("replan", "execute_research")   # 재수립 후 추가 research 실행
    workflow.add_edge("execute_analysis", "execute_writing")

    # Validation
    workflow.add_edge("execute_writing", "validator")
    workflow.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "retry_writing": "execute_writing",
            "finalize": "finalize",
        }
    )
    workflow.add_edge("finalize", END)
    
    # Checkpointer (in-memory)
    # checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)
