"""
FastAPI backend 진입점.

- POST /chat: 단순 request/response
- 에러 처리는 graceful degradation 없이 처리
"""
import uuid
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from agent.graph import build_agent
from schemas.chat import ChatRequest, ChatResponse


# Agent를 lifespan으로 1회 생성 (서버 시작 시)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: agent 생성
    app.state.agent = await build_agent()
    yield
    # Shutdown: 별도 정리 필요시 여기에


app = FastAPI(
    title="ICT Operations Support Backend",
    description="Capstone Day 1 — RAG + Agent + MCP integrated backend",
    lifespan=lifespan,
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

    # Agent 호출 (실패 시 그대로 전파)
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
