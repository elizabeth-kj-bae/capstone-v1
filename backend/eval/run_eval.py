"""
본 capstone supervisor multi-agent에 대한 LangSmith Evaluation.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR.parent / ".env")

import asyncio
import uuid
from langsmith import aevaluate
from langgraph.checkpoint.memory import MemorySaver
from agent.supervisor_graph import build_supervisor_graph
from eval.evaluators import has_expected_topics, response_quality_judge


async def target_function(inputs: dict) -> dict:
    """
    Eval의 대상: supervisor multi-agent.
    
    Args:
        inputs: {"message": "..."}
    
    Returns:
        agent의 응답 dict
    """
    graph = await build_supervisor_graph(MemorySaver())  # a32부터 checkpointer 외부 주입 필수 → 오프라인 스크립트는 in-memory 사용
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": inputs["message"]}]},
        config=config,
    )
    
    # 최종 응답과 메타데이터 추출
    final_response = result["messages"][-1].content
    tools_used = []
    for task in result.get("tasks", []):
        # task의 결과에서 tool 호출 정보 추출 (단순화)
        # 실제로는 trace metadata에서 추출하는 것이 더 정확
        pass
    
    return {
        "response": final_response,
        "plan": result.get("plan", ""),
        "tasks": result.get("tasks", []),
    }


async def main():
    # 위에서 정의한 target_function, evaluators 사용
    results = await aevaluate(
        target_function,
        data="capstone-ict-operations",
        evaluators=[has_expected_topics, response_quality_judge],
        experiment_prefix="supervisor-v1",
        description="본 capstone supervisor multi-agent 첫 평가",
        max_concurrency=2,  # 동시 실행 수
    )
    
    print("Evaluation completed.")
    print(f"View at: https://smith.langchain.com/...")


if __name__ == "__main__":
    asyncio.run(main())
