"""
Retry 정책.

본 capstone 결정:
- Transient error에만 retry
- 최대 2회 재시도 (총 3회 시도)
- Exponential backoff: 0.5초, 1.5초
"""
import asyncio
from typing import Callable, Awaitable, TypeVar
from schemas.error import ToolError

T = TypeVar("T")


async def with_retry(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 2,
    initial_delay: float = 0.5,
    tool_name: str = "unknown",
) -> T:
    """
    함수를 retry policy로 감싸 실행.
    
    Args:
        func: 호출할 async 함수
        max_retries: 최대 재시도 횟수
        initial_delay: 첫 재시도 전 대기 시간 (초)
        tool_name: 실패 시 error에 포함할 tool 이름
    
    Returns:
        함수의 결과
    
    Raises:
        ToolError: 모든 retry 실패 시
    """
    delay = initial_delay
    last_exception: Exception | None = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except asyncio.TimeoutError as e:
            last_exception = e
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 3  # Exponential backoff
            continue
        except Exception as e:
            # Timeout이 아닌 error는 즉시 raise (transient 아님)
            raise ToolError(
                code="TOOL_EXECUTION_ERROR",
                message=f"Tool {tool_name} failed: {str(e)}",
                tool_name=tool_name,
                recoverable=True,
            )
    
    # 모든 retry 실패
    raise ToolError(
        code="TOOL_TIMEOUT_AFTER_RETRY",
        message=f"Tool {tool_name} timeout after {max_retries + 1} attempts: {str(last_exception)}",
        tool_name=tool_name,
        recoverable=True,
    )
