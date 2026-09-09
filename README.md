# a21 · Multi-Agent Streaming (Day2)

이 태그는 **Supervisor 멀티에이전트 단계의 완성본**입니다. a20에 Supervisor 패턴과 그 가시화가 추가됩니다.

## 이 단계에서 완성되어야 할 것
- 백엔드
  - `backend/agent/supervisor_graph.py` — Supervisor(Planning → Task 분해 → 실행 → 통합) + Research / Writing sub-agent
  - `backend/main.py` — `POST /chat/supervisor/stream` 추가, lifespan에서 supervisor graph 초기화
  - `backend/schemas/stream.py` — 멀티에이전트 이벤트(plan_created / task_started / task_completed / sub_agent_token …)
  - `backend/streaming/event_converter.py` — `convert_supervisor_events` 추가
- 프론트엔드
  - `frontend/components/PlanView.tsx`, `TaskListView.tsx` — Plan / Task 진행 상황 가시화(신규)
  - `frontend/components/ChatMessage.tsx`, `frontend/app/page.tsx` — 멀티에이전트 이벤트 처리로 확장
  - `frontend/lib/types.ts`, `transport.ts` — 이벤트 타입 / 전송(endpoint 인자) 확장
- Single vs Multi 모드 토글로 UX 차이 확인

## 이전 / 다음
이전: `a20-streaming` · 다음: `a22-eval`
