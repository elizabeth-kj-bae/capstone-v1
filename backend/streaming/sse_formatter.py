"""
SSE 표준 format 변환 유틸.
"""
import json
from schemas.stream import StreamEvent


def format_sse(event: StreamEvent) -> str:
    """
    Pydantic StreamEvent를 SSE 표준 format 문자열로 변환.
    
    Args:
        event: StreamEvent 인스턴스 (TokenEvent, ToolCallStartEvent 등)
    
    Returns:
        SSE format 문자열 (event 라인, data 라인, 빈 줄)
    
    Example:
        >>> format_sse(TokenEvent(content="안녕"))
        'event: token\\ndata: {"type":"token","content":"안녕"}\\n\\n'
    """
    event_type = event.type
    data = event.model_dump_json()
    return f"event: {event_type}\ndata: {data}\n\n"
