# Tokenizer 本地存储配置

本文档说明如何配置 tokenizer 模型使用本地存储。

## 概述

现在 tokenizer 模型（`cl100k_base`）会自动从本地目录读取，而不是使用系统默认的缓存目录。这样可以：
- 更好地控制模型文件位置
- 方便离线使用
- 便于项目部署和分发

## 实现方式

### 1. 本地存储目录

模型文件优先存储在绝对路径 `/models/tokenizer/` 下。如果该目录不可用，会回退到项目根目录中的 `models/tokenizer/` 目录。你也可以通过环境变量 `TOKENIZER_LOCAL_PATH` 指定自定义目录。

### 2. 自动配置

代码已自动配置为使用本地目录：
- `TiktokenTokenizer` 会优先选择 `/models/tokenizer/`，否则回退到项目目录
- 自动设置 `TIKTOKEN_CACHE_DIR` 环境变量，并强制所有 tiktoken 调用走本地路径
- 如需覆盖默认路径，可以设置 `TOKENIZER_LOCAL_PATH=/your/custom/path`

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
os.environ["TOKENIZER_LOCAL_PATH"] = "/path/to/your/cache"
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

### 问题: 离线环境下报网络连接错误

**错误信息**:
```
HTTPSConnectionPool(host='openaipublic.blob.core.windows.net', ...): 
Failed to resolve 'openaipublic.blob.core.windows.net' 
([Errno -3] Temporary failure in name resolution)
```

**原因**:
在离线环境下，tiktoken 库尝试从网络下载模型文件，但无法访问网络。

**解决方案**:

1. **确保模型文件已下载**:
   ```bash
   # 在有网络的环境中运行
   python scripts/download_tokenizer_model.py
   ```

2. **验证文件存在**:
   检查文件是否存在：
   ```bash
   ls models/tokenizer/9b5ad71b2ce5302211f9c61530b329a4922fc6a4
   ```
   
   文件名是 URL 的 SHA-1 哈希值：`9b5ad71b2ce5302211f9c61530b329a4922fc6a4`

3. **手动下载（如果脚本不可用）**:
   ```bash
   # 在有网络的环境中
   wget https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken
   # 计算文件名（URL的SHA-1）
   echo -n "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken" | sha1sum
   # 重命名并移动到正确位置
   mv cl100k_base.tiktoken models/tokenizer/9b5ad71b2ce5302211f9c61530b329a4922fc6a4
   ```

4. **检查环境变量**:
   确保 `TIKTOKEN_CACHE_DIR` 环境变量指向正确的目录：
   ```bash
   export TIKTOKEN_CACHE_DIR=/path/to/GraphGen/models/tokenizer
   ```

5. **代码已自动检查**:
   现在代码会在初始化时自动检查文件是否存在。如果文件不存在，会抛出明确的错误信息，提示如何解决。

**注意**: 
- 文件名必须是 URL 的 SHA-1 哈希值，不能使用原始文件名
- 文件必须放在 `TIKTOKEN_CACHE_DIR` 指定的目录中
- 确保文件完整且未损坏（文件大小应该 > 0）

