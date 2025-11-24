# 脚本说明

## download_tokenizer_model.py

下载 tokenizer 模型文件到本地目录。

### 使用方法

```bash
python scripts/download_tokenizer_model.py
```

### 功能

- 自动下载 `cl100k_base` tokenizer 模型
- 验证文件完整性（SHA1）
- 保存到 `models/tokenizer/` 目录
- 支持重新下载（如果文件已存在会提示）

### 注意事项

- 需要网络连接
- 需要安装 `requests` 库：`pip install requests`
- 模型文件大小约 1-2 MB

