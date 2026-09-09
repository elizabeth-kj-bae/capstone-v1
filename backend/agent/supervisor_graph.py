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
from .mcp_client import get_mcp_tools


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
    
    # Task 실행 함수
    async def execute_task_node(state: SupervisorState) -> dict:
        """
        현재 task를 담당 sub-agent에게 위임하여 실행.
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
            # Writing agent는 이전 research 결과들을 context로 받음
            previous_results = "\n\n".join([
                f"- {t['description']}\n  결과: {t['result']}"
                for t in tasks if t["result"] is not None
            ])
            task_context = (
                f"이전 task의 수집 결과:\n{previous_results}\n\n"
                f"위 정보를 바탕으로: {task['description']}"
            )
            agent = writing_agent
        
        # Sub-agent 호출
        agent_input_message = task["description"] if task["agent"] == "research" else task_context
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=agent_input_message)]},
        )
        
        # task 완료 처리
        result_text = result["messages"][-1].content
        tasks[idx] = {**tasks[idx], "status": "completed", "result": result_text}
        
        return {
            "tasks": tasks,
            "current_task_index": idx + 1,
        }
    
    # 다음 단계 결정
    def should_continue(state: SupervisorState) -> Literal["execute", "finalize"]:
        if state["current_task_index"] < len(state["tasks"]):
            return "execute"
        return "finalize"
    
    # 최종 응답 생성
    async def finalize_node(state: SupervisorState) -> dict:
        """
        모든 task 완료 후 최종 응답을 사용자에게 반환.
        """
        # 마지막 task가 writing이라면 그 결과를 최종 응답으로 사용
        last_task = state["tasks"][-1]
        final_response = last_task["result"]
        
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
