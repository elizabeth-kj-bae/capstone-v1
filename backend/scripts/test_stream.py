# 임시 테스트 코드 
import asyncio
from agent.graph import build_agent
from streaming.event_converter import convert_langgraph_events

async def test_stream():
    agent = await build_agent()
    langgraph_stream = agent.astream(
        {"messages": [{"role": "user", "content": "운영 매뉴얼 검색해 주세요"}]},
        config={"configurable": {"thread_id": "test-001"}},
        stream_mode=["messages", "updates"],
    )
    async for event in convert_langgraph_events(langgraph_stream, "test-001"):
        print(event.model_dump_json())

asyncio.run(test_stream())
