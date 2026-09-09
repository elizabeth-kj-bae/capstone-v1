"""Validator 노드.

Writing agent의 응답을 4가지 기준(Relevance / Completeness / Clarity /
Domain Appropriateness)으로 평가하여 사용자에게 노출할 수 있는 품질인지 판단.

- validator_node: ValidationResult로 structured output 수행.
                  미달 시 feedback 생성해 writing 재시도의 context로 활용.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from .. import prompts
from ..deps import SupervisorDeps
from ..schemas import ValidationResult
from ..state import SupervisorState


async def validator_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """Writing agent의 응답을 검증.

    평가 기준:
        1. Relevance: 응답이 사용자 질문에 답하는가
        2. Completeness: 수집된 정보를 충분히 활용했는가
        3. Clarity: 응답이 구조적이고 명확한가
        4. Domain Appropriateness: ICT 운영 도메인 전문성을 보이는가

    재시도 메커니즘:
        is_acceptable=False이면 feedback을 생성해 state에 저장.
        다음 writing 호출이 feedback을 context에 포함하여 응답 개선.

    카운터:
        validation_attempts는 매 호출 증가. route_after_validation의
        MAX_VALIDATION_ROUNDS 안전장치가 동작하도록 보장.

    Returns:
        validation_result: 전체 평가 결과 (UI 표시용)
        validation_feedback: 재시도 feedback (acceptable이면 None)
        validation_attempts: +1
    """
    # 최초 사용자 질문 추출 (재시도 경로에서도 원본 질문 참조 필요)
    user_question = ""
    for msg in state["messages"]:
        if hasattr(msg, "type") and msg.type == "human":
            user_question = msg.content
            break

    draft = state.get("draft_response", "")
    plan = state.get("plan", "")
    tasks = state.get("tasks", [])

    # Research task 결과 요약 (validator가 'completeness' 평가에 활용)
    task_summary = "\n".join(
        [
            (
                f"- {t['description']} → "
                f"{t.get('result', '실패')[:200] if t.get('result') else '실패'}"
            )
            for t in tasks
            if t["agent"] == "research"
        ]
    )

    validation_prompt = prompts.VALIDATION_PROMPT_TEMPLATE.format(
        user_question=user_question,
        plan=plan,
        task_summary=task_summary,
        draft=draft,
    )

    result = await deps.validator_llm.with_structured_output(
        ValidationResult
    ).ainvoke(
        [
            SystemMessage(
                content="You are a quality validator for AI agent responses."
            ),
            HumanMessage(content=validation_prompt),
        ]
    )

    return {
        "validation_result": {
            "is_acceptable": result.is_acceptable,
            "score": result.score,
            "reasoning": result.reasoning,
            "feedback": result.feedback,
        },
        "validation_feedback": (
            result.feedback if not result.is_acceptable else None
        ),
        "validation_attempts": state.get("validation_attempts", 0) + 1,
    }
