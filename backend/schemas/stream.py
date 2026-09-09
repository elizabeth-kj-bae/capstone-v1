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
