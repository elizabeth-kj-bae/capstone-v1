"""
본 capstone 시스템의 Cost/Latency 벤치마크.

같은 질문 셋을 N회 실행하여 평균 latency와 추정 cost 측정.
최적화 전/후 비교 시 사용.
"""
import asyncio
import os
import sys
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR.parent / ".env")

from agent.supervisor_graph import build_supervisor_graph


# 본 capstone 도메인의 benchmark 질문 셋
BENCHMARK_QUESTIONS = [
    "데이터베이스 다운 시 대응 절차를 알려주세요.",
    "auth-service 시스템 상태와 관련 ticket을 알려주세요.",
    "운영 매뉴얼과 최근 incident를 종합해 장애 대응 가이드를 만들어 주세요.",
    "네트워크 장애 시 첫 단계는?",
    "최근 발생한 critical 등급 incident 목록을 알려주세요.",
]


async def benchmark_single_request(graph, question: str) -> dict:
    """단일 요청의 latency 측정."""
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    start = time.perf_counter()
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": question}]},
        config=config,
    )
    elapsed = time.perf_counter() - start
    
    return {
        "question": question[:50],
        "latency_seconds": round(elapsed, 2),
        "num_tasks": len(result.get("tasks", [])),
        "completed_tasks": sum(1 for t in result.get("tasks", []) if t.get("status") == "completed"),
        "failed_tasks": sum(1 for t in result.get("tasks", []) if t.get("status") == "failed"),
    }


async def main():
    """벤치마크 실행."""
    print("Building supervisor graph...")
    graph = await build_supervisor_graph()
    
    print(f"\nRunning benchmark on {len(BENCHMARK_QUESTIONS)} questions...\n")
    
    results = []
    for q in BENCHMARK_QUESTIONS:
        print(f"Running: {q[:50]}...")
        result = await benchmark_single_request(graph, q)
        results.append(result)
        print(f"  → Latency: {result['latency_seconds']}s, "
              f"Tasks: {result['completed_tasks']} done / {result['failed_tasks']} failed")
    
    # 요약
    avg_latency = sum(r["latency_seconds"] for r in results) / len(results)
    avg_tasks = sum(r["num_tasks"] for r in results) / len(results)
    
    print(f"\n=== Summary ===")
    print(f"Total requests: {len(results)}")
    print(f"Average latency: {avg_latency:.2f}s")
    print(f"Average tasks per request: {avg_tasks:.1f}")
    
    print(f"\n=== Detailed Results ===")
    for r in results:
        print(f"  {r['latency_seconds']:>5.2f}s | {r['question']}")
    
    print(f"\nDetailed cost/token analysis: check LangSmith trace UI")
    print(f"Project: {os.environ.get('LANGSMITH_PROJECT', 'default')}")


if __name__ == "__main__":
    asyncio.run(main())
