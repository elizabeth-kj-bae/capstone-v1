"""
FastAPI backend 진입점.

- POST /chat: 단순 request/response
- 에러 처리는 graceful degradation 없이 처리 
"""
import uuid
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from persistence.checkpointer import create_checkpointer
from streaming.sse_formatter import format_sse
from streaming.event_converter import convert_langgraph_events, convert_supervisor_events


import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from agent.graph import build_agent
from schemas.chat import ChatRequest, ChatResponse

# Supervisor 버전 분기 (환경변수로 결정, 기본값 v1)
SUPERVISOR_VERSION = os.getenv("SUPERVISOR_VERSION", "v1")

if SUPERVISOR_VERSION == "v2":
    from agent.supervisor.v2 import build_supervisor_graph
elif SUPERVISOR_VERSION == "v1":
    from agent.supervisor.v1 import build_supervisor_graph
else:
    raise ValueError(
        f"Unknown SUPERVISOR_VERSION: {SUPERVISOR_VERSION!r}. "
        f"Expected 'v1' or 'v2'."
    )

print(f"[Startup] Supervisor version: {SUPERVISOR_VERSION}")


# Agent를 lifespan으로 1회 생성 (서버 시작 시)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Backend Lifecycle 관리. 

    Session 관리 강화:
    - PostgreSQL checkpointer를 lifespan 동안 한 번만 생성 
    - Graph은 생성된 checkpointer 공유 
    - 종료 시 connection 정리 
    """
    # Startup: checkpointer 생성 후 graph 빌드
    async with create_checkpointer() as checkpointer:
        # 두 agent가 같은 checkpointer 공유
        # (thread_id가 같으면 두 agent가 같은 state를 보게 됨 — 본 capstone 결정)
        app.state.checkpointer = checkpointer
        app.state.agent = await build_agent(checkpointer)
        app.state.supervisor_graph = await build_supervisor_graph(checkpointer)
        
        print("Backend startup complete (PostgreSQL checkpointer active)")
        
        yield
        
        # Shutdown: context manager가 자동으로 connection 정리
        print("Backend shutdown: closing PostgreSQL connections")


app = FastAPI(
    title="ICT Operations Support Backend",
    description="Capstone Day 1 — RAG + Agent + MCP integrated backend",
    lifespan=lifespan,
)
# CORS 설정 
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
    
    단일 요청 - 응답 (streaming 다음에 고려함)
    """
    # thread_id 처리 (없으면 새로 생성)
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # Agent 호출
    # 에러 처리: 실패 시 그대로 전파
    config = {"configurable": {"thread_id": thread_id}}
    
    result = await app.state.agent.ainvoke(
        {"messages": [{"role": "user", "content": request.message}]},
        config=config,
    )
    
    # 응답 메시지 추출
    final_message = result["messages"][-1]
    
    # Tool calls 추출 (디버깅용)
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
    - Multi-event streaming 
    """
    # thread_id 처리 (Day 1과 동일 로직)
    thread_id = request.thread_id or str(uuid.uuid4())
    
    async def event_generator():
        """
        SSE event를 생성하는 async generator.
        FastAPI StreamingResponse가 이를 chunk 단위로 client에 전송.
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        # LangGraph astream 호출
        langgraph_stream = app.state.agent.astream(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config,
            stream_mode=["messages", "updates"],
        )
        
        # LangGraph event → 본 capstone event → SSE format
        async for event in convert_langgraph_events(langgraph_stream, thread_id):
            yield format_sse(event)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Proxy/Load Balancer buffering 방지
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/chat/supervisor/stream")
async def chat_supervisor_stream(request: ChatRequest):
    """
    Multi-agent (Supervisor pattern) streaming endpoint.
    
    Day 2 Multi-agent UX hands-on용.
    """
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

