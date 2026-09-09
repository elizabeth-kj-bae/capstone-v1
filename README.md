# a31 · Cost & Latency (Day3)

이 태그는 **비용·지연 최적화 단계의 완성본**입니다. a30에 측정 스크립트와 supervisor 최적화가 추가됩니다.

## 이 단계에서 완성되어야 할 것
- `backend/perf/benchmark.py` — latency/cost 벤치마크 스크립트(최적화 전/후 비교)
- `backend/agent/supervisor_graph.py` — 두 가지 최적화 적용
  - 모델 분리: Planning=`gpt-4o-mini`(fast), Research/Writing=`gpt-4o`(quality)
  - 병렬 실행: research task를 `asyncio.gather`로 fan-out/fan-in (순차 → 병렬), writing은 별도 노드
- LangSmith trace로 단계별 latency/token 분해 후 최적화 효과 측정

## 이전 / 다음
이전: `a30-error-handling` · 다음: `a32-stateless`
