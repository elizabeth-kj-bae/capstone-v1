# refactor/v2 (참고용 — 학습 범위 외)

이 브랜치는 Part A+B 완성 코드를 **product-grade로 리팩터링한 참고본**입니다.
학생 과정(`main`의 a10~b20 태그)에는 포함되지 않습니다.

## main 대비 차이
- `backend/agent/supervisor_graph.py`(flat) → `backend/agent/supervisor/v1/`(legacy) + `v2/`(modular) 패키지로 분리
- `backend/config.py` — LLM 모델, MAX_REPLAN_ROUNDS 등 설정 통합
- `backend/main.py` — 환경변수 `SUPERVISOR_VERSION`(v1/v2)으로 supervisor 구현 전환

