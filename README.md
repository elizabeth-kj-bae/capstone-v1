# b11 · Supervisor Query Routing (Part B-1)

이 태그는 **Part B-1 (단순 질문 Routing) 완성본**입니다. `b10`에 Routing 노드가 추가됩니다.

## 이 단계에서 완성되어야 할 것
- `backend/agent/supervisor_graph.py`
  - `RoutingDecision` (structured output) · `SupervisorState`에 `route` / `route_reasoning` 추가
  - `routing_node`, `simple_response_node`, `route_after_routing`
  - Graph: `START → routing → (simple) simple_response → END` / `(complex) planning → execute_research → execute_writing → finalize`
- `backend/schemas/stream.py` — `RoutingDecidedEvent`
- `backend/streaming/event_converter.py` — `routing` · `simple_response` 노드 처리
- 프론트엔드: `lib/types.ts`(RoutingDecidedEvent, route 필드) · `app/page.tsx`(`routing_decided` case) · `components/ChatMessage.tsx`(simple / complex 분기)

## 이전 / 다음
이전: `b10-supervisor-start` · 다음: `b12-supervisor-validator`
