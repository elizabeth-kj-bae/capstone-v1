"""
Supervisor 패턴 기반 Multi-agent Graph.
"""
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI  
from langchain.agents import create_agent
from ...mcp_client import get_mcp_tools
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
    plan: str
    tasks: list[dict]  # [{id, description, agent, status, result}, ...]
    current_task_index: int


async def build_supervisor_graph():
    """
    Supervisor 기반 multi-agent graph 생성.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # Sub-agent 1: Research Agent (MCP tools 사용)
    mcp_tools = await get_mcp_tools()
    research_agent = create_agent(
        model=llm,
        tools=mcp_tools,
        system_prompt=(
            "당신은 Research Agent입니다. "
            "주어진 task에 대해 적절한 tool을 호출하여 정보를 수집하세요. "
            "수집된 정보를 명확하게 요약하여 반환하세요."
        ),
    )
    
    # Sub-agent 2: Writing Agent (LLM만)
    writing_agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=(
            "당신은 Writing Agent입니다. "
            "Research Agent가 수집한 정보를 받아 사용자가 이해하기 쉬운 형태로 "
            "통합된 답변을 작성하세요."
        ),
    )
    
    # Supervisor의 Planning 함수
    async def planning_node(state: SupervisorState) -> dict:
        """
        Supervisor: 사용자 요청을 받아 plan을 수립하고 task로 분해.
        """
        user_msg = state["messages"][-1].content
        
        planning_prompt = f"""\
사용자 요청을 분석하여 다음 두 가지를 작성하세요.

사용자 요청: {user_msg}

1. plan: 전체 진행 계획 (자연어 2-3문장)
2. tasks: 실행할 task 목록 (각 task는 어느 sub-agent가 담당하는지 명시)
   - 가능한 agent: "research" (정보 검색), "writing" (응답 작성)

