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
    SubAgentToolCallEvent,
    ErrorEvent,
    RoutingDecidedEvent,
    ValidationStartedEvent,
    ValidationCompletedEvent,
    WritingRetryEvent,
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
    (+) routing event 추가.
    """
    current_task_id = None  # 현재 활성 task
    previous_tasks = None   # 이전 state의 tasks (변화 감지용)
    last_validation_feedback = None  # 직전 validator가 생성한 재시도 feedback
    last_writing_attempts = 0        # 직전 execute_writing이 기록한 시도 횟수 (will_retry 계산용)
        
    try:
        async for mode, data in supervisor_stream: 

            if mode == "updates":
                # 어느 node가 업데이트되었는지 확인
                for node_name, node_update in data.items():
                    
                    if node_name == "routing":
                        if "route" in node_update:
                            yield RoutingDecidedEvent(
                                route=node_update["route"],
                                reasoning=node_update.get("route_reasoning", ""),
                            )
                    
                    elif node_name == "simple_response":
                        if "messages" in node_update:
                            last_msg = node_update["messages"][-1]
                            if hasattr(last_msg, "content"):
                                yield TokenEvent(content=last_msg.content)

                    elif node_name == "planning":
                        # Planning 완료 → plan_created + task_list_created
                        if "plan" in node_update:
                            yield PlanCreatedEvent(plan=node_update["plan"])
                        if "tasks" in node_update:
                            yield TaskListCreatedEvent(tasks=node_update["tasks"])
                            previous_tasks = node_update["tasks"]
                        
                    elif node_name == "finalize":
                        # 최종 응답 → 기존 token event로 흘려보냄 (단순화)
                        if "messages" in node_update:
                            last_msg = node_update["messages"][-1]
                            if hasattr(last_msg, "content"):
                                # 전체 응답을 한 번에 보냄 (단순화)
                                yield TokenEvent(content=last_msg.content)

                    elif node_name == "validator":
                        # Validator 결과 처리 
                        if "validation_result" in node_update:
                            val = node_update["validation_result"]
                            # 재시도 시 execute_writing 단계에서 사용하기 위해 보관
                            last_validation_feedback = val.get("feedback")
                            # validator 노드의 update에는 writing_attempts가 없으므로
                            # 직전 execute_writing의 값을 사용 (route_after_validation과 동일 기준)
                            attempts = node_update.get("writing_attempts", last_writing_attempts)
                            rounds = node_update.get("validation_attempts", 0)
                            will_retry = (
                                not val.get("is_acceptable", True) and
                                attempts < 2 and
                                rounds < 3
                            )
                            yield ValidationCompletedEvent(
                                is_acceptable=val.get("is_acceptable", False),
                                score=val.get("score", 0.0),
                                reasoning=val.get("reasoning", ""),
                                will_retry=will_retry,
                            )

                    elif node_name in ("execute_research", "execute_writing"):
                        # 모든 execute_* 노드 공통: tasks status diff로 lifecycle 이벤트 발행.
                        # agent 종류와 무관하게 동일 로직 적용 (research·writing 모두 처리).
                        if "tasks" in node_update:
                            new_tasks = node_update["tasks"]
                            for new_t, old_t in zip(new_tasks, previous_tasks or []):
                                if (new_t["status"] == "in_progress"
                                        and old_t["status"] == "pending"):
                                    yield TaskStartedEvent(
                                        task_id=new_t["id"],
                                        agent_name=new_t["agent"],
                                    )
                                    current_task_id = new_t["id"]
                                elif (new_t["status"] in ("completed", "failed")
                                        and old_t["status"] != new_t["status"]):
                                    yield TaskCompletedEvent(
                                        task_id=new_t["id"],
                                        status=new_t["status"],
                                        result_preview=(new_t.get("result") or "")[:200] if new_t.get("result") else None,
                                        error_message=new_t.get("error_message"),
                                    )
                            previous_tasks = new_tasks

                        # writing 재시도 감지 (execute_writing 전용 부가 로직)
                        if node_name == "execute_writing":
                            attempts = node_update.get("writing_attempts", 0)
                            last_writing_attempts = attempts
                            if attempts == 2:
                                yield WritingRetryEvent(
                                    attempt=2,
                                    feedback=last_validation_feedback or "",
                                )

            elif mode == "messages":
                # Sub-agent의 LLM token chunk
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

    # 정상 종료 
    yield DoneEvent(thread_id=thread_id)

