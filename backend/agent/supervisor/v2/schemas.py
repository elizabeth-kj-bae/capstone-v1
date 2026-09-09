"""Supervisor graph가 LLM과 주고받는 Pydantic 모델.

Structured output용 schema를 도메인별로 정리.

도메인 그룹:
- Routing:    RoutingDecision
- Planning:   TaskSpec, PlanDecision
- Replan:     ReplanDecision, ReplanPlanDecision
- Validation: ValidationResult
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------

class RoutingDecision(BaseModel):
    """Supervisor의 routing 결정."""

    route: Literal["simple", "complex"] = Field(
        description=(
            "질문의 복잡도. "
            "simple: 인사·메타질문·단순한 정보 요청. "
            "complex: 정보 수집·통합·분석이 필요한 작업"
        )
    )
    reasoning: str = Field(description="결정 근거를 한 문장으로")


# ---------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------

class TaskSpec(BaseModel):
    """Planner가 분해한 단일 task."""

    description: str = Field(description="task가 수행할 작업 설명")
    agent: Literal["research", "analysis", "writing"] = Field(
        description=(
            '담당 sub-agent. '
            '"research": 정보 검색, '
            '"analysis": 수집 정보 분석/가공, '
            '"writing": 최종 응답 작성'
        )
    )


class PlanDecision(BaseModel):
    """Supervisor의 계획 수립 결과 (structured output)."""

    plan: str = Field(description="전체 진행 계획 (자연어 2-3문장)")
    needs_analysis: bool = Field(
        description=(
            "별도 analysis 단계가 필요한지 여부. "
            "True: 패턴 식별·비교/분류·여러 source 통합·우선순위화·"
            "근본원인 분석 등 수집 정보에 대한 가공/추론이 필요한 경우. "
            "False: 단순 검색·필터·나열·요약 등 수집 결과를 거의 "
            "그대로 전달하면 되는 경우."
        )
    )
    tasks: list[TaskSpec] = Field(
        description="실행할 task 목록. 순서는 research → (analysis) → writing"
    )


# ---------------------------------------------------------------------
# Replan (Dynamic Planning)
# ---------------------------------------------------------------------

class ReplanDecision(BaseModel):
    """Research 결과를 평가하여 추가 정보 수집이 필요한지 판단.

    평가 전용 모델. 실제 plan/tasks 갱신은 별도 replan_node가 수행한다.

    Dynamic Planning:
    - is_sufficient: Research 결과가 사용자 의도를 충족하는지
    - reasoning:     판단 근거 (LangSmith trace에 기록)
    """

    is_sufficient: bool = Field(
        description=(
            "현재까지의 Research 결과가 사용자 질문에 답하기에 충분한지. "
            "True: 추가 검색 불필요, 다음 단계 진행. "
            "False: 추가 정보 수집이 필요"
        )
    )
    reasoning: str = Field(description="판단 근거를 1-2 문장으로")


class ReplanPlanDecision(BaseModel):
    """Replan 시 Supervisor가 갱신한 plan과 추가 research task."""

    plan: str = Field(
        description=(
            "갱신된 plan (직전 plan을 보강한 형태). "
            "이미 수집된 raw material은 재수집하지 말고, "
            "부족한 부분만 명시적으로 보강."
        )
    )
    additional_research_tasks: list[TaskSpec] = Field(
        description=(
            "추가로 실행할 research task 목록. "
            "기존 task와 중복되지 않는 새 키워드/source 사용. "
            "agent는 반드시 'research' "
            "(analysis/writing은 이후 단계에서 처리)."
        )
    )


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

class ValidationResult(BaseModel):
    """Validator의 평가 결과.

    v1에서는 build_supervisor_graph closure 내부에 정의되어 있어
    재사용·테스트가 어려웠음. v2에서 모듈 레벨로 끌어냄.
    """

    is_acceptable: bool = Field(
        description=(
            "응답을 사용자에게 그대로 전달할 수 있는 품질인지 (True/False)"
        )
    )
    score: float = Field(
        description="0.0-1.0 점수. 0.7 이상을 acceptable 기준으로 권장",
        ge=0.0,
        le=1.0,
    )
    reasoning: str = Field(description="판단 근거를 2-3 문장으로")
    feedback: Optional[str] = Field(
        default=None,
        description=(
            "재시도가 필요할 때 Writing agent에게 전달할 구체적 개선 지시. "
            "is_acceptable이 False일 때만 작성"
        ),
    )
