"""
ICT 운영 지원 Agent용 MCP Server — Reference Implementation

본 파일은 노션 가이드 "410. MCP Server"의 학생 실습 결과를 비교하기 위한
참조 구현입니다. 단 하나의 정답이 아니며, 시그니처와 schema는 학습 의도에 맞게
달라질 수 있습니다.

구성:
- Tools: 운영 매뉴얼 검색, Jira 조회/생성, 모니터링 시스템 상태 조회
- Resources: Incident runbook
- Prompts: 장애 진단 표준 절차

실행:
  $ python server.py

Inspector (별도 터미널):
  $ npx @modelcontextprotocol/inspector python server.py
"""

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime
from typing import Literal, Optional
import json
import os

# Server instance — name은 client에 표시되는 식별자
mcp = FastMCP(name="ict-operations-support")

# Mock 데이터 경로
DATA_DIR = Path(__file__).parent / "data"


# ===========================================================================
# Pydantic 모델 (입출력 schema)
# ===========================================================================

class SystemStatus(BaseModel):
    """모니터링 시스템 상태 조회 결과"""
    system_name: str = Field(description="시스템 이름")
    status: str = Field(description="상태: healthy / degraded / down / unknown")
    cpu_percent: float = Field(description="CPU 사용률 (%)")
    memory_percent: float = Field(description="메모리 사용률 (%)")
    last_checked: str = Field(description="마지막 체크 시각 (ISO 8601)")
    alerts: list[str] = Field(default_factory=list, description="활성 알림 목록")


class ManualSnippet(BaseModel):
    """운영 매뉴얼 검색 결과 단일 항목"""
    title: str = Field(description="문서 제목 또는 식별자")
    source: str = Field(description="문서 경로 또는 URI")
    snippet: str = Field(description="질의에 매칭된 본문 일부")
    score: float = Field(description="유사도 점수 (높을수록 유사)")


class JiraTicket(BaseModel):
    """Jira ticket 검색 결과 단일 항목"""
    key: str = Field(description="Ticket key (예: OPS-123)")
    summary: str = Field(description="요약")
    status: str = Field(description="현재 상태 (예: Open, In Progress, Done)")
    priority: str = Field(description="우선순위 (예: Highest, High, Medium, Low)")
    assignee: Optional[str] = Field(default=None, description="담당자 이메일/계정")
    updated: str = Field(description="마지막 업데이트 시각 (ISO 8601)")


class JiraTicketCreated(BaseModel):
    """Jira ticket 생성 결과"""
    key: str = Field(description="생성된 ticket key")
    url: str = Field(description="ticket 조회 URL")
    summary: str = Field(description="제목")
    status: str = Field(description="초기 상태 (보통 'To Do')")
    created_at: str = Field(description="생성 시각 (ISO 8601)")


# ===========================================================================
# 1. Tool — 운영 매뉴얼 절차 검색  (TO-DO)
# ===========================================================================

@mcp.tool()
def search_operations_manual(query: str, top_k: int = 3) -> list[ManualSnippet]:
    """
    사내 운영 매뉴얼/문서에서 query에 가장 관련 있는 절차 스니펫을 검색합니다.

    장애 대응이나 절차 확인이 필요할 때, runbook·정책 문서 등에서 관련 부분을 찾아
    Agent에게 컨텍스트로 제공하기 위한 Tool입니다.

    Args:
        query: 자연어 검색 질의 (예: "DB 연결 timeout 발생 시 대응")
        top_k: 반환할 최대 결과 개수 (기본 3)

    Returns:
        ManualSnippet 리스트. score 내림차순 정렬.
    """
    # =====================================================================
    # mock retriever — 단순 키워드 매칭
    # data/runbooks/*.md 를 그대로 훑어서 키워드 빈도 기반으로 점수화
    # =====================================================================
    return _mock_manual_search(query, top_k)

    # =====================================================================
    # 실제 Vector DB로 교체 (Chroma + OpenAI Embeddings 예시)
    # 위 mock return을 주석 처리하고 아래 줄을 활성화하세요.
    # ---------------------------------------------------------------------
    # return _vector_manual_search(query, top_k)
    # =====================================================================


