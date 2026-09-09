# b10 · Supervisor 시작점 (Part B)

이 태그는 **Part B의 출발 상태**입니다. 코드는 Part A 완료 시점(`a32`)의 supervisor와 동일하며,
여기서부터 4가지 개선을 더해 `b20`으로 발전시킵니다.

## 현재 supervisor 구조
`planning → execute_research(병렬) → execute_writing → finalize`

## Part B에서 더할 것 (→ b20)
1. Query Routing — 단순 질문은 Supervisor가 직접 답, 복잡한 질문만 multi-agent
2. Validator sub-agent — 최종 응답 품질 검증
3. Conditional Routing — Supervisor 내부 분기
4. Dynamic Planning — Supervisor 자체 판단(replan)

## 이전 / 다음
이전: `a32-stateless` · 다음: `b20-supervisor-final`
