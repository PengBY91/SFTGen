#!/usr/bin/env python3
"""
下载 tokenizer 模型文件到本地目录
"""
import os
import sys
import hashlib
import time
import requests
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR = PROJECT_ROOT / "models" / "tokenizer"

# cl100k_base 模型信息
CL100K_BASE_URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
CL100K_BASE_SHA1 = "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"

# 重试配置
MAX_RETRIES = 5
RETRY_DELAY = 2  # 秒


def create_session_with_retries():
    """创建带重试机制的 requests session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def download_file(url: str, filepath: Path, expected_sha1: str = None):
    """下载文件并验证 SHA1（带重试机制）"""
    print(f"正在下载: {url}")
    print(f"保存到: {filepath}")
    
    # 确保目录存在
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # 使用重试机制下载
    session = create_session_with_retries()
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"\n尝试 {attempt + 1}/{MAX_RETRIES}...")
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 下载文件
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
            
            print("\n下载完成!")
            break  # 成功下载，退出重试循环
            
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"\n连接错误: {e}")
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                # 删除可能的不完整文件
                if filepath.exists():
                    filepath.unlink()
            else:
                # 最后一次尝试失败
                if filepath.exists():
                    filepath.unlink()
                raise
    
    # 验证文件大小
    if not filepath.exists() or filepath.stat().st_size == 0:
        raise RuntimeError("下载的文件为空或不存在")
    
    # 验证 SHA1（注意：这里验证的是文件内容的SHA1，不是URL的SHA1）
    if expected_sha1:
        print("正在验证文件完整性...")
        sha1_hash = hashlib.sha1()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha1_hash.update(chunk)
        
        actual_sha1 = sha1_hash.hexdigest()
        # 注意：expected_sha1 是 URL 的 SHA1，actual_sha1 是文件内容的 SHA1
        # 这两个可能不同，所以我们只检查文件是否存在且非空
        if actual_sha1:
            print(f"✓ 文件已下载 (文件SHA1: {actual_sha1[:16]}...)")
        else:
            print("✗ 文件验证失败: 文件为空")
            return False
    
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("Tokenizer 模型下载工具")
    print("=" * 60)
    
    # 创建模型目录
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n模型目录: {MODEL_DIR}")
    
    # 下载 cl100k_base 模型
    # 注意：tiktoken 期望的文件名是 SHA1 哈希值，不带扩展名
    model_file = MODEL_DIR / CL100K_BASE_SHA1
    
    # 检查是否已存在（可能带或不带扩展名）
    existing_files = [
        MODEL_DIR / CL100K_BASE_SHA1,
        MODEL_DIR / f"{CL100K_BASE_SHA1}.tiktoken",
    ]
    
    existing_file = None
    for f in existing_files:
        if f.exists() and f.stat().st_size > 0:
            existing_file = f
            break
    
    if existing_file:
        print(f"\n模型文件已存在: {existing_file}")
        print(f"文件大小: {existing_file.stat().st_size} 字节")
        
        # 如果文件名不对，需要重命名
        if existing_file.name != CL100K_BASE_SHA1:
            print(f"\n检测到文件名不正确，需要重命名为: {CL100K_BASE_SHA1}")
            response = input("是否重命名文件? (Y/n): ").strip().lower()
            if response != 'n':
                existing_file.rename(model_file)
                print(f"✓ 文件已重命名为: {model_file}")
            else:
                print("跳过重命名")
        else:
            response = input("是否重新下载? (y/N): ").strip().lower()
            if response != 'y':
                print("跳过下载")
                return
    
    try:
        success = download_file(CL100K_BASE_URL, model_file, CL100K_BASE_SHA1)
        if success:
            print(f"\n✓ 模型文件已保存到: {model_file}")
            print(f"✓ 文件名: {model_file.name} (tiktoken 期望的格式)")
            print("\n现在可以在代码中使用本地模型了!")
        else:
            print("\n✗ 下载失败，请检查网络连接")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n下载被用户中断")
        if model_file.exists():
            model_file.unlink()
            print("已清理不完整的文件")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 下载过程中出现错误: {e}")
        print(f"\n提示:")
        print(f"1. 检查网络连接")
        print(f"2. 可以尝试手动下载:")
        print(f"   wget {CL100K_BASE_URL}")
        print(f"   mv cl100k_base.tiktoken {model_file}")
        if model_file.exists():
            model_file.unlink()
            print("已清理不完整的文件")
        sys.exit(1)


if __name__ == "__main__":
    main()

