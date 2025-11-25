from typing import List

from graphgen.bases import BaseTokenizer

from .tiktoken_tokenizer import TiktokenTokenizer
from transformers import AutoTokenizer

# try:
#     from transformers import AutoTokenizer

#     _HF_AVAILABLE = True
# except ImportError:
#     _HF_AVAILABLE = False


def get_tokenizer_impl(tokenizer_name: str = "cl100k_base", local_cache_dir: str = None) -> BaseTokenizer:
    import tiktoken
    import os

    if tokenizer_name in tiktoken.list_encoding_names():
        return TiktokenTokenizer(model_name=tokenizer_name, local_cache_dir=local_cache_dir)

    # 2. HuggingFace
    # 设置 HuggingFace 缓存目录
    if local_cache_dir is None:
        # 获取项目根目录
        current_file = os.path.abspath(__file__)
        project_root = os.path.abspath(os.path.join(current_file, "..", "..", "..", ".."))
        hf_cache_dir = os.path.join(project_root, "models", "huggingface")
    else:
        # 如果提供了 local_cache_dir，使用其父目录的 huggingface 子目录
        hf_cache_dir = os.path.join(os.path.dirname(local_cache_dir), "huggingface")
    
    os.makedirs(hf_cache_dir, exist_ok=True)
    
    # 设置环境变量（如果未设置）
    if "TRANSFORMERS_CACHE" not in os.environ:
        os.environ["TRANSFORMERS_CACHE"] = hf_cache_dir
    if "HF_HOME" not in os.environ:
        os.environ["HF_HOME"] = hf_cache_dir
    
    # if _HF_AVAILABLE:
    #     from .hf_tokenizer import HFTokenizer
    #     return HFTokenizer(model_name=tokenizer_name)
    
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, cache_dir=hf_cache_dir)
    return tokenizer

    # raise ValueError(
    #     f"Unknown tokenizer {tokenizer_name} and HuggingFace not available."
    # )


class Tokenizer(BaseTokenizer):
    """
    Encapsulates different tokenization implementations based on the specified model name.
    """

    def __init__(self, model_name: str = "cl100k_base", local_cache_dir: str = None):
        super().__init__(model_name)
        if not self.model_name:
            raise ValueError("TOKENIZER_MODEL must be specified in the ENV variables.")
        self._impl = get_tokenizer_impl(self.model_name, local_cache_dir=local_cache_dir)

    def encode(self, text: str) -> List[int]:
        return self._impl.encode(text)

    def decode(self, token_ids: List[int]) -> str:
        return self._impl.decode(token_ids)

    def count_tokens(self, text: str) -> int:
        return self._impl.count_tokens(text)
