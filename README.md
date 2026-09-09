# a22 · Observability & Eval (Day2)

이 태그는 **관찰(LangSmith trace) + 평가 단계의 완성본**입니다. a21에 오프라인 평가 파이프라인이 추가됩니다. (백엔드 서버 코드·프론트엔드 변경 없음)

## 이 단계에서 완성되어야 할 것
- `backend/eval/create_dataset.py` — 평가용 ground-truth dataset 생성
- `backend/eval/evaluators.py` — Heuristic + LLM-as-a-Judge evaluator
- `backend/eval/run_eval.py` — supervisor 대상 LangSmith 평가 실행
- LangSmith에서 trace 관찰 → 저품질 trace를 dataset에 추가 → 재평가

## 이전 / 다음
이전: `a21-multiagent-streaming` · 다음: `a30-error-handling`
