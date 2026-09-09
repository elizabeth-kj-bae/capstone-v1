"""
LangGraph Checkpointer 생성 및 lifecycle 관리.

Stateful 세션 관리 강화:
- MemorySaver → AsyncPostgresSaver 전환
- FastAPI lifespan에서 connection lifecycle 관리
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


def get_database_url() -> str:
    """환경 변수에서 PostgreSQL connection URL 반환."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL 환경 변수가 설정되지 않았습니다. "
            ".env 파일을 확인하세요."
        )
    return url


@asynccontextmanager
async def create_checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    """
    AsyncPostgresSaver를 lifecycle context로 제공.
    
    사용 방식 (FastAPI lifespan 안에서):
        async with create_checkpointer() as checkpointer:
            # checkpointer 사용
            ...
    
    Context 종료 시 자동으로 connection 정리.
    """
    db_url = get_database_url()
    
    async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
        # 최초 사용 시 필요한 테이블 생성
        # (이미 생성되어 있으면 idempotent)
        await checkpointer.setup()
        
        yield checkpointer
