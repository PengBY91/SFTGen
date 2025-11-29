from typing import List
import os
import hashlib

from graphgen.bases import BaseTokenizer


def get_local_tokenizer_cache_dir():
    """获取本地 tokenizer 模型缓存目录，优先使用 /models/tokenizer/"""
    current_file = os.path.abspath(__file__)
    project_root = os.path.abspath(os.path.join(current_file, "..", "..", "..", ".."))

    candidate_dirs = [
        os.environ.get("TOKENIZER_LOCAL_PATH"),
        os.environ.get("TIKTOKEN_CACHE_DIR"),
        "/models/tokenizer",
        os.path.join(project_root, "models", "tokenizer"),
    ]

    for path in candidate_dirs:
        if not path:
            continue
        resolved = os.path.abspath(path)
        try:
            os.makedirs(resolved, exist_ok=True)
        except OSError:
            continue
        return resolved

    raise RuntimeError("无法确定 tokenizer 本地缓存目录，请检查 /models/tokenizer/ 是否可用。")


def get_tiktoken_file_hash(url: str) -> str:
    """计算 tiktoken URL 的 SHA-1 哈希值（用于文件名）"""
    return hashlib.sha1(url.encode('utf-8')).hexdigest()


def check_local_tokenizer_file(model_name: str, cache_dir: str) -> tuple[bool, str]:
    """
    检查本地 tokenizer 文件是否存在
    
    Returns:
        (exists, file_path): 文件是否存在和文件路径
    """
    # tiktoken 使用的 URL 映射
    tiktoken_urls = {
        "cl100k_base": "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
        "p50k_base": "https://openaipublic.blob.core.windows.net/encodings/p50k_base.tiktoken",
        "r50k_base": "https://openaipublic.blob.core.windows.net/encodings/r50k_base.tiktoken",
        "p50k_edit": "https://openaipublic.blob.core.windows.net/encodings/p50k_edit.tiktoken",
        "gpt2": "https://openaipublic.blob.core.windows.net/encodings/gpt2.tiktoken",
    }
    
    if model_name not in tiktoken_urls:
        # 未知的模型名，让 tiktoken 自己处理
        return True, ""
    
    url = tiktoken_urls[model_name]
    file_hash = get_tiktoken_file_hash(url)
    file_path = os.path.join(cache_dir, file_hash)
    
    exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0
    
    return exists, file_path


class TiktokenTokenizer(BaseTokenizer):
    def __init__(self, model_name: str = "cl100k_base", local_cache_dir: str = None):
        super().__init__(model_name)
        # 设置本地缓存目录
        if local_cache_dir is None:
            local_cache_dir = get_local_tokenizer_cache_dir()
        
        # 设置环境变量，让 tiktoken 使用本地目录
        # 必须在导入 tiktoken 之前设置，始终强制使用本地目录
        if os.environ.get("TIKTOKEN_CACHE_DIR") != local_cache_dir:
            os.environ["TIKTOKEN_CACHE_DIR"] = local_cache_dir
        
        # 检查本地文件是否存在（离线模式检查）
        file_exists, file_path = check_local_tokenizer_file(model_name, local_cache_dir)
        
        if not file_exists and file_path:
            # 文件不存在，抛出明确的错误
            from graphgen.utils.log import logger
            logger.error(
                "Tokenizer model file not found in offline mode. "
                "Expected file: %s\n"
                "Please download the model file first using:\n"
                "  python scripts/download_tokenizer_model.py\n"
                "Or ensure the file exists at: %s",
                file_path, local_cache_dir
            )
            raise FileNotFoundError(
                f"Tokenizer model file not found: {file_path}\n"
                f"In offline mode, the tokenizer file must be pre-downloaded.\n"
                f"Please run: python scripts/download_tokenizer_model.py\n"
                f"Or manually place the file at: {file_path}"
            )
        
        # 导入 tiktoken（在环境变量设置之后）
        import tiktoken
        
        try:
            self.enc = tiktoken.get_encoding(self.model_name)
        except Exception as e:
            # 如果仍然失败，提供更详细的错误信息
            from graphgen.utils.log import logger
            logger.error(
                "Failed to load tiktoken encoding '%s'. "
                "Cache dir: %s, File exists: %s, File path: %s",
                model_name, local_cache_dir, file_exists, file_path
            )
            raise RuntimeError(
                f"Failed to load tiktoken encoding '{model_name}'. "
                f"This might be due to:\n"
                f"1. Missing model file in offline mode (expected: {file_path})\n"
                f"2. Corrupted model file\n"
                f"3. Network access required but unavailable\n\n"
                f"Original error: {e}"
            ) from e

    def encode(self, text: str) -> List[int]:
        return self.enc.encode(text)

    def decode(self, token_ids: List[int]) -> str:
        return self.enc.decode(token_ids)
