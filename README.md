# AI Agent Capstone — 단계별 참조 저장소

각 실습 단계의 "완성본 코드"를 확인하기 위한 참조용 저장소입니다.
직접 코딩하는 작업 폴더가 아니라, "내가 여기까지 했으면 코드가 이렇게 되어야
한다"를 단계별로 비교해 보는 용도 입니다.

## 사용법

### 사전 준비
Git 설치가 되어 있지 않다면, 아래 내용 참고하여 설치 바랍니다. 
- 설치 확인 : 터미널에서 `git --version` 실행 후 버전 확인
- 설치 필요 : [Homebrew](https://brew.sh) 사용 시 `brew install git` 

### 실행 (최초 1회) 
```bash
# 1. 저장소 클론 및 이동 
git clone https://github.com/elizabeth-kj-bae/capstone-v1.git
cd capstone-v1

# 2. 참조 폴더(_ref) 자동 생성 스크립트 실행 
bash setup.sh
```

실행하면 각 단계 완성본이 `_ref/<태그>/` 폴더로 펼쳐집니다. 폴더 안의 `README.md`에
그 단계에서 완성되어야 할 내용이 정리돼 있습니다. 서로 다른 단계를 동시에 열어
각자 작성한 코드와 나란히 비교하세요. (git worktree 방식 — 체크아웃으로 폴더가
바뀌지 않아 내 작업이 사라질 위험이 없습니다.)

### 단계 태그
| 태그 | 내용 |
|---|---|
| a10-mcp-server | Part A · MCP Server |
| a11-fastapi | Part A · FastAPI + Agent + MCP 통합 |
| a20-streaming | Part A · Streaming |
| a21-multiagent-streaming | Part A · Multi-Agent Streaming |
| a22-eval | Part A · Observability & Eval |
| a30-error-handling | Part A · Error Handling |
| a31-cost-latency | Part A · Cost & Latency |
| a32-stateless | Part A · Stateless Session |
| b10-supervisor-start | Part B · Supervisor 시작점 |
| b20-supervisor-final | Part B · Supervisor 최종(routing/validator/conditional/planning) |

> `refactor/v2` 브랜치는 Part C · product-grade 리팩터링 참고본 입니다.

## 환경 설정 
각 완성본 실행에는 `.env`가 필요합니다. 과정 전에 안내된 노션 참고하여 구성 합니다.
