"""
LangGraph agent 정의.

capstone의 결정 1, 3의 구현:
- 결정 1: Agent가 tool로 retrieval 호출 → ReAct agent + MCP tools
- 결정 3: In-memory state → MemorySaver checkpointer
"""
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI  # 또는 langchain_anthropic
from .mcp_client import get_mcp_tools


# System prompt: agent의 역할 정의
SYSTEM_PROMPT = """\
당신은 ICT 운영 지원 agent입니다.

다음 능력을 가지고 있습니다:
- 사내 운영 매뉴얼 검색
- Incident runbook 조회
- 장애 ticket 검색 및 생성
- 모니터링 시스템 상태 확인
- 장애 진단 표준 절차 수행

사용자의 운영 관련 질문에 위 도구들을 적절히 활용하여 답하세요.
어떤 도구를 호출했는지, 그 결과로 무엇을 알았는지 사용자에게 명확히 전달하세요.
"""


async def build_agent():
    """
    LangGraph ReAct agent 생성.

    Returns:
        Compiled LangGraph (checkpointer 포함)
    """
    # MCP server에서 Tool 로드
    tools = await get_mcp_tools()

    # LLM 설정
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # Checkpointer: in-memory
    checkpointer = MemorySaver()

    # ReAct agent 생성
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return agent