def _mock_manual_search(query: str, top_k: int) -> list[ManualSnippet]:
    """mock 구현. data/runbooks/*.md 에서 단순 키워드 매칭."""
    runbook_dir = DATA_DIR / "runbooks"
    if not runbook_dir.exists():
        return []

    keywords = [w.lower() for w in query.split() if len(w) > 1]
    scored: list[tuple[float, ManualSnippet]] = []

    for path in sorted(runbook_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        score = sum(lower.count(kw) for kw in keywords)
        if score == 0:
            continue
        # 첫 매칭 위치 주변 발췌
        idx = next((lower.find(kw) for kw in keywords if kw in lower), 0)
        snippet = text[max(0, idx - 80): idx + 220].strip()
        scored.append((
            float(score),
            ManualSnippet(
                title=path.stem,
                source=f"runbook://incident-response/{path.stem}",
                snippet=snippet,
                score=float(score),
            ),
        ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def _vector_manual_search(query: str, top_k: int) -> list[ManualSnippet]:
    """
    실제 Vector DB 구현 예시.
    사전에 data/chroma_db/ 에 운영 매뉴얼 임베딩이 인덱싱되어 있다고 가정합니다.
    """
    # lazy import — 의존성 로딩을 피하기 위해 함수 안에서 import
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    persist_dir = str(DATA_DIR / "chroma_db")
    vectordb = Chroma(
        collection_name="ops_runbooks",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
        persist_directory=persist_dir,
    )
    docs_with_score = vectordb.similarity_search_with_score(query, k=top_k)
    return [
        ManualSnippet(
            title=doc.metadata.get("title", doc.metadata.get("source", "untitled")),
            source=doc.metadata.get("source", ""),
            snippet=doc.page_content[:300],
            # Chroma score는 'distance' → 유사도로 변환 (clamp 0~1)
            score=float(max(0.0, 1.0 - distance)),
        )
        for doc, distance in docs_with_score
    ]


# ===========================================================================
# 2. Resource — Incident Runbook 가져오기  (Guide 제공)
# ===========================================================================

@mcp.resource("runbook://incident-response/{incident_type}")
def get_incident_runbook(incident_type: str) -> str:
    """
    특정 incident 유형의 runbook을 반환합니다.

    Runbook은 incident 발생 시 따라야 할 표준 대응 절차를 담은 markdown 문서입니다.
    URI 패턴: runbook://incident-response/{incident_type}

    예시 incident_type:
    - db-down: 데이터베이스 다운 대응
    - api-latency: API 지연 대응
    - auth-failure: 인증 실패 급증 대응

    Args:
        incident_type: incident 유형 식별자 (URI 변수와 동일한 인자명이어야 함)

    Returns:
        Markdown 형식의 runbook 본문. 해당 incident_type이 없으면 안내 문자열.
    """
    runbook_path = DATA_DIR / "runbooks" / f"{incident_type}.md"
    if not runbook_path.exists():
        return f"# Runbook Not Found\n\nNo runbook for incident type: {incident_type}"
    return runbook_path.read_text(encoding="utf-8")


# ===========================================================================
# 3. Tool — Jira ticket 검색  (TO-DO)
# ===========================================================================

@mcp.tool()
def search_jira_tickets(
    query: str,
    project_key: str = "OPS",
    max_results: int = 5,
) -> list[JiraTicket]:
    """
    Jira에서 query 조건에 맞는 ticket을 검색합니다.

    Read-only이지만 시점마다 결과가 달라지고 외부 시스템을 호출하므로 Tool로 분류합니다.
    동일 시스템에 대해 진행 중인 incident 유무, 같은 증상의 과거 ticket 등을 조사할 때
    호출합니다.

    환경변수:
        JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN 이 모두 설정되어 있으면 실제 API를
        호출하고, 그렇지 않으면 시연용 mock 응답을 반환합니다.

    Args:
        query: 자유 텍스트 검색어 (예: "auth-service login error")
        project_key: 검색할 Jira 프로젝트 key (기본 "OPS")
        max_results: 반환할 최대 ticket 수 (기본 5)

    Returns:
        JiraTicket 리스트. 최근 업데이트 순.
    """
    base_url = os.getenv("JIRA_BASE_URL")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")

    # 환경변수가 하나라도 비어 있으면 mock 응답 (수업/오프라인 환경 대비)
    if not (base_url and email and token):
        return _mock_jira_search(query, project_key, max_results)

    import httpx
    jql = f'project = {project_key} AND text ~ "{query}" ORDER BY updated DESC'
    resp = httpx.get(
        f"{base_url.rstrip('/')}/rest/api/3/search",
        params={
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,status,priority,assignee,updated",
        },
        auth=(email, token),
        timeout=10.0,
    )
    resp.raise_for_status()
    issues = resp.json().get("issues", [])
    return [
        JiraTicket(
            key=i["key"],
            summary=i["fields"]["summary"],
            status=i["fields"]["status"]["name"],
            priority=(i["fields"].get("priority") or {}).get("name", "Unknown"),
            assignee=(i["fields"].get("assignee") or {}).get("emailAddress"),
            updated=i["fields"]["updated"],
        )
        for i in issues
    ]


def _mock_jira_search(query: str, project_key: str, max_results: int) -> list[JiraTicket]:
    """JIRA_* 환경변수 미설정 시 사용하는 시연용 고정 응답."""
    now = datetime.now().isoformat()
    samples = [
        JiraTicket(
            key=f"{project_key}-101",
            summary=f"[mock] '{query}' 관련 incident 조사",
            status="In Progress",
            priority="High",
            assignee="ops-oncall@example.com",
            updated=now,
        ),
        JiraTicket(
            key=f"{project_key}-87",
            summary=f"[mock] '{query}' 과거 발생 사례 (resolved)",
            status="Done",
            priority="Medium",
            assignee=None,
            updated=now,
        ),
    ]
    return samples[:max_results]


# ===========================================================================
# 4. Tool — Jira ticket 생성  (TO-DO)
# ===========================================================================

@mcp.tool()
def create_jira_ticket(
    summary: str,
    description: str,
    project_key: str = "OPS",
    issue_type: Literal["Bug", "Incident", "Task"] = "Incident",
    priority: Literal["Highest", "High", "Medium", "Low"] = "High",
) -> JiraTicketCreated:
    """
    Jira에 새 ticket을 생성합니다 (Action을 수행하는 Tool).

    장애 대응 워크플로우에서 새 incident 기록을 남길 때 호출합니다.
    이 함수는 외부 시스템 상태를 변경하므로, agent는 사용자 확인 없이 자동
    호출하지 말고 반드시 사용자에게 생성 여부를 확인한 뒤 호출하는 것을 권장합니다.

    환경변수가 비어 있으면 실제 ticket을 만들지 않고 mock 응답만 반환합니다.

    Args:
        summary: ticket 제목 (예: "auth-service 로그인 실패율 급증")
        description: 본문 (재현 절차, 영향 범위, 첨부 정보 등)
        project_key: 생성할 프로젝트 key (기본 "OPS")
        issue_type: issue 유형 (기본 "Incident")
        priority: 우선순위 (기본 "High")

    Returns:
        JiraTicketCreated. 생성된 ticket의 key, URL, 초기 상태 포함.
    """
    base_url = os.getenv("JIRA_BASE_URL")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")

    # 환경변수 미설정 시 mock — 모양만 반환하여 워크플로우 검증 가능
    if not (base_url and email and token):
        now = datetime.now().isoformat()
        fake_key = f"{project_key}-9999"
        return JiraTicketCreated(
            key=fake_key,
            url=f"https://example.atlassian.net/browse/{fake_key}",
            summary=summary,
            status="To Do",
            created_at=now,
        )

    import httpx
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            # Atlassian Document Format (ADF)
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}],
                }],
            },
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }
    }
    resp = httpx.post(
        f"{base_url.rstrip('/')}/rest/api/3/issue",
        json=payload,
        auth=(email, token),
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json()
    key = data["key"]
    return JiraTicketCreated(
        key=key,
        url=f"{base_url.rstrip('/')}/browse/{key}",
        summary=summary,
        status="To Do",
        created_at=datetime.now().isoformat(),
    )


# ===========================================================================
# 5. Tool — 모니터링 시스템 상태 조회  (Guide 제공)
# ===========================================================================

@mcp.tool()
def get_monitoring_status(system_name: str) -> SystemStatus:
    """
    지정된 시스템의 현재 모니터링 상태를 조회합니다.

    장애 진단·incident 대응 시 시스템의 호출 시점 상태(CPU, 메모리, 활성 알림)를
    확인하는 데 사용합니다.

    Args:
        system_name: 조회 대상 시스템 이름 (예: "auth-service", "payment-db")

    Returns:
        SystemStatus 객체. 시스템이 monitoring.json에 없으면 status='unknown'.
    """
    monitoring_path = DATA_DIR / "monitoring.json"
    if not monitoring_path.exists():
        return SystemStatus(
            system_name=system_name,
            status="unknown",
            cpu_percent=0.0,
            memory_percent=0.0,
            last_checked=datetime.now().isoformat(),
            alerts=["monitoring.json not found"],
        )

    monitoring_data = json.loads(monitoring_path.read_text(encoding="utf-8"))
    if system_name not in monitoring_data:
        return SystemStatus(
            system_name=system_name,
            status="unknown",
            cpu_percent=0.0,
            memory_percent=0.0,
            last_checked=datetime.now().isoformat(),
            alerts=[f"System '{system_name}' not found in monitoring"],
        )

    data = monitoring_data[system_name]
    return SystemStatus(
        system_name=system_name,
        status=data["status"],
        cpu_percent=data["cpu_percent"],
        memory_percent=data["memory_percent"],
        last_checked=datetime.now().isoformat(),
        alerts=data.get("alerts", []),
    )


# ===========================================================================
# 6. Prompt — 장애 진단 표준 절차 제공  (Guide 제공)
# ===========================================================================

@mcp.prompt()
def incident_analysis_prompt(system_name: str, symptom: str) -> str:
    """
    장애 진단을 위한 표준 분석 절차 프롬프트를 생성합니다.

    사용자가 장애를 신고했을 때 agent가 따라야 할 분석 단계를 정의합니다.
    이 prompt를 통해 호출되면 agent는 일관된 진단 워크플로우를 수행합니다.

    Args:
        system_name: 장애가 발생한 시스템 이름
        symptom: 사용자가 보고한 증상

    Returns:
        Agent에게 전달될 분석 지시 prompt (markdown 형식).
    """
    return f"""
다음 장애에 대해 표준 진단 절차를 수행하세요.

## 장애 정보
- 시스템: {system_name}
- 증상: {symptom}

## 진단 절차 (반드시 순서대로 수행)

1. **현재 상태 확인**: get_monitoring_status Tool로 {system_name}의 현재 상태를 조회하세요.
2. **Runbook 참조**: 증상에 해당하는 runbook이 있는지 확인하세요.
   (예: 'api-latency', 'db-down', 'auth-failure')
3. **관련 ticket 확인**: search_jira_tickets로 같은 시스템에 대한 최근 Jira ticket이 있는지 검색하세요.
4. **종합 분석**: 위 3가지 정보를 종합해 가능한 원인과 권장 조치를 제시하세요.
5. **Ticket 생성 제안**: 사용자에게 새 incident ticket 생성 여부를 확인 후 create_jira_ticket을 호출하세요.

각 단계에서 얻은 정보를 사용자에게 명시적으로 보고하면서 진행하세요.
""".strip()


# ===========================================================================
# Server 실행
# ===========================================================================

if __name__ == "__main__":
    mcp.run()
