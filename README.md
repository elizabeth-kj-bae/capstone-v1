# b12 · Supervisor Validator Agent (Part B-2)

이 태그는 **Part B-2 (Validator Agent) 완성본**입니다. `b11`에 Validator와 Writing 재시도가 추가됩니다.

## 이 단계에서 완성되어야 할 것
- `backend/agent/supervisor_graph.py`
  - `SupervisorState`에 Validation 필드(`draft_response`, `validation_result`, `writing_attempts`, `validation_feedback`, `validation_attempts`) 추가
  - `ValidationResult`, `validator_node`, `route_after_validation` (Routing 분기 함수는 `route_by_complexity`로 이름 변경)
  - `execute_writing_task_node` — draft 보관 + feedback 반영 재시도, `finalize_node` — draft 기반 응답
  - Graph: `… → execute_writing → validator → (retry) execute_writing / (통과·한계) finalize`
- `backend/schemas/stream.py` — `ValidationStartedEvent` / `ValidationCompletedEvent` / `WritingRetryEvent`
- `backend/streaming/event_converter.py` — `validator` 처리, writing 재시도 감지
- 프론트엔드: `components/ValidationView.tsx`(신규) · `ChatMessage.tsx` · `lib/types.ts` · `app/page.tsx`(`validation_completed`, `writing_retry` case)

## 이전 / 다음
이전: `b11-supervisor-routing` · 다음: `b13-supervisor-conditional`
