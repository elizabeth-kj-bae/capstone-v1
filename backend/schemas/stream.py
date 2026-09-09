"""
SSE Streaming 이벤트 schema.

- type field로 명시적 분류
- Payload는 type별로 구조화
- Pydantic v2로 타입 검증
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional

class StreamEvent(BaseModel):
    """모든 SSE event의 base class."""
    type: str

class TokenEvent(StreamEvent):
    """LLM 응답의 token chunk."""
    type: Literal["token"] = "token"
    content: str = Field(
        description="이번 chunk의 텍스트 내용"
    )

class ToolCallStartEvent(StreamEvent):
    """Agent가 tool 호출을 시작."""
    type: Literal["tool_call_start"] = "tool_call_start"
    tool_name: str = Field(
        description="호출된 tool의 이름"
    )
    args: dict = Field(
        description="tool에 전달된 인자"
    )

class ToolCallEndEvent(StreamEvent):
    """Tool 응답이 도착하여 호출 종료."""
    type: Literal["tool_call_end"] = "tool_call_end"
    tool_name: str = Field(
        description="호출이 종료된 tool의 이름"
    )
    result: Optional[str] = Field(
        default=None,
        description="tool의 응답 (요약/preview)"
    )

class DoneEvent(StreamEvent):
    """Stream 정상 종료 신호."""
    type: Literal["done"] = "done"
    thread_id: str = Field(
        description="이번 stream의 thread_id"
    )


# ===== Day2 Multi-agent(Supervisor) 이벤트 =====

class PlanCreatedEvent(BaseModel):
    type: Literal["plan_created"] = "plan_created"
    plan: str = Field(description="Supervisor가 수립한 계획 (자연어)")


class TaskListCreatedEvent(BaseModel):
    type: Literal["task_list_created"] = "task_list_created"
    tasks: list[dict] = Field(
        description="분해된 task 목록 (id, description, agent, status)"
    )


class TaskStartedEvent(BaseModel):
    type: Literal["task_started"] = "task_started"
    task_id: str
    agent_name: str = Field(description="이 task를 담당하는 sub-agent 이름")


class TaskCompletedEvent(BaseModel):
    type: Literal["task_completed"] = "task_completed"
    task_id: str
    result_preview: Optional[str] = Field(
        default=None,
        description="결과 요약 (200자 내외)"
    )


class SubAgentTokenEvent(BaseModel):
    """Sub-agent의 token (어느 task에 속하는지 명시)."""
    type: Literal["sub_agent_token"] = "sub_agent_token"
    task_id: str
    content: str


class SubAgentToolCallEvent(BaseModel):
    type: Literal["sub_agent_tool_call"] = "sub_agent_tool_call"
    task_id: str
    tool_name: str
    args: dict
    status: Literal["start", "end"]
    result: Optional[str] = None

