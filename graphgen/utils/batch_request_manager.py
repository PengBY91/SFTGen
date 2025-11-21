"""
批量请求管理器
用于将多个LLM请求合并处理，减少网络延迟
"""

import asyncio
from typing import List, Dict, Any, Callable, Awaitable, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from .log import logger


@dataclass
class BatchRequest:
    """单个批量请求项"""
    prompt: str
    history: Optional[List[str]] = None
    extra_params: Optional[Dict[str, Any]] = None
    callback: Optional[Callable[[str], Any]] = None
    index: int = 0


class BatchRequestManager:
    """
    批量请求管理器
    收集多个请求，批量并发处理，减少网络延迟
    """
    
    def __init__(
        self,
        llm_client,
        batch_size: int = 10,
        max_wait_time: float = 0.5,
        enable_batching: bool = True
    ):
        """
        初始化批量请求管理器
        
        :param llm_client: LLM客户端实例
        :param batch_size: 每批处理的请求数量
        :param max_wait_time: 最大等待时间（秒），超过此时间即使未达到batch_size也会发送
        :param enable_batching: 是否启用批量处理
        """
        self.llm_client = llm_client
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.enable_batching = enable_batching
        
        self.request_queue: List[BatchRequest] = []
        self.queue_lock = asyncio.Lock()
        self.batch_task: Optional[asyncio.Task] = None
        self.pending_futures: Dict[int, asyncio.Future] = {}
        self.request_counter = 0
    
    async def add_request(
        self,
        prompt: str,
        history: Optional[List[str]] = None,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加一个请求到批量队列
        
        :param prompt: 提示文本
        :param history: 历史对话
        :param extra_params: 额外参数
        :return: 生成的结果
        """
        if not self.enable_batching:
            # 如果未启用批量处理，直接调用
            if extra_params:
                return await self.llm_client.generate_answer(prompt, history, **extra_params)
            else:
                return await self.llm_client.generate_answer(prompt, history)
        
        # 创建future用于返回结果
        future = asyncio.Future()
        request_index = self.request_counter
        self.request_counter += 1
        
        async with self.queue_lock:
            request = BatchRequest(
                prompt=prompt,
                history=history,
                extra_params=extra_params,
                callback=lambda result, idx=request_index: self._set_future_result(idx, result),
                index=request_index
            )
            self.request_queue.append(request)
            self.pending_futures[request_index] = future
            
            # 如果队列达到batch_size，立即触发处理
            if len(self.request_queue) >= self.batch_size:
                await self._process_batch()
            elif self.batch_task is None or self.batch_task.done():
                # 启动定时任务
                self.batch_task = asyncio.create_task(self._batch_timer())
        
        # 等待结果
        return await future
    
    def _set_future_result(self, index: int, result: str):
        """设置future的结果"""
        if index in self.pending_futures:
            future = self.pending_futures.pop(index)
            if not future.done():
                future.set_result(result)
    
    async def _batch_timer(self):
        """定时器，在max_wait_time后处理队列"""
        await asyncio.sleep(self.max_wait_time)
        async with self.queue_lock:
            if self.request_queue:
                await self._process_batch()
    
    async def _process_batch(self):
        """处理当前队列中的所有请求"""
        if not self.request_queue:
            return
        
        # 取出当前批次
        batch = self.request_queue[:self.batch_size]
        self.request_queue = self.request_queue[self.batch_size:]
        
        # 并发处理批次中的请求
        tasks = []
        for request in batch:
            task = self._process_single_request(request)
            tasks.append(task)
        
        # 等待所有请求完成
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_request(self, request: BatchRequest):
        """处理单个请求"""
        try:
            if request.extra_params:
                result = await self.llm_client.generate_answer(
                    request.prompt,
                    request.history,
                    **request.extra_params
                )
            else:
                result = await self.llm_client.generate_answer(
                    request.prompt,
                    request.history
                )
            if request.callback:
                request.callback(result)
        except Exception as e:
            logger.error("Error processing batch request: %s", e)
            if request.index in self.pending_futures:
                future = self.pending_futures.pop(request.index)
                if not future.done():
                    future.set_exception(e)
    
    async def flush(self):
        """刷新队列，处理所有剩余的请求"""
        async with self.queue_lock:
            while self.request_queue:
                await self._process_batch()
        
        # 等待所有future完成
        if self.pending_futures:
            await asyncio.gather(*self.pending_futures.values(), return_exceptions=True)


async def batch_generate_answers(
    llm_client,
    prompts: List[str],
    histories: Optional[List[Optional[List[str]]]] = None,
    batch_size: int = 10,
    max_wait_time: float = 0.5,
    enable_batching: bool = True
) -> List[str]:
    """
    批量生成答案的便捷函数
    
    :param llm_client: LLM客户端
    :param prompts: 提示列表
    :param histories: 历史对话列表（可选）
    :param batch_size: 批次大小
    :param max_wait_time: 最大等待时间
    :param enable_batching: 是否启用批量处理
    :return: 结果列表
    """
    if not enable_batching or len(prompts) == 1:
        # 如果只有一个请求或未启用批量，直接处理
        if histories and len(histories) == len(prompts):
            results = []
            for prompt, history in zip(prompts, histories):
                result = await llm_client.generate_answer(prompt, history)
                results.append(result)
            return results
        else:
            results = []
            for prompt in prompts:
                result = await llm_client.generate_answer(prompt)
                results.append(result)
            return results
    
    # 使用批量管理器
    manager = BatchRequestManager(
        llm_client=llm_client,
        batch_size=batch_size,
        max_wait_time=max_wait_time,
        enable_batching=True
    )
    
    # 添加所有请求
    tasks = []
    if histories and len(histories) == len(prompts):
        for prompt, history in zip(prompts, histories):
            task = manager.add_request(prompt, history)
            tasks.append(task)
    else:
        for prompt in prompts:
            task = manager.add_request(prompt)
            tasks.append(task)
    
    # 等待所有请求完成并刷新队列
    results = await asyncio.gather(*tasks)
    await manager.flush()
    
    return results

