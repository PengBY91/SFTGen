# 模型依赖和网络需求

本文档列出项目中所有需要从网络下载的模型和数据，以及如何配置本地存储。

## 📋 依赖清单

### 1. ✅ Tiktoken 模型（已配置本地存储）

- **模型**: `cl100k_base`
- **位置**: `models/tokenizer/`
- **状态**: ✅ 已配置为本地存储
- **详情**: 参见 [TOKENIZER_LOCAL_STORAGE.md](TOKENIZER_LOCAL_STORAGE.md)

### 2. ✅ HuggingFace Transformers 模型（已配置本地存储）

#### 2.1 Tokenizer（备用）

- **文件**: `graphgen/models/tokenizer/__init__.py`
- **触发条件**: 当 `tokenizer_name` 不是 tiktoken 支持的编码时
- **模型**: 根据 `tokenizer_name` 参数动态下载
- **代码位置**: 第27行 `AutoTokenizer.from_pretrained(tokenizer_name, cache_dir=...)`
- **使用场景**: 如果用户指定了非 tiktoken 的 tokenizer（如 HuggingFace 模型名）
- **状态**: ✅ 已配置为本地存储到 `models/huggingface/`

#### 2.2 Reward Evaluator 模型

- **文件**: `graphgen/models/evaluator/reward_evaluator.py`
- **模型**: `OpenAssistant/reward-model-deberta-v3-large-v2`
- **用途**: 用于评估生成文本的质量（奖励模型）
- **代码位置**: 第32-33行
- **使用场景**: 运行评估脚本 `graphgen/evaluate.py` 时
- **大小**: 约 1-2 GB
- **状态**: ✅ 已配置为本地存储到 `models/huggingface/`

#### 2.3 UniEval 模型

- **文件**: `graphgen/models/evaluator/uni_evaluator.py`
- **模型**: `MingZhong/unieval-sum`
- **用途**: 用于评估文本的自然性、连贯性和理解性
- **代码位置**: 第58-59行
- **使用场景**: 运行评估脚本 `graphgen/evaluate.py` 时
- **大小**: 约 1-2 GB
- **状态**: ✅ 已配置为本地存储到 `models/huggingface/`

### 3. ✅ NLTK 数据（已配置本地存储）

- **文件**: `graphgen/utils/help_nltk.py`
- **数据**: 
  - `stopwords` (停用词)
  - `punkt_tab` (分词器)
- **位置**: `resources/nltk_data/`
- **状态**: ✅ 已配置为本地存储
- **说明**: 代码已自动下载到项目本地目录

## 🔧 HuggingFace 本地缓存配置

**✅ 已自动配置**: 代码已自动配置为使用本地缓存目录 `models/huggingface/`，无需手动配置。

### 自动配置说明

所有使用 HuggingFace 模型的代码已自动配置为：
1. 自动创建 `models/huggingface/` 目录
2. 自动设置环境变量 `TRANSFORMERS_CACHE` 和 `HF_HOME`
3. 在 `from_pretrained()` 调用中指定 `cache_dir` 参数

### 手动配置（可选）

如果需要自定义缓存目录，可以设置环境变量：

```bash
# Windows
set TRANSFORMERS_CACHE=D:\code\GraphGen\models\huggingface
set HF_HOME=D:\code\GraphGen\models\huggingface

# Linux/Mac
export TRANSFORMERS_CACHE=/path/to/GraphGen/models/huggingface
export HF_HOME=/path/to/GraphGen/models/huggingface
```

或者在 `.env` 文件中：

```env
TRANSFORMERS_CACHE=./models/huggingface
HF_HOME=./models/huggingface
```

### 使用配置脚本

运行配置脚本自动设置所有缓存目录：

```bash
python scripts/setup_model_cache.py
```

## 📦 预下载模型

### 使用 HuggingFace CLI

```bash
# 安装 huggingface-cli
pip install huggingface_hub

# 下载 Reward 模型
huggingface-cli download OpenAssistant/reward-model-deberta-v3-large-v2 --local-dir ./models/huggingface/OpenAssistant/reward-model-deberta-v3-large-v2

# 下载 UniEval 模型
huggingface-cli download MingZhong/unieval-sum --local-dir ./models/huggingface/MingZhong/unieval-sum
```

### 使用 Python 脚本

