"""Analysis 노드.

Analysis task들을 병렬 실행하는 노드.

- execute_analysis_tasks_node: 모든 analysis task를 asyncio.gather로
  병렬 호출. Research 결과를 context로 받아 패턴 식별·비교·통합 등 분석
  활동 수행. 결과는 Writing agent가 활용.

Research와의 차이:
    - Research는 MCP tool을 호출 (외부 IO)
    - Analysis는 LLM 호출만 (tool 없음, deps.analysis_agent)
    - 둘 다 병렬 실행 가능하나 의존 순서: research → analysis → writing
"""

import asyncio

from langchain_core.messages import HumanMessage

from ..deps import SupervisorDeps
from ..state import SupervisorState


async def execute_analysis_tasks_node(
    state: SupervisorState, deps: SupervisorDeps
) -> dict:
    """Analysis task들을 실행.

    Cost/Latency 최적화:
        - 여러 analysis task가 있으면 asyncio.gather로 병렬 실행
        - Research와 같은 패턴

    Context:
        - 완료된 모든 research 결과를 한 context로 결합
        - 각 analysis task가 동일 context를 받아 독립적으로 수행
        - Analysis 결과는 이후 Writing agent가 활용

    Error Handling:
        - 실패 task는 status='failed' + error_message로 마킹
        - Tool 호출이 없으므로 ToolError 분기 불필요
          (general Exception만 처리)

    Returns:
        tasks: 갱신된 task 목록
    """
    tasks = state["tasks"].copy()

    # Analysis task indices 추출
    analysis_indices = [
        i for i, t in enumerate(tasks) if t["agent"] == "analysis"
    ]

    # Analysis task가 없으면 통과
    if not analysis_indices:
        return {"tasks": tasks}

    # Research 결과 context 준비 (analysis가 직접 활용하므로 truncate 없음)
    research_results = "\n\n".join(
        [
            f"- {t['description']}\n  결과: {t['result']}"
            for t in tasks
            if t["agent"] == "research"
            and t.get("status") == "completed"
            and t.get("result")
        ]
    )

    # 각 analysis task를 in_progress로 표시
    for i in analysis_indices:
        tasks[i] = {**tasks[i], "status": "in_progress"}

    async def run_single_analysis(idx: int) -> tuple[int, dict]:
        """단일 analysis task 실행. (index, updated_task) 반환."""
        task = tasks[idx]

        analysis_context = (
            f"[Research 결과]\n{research_results}\n\n"
            f"[분석 task]\n{task['description']}\n\n"
            f"위 Research 결과를 바탕으로 분석 task를 수행하세요."
        )

        try:
            result = await deps.analysis_agent.ainvoke(
                {"messages": [HumanMessage(content=analysis_context)]},
            )
            result_text = result["messages"][-1].content
            return idx, {
                **task,
                "status": "completed",
                "result": result_text,
            }
        except Exception:
            return idx, {
                **task,
                "status": "failed",
                "result": None,
                "error_message": "분석 중 오류가 발생했습니다",
            }

    # asyncio.gather로 병렬 실행
    results = await asyncio.gather(
        *[run_single_analysis(idx) for idx in analysis_indices]
    )

    # 결과 반영
    for idx, updated_task in results:
        tasks[idx] = updated_task

    return {"tasks": tasks}
