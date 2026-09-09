"""
FastAPI backend 진입점.

- POST /chat: 단순 request/response
- POST /chat/stream: SSE streaming (Day2)
- 에러 처리는 graceful degradation 없이 처리
"""
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from agent.graph import build_agent
from schemas.chat import ChatRequest, ChatResponse
from streaming.sse_formatter import format_sse
from streaming.event_converter import convert_langgraph_events


# Agent를 lifespan으로 1회 생성 (서버 시작 시)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: agent 생성
    app.state.agent = await build_agent()
    yield
    # Shutdown: 별도 정리 필요시 여기에


app = FastAPI(
    title="ICT Operations Support Backend",
    description="Capstone Day 2 — RAG + Agent + MCP + Streaming",
    lifespan=lifespan,
)

# CORS 설정 (Frontend localhost:3000 → Backend localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    사용자 메시지를 받아 agent로 처리.

    단일 요청 - 응답 (streaming은 /chat/stream)
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = await app.state.agent.ainvoke(
        {"messages": [{"role": "user", "content": request.message}]},
        config=config,
    )
    final_message = result["messages"][-1]
    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "name": tc["name"],
                    "args": tc["args"],
                })
    return ChatResponse(
        thread_id=thread_id,
        message=final_message.content,
        tool_calls=tool_calls,
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint.

    Day 2 추가:
    - SSE (Server-Sent Events) format으로 stream
    - 4가지 event type: token, tool_call_start, tool_call_end, done
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    async def event_generator():
        config = {"configurable": {"thread_id": thread_id}}
        langgraph_stream = app.state.agent.astream(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config,
            stream_mode=["messages", "updates"],
        )
        async for event in convert_langgraph_events(langgraph_stream, thread_id):
            yield format_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
