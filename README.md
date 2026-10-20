# b13 · Supervisor Conditional Routing (Part B-3)

이 태그는 **Part B-3 (Conditional Routing in Supervisor) 완성본**입니다. `b12`에 Analysis Agent와 조건부 분기가 추가됩니다.

## 이 단계에서 완성되어야 할 것
- `backend/agent/supervisor_graph.py`
  - `analysis_agent` (LLM only)
  - Planning 강화: `TaskSpec` / `PlanDecision`(`needs_analysis`) + `with_structured_output`, needs_analysis=False면 analysis task 제거
  - `execute_analysis_tasks_node`, `route_after_planning`, `route_after_research`
  - Graph: `planning → (조건) execute_research → (조건) execute_analysis → execute_writing → validator → finalize`
- `backend/streaming/event_converter.py` — `execute_analysis` 노드의 task 상태 이벤트 처리
- 프론트엔드: `components/TaskListView.tsx` Agent별 라벨(🔍 Research · 📊 Analysis · ✍️ Writing) — 이전 태그부터 포함되어 있음

## 이전 / 다음
이전: `b12-supervisor-validator` · 다음: `b14-supervisor-dynamic`
