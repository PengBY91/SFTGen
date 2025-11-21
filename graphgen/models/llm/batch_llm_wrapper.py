"""
批量LLM客户端包装器
将单个LLM客户端包装为支持批量请求的版本
"""

from typing import Any, List, Optional

from graphgen.bases.base_llm_client import BaseLLMClient
from graphgen.bases.datatypes import Token
from graphgen.utils.batch_request_manager import BatchRequestManager


class BatchLLMWrapper(BaseLLMClient):
    """
    批量LLM客户端包装器
    包装现有的LLM客户端，使其支持批量请求
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        batch_size: int = 10,
        max_wait_time: float = 0.5,
        enable_batching: bool = True
    ):
        """
        初始化批量包装器
        
        :param llm_client: 原始LLM客户端
        :param batch_size: 批次大小
        :param max_wait_time: 最大等待时间
        :param enable_batching: 是否启用批量处理
        """
        # 复制原始客户端的属性
        super().__init__(
            system_prompt=llm_client.system_prompt,
            temperature=llm_client.temperature,
            max_tokens=llm_client.max_tokens,
            repetition_penalty=llm_client.repetition_penalty,
            top_p=llm_client.top_p,
            top_k=llm_client.top_k,
            tokenizer=llm_client.tokenizer,
        )
        self.llm_client = llm_client
        self.enable_batching = enable_batching
        
        if enable_batching:
            self.batch_manager = BatchRequestManager(
                llm_client=llm_client,
                batch_size=batch_size,
                max_wait_time=max_wait_time,
                enable_batching=True
            )
        else:
            self.batch_manager = None
    
    async def generate_answer(
        self, text: str, history: Optional[List[str]] = None, **extra: Any
    ) -> str:
        """生成答案，使用批量管理器（如果启用）"""
        if self.batch_manager:
            return await self.batch_manager.add_request(text, history, extra if extra else None)
        else:
            return await self.llm_client.generate_answer(text, history, **extra)
    
    async def generate_topk_per_token(
        self, text: str, history: Optional[List[str]] = None, **extra: Any
    ) -> List[Token]:
        """生成top-k tokens（不支持批量，直接调用）"""
        return await self.llm_client.generate_topk_per_token(text, history, **extra)
    
    async def generate_inputs_prob(
        self, text: str, history: Optional[List[str]] = None, **extra: Any
    ) -> List[Token]:
        """生成输入概率（不支持批量，直接调用）"""
        return await self.llm_client.generate_inputs_prob(text, history, **extra)
    
    async def flush(self):
        """刷新批量管理器，确保所有请求完成"""
        if self.batch_manager:
            await self.batch_manager.flush()
    
    @property
    def token_usage(self):
        """访问原始客户端的token使用量"""
        return self.llm_client.token_usage

