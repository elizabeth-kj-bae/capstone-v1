"""Routing 노드.

사용자 질문의 복잡도를 판단하여 처리 경로 결정.

- routing_node:         simple/complex 분기 판단
- simple_response_node: simple 경로의 직접 응답 생성
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .. import prompts
from ..deps import SupervisorDeps
from ..schemas import RoutingDecision
from ..state import SupervisorState


async def routing_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """사용자 질문의 복잡도를 판단하여 경로 결정.

    - simple:  Supervisor가 LLM 한 번으로 직접 답변
    - complex: 기존 multi-agent flow (Planning → Research → Writing)

    Structured output(RoutingDecision)으로 분류 안정성 확보.
    """
    user_msg = state["messages"][-1].content
    routing_prompt = prompts.ROUTING_PROMPT_TEMPLATE.format(user_msg=user_msg)

    decision = await deps.fast_llm.with_structured_output(
        RoutingDecision
    ).ainvoke(
        [
            SystemMessage(content="You are a routing classifier."),
            HumanMessage(content=routing_prompt),
        ]
    )

    return {
        "route": decision.route,
        "route_reasoning": decision.reasoning,
    }


async def simple_response_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """단순 질문에 LLM 한 번 호출로 직접 답변.

    Plan, Task list 없이 바로 응답. simple 경로의 종료 노드로,
    이 노드 다음에 바로 END로 흐름.
    """
    user_msg = state["messages"][-1].content

    response = await deps.quality_llm.ainvoke(
        [
            SystemMessage(content=prompts.SIMPLE_RESPONSE_SYSTEM),
            HumanMessage(content=user_msg),
        ]
    )

    return {"messages": [AIMessage(content=response.content)]}
