import asyncio

from retrykit import RetryPolicy, run_with_retry


def test_returns_first_result_without_sleeping():
    sleeps = []

    async def scenario():
        async def operation():
            return "ok"

        async def sleep(delay):
            sleeps.append(delay)

        return await run_with_retry(operation, RetryPolicy(), sleep=sleep)

    assert asyncio.run(scenario()) == "ok"
    assert sleeps == []
