"""速率限制器（RPM / TPM）。

实现为平滑令牌桶：
- 容量 = 每分钟限额，速率 = 限额/60 每秒连续补充；
- 超额时只睡眠"补足缺口"的时间，不再等到下一个整分钟边界；
- asyncio.Lock 保护，消除高并发下的计数竞态。

相比旧实现（分钟槽计数器 + 超限集体睡到下一分钟），吞吐更平滑，
不会出现"前 1 分钟打满 → 集体停摆最多 59s → 再集体突发"的锯齿模式。
"""

import asyncio
import time

from graphgen.utils import logger

# 单次等待上限，避免病态配置导致协程长时间挂起
_MAX_SLEEP_SECONDS = 120.0


class _TokenBucketLimiter:
    """基于令牌桶的平滑限流器基类。"""

    def __init__(self, limit_per_minute: int):
        # 兼容环境变量传入的字符串（如 RPM("1000")）
        try:
            limit_per_minute = int(limit_per_minute)
        except (TypeError, ValueError):
            limit_per_minute = 0
        if limit_per_minute <= 0:
            # 无限流
            limit_per_minute = 0

        self.limit = limit_per_minute
        self.rate_per_second = limit_per_minute / 60.0 if limit_per_minute else 0.0
        self.capacity = float(limit_per_minute)
        self.tokens = float(limit_per_minute)
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()
        self._total_waited = 0.0
        self._wait_count = 0

    @property
    def unlimited(self) -> bool:
        return self.limit <= 0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        if elapsed > 0 and self.capacity:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_second)
        self.last_refill = now

    async def acquire(self, amount: float = 1.0, silent: bool = False) -> None:
        """获取 amount 个令牌，不足时按补充速率平滑等待。"""
        if self.unlimited:
            return

        async with self.lock:
            while True:
                self._refill()
                if self.tokens >= amount:
                    self.tokens -= amount
                    return

                deficit = amount - self.tokens
                sleep_for = min(deficit / self.rate_per_second, _MAX_SLEEP_SECONDS)
                self._total_waited += sleep_for
                self._wait_count += 1
                if not silent:
                    logger.info(
                        "%s limit (%s/min) reached, smooth-waiting %.2fs",
                        type(self).__name__, self.limit, sleep_for,
                    )
                await asyncio.sleep(sleep_for)

    def stats(self) -> dict:
        return {
            "limit_per_minute": self.limit,
            "tokens_remaining": round(self.tokens, 1) if not self.unlimited else None,
            "total_waited_seconds": round(self._total_waited, 1),
            "wait_count": self._wait_count,
        }


class RPM(_TokenBucketLimiter):
    """每分钟请求数限制。amount 固定为 1（一次请求）。"""

    def __init__(self, rpm: int = 1000):
        super().__init__(rpm)

    async def wait(self, silent: bool = False, **kwargs) -> None:
        # 兼容旧签名：部分调用方可能传 token_count 之类的位置参数
        await self.acquire(1, silent=silent)


class TPM(_TokenBucketLimiter):
    """每分钟 token 数限制。amount = 本次请求的 token 估算。"""

    def __init__(self, tpm: int = 20000):
        super().__init__(tpm)

    async def wait(self, token_count: float = 1.0, silent: bool = False, **kwargs) -> None:
        try:
            amount = max(1.0, float(token_count))
        except (TypeError, ValueError):
            amount = 1.0
        await self.acquire(amount, silent=silent)
