"""Replan 노드 (Dynamic Planning).

Research 결과의 충분성을 평가하고, 부족 시 plan을 재수립.

- replan_check_node: Research 결과를 평가만 (is_sufficient + reasoning).
                     실제 task 갱신은 하지 않음.
- replan_node:       insufficient 판정 시 호출. Plan 갱신 + 추가 research
                     task를 state['tasks']에 append.

두 노드 분리 이유:
    평가(check)와 행동(replan)의 책임을 분리. replan_check만 수행하고
    충분하면 다음 단계로 직진. 부족할 때만 replan_node로 진입.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from config import RESEARCH_RESULT_TRUNCATE

from .. import prompts
from ..deps import SupervisorDeps
from ..schemas import ReplanDecision, ReplanPlanDecision
from ..state import SupervisorState


def _extract_user_message(state: SupervisorState) -> str:
    """state 메시지 이력에서 최초의 사용자 질문을 추출.

    Validator/Replan 재시도 경로에서도 원본 질문을 참조해야 하므로,
    마지막 메시지가 아닌 최초 HumanMessage를 찾는다.
    """
    for msg in state["messages"]:
        if hasattr(msg, "type") and msg.type == "human":
            return msg.content
    return ""


def _summarize_research(tasks: list[dict]) -> str:
    """완료된 research task의 결과를 요약 형태로 결합.

    각 결과는 RESEARCH_RESULT_TRUNCATE 길이로 잘라 LLM prompt token 누적 방지.
    """
    completed = [
        t
        for t in tasks
        if t["agent"] == "research"
        and t.get("status") == "completed"
        and t.get("result")
    ]
    return "\n\n".join(
        [
            (
                f"- Task: {t['description']}\n"
                f"  결과: {t['result'][:RESEARCH_RESULT_TRUNCATE]}"
                f"{'...' if len(t.get('result', '')) > RESEARCH_RESULT_TRUNCATE else ''}"
            )
            for t in completed
        ]
    )


async def replan_check_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """Research 결과를 평가하여 추가 task가 필요한지 판단.

    Dynamic Planning:
        - 현재까지의 research 결과를 종합
        - Supervisor LLM이 사용자 의도와 비교
        - 충분(is_sufficient=True) / 부족(False) 결정

    평가 전용 노드:
        실제 plan/tasks 갱신은 replan_node가 수행한다. 본 노드는
        is_sufficient + reasoning만 결정하고 replan_rounds 카운터를 증가.

    Degenerate case:
        research task 자체가 없으면 즉시 다음 단계로 진행
        (LLM 호출 없이 short-circuit).
    """
    user_msg = _extract_user_message(state)
    plan = state.get("plan", "")
    tasks = state["tasks"].copy()

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

    research_summary = _summarize_research(tasks)

    # 실패한 research가 있으면 LLM 판단의 신호로 제공
    failed_research_context = ""
    if failed_research:
        failed_research_context = "\n\n[실패한 Research]\n" + "\n".join(
            f"- {t['description']}: {t.get('error_message', '사유 미상')}"
            for t in failed_research
        )

    existing_tasks = "\n".join(f"- {t['description']}" for t in tasks)

    replan_prompt = prompts.REPLAN_CHECK_PROMPT_TEMPLATE.format(
        user_msg=user_msg,
        plan=plan,
        existing_tasks=existing_tasks,
        research_summary=research_summary,
        failed_research_context=failed_research_context,
    )

    # replan 판단은 'research의 역할 vs writing의 산출물' 메타 추론이라
    # quality 모델 사용. 호출 빈도는 complex 1회/요청으로 비용 영향 제한적.
    decision = await deps.quality_llm.with_structured_output(
        ReplanDecision
    ).ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a planning evaluator who decides if more "
                    "research is needed."
                )
            ),
            HumanMessage(content=replan_prompt),
        ]
    )

    return {
        "replan_rounds": state.get("replan_rounds", 0) + 1,
        "replan_decision": {
            "is_sufficient": decision.is_sufficient,
            "reasoning": decision.reasoning,
            "added_task_count": 0,  # replan_node가 실제 추가 시 갱신
        },
    }


async def replan_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """Supervisor가 plan을 재수립.

    insufficient 판정 후 호출되어:
        - 직전 plan + 완료된 research 결과 + insufficient 사유를 종합
        - 갱신된 plan + 추가 research task를 생성
        - state['plan']을 갱신하고, 새 research task를 append
        - replan_decision의 added_task_count를 실제 추가 갯수로 갱신

    방어적 필터:
        LLM이 additional_research_tasks에 analysis/writing을 끼워 넣을
        가능성에 대비. agent != 'research'인 spec은 무시한다.
    """
    user_msg = _extract_user_message(state)
    previous_plan = state.get("plan", "")
    tasks = state["tasks"].copy()

    research_summary = _summarize_research(tasks)
    existing_tasks = "\n".join(f"- {t['description']}" for t in tasks)
    insufficient_reason = state.get("replan_decision", {}).get("reasoning", "")

    replan_plan_prompt = prompts.REPLAN_PLAN_PROMPT_TEMPLATE.format(
        user_msg=user_msg,
        previous_plan=previous_plan,
        research_summary=research_summary,
        existing_tasks=existing_tasks,
        insufficient_reason=insufficient_reason,
    )

    decision = await deps.quality_llm.with_structured_output(
        ReplanPlanDecision
    ).ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a re-planning supervisor who revises the plan "
                    "based on partial research results."
                )
            ),
            HumanMessage(content=replan_plan_prompt),
        ]
    )

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
        "plan": decision.plan,
        "tasks": tasks,
        "replan_decision": {
            **state.get("replan_decision", {}),
            "added_task_count": len(new_tasks_added),
        },
    }
