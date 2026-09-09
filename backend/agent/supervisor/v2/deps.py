"""Supervisor graph의 의존성 정의.

LLM 인스턴스와 sub-agent를 캡슐화한 SupervisorDeps와 factory.
build_supervisor_graph가 호출 시 1회 생성하고, 모든 node 함수에 명시적으로 주입.
"""

from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent.mcp_client import get_mcp_tools
from config import FAST_MODEL, QUALITY_MODEL

from . import prompts


@dataclass
class SupervisorDeps:
    """Node 함수가 사용하는 외부 의존성 집합.

    Cost & Latency 최적화 위해 LLM을 단계별로 분리:
    - fast_llm:    분류·구조화 task (config.FAST_MODEL)
    - quality_llm: 정보 추출 + 응답 생성 (config.QUALITY_MODEL)
    """

    fast_llm: BaseChatModel
    quality_llm: BaseChatModel
    research_agent: Any
    writing_agent: Any
    analysis_agent: Any
    validator_llm: BaseChatModel


async def build_supervisor_deps() -> SupervisorDeps:
    """LLM과 sub-agent를 생성하는 factory.

    호출 1회당:
    - LLM 인스턴스 2개 생성 (fast, quality)
    - MCP tools 1회 조회 (외부 IO)
    - Sub-agent 3개 생성 (research, writing, analysis)

    Returns:
        SupervisorDeps: 모든 노드가 공유할 의존성 객체.
    """
    fast_llm = init_chat_model(FAST_MODEL, temperature=0)
    quality_llm = init_chat_model(QUALITY_MODEL, temperature=0)

    mcp_tools = await get_mcp_tools()

    research_agent = create_agent(
        model=quality_llm,
        tools=mcp_tools,
        system_prompt=prompts.RESEARCH_AGENT_SYSTEM,
    )
    writing_agent = create_agent(
        model=quality_llm,
        tools=[],
        system_prompt=prompts.WRITING_AGENT_SYSTEM,
    )
    analysis_agent = create_agent(
        model=quality_llm,
        tools=[],
        system_prompt=prompts.ANALYSIS_AGENT_SYSTEM,
    )

    return SupervisorDeps(
        fast_llm=fast_llm,
        quality_llm=quality_llm,
        research_agent=research_agent,
        writing_agent=writing_agent,
        analysis_agent=analysis_agent,
        validator_llm=quality_llm,
    )
