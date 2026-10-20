# b14 · Supervisor Dynamic Planning (Part B-4)

이 태그는 **Part B-4 (Dynamic Planning) 완성본**이자 Part B(Supervisor 고도화)와 과정 전체의 마지막 참조입니다.
`b13`에 Dynamic Planning(replan)을 더해, `b10`에서 시작한 4가지 개선이 모두 적용된 상태입니다.

## 이 단계에서 완성되어야 할 것
- `backend/agent/supervisor_graph.py` — 4가지 개선 반영
  1. Query Routing — 단순/복잡 분기 (b11)
  2. Validator sub-agent — 최종 응답 품질 검증 (b12)
  3. Conditional Routing — Supervisor 내부 분기 (b13)
  4. Dynamic Planning — replan_check · replan (이번 단계)
- `backend/schemas/stream.py`, `streaming/event_converter.py` — replan 이벤트, execute_* 공통 처리
- 프론트엔드: `ReplanView.tsx`(신규) + `page.tsx`(immutable 업데이트)/`types.ts`/`ChatMessage` 확장

## 이전
이전: `b13-supervisor-conditional`
