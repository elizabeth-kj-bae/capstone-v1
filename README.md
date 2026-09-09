# a10 · MCP Server (Day1)

이 태그는 **MCP Server 단계의 완성본**입니다. 여기까지 하면 코드가 아래 상태가 되어야 합니다.

## 이 단계에서 완성되어야 할 것
- `mcp-server/server.py` — FastMCP 기반 MCP 서버
  - **Tool 4개**: 운영 매뉴얼 검색 / 모니터링 상태 조회 / Jira 티켓 조회 / Jira 티켓 생성
  - **Resource 1개**: incident runbook 조회
  - **Prompt 1개**: 장애 진단 표준 절차
- MCP Inspector로 각 capability 동작 확인

## 다음 단계
`a11-fastapi` — FastAPI에서 이 MCP 서버를 Agent로 호출
