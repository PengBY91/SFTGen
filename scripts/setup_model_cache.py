#!/usr/bin/env python3
"""
配置所有模型的本地缓存目录
"""
import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 创建模型目录
model_dirs = [
    PROJECT_ROOT / "models" / "tokenizer",
    PROJECT_ROOT / "models" / "huggingface",
]

print("=" * 60)
print("模型缓存目录配置工具")
print("=" * 60)

# 创建目录
for dir_path in model_dirs:
    dir_path.mkdir(parents=True, exist_ok=True)
    print(f"✓ 创建目录: {dir_path}")

# 设置环境变量（当前会话）
os.environ["TRANSFORMERS_CACHE"] = str(PROJECT_ROOT / "models" / "huggingface")
os.environ["HF_HOME"] = str(PROJECT_ROOT / "models" / "huggingface")
os.environ["TIKTOKEN_CACHE_DIR"] = str(PROJECT_ROOT / "models" / "tokenizer")

print("\n✓ 环境变量已设置（当前会话）:")
print(f"  TRANSFORMERS_CACHE: {os.environ['TRANSFORMERS_CACHE']}")
print(f"  HF_HOME: {os.environ['HF_HOME']}")
print(f"  TIKTOKEN_CACHE_DIR: {os.environ['TIKTOKEN_CACHE_DIR']}")

# 检查 .env 文件
env_file = PROJECT_ROOT / ".env"
env_content = []

if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        env_content = f.readlines()

# 检查是否需要添加环境变量到 .env
needs_update = False
env_vars = {
    "TRANSFORMERS_CACHE": str(PROJECT_ROOT / "models" / "huggingface"),
    "HF_HOME": str(PROJECT_ROOT / "models" / "huggingface"),
    "TIKTOKEN_CACHE_DIR": str(PROJECT_ROOT / "models" / "tokenizer"),
}

existing_vars = {line.split("=")[0].strip(): line for line in env_content if "=" in line and not line.strip().startswith("#")}

for var_name, var_value in env_vars.items():
    if var_name not in existing_vars:
        env_content.append(f"\n# HuggingFace 和 Tokenizer 缓存目录\n{var_name}={var_value}\n")
        needs_update = True
        print(f"\n✓ 将在 .env 文件中添加: {var_name}")

if needs_update:
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(env_content)
    print(f"\n✓ .env 文件已更新: {env_file}")
else:
    print(f"\n✓ .env 文件已包含所有必要的环境变量")

print("\n" + "=" * 60)
print("配置完成！")
print("=" * 60)
print("\n提示:")
print("1. 环境变量已在当前会话中设置")
print("2. 如需永久生效，请重启终端或重新加载 .env 文件")
print("3. HuggingFace 模型将在首次使用时自动下载到本地缓存目录")

