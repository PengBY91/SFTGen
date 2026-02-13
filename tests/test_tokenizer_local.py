#!/usr/bin/env python3
"""
测试本地 tokenizer 功能
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from graphgen.models.tokenizer import Tokenizer
from graphgen.models.tokenizer.tiktoken_tokenizer import get_local_tokenizer_cache_dir


def test_local_cache_dir():
    """测试本地缓存目录获取"""
    cache_dir = get_local_tokenizer_cache_dir()
    print(f"本地缓存目录: {cache_dir}")
    print(f"目录是否存在: {os.path.exists(cache_dir)}")
    return cache_dir


def test_tokenizer():
    """测试 tokenizer 功能"""
    print("\n" + "=" * 60)
    print("测试 Tokenizer")
    print("=" * 60)
    
    # 创建 tokenizer
    tokenizer = Tokenizer(model_name="cl100k_base")
    
    # 测试文本
    test_text = "Hello, this is a test sentence for tokenization."
    
    # 编码
    tokens = tokenizer.encode(test_text)
    print(f"\n原文: {test_text}")
    print(f"Token 数量: {len(tokens)}")
    print(f"Token IDs: {tokens[:10]}...")  # 只显示前10个
    
    # 解码
    decoded = tokenizer.decode(tokens)
    print(f"解码后: {decoded}")
    
    # 计数
    count = tokenizer.count_tokens(test_text)
    print(f"Token 计数: {count}")
    
    # 检查环境变量
    cache_dir = os.environ.get("TIKTOKEN_CACHE_DIR", "未设置")
    print(f"\nTIKTOKEN_CACHE_DIR: {cache_dir}")
    
    print("\n✓ Tokenizer 测试通过!")


if __name__ == "__main__":
    print("=" * 60)
    print("Tokenizer 本地存储测试")
    print("=" * 60)
    
    # 测试缓存目录
    cache_dir = test_local_cache_dir()
    
    # 测试 tokenizer
    try:
        test_tokenizer()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

