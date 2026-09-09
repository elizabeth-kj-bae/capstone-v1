"""
FastAPI backend 진입점.

- POST /chat: 단순 request/response
- POST /chat/stream: 단일 agent SSE streaming
- POST /chat/supervisor/stream: multi-agent(Supervisor) SSE streaming
- lifespan에서 PostgreSQL checkpointer lifecycle 관리 (Day3)
"""
import uuid
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from persistence.checkpointer import create_checkpointer
from agent.graph import build_agent
from agent.supervisor_graph import build_supervisor_graph
from schemas.chat import ChatRequest, ChatResponse
from streaming.sse_formatter import format_sse
from streaming.event_converter import convert_langgraph_events, convert_supervisor_events


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Backend lifecycle 관리.

    - PostgreSQL checkpointer를 lifespan 동안 한 번만 생성
    - 두 graph(single / supervisor)가 그 checkpointer를 공유
    - 종료 시 connection 정리
    """
    async with create_checkpointer() as checkpointer:
        # thread_id가 같으면 두 agent가 같은 state를 보게 됨 (본 capstone 결정)
        app.state.checkpointer = checkpointer
        app.state.agent = await build_agent(checkpointer)
        app.state.supervisor_graph = await build_supervisor_graph(checkpointer)

        print("Backend startup complete (PostgreSQL checkpointer active)")
        yield
        print("Backend shutdown: closing PostgreSQL connections")


app = FastAPI(
    title="ICT Operations Support Backend",
    description="Capstone Day 3 — Stateful session (PostgreSQL checkpointer)",
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
    """단일 요청 - 응답 (streaming은 /chat/stream)."""
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
    """단일 agent Streaming chat endpoint (SSE)."""
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


@app.post("/chat/supervisor/stream")
async def chat_supervisor_stream(request: ChatRequest):
    """Multi-agent (Supervisor pattern) streaming endpoint."""
    thread_id = request.thread_id or str(uuid.uuid4())

    async def event_generator():
        config = {"configurable": {"thread_id": thread_id}}
        supervisor_stream = app.state.supervisor_graph.astream(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config,
            stream_mode=["messages", "updates"],
        )
        async for event in convert_supervisor_events(supervisor_stream, thread_id):
            yield format_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )
