"""限流器（令牌桶）行为测试。"""

import asyncio
import time

from graphgen.models.llm.limitter import RPM, TPM


def test_string_limit_coerced():
    """环境变量传入字符串限额不应崩溃（旧实现 RPM("1000") 会在比较时 TypeError）。"""
    limiter = RPM("1000")
    assert limiter.limit == 1000
    tpm = TPM("50000")
    assert tpm.limit == 50000


def test_burst_up_to_capacity_passes():
    """容量内的突发请求应立即通过。"""
    rpm = RPM(100)

    async def run():
        await asyncio.gather(*(rpm.wait(silent=True) for _ in range(50)))

    start = time.time()
    asyncio.run(run())
    assert time.time() - start < 1.0


def test_over_capacity_smoothly_waits():
    """超出容量后按补充速率平滑等待，而不是睡到下一个整分钟。"""
    # TPM=600 → 每秒补充 10 个 token
    tpm = TPM(600)

    async def run():
        await tpm.wait(600, silent=True)  # 清空桶
        start = time.monotonic()
        await tpm.wait(10, silent=True)  # 需等待 ~1s 补充
        return time.monotonic() - start

    elapsed = asyncio.run(run())
    assert 0.8 <= elapsed <= 3.0, f"smooth wait out of range: {elapsed:.2f}s"


def test_concurrent_acquire_no_overshoot():
    """高并发下不超发：容量 30、并发 31 次 acquire(1)，至少 1 次平滑等待且全部完成。"""
    rpm = RPM(30)  # 容量 30，每秒 0.5 个

    async def run():
        results = await asyncio.gather(
            *(rpm.wait(silent=True) for _ in range(31)), return_exceptions=True
        )
        return results

    start = time.time()
    results = asyncio.run(run())
    elapsed = time.time() - start
    assert all(r is None for r in results)
    # 第 31 个请求需要等待补 token（0.5 个/秒 → ~2s）
    assert elapsed >= 1.5, f"overshoot suspected: {elapsed:.2f}s"
    assert rpm.stats()["wait_count"] >= 1
