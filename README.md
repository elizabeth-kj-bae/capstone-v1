# a30 · Error Handling (Day3)

이 태그는 **Layer 간 에러 처리 단계의 완성본**입니다. a22에 graceful degradation이 추가됩니다.

## 이 단계에서 완성되어야 할 것
- `backend/schemas/error.py` — Layer별 표준 에러 모델(CapstoneError / ToolError / OrchestrationError)
- `backend/error_handling/retry.py` — transient error에 대한 retry 정책
- `backend/agent/mcp_client.py` — MCP tool 예외를 ToolError로 래핑
- `backend/agent/supervisor_graph.py` — execute/finalize에 graceful degradation(task 실패해도 계속, partial fallback)
- `backend/schemas/stream.py` — `ErrorEvent` + `TaskCompletedEvent`(status/error_message)
- `backend/streaming/event_converter.py` — stream 예외 → `ErrorEvent`
- 프론트엔드: `ErrorBanner.tsx`, `TaskListView`(failed 표시), `types.ts`/`page.tsx` 확장

## 이전 / 다음
이전: `a22-eval` · 다음: `a31-cost-latency`
