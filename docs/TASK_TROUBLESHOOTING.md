# GraphGen 任务处理问题排查指南

## 问题：下载的结果文件为空

### 症状
- 任务状态显示为"已完成"
- 下载的文件只有 `[]`（空数组）
- Token 使用量显示为 0

### 原因分析

这个问题通常是由以下原因导致的：

1. **API Key 无效或错误**
   - 使用了测试/无效的 API key
   - API key 没有权限
   - API key 已过期

2. **LLM 服务不可用**
   - API 服务地址错误
   - 网络连接问题
   - API 服务限流或故障

3. **模型配置错误**
   - 模型名称错误
   - 模型不支持当前的 API 服务

### 解决方案

#### 1. 检查 API 配置

在创建任务时，确保提供**正确有效的 API 配置**：

```javascript
{
  "api_key": "sk-xxxxxxxxxxxxx",  // ✅ 真实的 API key
  "synthesizer_url": "https://api.openai.com/v1",  // ✅ 正确的 API 地址
  "synthesizer_model": "gpt-3.5-turbo",  // ✅ 支持的模型名称
  // ... 其他配置
}
```

❌ **错误示例**：
```javascript
{
  "api_key": "test_key",  // ❌ 测试 key，无效
  "synthesizer_url": "http://localhost:8000",  // ❌ 错误的地址
  "synthesizer_model": "invalid-model",  // ❌ 不存在的模型
}
```

#### 2. 测试 API 连接

在创建任务之前，使用"配置设置"页面的"测试连接"功能验证 API 配置：

1. 进入"配置设置"页面
2. 填写 API 配置信息
3. 点击"测试连接"按钮
4. 确认连接成功后再创建任务

#### 3. 查看任务错误信息

如果任务失败，系统会显示详细的错误信息：

- 在任务列表中查看任务状态
- 点击"查看详情"查看完整错误信息
- 根据错误提示调整配置

### 常见错误及解决方法

#### 错误 1：API Key 无效

**错误信息**：
```
数据生成失败：未使用任何 token。请检查 API key 是否正确。
```

**解决方法**：
1. 检查 API key 是否正确复制（没有多余空格）
2. 确认 API key 有效且未过期
3. 验证 API key 有足够的配额

#### 错误 2：网络连接失败

**错误信息**：
```
Connection error / Timeout
```

**解决方法**：
1. 检查网络连接
2. 确认 API 服务地址可访问
3. 检查防火墙设置
4. 如果在国内，可能需要使用代理

#### 错误 3：模型不存在

**错误信息**：
```
Model not found / Invalid model
```

**解决方法**：
1. 检查模型名称拼写
2. 确认所选模型在当前 API 服务中可用
3. 参考 API 服务文档选择正确的模型名称

### 推荐的 API 服务配置

#### OpenAI

```json
{
  "synthesizer_url": "https://api.openai.com/v1",
  "synthesizer_model": "gpt-3.5-turbo",
  "api_key": "sk-..."
}
```

#### Azure OpenAI

```json
{
  "synthesizer_url": "https://your-resource.openai.azure.com/",
  "synthesizer_model": "gpt-35-turbo",
  "api_key": "your-azure-key"
}
```

#### 其他兼容服务（如 SiliconFlow）

```json
{
  "synthesizer_url": "https://api.siliconflow.cn/v1",
  "synthesizer_model": "Qwen/Qwen2.5-7B-Instruct",
  "api_key": "sk-..."
}
```

### 验证任务成功的标志

一个成功的任务应该具有以下特征：

✅ **状态**：completed  
✅ **Token 使用量**：> 0（通常几千到几万）  
✅ **输出文件大小**：> 100 字节（通常几 KB 到几 MB）  
✅ **生成的数据项**：至少有几条问答对

### 调试步骤

1. **使用有效的 API key 创建测试任务**
   ```bash
   # 使用小文件测试
   # 选择简单的配置（atomic 模式）
   # 设置较小的 chunk_size（512）
   ```

2. **监控任务进度**
   - 实时查看任务状态
   - 注意任务是否快速完成（可能是失败）
   - 正常任务通常需要几分钟

3. **检查任务详情**
   - Token 使用量应该 > 0
   - 处理时间应该 > 30 秒
   - 输出文件应该存在且不为空

4. **下载并验证结果**
   - 下载结果文件
   - 检查文件大小
   - 打开文件查看内容格式

### 示例：正确的任务配置

```json
{
  "if_trainee_model": false,
  "tokenizer": "cl100k_base",
  "synthesizer_url": "https://api.openai.com/v1",
  "synthesizer_model": "gpt-3.5-turbo",
  "api_key": "sk-proj-xxxxxxxxxxxxx",
  "chunk_size": 1024,
  "chunk_overlap": 100,
  "partition_method": "ece",
  "ece_max_units": 20,
  "ece_min_units": 3,
  "ece_max_tokens": 10240,
  "mode": "atomic",
  "data_format": "Alpaca",
  "rpm": 1000,
  "tpm": 50000
}
```

### 获取帮助

如果问题仍然存在：

1. 查看后端日志：
   ```bash
   tail -f /tmp/backend.log
   ```

2. 查看任务详细信息
3. 检查 API 服务状态
4. 参考 API 服务文档

---

## 系统改进（v2.0.1）

### 新增验证机制

系统现在会在任务完成前验证：

1. **输出数据不为空**
   - 如果没有生成任何数据，任务会标记为失败
   - 错误信息会明确指出问题

2. **Token 使用量 > 0**
   - 如果没有使用任何 token，说明 LLM 调用失败
   - 任务会标记为失败并提示检查 API 配置

3. **清晰的错误提示**
   - 所有错误都会显示在任务详情中
   - 错误信息包含具体的解决建议

### 使用建议

1. **首次使用**：先用小文件测试配置是否正确
2. **生产使用**：确保 API key 有足够配额
3. **批量处理**：合理设置 RPM 和 TPM 限制
4. **监控任务**：定期检查任务状态和错误信息

---

**更新时间**：2025-10-26  
**版本**：v2.0.1  
**状态**：✅ 已改进

