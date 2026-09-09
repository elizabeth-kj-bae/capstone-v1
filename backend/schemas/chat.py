"""
Chat endpoint의 입출력 schema.

단순 request/response
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """사용자가 보내는 chat 요청"""

    message: str = Field(description="사용자의 자연어 메시지")
    thread_id: Optional[str] = Field(
        default=None, description="대화 세션 식별자. 없으면 새 세션 시작."
    )


class ChatResponse(BaseModel):
    """Agent의 응답"""

    thread_id: str = Field(
        description="대화 세션 식별자 (새로 생성되었거나 입력값 그대로)"
    )
    message: str = Field(description="Agent의 자연어 응답")
    tool_calls: list[dict] = Field(
        default_factory=list, description="Agent가 호출한 tool 목록 (디버깅용)"
    )
