"""
Prompt 缓存工具
用于缓存LLM调用结果，避免重复调用相同的prompt
"""

import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class PromptCache:
    """
    Prompt缓存类
    使用prompt的hash值作为key，缓存LLM调用结果
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: Optional[int] = None):
        """
        初始化缓存
        
        :param max_size: 最大缓存条目数
        :param ttl_seconds: 缓存过期时间（秒），None表示不过期
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def _hash_prompt(
        self, 
        prompt: str, 
        history: Optional[list] = None, 
        **kwargs
    ) -> str:
        """
        生成prompt的唯一hash
        
        :param prompt: 提示文本
        :param history: 历史对话
        :param kwargs: 其他参数（temperature, max_tokens等）
        :return: hash字符串
        """
        # 构建缓存key，包含所有影响结果的参数
        cache_key = {
            "prompt": prompt,
            "history": history or [],
            # 只包含影响结果的参数
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "top_p": kwargs.get("top_p", 0.95),
            "top_k": kwargs.get("top_k", 50),
        }
        # 排序确保一致性
        key_str = json.dumps(cache_key, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()
    
    def get(
        self, 
        prompt: str, 
        history: Optional[list] = None, 
        **kwargs
    ) -> Optional[str]:
        """
        从缓存获取结果
        
        :param prompt: 提示文本
        :param history: 历史对话
        :param kwargs: 其他参数
        :return: 缓存的结果，如果不存在或已过期则返回None
        """
        cache_key = self._hash_prompt(prompt, history, **kwargs)
        
        if cache_key not in self.cache:
            return None
        
        entry = self.cache[cache_key]
        
        # 检查是否过期
        if self.ttl_seconds is not None:
            if datetime.now() - entry["timestamp"] > timedelta(seconds=self.ttl_seconds):
                del self.cache[cache_key]
                return None
        
        return entry["result"]
    
    def set(
        self, 
        prompt: str, 
        result: str, 
        history: Optional[list] = None, 
        **kwargs
    ):
        """
        设置缓存
        
        :param prompt: 提示文本
        :param result: LLM返回的结果
        :param history: 历史对话
        :param kwargs: 其他参数
        """
        cache_key = self._hash_prompt(prompt, history, **kwargs)
        
        # 如果缓存已满，删除最旧的条目（简单FIFO策略）
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            # 删除第一个条目
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        self.cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now()
        }
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        :return: 统计信息字典
        """
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }

