import asyncio

import pytest

from retrykit import RetryPolicy, run_with_retry


def test_no_delay_after_last_failed_attempt():
    sleeps = []

    async def scenario():
        async def operation():
            raise LookupError("still unavailable")

        async def sleep(delay):
            sleeps.append(delay)

        with pytest.raises(LookupError, match="unavailable"):
            await run_with_retry(operation, RetryPolicy(max_attempts=2, base_delay=0.25), sleep=sleep)

    asyncio.run(scenario())
    assert sleeps == [0.25]


def test_exponential_delays_only_between_attempts_before_success():
    sleeps = []
    attempts = 0

    async def scenario():
        nonlocal attempts

        async def operation():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise OSError("temporary")
            return 42

        async def sleep(delay):
            sleeps.append(delay)

        return await run_with_retry(operation, RetryPolicy(max_attempts=4, base_delay=0.1), sleep=sleep)

    assert asyncio.run(scenario()) == 42
    assert attempts == 3
    assert sleeps == [0.1, 0.2]


def test_cancellation_is_propagated_without_retry_or_sleep():
    attempts = 0
    sleeps = []

    async def scenario():
        nonlocal attempts

        async def operation():
            nonlocal attempts
            attempts += 1
            raise asyncio.CancelledError

        async def sleep(delay):
            sleeps.append(delay)

        with pytest.raises(asyncio.CancelledError):
            await run_with_retry(operation, RetryPolicy(max_attempts=4), sleep=sleep)

    asyncio.run(scenario())
    assert attempts == 1
    assert sleeps == []
