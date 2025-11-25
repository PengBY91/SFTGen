# Tokenizer 本地存储配置

本文档说明如何配置 tokenizer 模型使用本地存储。

## 概述

现在 tokenizer 模型（`cl100k_base`）会自动从本地目录读取，而不是使用系统默认的缓存目录。这样可以：
- 更好地控制模型文件位置
- 方便离线使用
- 便于项目部署和分发

## 实现方式

### 1. 本地存储目录

模型文件存储在项目根目录下的 `models/tokenizer/` 目录中。

### 2. 自动配置

代码已自动配置为使用本地目录：
- `TiktokenTokenizer` 类会自动设置 `TIKTOKEN_CACHE_DIR` 环境变量
- 首次使用时，如果模型文件不存在，tiktoken 会自动下载并缓存到本地目录

### 3. 代码修改

#### 修改的文件

1. **graphgen/models/tokenizer/tiktoken_tokenizer.py**
   - 添加了 `get_local_tokenizer_cache_dir()` 函数
   - 修改了 `TiktokenTokenizer.__init__()` 以支持本地缓存目录
   - 自动设置 `TIKTOKEN_CACHE_DIR` 环境变量

2. **graphgen/models/tokenizer/__init__.py**
   - 更新了 `get_tokenizer_impl()` 和 `Tokenizer.__init__()` 以支持 `local_cache_dir` 参数

## 使用方法

### 方法 1: 自动下载（推荐）

直接使用 tokenizer，首次使用时会自动下载模型：

```python
from graphgen.models.tokenizer import Tokenizer

tokenizer = Tokenizer(model_name="cl100k_base")
tokens = tokenizer.encode("Hello, world!")
```

### 方法 2: 手动下载

如果需要预先下载模型文件（例如离线环境），可以运行：

```bash
python scripts/download_tokenizer_model.py
```

### 方法 3: 自定义目录

如果需要使用自定义目录：

```python
from graphgen.models.tokenizer import Tokenizer

custom_dir = "/path/to/your/cache"
tokenizer = Tokenizer(model_name="cl100k_base", local_cache_dir=custom_dir)
```

或者设置环境变量：

```python
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "/path/to/your/cache"
```

## 目录结构

```
GraphGen/
├── models/
│   └── tokenizer/
│       ├── README.md
│       └── {SHA1_HASH}.tiktoken  # 模型文件（自动生成）
├── scripts/
│   ├── README.md
│   └── download_tokenizer_model.py
└── ...
```

## 测试

运行测试脚本验证功能：

```bash
python test_tokenizer_local.py
```

## 注意事项

1. **首次使用**: 首次使用时会自动下载模型文件（需要网络连接）
2. **离线使用**: 如果需要在离线环境使用，请先运行下载脚本
3. **文件大小**: 模型文件大小约 1-2 MB
4. **兼容性**: 与现有代码完全兼容，无需修改调用方式

## 技术细节

### 环境变量

- `TIKTOKEN_CACHE_DIR`: 指定 tiktoken 的缓存目录
- 如果未设置，代码会自动设置为 `{项目根目录}/models/tokenizer`

### 模型文件

- 文件名格式: `{SHA1_HASH}.tiktoken`
- `cl100k_base` 的 SHA1: `9b5ad71b2ce5302211f9c61530b329a4922fc6a4`
- 下载 URL: `https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken`

## 故障排除

### 问题: 模型文件下载失败

**解决方案**:
1. 检查网络连接
2. 手动运行下载脚本: `python scripts/download_tokenizer_model.py`
3. 检查 `models/tokenizer/` 目录的写入权限

### 问题: 找不到模型文件

**解决方案**:
1. 确认 `models/tokenizer/` 目录存在
2. 检查环境变量 `TIKTOKEN_CACHE_DIR` 是否正确设置
3. 运行测试脚本: `python test_tokenizer_local.py`

### 问题: 路径计算错误

**解决方案**:
如果项目结构不同，可以手动指定缓存目录：

```python
tokenizer = Tokenizer(model_name="cl100k_base", local_cache_dir="/your/custom/path")
```

