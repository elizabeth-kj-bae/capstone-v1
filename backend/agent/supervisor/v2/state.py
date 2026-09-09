"""Supervisor graph의 state 정의.

LangGraph의 TypedDict 기반 state로, 모든 노드가 공유됨. 
"""

from typing import Annotated, Literal, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SupervisorState(TypedDict):
    """Supervisor graph의 모든 노드가 공유하는 state.

    필드 그룹:
    - 대화 이력 (messages)
    - Routing: 단순/복잡 분기 결정
    - Base: plan, tasks, current_task_index
    - Dynamic Planning: replan 추적
    - Validation: 응답 품질 검증 + 재시도 추적

    Tasks 항목 구조:
        {
            "id": str,            # "task_1", "task_2" 형식
            "description": str,   # task 내용
            "agent": str,         # "research" | "analysis" | "writing"
            "status": str,        # "pending" | "in_progress" | "completed" | "failed"
            "result": str | None, # 실행 결과
            "error_code": str,    # (실패 시) 에러 코드
            "error_message": str, # (실패 시) 사용자 친화적 메시지
        }
    """

    # 대화 이력 (add_messages reducer로 자동 누적)
    messages: Annotated[list[BaseMessage], add_messages]

    # Routing
    route: Optional[Literal["simple", "complex"]]
    route_reasoning: Optional[str]

    # Base
    plan: str
    tasks: list[dict]
    current_task_index: int

    # Dynamic Planning
    replan_rounds: int
    replan_decision: Optional[dict]

    # Validation
    draft_response: Optional[str]
    validation_result: Optional[dict]
    writing_attempts: int
    validation_feedback: Optional[str]
    validation_attempts: int
