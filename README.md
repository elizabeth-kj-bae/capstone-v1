# b20 · Supervisor 최종 (Part B)

이 태그는 **Part B(Supervisor 고도화)의 최종 완성본**이자 과정 전체의 마지막 참조입니다.
`b10` 상태에서 4가지 개선을 적용합니다.

## 이 단계에서 완성되어야 할 것
- `backend/agent/supervisor_graph.py` — 4가지 개선 반영
  1. Query Routing — 단순/복잡 분기
  2. Validator sub-agent — 최종 응답 품질 검증
  3. Conditional Routing — Supervisor 내부 분기
  4. Dynamic Planning — replan
- `backend/schemas/stream.py`, `streaming/event_converter.py` — routing/validation/replan 이벤트
- 프론트엔드: `ValidationView.tsx`, `ReplanView.tsx`(신규) + `page.tsx`/`types.ts`/`ChatMessage` 확장

## 이전
이전: `b10-supervisor-start`
