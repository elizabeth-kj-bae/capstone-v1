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
    PlanCreatedEvent,
    TaskListCreatedEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    SubAgentTokenEvent,
    ErrorEvent,
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


async def convert_supervisor_events(
    supervisor_stream,
    thread_id: str,
):
    """
    Supervisor graph의 stream event를 본 capstone SSE event로 변환.

    Multi-agent 시나리오의 event들을 frontend가 가시화할 수 있는 형태로 송출.
    Graceful Degradation: stream 중 예외는 ErrorEvent로 전달.
    """
    current_task_id = None
    previous_tasks = None

    try:
        async for mode, data in supervisor_stream:

            if mode == "updates":
                for node_name, node_update in data.items():

                    if node_name == "planning":
                        if "plan" in node_update:
                            yield PlanCreatedEvent(plan=node_update["plan"])
                        if "tasks" in node_update:
                            yield TaskListCreatedEvent(tasks=node_update["tasks"])
                            previous_tasks = node_update["tasks"]

                    # a31부터 execute 노드가 execute_research(병렬) / execute_writing 으로 분리됨
                    elif node_name in ("execute", "execute_research", "execute_writing"):
                        if "tasks" in node_update:
                            new_tasks = node_update["tasks"]
                            for new_t, old_t in zip(new_tasks, previous_tasks or []):
                                if new_t["status"] == "in_progress" and old_t["status"] == "pending":
                                    yield TaskStartedEvent(
                                        task_id=new_t["id"],
                                        agent_name=new_t["agent"],
                                    )
                                    current_task_id = new_t["id"]
                                elif new_t["status"] in ["completed", "failed"] and old_t["status"] != new_t["status"]:
                                    yield TaskCompletedEvent(
                                        task_id=new_t["id"],
                                        status=new_t["status"],
                                        result_preview=(new_t.get("result") or "")[:200] if new_t.get("result") else None,
                                        error_message=new_t.get("error_message"),
                                    )
                            previous_tasks = new_tasks

                    elif node_name == "finalize":
                        if "messages" in node_update:
                            last_msg = node_update["messages"][-1]
                            if hasattr(last_msg, "content"):
                                yield TokenEvent(content=last_msg.content)

            elif mode == "messages":
                message_chunk, metadata = data
                if hasattr(message_chunk, "content") and message_chunk.content:
                    if current_task_id:
                        yield SubAgentTokenEvent(
                            task_id=current_task_id,
                            content=message_chunk.content,
                        )

    except Exception as e:
        # Stream 중간 발생한 예상치 못한 error
        yield ErrorEvent(
            code="STREAM_INTERRUPTED",
            message="응답 생성 중 오류가 발생했습니다. 일부 결과는 위에 표시되었을 수 있습니다.",
            recoverable=True,
        )

    yield DoneEvent(thread_id=thread_id)
