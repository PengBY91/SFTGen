from typing import List
import os

import tiktoken

from graphgen.bases import BaseTokenizer


def get_local_tokenizer_cache_dir():
    """获取本地 tokenizer 模型缓存目录"""
    # 获取项目根目录
    # 从 graphgen/models/tokenizer/tiktoken_tokenizer.py 向上3级到项目根目录
    current_file = os.path.abspath(__file__)
    # graphgen/models/tokenizer/tiktoken_tokenizer.py 
    # -> graphgen/models/tokenizer (..)
    # -> graphgen/models (..)
    # -> graphgen (..)
    # -> 项目根目录 (..)
    project_root = os.path.abspath(os.path.join(current_file, "..", "..", "..", ".."))
    local_cache_dir = os.path.join(project_root, "models", "tokenizer")
    os.makedirs(local_cache_dir, exist_ok=True)
    return local_cache_dir


class TiktokenTokenizer(BaseTokenizer):
    def __init__(self, model_name: str = "cl100k_base", local_cache_dir: str = None):
        super().__init__(model_name)
        # 设置本地缓存目录
        if local_cache_dir is None:
            local_cache_dir = get_local_tokenizer_cache_dir()
        
        # 设置环境变量，让 tiktoken 使用本地目录
        if "TIKTOKEN_CACHE_DIR" not in os.environ:
            os.environ["TIKTOKEN_CACHE_DIR"] = local_cache_dir
        
        self.enc = tiktoken.get_encoding(self.model_name)

    def encode(self, text: str) -> List[int]:
        return self.enc.encode(text)

    def decode(self, token_ids: List[int]) -> str:
        return self.enc.decode(token_ids)