다음 JSON 형식으로 응답:
{{
  "plan": "...",
  "tasks": [
    {{"description": "...", "agent": "research"}},
    {{"description": "...", "agent": "writing"}}
  ]
}}
"""
        response = await llm.ainvoke([
            SystemMessage(content="You are a planning supervisor."),
            HumanMessage(content=planning_prompt),
        ])
        
        # JSON 파싱 (간단화 — production에서는 structured output 사용 권장)
        import json
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        parsed = json.loads(json_match.group())
        
        # task에 id와 status 추가
        tasks = [
            {
                "id": f"task_{i+1}",
                "description": t["description"],
                "agent": t["agent"],
                "status": "pending",
                "result": None,
            }
            for i, t in enumerate(parsed["tasks"])
        ]
        
        return {
            "plan": parsed["plan"],
            "tasks": tasks,
            "current_task_index": 0,
        }
    
    # Task 실행 함수 -- Update 
    async def execute_task_node(state: SupervisorState) -> dict:
        """
        현재 task를 담당 sub-agent에게 위임하여 실행.

        Graceful Degradation 적용 : 
        - Tool 실패 시 task를 'failed' 상태로 표시 
        - 다음 task로 계속 진행 (전체 실패 X)
        - 최종 응답 생성 시 failed task 정보를 Writing agent에게 전달 
        """
        idx = state["current_task_index"]
        task = state["tasks"][idx]
        
        # task 상태를 in_progress로 변경
        tasks = state["tasks"].copy()
        tasks[idx] = {**task, "status": "in_progress"}
        
        # 적절한 sub-agent 선택
        if task["agent"] == "research":
            agent = research_agent
        elif task["agent"] == "writing":
            previous_results = "\n\n".join([
                f"- {t['description']}\n  결과: {t['result']}"
                for t in tasks if t.get("result") is not None and t.get("status") == "completed"
            ])
            failed_tasks = [t for t in tasks if t.get("status") == "failed"]
            failed_context = ""
            if failed_tasks:
                failed_context = "\n\n다음 task는 실패로 정보 수집 불가:\n" + "\n".join([
                    f"- {t['description']}: {t.get('error_message', '알 수 없는 사유')}"
                    for t in failed_tasks
                ])
            task_context = (
                f"이전 task의 수집 결과:\n{previous_results}\n{failed_context}\n\n"
                f"위 정보(완성 정보 + 실패 정보)를 바탕으로 사용자에게 가치 있는 답변을 제공: "
                f"{task['description']}"
            )
            agent = writing_agent
        
        # Sub-agent 호출 — Graceful Degradation 적용
        agent_input_message = task["description"] if task["agent"] == "research" else task_context

        try:
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=agent_input_message)]},
            )
            # 성공 — task 완료 처리
            result_text = result["messages"][-1].content
            tasks[idx] = {**tasks[idx], "status": "completed", "result": result_text}
        
        except ToolError as e:
            # Tool 실패 — 본 task만 실패로 표시, 다음 task로 계속 진행
            tasks[idx] = {
                **tasks[idx],
                "status": "failed",
                "result": None,
                "error_code": e.error.code,
                "error_message": e.error.user_message or "도구 사용 중 오류 발생",
            }
            # Error 처리 핵심: 실패해도 전체 graph는 계속 진행
        
        except Exception as e:
            # 예상치 못한 error — orchestration error로 변환
            tasks[idx] = {
                **tasks[idx],
                "status": "failed",
                "result": None,
                "error_code": "UNEXPECTED_ERROR",
                "error_message": "예상치 못한 오류가 발생했습니다",
            }
    
        return {
            "tasks": tasks,
            "current_task_index": idx + 1,
        }
    
    # 다음 단계 결정
    def should_continue(state: SupervisorState) -> Literal["execute", "finalize"]:
        if state["current_task_index"] < len(state["tasks"]):
            return "execute"
        return "finalize"
    
    # 최종 응답 생성 -- Update
    async def finalize_node(state: SupervisorState) -> dict:
        """
        모든 task 완료 후 최종 응답을 사용자에게 반환.

        Graceful Degradation:
        - Writing task가 성공했다고 그 결과를 반환
        - Writing task도 실패했다면 partial result로 fallback 응답 생성 
        """
        last_task = state["tasks"][-1]

        if last_task.get("status") == "completed" and last_task.get("result"):
            # 정상 path
            final_response = last_task["result"]
        else:
            # Fallback: writing task도 실패한 경우
            # 수집된 partial result만으로 단순 응답 생성
            partial_results = [
                f"- {t['description']}: {t['result']}"
                for t in state["tasks"]
                if t.get("status") == "completed" and t.get("result")
            ]
            failed_count = sum(1 for t in state["tasks"] if t.get("status") == "failed")
        
            if partial_results:
                final_response = (
                    "일부 정보 수집은 성공했으나 응답 생성에 어려움이 있었습니다. "
                    "수집된 정보를 그대로 전달합니다:\n\n" + "\n".join(partial_results) +
                    f"\n\n(전체 {len(state['tasks'])} 작업 중 {failed_count}개 실패)"
                )
            else:
                final_response = (
                    "죄송합니다. 요청을 처리하는 중 여러 단계에서 문제가 발생했습니다. "
                    "잠시 후 다시 시도해 주세요."
                )
    
        return {
            "messages": [AIMessage(content=final_response)],
        }
    
    # Graph 구성
    workflow = StateGraph(SupervisorState)
    workflow.add_node("planning", planning_node)
    workflow.add_node("execute", execute_task_node)
    workflow.add_node("finalize", finalize_node)
    
    workflow.add_edge(START, "planning")
    workflow.add_edge("planning", "execute")
    workflow.add_conditional_edges(
        "execute",
        should_continue,
        {"execute": "execute", "finalize": "finalize"},
    )
    workflow.add_edge("finalize", END)
    
    # Checkpointer (in-memory, Day 1과 동일)
    checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)
