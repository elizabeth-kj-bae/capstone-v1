"""Supervisor graph의 conditional edge 분기 함수.

Node가 아닌 routing 결정 전용 함수. state만 받아 다음 node 이름을
반환하는 단순한 형태이므로 deps 주입은 불필요.
"""

from typing import Literal

from config import (
    MAX_REPLAN_ROUNDS,
    MAX_VALIDATION_ROUNDS,
    MAX_WRITING_ATTEMPTS,
)

from .state import SupervisorState


def route_by_complexity(
    state: SupervisorState,
) -> Literal["simple_response", "planning"]:
    """routing_node가 채운 state["route"]에 따라 처리 경로 결정.

    - route == "simple"  → simple_response (LLM 1회 직접 응답)
    - route == "complex" → planning (multi-agent flow)
    """
    return "simple_response" if state.get("route") == "simple" else "planning"


def route_after_planning(
    state: SupervisorState,
) -> Literal["execute_research", "execute_analysis", "execute_writing"]:
    """Planning 결과에 따라 첫 task 실행 경로 결정.

    - research task가 있으면 research부터
    - research 없이 analysis만 있으면 analysis부터 (드문 경우)
    - 둘 다 없으면 writing으로 (이론적 fallback)
    """
    tasks = state.get("tasks", [])
    has_research = any(t["agent"] == "research" for t in tasks)
    has_analysis = any(t["agent"] == "analysis" for t in tasks)

    if has_research:
        return "execute_research"
    if has_analysis:
        return "execute_analysis"
    return "execute_writing"


def route_after_research(
    state: SupervisorState,
) -> Literal["execute_analysis", "execute_writing"]:
    """Research 완료 후 다음 단계 결정.

    - Analysis task가 있으면 → execute_analysis
    - 없으면 → execute_writing
    """
    tasks = state.get("tasks", [])
    has_analysis = any(t["agent"] == "analysis" for t in tasks)

    return "execute_analysis" if has_analysis else "execute_writing"


def route_after_validation(
    state: SupervisorState,
) -> Literal["retry_writing", "finalize"]:
    """Validator 결과에 따라 다음 step 결정.

    - is_acceptable=True → finalize
    - is_acceptable=False AND writing_attempts < MAX → retry_writing
    - 한계 도달 → finalize (graceful degradation)

    안전장치 두 단계:
    - MAX_WRITING_ATTEMPTS: 정상적인 재시도 한계
    - MAX_VALIDATION_ROUNDS: 방어적 hard stop (카운터 손상 시 무한 루프 차단)
    """
    validation = state.get("validation_result", {})
    is_acceptable = validation.get("is_acceptable", True)
    attempts = state.get("writing_attempts", 0)
    validation_rounds = state.get("validation_attempts", 0)

    if is_acceptable:
        return "finalize"

    # 방어적 안전장치: validator가 과도하게 반복되면 무조건 종료
    if validation_rounds >= MAX_VALIDATION_ROUNDS:
        return "finalize"

    if attempts >= MAX_WRITING_ATTEMPTS:
        return "finalize"

    return "retry_writing"


def route_after_replan(
    state: SupervisorState,
) -> Literal["replan", "execute_analysis", "execute_writing"]:
    """Replan 평가 결과에 따라 다음 step 결정.

    - is_sufficient=True → 다음 단계 (analysis 또는 writing)
    - is_sufficient=False AND rounds <= MAX → replan (plan 재수립)
    - 재계획 한계 도달 → 다음 단계 (graceful degradation)
    """
    replan = state.get("replan_decision", {})
    is_sufficient = replan.get("is_sufficient", True)
    rounds = state.get("replan_rounds", 0)

    if is_sufficient or rounds > MAX_REPLAN_ROUNDS:
        tasks = state.get("tasks", [])
        has_analysis = any(t["agent"] == "analysis" for t in tasks)
        return "execute_analysis" if has_analysis else "execute_writing"

    return "replan"
