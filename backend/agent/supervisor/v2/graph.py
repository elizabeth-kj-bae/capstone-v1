"""Supervisor graph 구성.

build_supervisor_graph가 호출 시:
1. build_supervisor_deps()로 LLM·sub-agent 1회 생성
2. functools.partial로 각 node에 deps 주입
3. StateGraph로 workflow 구성 후 compile
"""

from functools import partial

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from . import nodes, routers
from .deps import build_supervisor_deps
from .state import SupervisorState


async def build_supervisor_graph(
    checkpointer: BaseCheckpointSaver,
):
    """Supervisor 기반 multi-agent graph 생성.

    Cost & Latency 최적화:
    - Planning: 빠르고 저렴한 모델 (단순 분류/구조화 task)
    - Writing:  고품질 모델 (정보 추출 + 응답 생성 품질 중요)

    Session 관리 강화:
    - checkpointer를 외부에서 주입 받음
    - Agent 코드는 checkpointer 구현체와 분리

    Routing:
    - Simple/Complex 분기로 단순 질문 즉시 응답

    Dynamic Planning:
    - Research 결과 평가 후 부족 시 plan 재수립

    Args:
        checkpointer: LangGraph checkpointer. lifespan에서 주입됨.

    Returns:
        Compiled LangGraph workflow.
    """
    deps = await build_supervisor_deps()

    workflow = StateGraph(SupervisorState)

    # ----- Node 등록 (deps 주입) -----
    workflow.add_node("routing", partial(nodes.routing_node, deps=deps))
    workflow.add_node(
        "simple_response", partial(nodes.simple_response_node, deps=deps)
    )
    workflow.add_node("planning", partial(nodes.planning_node, deps=deps))
    workflow.add_node(
        "execute_research",
        partial(nodes.execute_all_research_tasks_node, deps=deps),
    )
    workflow.add_node(
        "replan_check", partial(nodes.replan_check_node, deps=deps)
    )
    workflow.add_node("replan", partial(nodes.replan_node, deps=deps))
    workflow.add_node(
        "execute_writing",
        partial(nodes.execute_writing_task_node, deps=deps),
    )
    workflow.add_node(
        "execute_analysis",
        partial(nodes.execute_analysis_tasks_node, deps=deps),
    )
    workflow.add_node("validator", partial(nodes.validator_node, deps=deps))
    workflow.add_node("finalize", nodes.finalize_node)  # deps 불필요

    # ----- Routing (Simple vs Complex) -----
    workflow.add_edge(START, "routing")
    workflow.add_conditional_edges(
        "routing",
        routers.route_by_complexity,
        {
            "simple_response": "simple_response",
            "planning": "planning",
        },
    )
    workflow.add_edge("simple_response", END)

    # ----- Complex flow: Planning → Execute -----
    workflow.add_conditional_edges(
        "planning",
        routers.route_after_planning,
        {
            "execute_research": "execute_research",
            "execute_analysis": "execute_analysis",
            "execute_writing": "execute_writing",
        },
    )

    # ----- Dynamic Planning (Replan 사이클) -----
    workflow.add_edge("execute_research", "replan_check")
    workflow.add_conditional_edges(
        "replan_check",
        routers.route_after_replan,
        {
            "replan": "replan",
            "execute_analysis": "execute_analysis",
            "execute_writing": "execute_writing",
        },
    )
    workflow.add_edge("replan", "execute_research")
    workflow.add_edge("execute_analysis", "execute_writing")

    # ----- Validation 사이클 -----
    workflow.add_edge("execute_writing", "validator")
    workflow.add_conditional_edges(
        "validator",
        routers.route_after_validation,
        {
            "retry_writing": "execute_writing",
            "finalize": "finalize",
        },
    )
    workflow.add_edge("finalize", END)

    return workflow.compile(checkpointer=checkpointer)
