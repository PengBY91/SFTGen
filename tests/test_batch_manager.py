"""BatchRequestManager 调度行为测试。

重点验证锁外处理改造：
- 结果正确性（含不满一批的尾部队列）
- 批次之间不再锁步——在飞请求数可以超过 batch_size
"""

import asyncio
import time

from graphgen.utils.batch_request_manager import BatchRequestManager


class DelayedLLMClient:
    """记录并发在飞数的延迟 mock。"""

    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.in_flight = 0
        self.max_in_flight = 0
        self.calls = 0

    async def generate_answer(self, prompt, history=None, **extra):
        self.calls += 1
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(self.delay)
        self.in_flight -= 1
        return f"resp-{prompt}"


def test_batch_manager_results_correct():
    """12 个请求、batch_size=5：两个满批 + 尾部 2 个经定时器处理。"""
    client = DelayedLLMClient(0.05)
    mgr = BatchRequestManager(client, batch_size=5, max_wait_time=0.05)

    async def run():
        tasks = [mgr.add_request(f"p{i}") for i in range(12)]
        return await asyncio.gather(*tasks)

    results = asyncio.run(run())
    assert results == [f"resp-p{i}" for i in range(12)]


def test_batch_manager_batches_overlap():
    """60 个请求、batch_size=10、每请求 0.3s：

    旧实现持有 queue_lock 等整批完成（在飞 ≤ 10，总耗时 ≈ 6×0.3s）；
    新实现批次并发启动，在飞数应远超 batch_size，总耗时接近单请求延迟。
    """
    client = DelayedLLMClient(0.3)
    mgr = BatchRequestManager(client, batch_size=10, max_wait_time=0.1)

    async def run():
        tasks = [mgr.add_request(f"p{i}") for i in range(60)]
        return await asyncio.gather(*tasks)

    start = time.time()
    results = asyncio.run(run())
    elapsed = time.time() - start

    assert len(results) == 60
    assert all(r == f"resp-p{i}" for i, r in enumerate(results))
    assert client.max_in_flight > 10, (
        f"expected overlapping batches, max_in_flight={client.max_in_flight}"
    )
    assert elapsed < 1.5, f"batches appear serialized: {elapsed:.2f}s"


class FlakyLLMClient(DelayedLLMClient):
    async def generate_answer(self, prompt, history=None, **extra):
        if "bad" in prompt:
            raise RuntimeError("boom")
        return await super().generate_answer(prompt, history, **extra)


def test_batch_manager_error_propagates():
    """单个请求失败时异常传回对应 future，其他请求不受影响。"""
    client = FlakyLLMClient(0.02)
    mgr = BatchRequestManager(client, batch_size=4, max_wait_time=0.02)

    async def run():
        good1 = asyncio.create_task(mgr.add_request("good-1"))
        bad = asyncio.create_task(mgr.add_request("bad"))
        good2 = asyncio.create_task(mgr.add_request("good-2"))
        results = []
        results.append(await good1)
        try:
            await bad
            raised = False
        except RuntimeError:
            raised = True
        results.append(await good2)
        return results, raised

    results, raised = asyncio.run(run())
    assert raised, "failure should propagate to its own future"
    assert results == ["resp-good-1", "resp-good-2"]
