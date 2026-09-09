"""Writing 노드.

Research/Analysis 결과를 받아 최종 응답을 작성하는 노드.

- execute_writing_task_node: Writing task 실행. Validator feedback이
  있으면 feedback을 context에 포함하여 재시도. draft_response state에
  응답 저장 (validator가 검증할 대상).

재시도 흐름:
    1차: writing → validator → 품질 미달 → validation_feedback 생성
    2차: writing(feedback 반영) → validator → ...
    한계 도달 시 finalize에서 graceful degradation
"""

from langchain_core.messages import HumanMessage

from ..deps import SupervisorDeps
from ..state import SupervisorState


async def execute_writing_task_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """Writing task 실행. Validator feedback이 있으면 재시도.

    Index 탐색 전략:
        next()로 writing task를 명시적으로 탐색. current_task_index를
        쓰지 않는 이유는 validator → writing 재진입 시 index가 이미
        다음 task로 전진해 있어도 동일 writing task를 재실행해야 하기 때문.

    Context 구성:
        - Research 결과 (completed만)
        - Failed task context (graceful degradation 정보)
        - Validation feedback (재시도 시)

    카운터 증가 규칙:
        writing_attempts는 성공/실패와 무관하게 증가. 무한 루프 방지를
        위한 종료 안전장치(route_after_validation의 MAX_WRITING_ATTEMPTS)
        가 동작하도록 보장.

    Returns:
        tasks: 갱신된 task 목록
        current_task_index: idx + 1
        draft_response: 생성된 응답 (실패 시 None) — validator가 검증할 대상
        writing_attempts: +1
        validation_feedback: None (사용 완료, 비움)
    """
    tasks = state["tasks"].copy()

    # Writing task를 명시적 탐색으로 지정.
    # 재시도 재진입 시 current_task_index가 이미 전진해 있어도
    # 동일 writing task를 재실행.
    writing_idx = next(
        (i for i, t in enumerate(tasks) if t["agent"] == "writing"),
        None,
    )

    if writing_idx is None:
        # Writing task 자체가 없는 경우 (재시도 재진입과 명확히 구분)
        return {"current_task_index": state["current_task_index"]}

    idx = writing_idx
    task = tasks[idx]
    tasks[idx] = {**task, "status": "in_progress"}

    # Research 결과 통합 (writing 자신의 직전 거절 응답이 재투입되지 않도록
    # research만 포함)
    previous_results = "\n\n".join(
        [
            f"- {t['description']}\n  결과: {t['result']}"
            for t in tasks
            if t["agent"] == "research"
            and t.get("result") is not None
            and t.get("status") == "completed"
        ]
    )

    # 실패 task 정보 (graceful degradation 위해 writing에게 알림)
    failed_tasks = [t for t in tasks if t.get("status") == "failed"]
    failed_context = ""
    if failed_tasks:
        failed_context = "\n\n다음 task는 실패로 정보 수집 불가:\n" + "\n".join(
            [
                f"- {t['description']}: {t.get('error_message', '알 수 없는 사유')}"
                for t in failed_tasks
            ]
        )

    # 재시도 시 Validator feedback을 context에 포함
    feedback = state.get("validation_feedback")
    feedback_context = ""
    if feedback:
        feedback_context = (
            f"\n\n[중요] 직전 응답이 다음 이유로 재작성이 필요합니다:\n"
            f"{feedback}\n위 피드백을 반영하여 응답을 개선하세요.\n"
        )

    task_context = (
        f"이전 task의 수집 결과:\n{previous_results}\n"
        f"{failed_context}{feedback_context}\n\n"
        f"위 정보를 바탕으로: {task['description']}"
    )

    # writing_attempts는 성공/실패 무관 증가 (무한 루프 방지 안전장치 동작)
    current_attempts = state.get("writing_attempts", 0)

    try:
        result = await deps.writing_agent.ainvoke(
            {"messages": [HumanMessage(content=task_context)]},
        )
        result_text = result["messages"][-1].content
        tasks[idx] = {
            **tasks[idx],
            "status": "completed",
            "result": result_text,
        }

        # draft_response에 저장 (validator가 검증할 대상, 사용자에 아직 노출 안 함)
        return {
            "tasks": tasks,
            "current_task_index": idx + 1,
            "draft_response": result_text,
            "writing_attempts": current_attempts + 1,
            "validation_feedback": None,  # feedback 사용 완료, 비움
        }

    except Exception:
        tasks[idx] = {
            **tasks[idx],
            "status": "failed",
            "result": None,
            "error_message": "응답 생성 중 오류가 발생했습니다",
        }

    # 실패 경로: except 블록 종료 후 fall-through.
    # draft_response=None으로 finalize에서 graceful degradation 처리.
    return {
        "tasks": tasks,
        "current_task_index": idx + 1,
        "draft_response": None,
        "writing_attempts": current_attempts + 1,
        "validation_feedback": None,
    }
