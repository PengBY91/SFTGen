#!/usr/bin/env python3
"""
下载 tokenizer 模型文件到本地目录
"""
import os
import sys
import hashlib
import requests
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR = PROJECT_ROOT / "models" / "tokenizer"

# cl100k_base 模型信息
CL100K_BASE_URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
CL100K_BASE_SHA1 = "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"


def download_file(url: str, filepath: Path, expected_sha1: str = None):
    """下载文件并验证 SHA1"""
    print(f"正在下载: {url}")
    print(f"保存到: {filepath}")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    # 确保目录存在
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
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
    
    # 验证 SHA1
    if expected_sha1:
        print("正在验证文件完整性...")
        sha1_hash = hashlib.sha1()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha1_hash.update(chunk)
        
        actual_sha1 = sha1_hash.hexdigest()
        if actual_sha1 == expected_sha1:
            print("✓ 文件验证通过!")
        else:
            print(f"✗ 文件验证失败! 期望: {expected_sha1}, 实际: {actual_sha1}")
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
    model_file = MODEL_DIR / f"{CL100K_BASE_SHA1}.tiktoken"
    
    if model_file.exists():
        print(f"\n模型文件已存在: {model_file}")
        response = input("是否重新下载? (y/N): ").strip().lower()
        if response != 'y':
            print("跳过下载")
            return
    
    try:
        success = download_file(CL100K_BASE_URL, model_file, CL100K_BASE_SHA1)
        if success:
            print(f"\n✓ 模型文件已保存到: {model_file}")
            print("\n现在可以在代码中使用本地模型了!")
        else:
            print("\n✗ 下载失败，请检查网络连接")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ 下载过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

