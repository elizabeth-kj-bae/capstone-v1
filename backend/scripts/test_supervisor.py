# 임시 테스트 코드
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from langgraph.checkpoint.memory import MemorySaver
from agent.supervisor_graph import build_supervisor_graph


async def test():
    graph = await build_supervisor_graph(MemorySaver())  # a32부터 checkpointer 외부 주입 필수 → 오프라인 스크립트는 in-memory 사용
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "운영 매뉴얼 검색해서 DB 다운 시 절차 알려주세요"}]},
        config={"configurable": {"thread_id": "test"}},
    )
    print("Plan:", result["plan"])
    print("Tasks:")
    for t in result["tasks"]:
        print(f"  - {t['description']} [{t['status']}]")
    print("Final:", result["messages"][-1].content[:200])


asyncio.run(test())