```python
from huggingface_hub import snapshot_download

# 下载 Reward 模型
snapshot_download(
    repo_id="OpenAssistant/reward-model-deberta-v3-large-v2",
    local_dir="./models/huggingface/OpenAssistant/reward-model-deberta-v3-large-v2"
)

# 下载 UniEval 模型
snapshot_download(
    repo_id="MingZhong/unieval-sum",
    local_dir="./models/huggingface/MingZhong/unieval-sum"
)
```

## 🚀 自动化配置脚本

可以创建一个初始化脚本来配置所有模型缓存：

```python
#!/usr/bin/env python3
"""配置所有模型的本地缓存目录"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# 创建模型目录
model_dirs = [
    PROJECT_ROOT / "models" / "tokenizer",
    PROJECT_ROOT / "models" / "huggingface",
]

for dir_path in model_dirs:
    dir_path.mkdir(parents=True, exist_ok=True)
    print(f"✓ 创建目录: {dir_path}")

# 设置环境变量
os.environ["TRANSFORMERS_CACHE"] = str(PROJECT_ROOT / "models" / "huggingface")
os.environ["HF_HOME"] = str(PROJECT_ROOT / "models" / "huggingface")
os.environ["TIKTOKEN_CACHE_DIR"] = str(PROJECT_ROOT / "models" / "tokenizer")

print("\n✓ 环境变量已设置")
print(f"  TRANSFORMERS_CACHE: {os.environ['TRANSFORMERS_CACHE']}")
print(f"  HF_HOME: {os.environ['HF_HOME']}")
print(f"  TIKTOKEN_CACHE_DIR: {os.environ['TIKTOKEN_CACHE_DIR']}")
```

## 📊 模型使用情况

### 核心功能（必需）

- **Tiktoken (`cl100k_base`)**: ✅ 已配置本地存储
  - 用于所有 token 计数和文本处理
  - 默认 tokenizer

### 评估功能（可选）

- **Reward Evaluator**: ⚠️ 需要网络下载
  - 仅在运行 `graphgen/evaluate.py` 时使用
  - 如果不需要评估功能，可以忽略

- **UniEval**: ⚠️ 需要网络下载
  - 仅在运行 `graphgen/evaluate.py` 时使用
  - 如果不需要评估功能，可以忽略

### 备用 Tokenizer（可选）

- **HuggingFace Tokenizer**: ⚠️ 需要网络下载
  - 仅在用户指定非 tiktoken tokenizer 时使用
  - 默认使用 tiktoken，通常不需要

## ⚠️ 注意事项

1. **评估模型很大**: Reward 和 UniEval 模型每个约 1-2 GB，下载需要时间
2. **首次使用**: 首次使用时会自动下载，需要网络连接
3. **离线使用**: 如需离线使用，请预先下载所有模型
4. **磁盘空间**: 确保有足够的磁盘空间（至少 5-10 GB）

## 🔍 检查网络依赖

运行以下命令检查哪些模型需要下载：

```python
import os
from pathlib import Path

# 检查 tiktoken
tiktoken_dir = Path("models/tokenizer")
print(f"Tiktoken 模型目录: {tiktoken_dir.exists()}")

# 检查 HuggingFace
hf_dir = Path("models/huggingface")
print(f"HuggingFace 缓存目录: {hf_dir.exists()}")

# 检查 NLTK
nltk_dir = Path("resources/nltk_data")
print(f"NLTK 数据目录: {nltk_dir.exists()}")
```

## 📝 总结

| 模型/数据 | 状态 | 本地存储 | 必需性 |
|---------|------|---------|--------|
| Tiktoken (cl100k_base) | ✅ 已配置 | `models/tokenizer/` | 必需 |
| NLTK 数据 | ✅ 已配置 | `resources/nltk_data/` | 必需 |
| HuggingFace Tokenizer | ✅ 已配置 | `models/huggingface/` | 可选 |
| Reward Evaluator | ✅ 已配置 | `models/huggingface/` | 可选 |
| UniEval | ✅ 已配置 | `models/huggingface/` | 可选 |

## ✨ 更新说明

**2024-11-24**: 所有模型已配置为自动使用本地存储目录，无需手动配置。代码会自动：
- 创建必要的目录结构
- 设置环境变量
- 在模型加载时指定本地缓存目录

首次使用时，模型会自动下载到本地目录，之后即可离线使用。

