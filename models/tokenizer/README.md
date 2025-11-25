# Tokenizer 模型本地存储

本目录用于存储 tokenizer 模型文件，实现离线使用。

## 目录结构

```
models/tokenizer/
├── README.md
└── {SHA1_HASH}.tiktoken  # 模型文件（由 tiktoken 自动管理）
```

## 使用方法

### 1. 下载模型文件

运行下载脚本：

```bash
python scripts/download_tokenizer_model.py
```

或者手动下载：

1. 从以下 URL 下载 `cl100k_base.tiktoken`:
   ```
   https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken
   ```

2. 将文件重命名为其 SHA1 哈希值：`9b5ad71b2ce5302211f9c61530b329a4922fc6a4.tiktoken`

3. 将文件放入 `models/tokenizer/` 目录

### 2. 自动使用

代码已配置为自动从本地目录读取模型。首次使用时，如果模型文件不存在，tiktoken 会自动下载并缓存到本目录。

### 3. 环境变量（可选）

如果需要自定义缓存目录，可以设置环境变量：

```bash
export TIKTOKEN_CACHE_DIR=/path/to/your/cache
```

或者在代码中：

```python
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "/path/to/your/cache"
```

## 支持的模型

- `cl100k_base` - GPT-4 和 GPT-3.5-turbo 使用的编码器

## 注意事项

- 模型文件会自动下载和缓存，无需手动管理
- 如果网络不可用，请先运行下载脚本确保模型文件存在
- 模型文件大小约 1-2 MB

