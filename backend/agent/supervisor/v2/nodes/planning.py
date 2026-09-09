"""Planning 노드.

사용자 요청을 받아 plan을 수립하고 task로 분해.

- planning_node: Supervisor의 의사결정. Structured output(PlanDecision)
  으로 plan + needs_analysis + tasks를 한 번에 생성.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from .. import prompts
from ..deps import SupervisorDeps
from ..schemas import PlanDecision
from ..state import SupervisorState


async def planning_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """Supervisor: 사용자 요청을 받아 plan을 수립하고 task로 분해.

    needs_analysis 권위 게이트:
        LLM이 규칙을 어기고 analysis task를 끼워 넣어도, decision의
        needs_analysis=False이면 후처리에서 analysis task를 제거한다.
        Plan과 task list의 정합성 보장.

    Returns:
        plan: 자연어 진행 계획
        tasks: id/status/result가 추가된 dict 목록
        current_task_index: 0으로 초기화
    """
    user_msg = state["messages"][-1].content
    planning_prompt = prompts.PLANNING_PROMPT_TEMPLATE.format(user_msg=user_msg)

    decision = await deps.fast_llm.with_structured_output(
        PlanDecision
    ).ainvoke(
        [
            SystemMessage(content="You are a planning supervisor."),
            HumanMessage(content=planning_prompt),
        ]
    )

    # needs_analysis를 권위 있는 게이트로 사용:
    # 모델이 규칙을 어기고 analysis task를 끼워 넣어도 제거.
    spec_tasks = decision.tasks
    if not decision.needs_analysis:
        spec_tasks = [t for t in spec_tasks if t.agent != "analysis"]

    # task에 id와 status 추가 (state.py의 Tasks 항목 구조와 정합)
    tasks = [
        {
            "id": f"task_{i + 1}",
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
