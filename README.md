# a20 · Streaming (Day2)

이 태그는 **SSE 스트리밍 단계의 완성본**입니다. a11에 스트리밍과 프론트엔드(기본)가 추가됩니다.

## 이 단계에서 완성되어야 할 것
- 백엔드
  - `backend/main.py` — `POST /chat/stream`(SSE) 추가, CORS 설정
  - `backend/schemas/stream.py` — SSE 이벤트 스키마(token / tool_call_start / tool_call_end / done)
  - `backend/streaming/sse_formatter.py`, `event_converter.py` — LangGraph 이벤트 → SSE 변환
- 프론트엔드 (신규, 기본 chat UI)
  - `frontend/app/page.tsx` — 메인 chat 페이지
  - `frontend/components/` — ChatMessage / ChatInput / ToolCallView
  - `frontend/lib/` — transport(SSE 파싱) / thread(thread_id 관리) / types
- `curl -N`로 스트림 확인, 브라우저에서 E2E 확인

## 이전 / 다음
이전: `a11-fastapi` · 다음: `a21-multiagent-streaming` (multi-agent 뷰는 a21부터)
