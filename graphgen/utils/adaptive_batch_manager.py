"""
自适应批量请求管理器
根据API响应时间和错误率动态调整批量大小
"""

import time
from typing import Optional
from graphgen.utils.batch_request_manager import BatchRequestManager
from graphgen.utils.log import logger


class AdaptiveBatchRequestManager(BatchRequestManager):
    """
    自适应批量请求管理器
    根据API响应时间和错误率动态调整批量大小
    """
    
    def __init__(
        self,
        llm_client,
        batch_size: int = 10,
        max_wait_time: float = 0.5,
        enable_batching: bool = True,
        min_batch_size: int = 5,
        max_batch_size: int = 50,
        adaptation_window: int = 10,
        slow_threshold: float = 5.0,
        fast_threshold: float = 2.0,
        error_rate_threshold: float = 0.1,
    ):
        """
        初始化自适应批量管理器
        
        :param llm_client: LLM客户端实例
        :param batch_size: 初始批量大小
        :param max_wait_time: 最大等待时间（秒）
        :param enable_batching: 是否启用批量处理
        :param min_batch_size: 最小批量大小
        :param max_batch_size: 最大批量大小
        :param adaptation_window: 适应窗口大小（用于计算平均响应时间）
        :param slow_threshold: 慢响应阈值（秒），超过此值会减小批量
        :param fast_threshold: 快响应阈值（秒），低于此值且错误率低会增大批量
        :param error_rate_threshold: 错误率阈值，超过此值会减小批量
        """
        super().__init__(llm_client, batch_size, max_wait_time, enable_batching)
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.adaptation_window = adaptation_window
        self.slow_threshold = slow_threshold
        self.fast_threshold = fast_threshold
        self.error_rate_threshold = error_rate_threshold
        
        self.response_times = []
        self.error_count = 0
        self.success_count = 0
        self.last_adaptation_time = time.time()
        self.adaptation_interval = 10  # 每10秒最多调整一次
    
    async def _process_batch(self):
        """处理当前队列中的所有请求，并记录性能指标"""
        start_time = time.time()
        initial_batch_size = self.batch_size
        
        try:
            await super()._process_batch()
            self.success_count += 1
        except Exception as e:
            self.error_count += 1
            logger.warning("Batch request failed: %s", e)
            raise
        finally:
            elapsed = time.time() - start_time
            self.response_times.append(elapsed)
            
            # 保持响应时间窗口大小
            if len(self.response_times) > self.adaptation_window:
                self.response_times.pop(0)
            
            # 动态调整批量大小（限制调整频率）
            current_time = time.time()
            if current_time - self.last_adaptation_time >= self.adaptation_interval:
                self._adapt_batch_size()
                self.last_adaptation_time = current_time
                
                if self.batch_size != initial_batch_size:
                    logger.info(
                        "Adaptive batch size adjusted: %d -> %d (avg_time=%.2fs, error_rate=%.2f%%)",
                        initial_batch_size,
                        self.batch_size,
                        sum(self.response_times[-self.adaptation_window:]) / min(len(self.response_times), self.adaptation_window),
                        (self.error_count / (self.success_count + self.error_count) * 100) if (self.success_count + self.error_count) > 0 else 0
                    )
    
    def _adapt_batch_size(self):
        """根据性能指标调整批量大小"""
        if len(self.response_times) < 5:
            # 数据不足，不调整
            return
        
        # 计算平均响应时间
        avg_time = sum(self.response_times[-self.adaptation_window:]) / min(len(self.response_times), self.adaptation_window)
        
        # 计算错误率
        total_requests = self.success_count + self.error_count
        error_rate = self.error_count / total_requests if total_requests > 0 else 0
        
        # 调整策略
        if avg_time > self.slow_threshold or error_rate > self.error_rate_threshold:
            # 响应慢或错误率高，减小批量
            new_batch_size = max(self.min_batch_size, self.batch_size - 2)
            if new_batch_size != self.batch_size:
                self.batch_size = new_batch_size
                # 重置计数器，给新批量大小一些时间
                self.response_times = self.response_times[-3:]  # 保留最近3个
                self.error_count = 0
                self.success_count = 0
        elif avg_time < self.fast_threshold and error_rate < 0.05:
            # 响应快且稳定，增大批量
            new_batch_size = min(self.max_batch_size, self.batch_size + 2)
            if new_batch_size != self.batch_size:
                self.batch_size = new_batch_size
                # 重置计数器
                self.response_times = self.response_times[-3:]
                self.error_count = 0
                self.success_count = 0
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total_requests = self.success_count + self.error_count
        return {
            "batch_size": self.batch_size,
            "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "error_rate": self.error_count / total_requests if total_requests > 0 else 0,
            "success_count": self.success_count,
            "error_count": self.error_count,
        }

