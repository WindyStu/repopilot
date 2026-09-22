import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from retrykit.policy import RetryPolicy

T = TypeVar("T")


async def run_with_retry(
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    last_error: Exception | None = None
    for attempt in range(policy.max_attempts):
        try:
            return await operation()
        except Exception as error:
            last_error = error
            await sleep(policy.delay_for(attempt))
    assert last_error is not None
    raise last_error
