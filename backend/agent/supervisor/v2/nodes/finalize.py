"""Finalize 노드.

최종 응답을 사용자에게 반환하는 종료 노드.

- finalize_node: draft_response를 최종 응답으로 사용. 실패 또는 validation
                 한계 도달 시 graceful degradation 처리.

deps 불필요:
    LLM 호출 없이 state 기반으로 응답 텍스트만 결정. 
"""

from langchain_core.messages import AIMessage

from config import MAX_WRITING_ATTEMPTS

from ..state import SupervisorState


# 사용자 노출 메시지 (graceful degradation)
_PARTIAL_RESULT_PREFIX = (
    "일부 정보 수집은 성공했으나 응답 생성에 어려움이 있었습니다. "
    "수집된 정보를 그대로 전달합니다:\n\n"
)
_TOTAL_FAILURE_MESSAGE = (
    "죄송합니다. 요청을 처리하는 중 여러 단계에서 문제가 발생했습니다. "
    "잠시 후 다시 시도해 주세요."
)
_VALIDATION_LIMIT_SUFFIX = (
    "\n\n---\n*응답을 두 차례 작성했으나 자체 품질 기준에 완전히 도달하지 "
    "못했습니다. 필요하시면 추가 질문을 통해 더 자세한 정보를 요청해 주세요.*"
)


async def finalize_node(state: SupervisorState) -> dict:
    """최종 응답을 사용자에게 반환.

    Graceful Degradation 세 경로:
        1. draft_response가 None (Writing 자체 실패)
           → partial research result로 fallback
           → research도 없으면 사과 메시지
        2. Validation 한계 도달 (is_acceptable=False AND attempts >= MAX)
           → draft에 한계 안내 suffix 첨부
        3. 정상 경로
           → draft를 그대로 반환

    deps 없음:
        본 노드는 LLM 호출 없이 state 기반으로 응답 텍스트만 결정.
        graph.py에서 partial 없이 직접 등록.

    Returns:
        messages: 최종 응답 AIMessage 1개
    """
    draft = state.get("draft_response")
    validation = state.get("validation_result", {})
    attempts = state.get("writing_attempts", 0)

    if draft is None:
        # 경로 1: Writing 자체가 실패한 경우
        partial_results = [
            f"- {t['description']}: {t['result']}"
            for t in state["tasks"]
            if t.get("status") == "completed"
            and t.get("result")
            and t["agent"] == "research"
        ]
        if partial_results:
            final_response = _PARTIAL_RESULT_PREFIX + "\n".join(partial_results)
        else:
            final_response = _TOTAL_FAILURE_MESSAGE

    elif (
        not validation.get("is_acceptable", True)
        and attempts >= MAX_WRITING_ATTEMPTS
    ):
        # 경로 2: Validation 한계 도달 (graceful degradation)
        final_response = draft + _VALIDATION_LIMIT_SUFFIX

    else:
        # 경로 3: 정상 — validation 통과
        final_response = draft

    return {"messages": [AIMessage(content=final_response)]}
