# a11 · FastAPI + Agent + MCP 통합 (Day1)

이 태그는 **FastAPI 통합 단계의 완성본**입니다. a10에 `backend/`가 추가됩니다.

## 이 단계에서 완성되어야 할 것
- `backend/main.py` — FastAPI, **`POST /chat` 단일 endpoint** (스트리밍은 a20부터)
- `backend/agent/graph.py` — LangGraph ReAct agent(`build_agent`), MemorySaver 내부 사용
- `backend/agent/mcp_client.py` — MCP 서버를 subprocess로 실행하는 client
- `backend/schemas/chat.py` — 요청/응답 스키마
- `curl`로 `/chat` 통합 동작 확인

## 이전 / 다음
이전: `a10-mcp-server` · 다음: `a20-streaming`
