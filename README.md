# a32 · Stateless Session (Day3)

이 태그는 **state 영속화 단계의 완성본**입니다. in-memory → PostgreSQL checkpointer로 전환합니다. (Part A의 마지막 단계)

## 이 단계에서 완성되어야 할 것
- `docker-compose.yml` — PostgreSQL 16 컨테이너
- `backend/persistence/checkpointer.py` — `AsyncPostgresSaver` 팩토리(lifecycle 관리)
- `backend/agent/graph.py`, `backend/agent/supervisor_graph.py` — checkpointer를 **외부 주입**받도록 변경(MemorySaver 생성 제거)
- `backend/main.py` — lifespan에서 checkpointer를 한 번 생성해 두 graph가 공유
- Backend 재시작/멀티 인스턴스에서도 thread state가 이어지는지 검증

## 이전 / 다음
이전: `a31-cost-latency` · 다음: `b10-supervisor-start` (Part B)
