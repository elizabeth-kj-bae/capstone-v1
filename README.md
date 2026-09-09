# AI Agent Capstone — 단계별 완성본 참조 저장소

각 실습 단계의 "완성본 코드"를 확인하기 위한 참조용 저장소입니다.
직접 코딩하는 작업 폴더가 아니라, "내가 여기까지 했으면 코드가 이렇게 되어야
한다"를 단계별로 비교해 보는 용도입니다.

## 사용법 (최초 1회)

    ./setup.sh

각 단계 완성본이 `_ref/<태그>/` 폴더로 펼쳐집니다. 폴더 안의 `README.md`에
그 단계에서 완성되어야 할 내용이 정리돼 있습니다. 서로 다른 단계를 동시에 열어
내 코드와 나란히 비교할 수 있습니다. (git worktree 방식 — 체크아웃으로 폴더가
바뀌지 않아 내 작업이 사라질 위험이 없습니다.)

## 단계 태그
| 태그 | 내용 |
|---|---|
| a10-mcp-server | Day1 · MCP Server |
| a11-fastapi | Day1 · FastAPI + Agent + MCP 통합 |
| a20-streaming | Day2 · Streaming |
| a21-multiagent-streaming | Day2 · Multi-Agent Streaming |
| a22-eval | Day2 · Observability & Eval |
| a30-error-handling | Day3 · Error Handling |
| a31-cost-latency | Day3 · Cost & Latency |
| a32-stateless | Day3 · Stateless Session |
| b10-supervisor-start | Part B · Supervisor 시작점 |
| b20-supervisor-final | Part B · Supervisor 최종(routing/validator/conditional/planning) |

> `refactor/v2` 브랜치는 product-grade 리팩터링 참고본(학습 범위 외)입니다.

## 실행에 필요한 것
각 완성본 실행에는 `.env`가 필요합니다. `.env.example`를 복사해 본인 키를 채우세요.
(`.env`는 저장소에 포함되지 않습니다. Python 의존성 환경은 과정에서 사전 구성됩니다.)
