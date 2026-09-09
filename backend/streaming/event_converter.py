"""
LangGraph event → SSE event 변환.

다음 4가지 SSE event로 변환:
- TokenEvent
- ToolCallStartEvent
- ToolCallEndEvent
- DoneEvent
"""
from typing import AsyncIterator, Optional
from langchain_core.messages import AIMessageChunk, ToolMessage
from schemas.stream import (
    StreamEvent,
    TokenEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    DoneEvent,
)


async def convert_langgraph_events(
    langgraph_stream: AsyncIterator,
    thread_id: str,
) -> AsyncIterator[StreamEvent]:
    """
    LangGraph event stream을 SSE event stream으로 변환.
    
    Args:
        langgraph_stream: agent.astream(...)이 반환한 async iterator
        thread_id: 이번 stream의 thread_id (DoneEvent에 포함)
    
    Yields:
        StreamEvent 인스턴스
    """
    async for mode, data in langgraph_stream:
        
        if mode == "messages":
            # LLM token chunk
            message_chunk, metadata = data
            
            if isinstance(message_chunk, AIMessageChunk):
                # Tool call이 시작된 chunk인지 확인
                if message_chunk.tool_call_chunks:
                    for tc_chunk in message_chunk.tool_call_chunks:
                        if tc_chunk.get("name"):
                            yield ToolCallStartEvent(
                                tool_name=tc_chunk["name"],
                                args=tc_chunk.get("args", {}) or {},
                            )
                # 일반 token (텍스트 content)
                elif message_chunk.content:
                    yield TokenEvent(content=message_chunk.content)
        
        elif mode == "updates":
            # Node 단위 업데이트 — tool 응답 도착 시 ToolCallEndEvent
            for node_name, node_update in data.items():
                if "messages" in node_update:
                    for msg in node_update["messages"]:
                        if isinstance(msg, ToolMessage):
                            yield ToolCallEndEvent(
                                tool_name=msg.name,
                                result=str(msg.content)[:200],  # preview
                            )
    
    # 모든 event 처리 완료 후 done event
    yield DoneEvent(thread_id=thread_id)
