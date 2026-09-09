"""Research 노드.

Research task들을 병렬 실행하는 노드.

- execute_all_research_tasks_node: pending 상태의 research task들을
  asyncio.gather로 병렬 호출. ToolError와 기타 예외를 분류하여 task의
  status를 'completed' 또는 'failed'로 갱신.

Dynamic Planning 호환:
    pending 상태의 task만 실행하므로, replan_node가 추가한 새 task만
    이번 호출에서 실행된다. 이미 completed인 task는 건너뜀.
"""

import asyncio

from langchain_core.messages import HumanMessage

from schemas.error import ToolError

from ..deps import SupervisorDeps
from ..state import SupervisorState


async def execute_all_research_tasks_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """Research task들을 병렬 실행.

    Cost/Latency 최적화:
        - 순차 실행 → 병렬 실행 (asyncio.gather)
        - Research task들은 서로 독립적이라 병렬 가능
        - Writing task는 모든 research 결과 필요하므로 별도 실행

    Dynamic Planning 호환:
        - pending 상태의 research task만 실행
        - 이미 completed인 task는 건너뜀 (replan으로 추가된 task만 신규 실행)

    Error Handling:
        - ToolError: error_code와 user_message를 task에 기록
        - 그 외 Exception: UNEXPECTED_ERROR로 분류

    Returns:
        tasks: 갱신된 task 목록 (status: completed/failed)
        current_task_index: 모든 research task 이후 위치로 점프
    """
    tasks = state["tasks"].copy()

    # pending 상태의 research task indices 추출
    research_indices = [
        i
        for i, t in enumerate(tasks)
        if t["agent"] == "research" and t.get("status") == "pending"
    ]

    # v1 버그 fix: 변수명 typo (`research_agent` → `research_indices`)
    if not research_indices:
        # 새로 실행할 task 없음 (이미 모두 완료된 경우)
        return {
            "tasks": tasks,
            "current_task_index": state.get("current_task_index", 0),
        }

    # 각 research task를 in_progress로 표시
    for i in research_indices:
        tasks[i] = {**tasks[i], "status": "in_progress"}

    async def run_single_task(idx: int) -> tuple[int, dict]:
        """단일 task 실행. (index, updated_task) 반환."""
        task = tasks[idx]
        try:
            result = await deps.research_agent.ainvoke(
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
        except Exception:
            return idx, {
                **task,
                "status": "failed",
                "result": None,
                "error_code": "UNEXPECTED_ERROR",
                "error_message": "예상치 못한 오류가 발생했습니다",
            }

    # asyncio.gather로 병렬 실행
    results = await asyncio.gather(
        *[run_single_task(idx) for idx in research_indices]
    )

    # 결과 반영
    for idx, updated_task in results:
        tasks[idx] = updated_task

    # current_task_index를 모든 research task가 끝난 다음으로 점프
    new_index = max(research_indices) + 1

    return {
        "tasks": tasks,
        "current_task_index": new_index,
    }
