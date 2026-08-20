import math
from typing import Any, Dict, List, Optional

import openai
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from graphgen.bases.base_llm_client import BaseLLMClient
from graphgen.bases.datatypes import Token
from graphgen.models.llm.limitter import RPM, TPM


def get_top_response_tokens(response: openai.ChatCompletion) -> List[Token]:
    token_logprobs = response.choices[0].logprobs.content
    tokens = []
    for token_prob in token_logprobs:
        prob = math.exp(token_prob.logprob)
        candidate_tokens = [
            Token(t.token, math.exp(t.logprob)) for t in token_prob.top_logprobs
        ]
        token = Token(token_prob.token, prob, top_candidates=candidate_tokens)
        tokens.append(token)
    return tokens


class OpenAIClient(BaseLLMClient):
    def __init__(
        self,
        *,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        json_mode: bool = False,
        seed: Optional[int] = None,
        topk_per_token: int = 5,  # number of topk tokens to generate for each token
        request_limit: bool = False,
        rpm: Optional[RPM] = None,
        tpm: Optional[TPM] = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.json_mode = json_mode
        self.seed = seed
        self.topk_per_token = topk_per_token

        self.token_usage: list = []
        self.request_limit = request_limit
        self.rpm = rpm or RPM()
        self.tpm = tpm or TPM()

        self.__post_init__()

    def __post_init__(self):
        assert self.api_key is not None, "Please provide api key to access openai api."
        self.client = AsyncOpenAI(
            api_key=self.api_key.strip() if self.api_key else "dummy", base_url=self.base_url
        )
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出，确保客户端正确关闭"""
        await self.aclose()
        return False
    
    async def aclose(self):
        """关闭异步客户端"""
        try:
            if hasattr(self, 'client') and self.client is not None:
                await self.client.close()
        except RuntimeError as e:
            # 忽略"Event loop is closed"错误
            if "Event loop is closed" not in str(e):
                raise
        except Exception:
            # 静默处理其他关闭错误
            pass
    
    def get_usage(self) -> Dict[str, int]:
        """获取token使用统计
        
        Returns:
            Dict包含:
                - total: 总token数
                - input: 输入token数
                - output: 输出token数
        """
        if not self.token_usage:
            return {"total": 0, "input": 0, "output": 0}
        
        total_prompt = sum(usage["prompt_tokens"] for usage in self.token_usage)
        total_completion = sum(usage["completion_tokens"] for usage in self.token_usage)
        total = sum(usage["total_tokens"] for usage in self.token_usage)
        
        return {
            "total": total,
            "input": total_prompt,
            "output": total_completion
        }

    # generate_answer 中允许被 per-call extra 覆盖的 OpenAI 请求参数
    _OVERRIDABLE_PARAMS = (
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
        "presence_penalty",
        "frequency_penalty",
        "stop",
        "reasoning_effort",
    )

    def _pre_generate(self, text: str, history: List[str], extra: Optional[Dict] = None) -> Dict:
        kwargs = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        if self.seed:
            kwargs["seed"] = self.seed
        if self.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        # 提供商特有参数（如 DeepSeek 的 thinking / enable_thinking）：
        # OpenAI SDK 不认识这些顶层参数，必须经 extra_body 透传到请求体
        extra_body = dict(self.extra_request_params) if self.extra_request_params else None

        # 合并 per-call 覆盖参数（旧实现接受了 **extra 但从未生效）
        if extra:
            for key, value in extra.items():
                if key in self._OVERRIDABLE_PARAMS and value is not None:
                    kwargs[key] = value

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": text})

        if history:
            assert len(history) % 2 == 0, "History should have even number of elements."
            messages = history + messages

        kwargs["messages"] = messages
        if extra_body:
            kwargs["extra_body"] = extra_body
        return kwargs

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            (RateLimitError, APIConnectionError, APITimeoutError)
        ),
    )
    async def generate_topk_per_token(
        self,
        text: str,
        history: Optional[List[str]] = None,
        **extra: Any,
    ) -> List[Token]:
        kwargs = self._pre_generate(text, history, extra)
        if self.topk_per_token > 0:
            kwargs["logprobs"] = True
            kwargs["top_logprobs"] = self.topk_per_token

        # Limit max_tokens to 1 to avoid long completions
        kwargs["max_tokens"] = 1

        if self.request_limit:
            # 判分调用同样受 RPM/TPM 约束（max_tokens=1，输出侧可忽略）
            prompt_tokens = sum(
                len(self.tokenizer.encode(m["content"])) for m in kwargs["messages"]
            )
            await self.rpm.wait(silent=True)
            await self.tpm.wait(prompt_tokens + 1, silent=True)

        completion = await self.client.chat.completions.create(  # pylint: disable=E1125
            model=self.model_name, **kwargs
        )

        tokens = get_top_response_tokens(completion)

        return tokens

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            (RateLimitError, APIConnectionError, APITimeoutError)
        ),
    )
    async def generate_answer(
        self,
        text: str,
        history: Optional[List[str]] = None,
        **extra: Any,
    ) -> str:
        kwargs = self._pre_generate(text, history, extra)

        if self.request_limit:
            # 令牌数仅在需要限流时估算（同步 encode 会阻塞事件循环，能省则省）。
            # 输出侧按最近实际 completion 的 1.2 倍预留，避免按 max_tokens(4096)
            # 虚高估算导致 TPM 远早于实际耗尽（旧实现实测等效限速只有 ~9 请求/分钟）。
            prompt_tokens = sum(
                len(self.tokenizer.encode(m["content"])) for m in kwargs["messages"]
            )
            estimated_tokens = prompt_tokens + self._estimate_output_tokens(
                kwargs.get("max_tokens", self.max_tokens)
            )
            await self.rpm.wait(silent=True)
            await self.tpm.wait(estimated_tokens, silent=True)

        completion = await self.client.chat.completions.create(  # pylint: disable=E1125
            model=self.model_name, **kwargs
        )
        if hasattr(completion, "usage"):
            self.token_usage.append(
                {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }
            )
        return self.filter_think_tags(completion.choices[0].message.content)

    # 输出 token 预留估算的初始值与样本数阈值
    _DEFAULT_OUTPUT_RESERVE = 2048
    _OUTPUT_SAMPLE_MIN = 4

    def _estimate_output_tokens(self, max_tokens: int) -> int:
        """根据近期真实 completion 用量自适应地估计输出预留。"""
        completions = [u["completion_tokens"] for u in self.token_usage[-20:]]
        if len(completions) >= self._OUTPUT_SAMPLE_MIN:
            avg = sum(completions) / len(completions)
            reserve = int(avg * 1.2) + 64
        else:
            reserve = self._DEFAULT_OUTPUT_RESERVE
        return min(reserve, max_tokens)

    async def generate_inputs_prob(
        self, text: str, history: Optional[List[str]] = None, **extra: Any
    ) -> List[Token]:
        """Generate probabilities for each token in the input."""
        raise NotImplementedError
