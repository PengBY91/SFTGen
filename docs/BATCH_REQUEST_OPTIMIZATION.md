# 批量请求优化实现文档

## 概述

批量请求优化通过将多个LLM请求合并处理，减少网络延迟，提升整体处理效率。该优化在知识图谱提取、内容重述、问答对生成等关键环节应用。

## 实现原理

### 核心组件

1. **BatchRequestManager** (`graphgen/utils/batch_request_manager.py`)
   - 批量请求管理器，收集多个请求并批量并发处理
   - 支持配置批量大小和最大等待时间
   - 自动触发批量处理（达到批量大小或超时）

2. **BatchLLMWrapper** (`graphgen/models/llm/batch_llm_wrapper.py`)
   - LLM客户端包装器，透明地支持批量请求
   - 保持与原始LLM客户端相同的接口
   - 自动管理批量请求的生命周期

### 工作流程

```
多个请求 → BatchRequestManager → 收集到队列
    ↓
达到batch_size 或 max_wait_time
    ↓
批量并发处理 → 返回结果
```

## 应用场景

### 1. 知识提取 (`build_text_kg` / `build_mm_kg`)

**位置**：`graphgen/operators/build_kg/build_text_kg.py`

**优化效果**：
- 多个chunk的实体/关系提取请求被批量处理
- 减少网络往返次数
- 提升提取速度

**实现方式**：
```python
kg_builder = LightRAGKGBuilder(
    llm_client=llm_client,
    enable_batch_requests=True,  # 启用批量请求
    batch_size=10,                # 批量大小
    max_wait_time=0.5             # 最大等待时间
)
```

### 2. 语义变体生成 (`quiz`)

**位置**：`graphgen/operators/quiz.py`

**优化效果**：
- 多个描述的重述请求被批量处理
- 显著减少语义变体生成时间

**实现方式**：
```python
batch_manager = BatchRequestManager(
    llm_client=synth_llm_client,
    batch_size=10,
    max_wait_time=0.5,
    enable_batching=True
)
```

### 3. QA对生成 (`generate_qas`)

**位置**：`graphgen/operators/generate/generate_qas.py`

**优化效果**：
- 多个batch的QA生成请求被批量处理
- 使用BatchLLMWrapper包装LLM客户端
- 对生成器透明，无需修改生成器代码

**实现方式**：
```python
batch_wrapper = BatchLLMWrapper(
    llm_client=llm_client,
    batch_size=10,
    max_wait_time=0.5,
    enable_batching=True
)
generator = AtomicGenerator(batch_wrapper)  # 使用包装后的客户端
```

## 配置参数

### 批量请求配置

- **enable_batch_requests**: 是否启用批量请求（默认：True）
- **batch_size**: 每批处理的请求数量（默认：10，建议：5-20）
- **max_wait_time**: 最大等待时间（秒）（默认：0.5，建议：0.3-1.0）

### 配置位置

1. **前端配置页面** (`frontend/src/views/Config.vue`)
   - 在"性能优化配置"章节中
   - 可以单独配置批量请求参数

2. **后端配置** (`backend/core/task_processor.py`)
   - 自动从TaskConfig中读取配置
   - 传递到各个处理阶段

3. **代码配置** (`graphgen/graphgen.py`)
   - 在`insert()`、`quiz_and_judge()`、`generate()`中应用

## 性能提升

### 预期效果

1. **网络延迟减少**：
   - 批量处理减少网络往返次数
   - 预计减少30-50%的网络等待时间

2. **吞吐量提升**：
   - 并发处理多个请求
   - 充分利用网络带宽和API并发能力

3. **资源利用优化**：
   - 减少空闲等待时间
   - 提升整体处理效率

### 适用场景

- **大规模处理**：处理大量chunk或batch时效果显著
- **高延迟网络**：网络延迟较高时效果更明显
- **API限流场景**：在RPM/TPM限制下，批量处理可以更好地利用配额

## 使用示例

### 代码示例

```python
from graphgen.graphgen import GraphGen
from graphgen.models import OpenAIClient, Tokenizer

# 初始化GraphGen
graph_gen = GraphGen(...)

# 配置批量请求
split_config = {
    "chunk_size": 1024,
    "chunk_overlap": 100,
    "enable_batch_requests": True,  # 启用批量请求
    "batch_size": 10,               # 批量大小
    "max_wait_time": 0.5            # 最大等待时间
}

# 插入文档（自动应用批量请求）
await graph_gen.insert(read_config, split_config)

# 生成QA（自动应用批量请求）
generate_config = {
    "mode": "atomic",
    "data_format": "Alpaca",
    "enable_batch_requests": True,
    "batch_size": 10,
    "max_wait_time": 0.5
}
await graph_gen.generate(partition_config, generate_config)
```

### 前端配置示例

在配置页面的"性能优化配置"章节中：

1. **启用批量请求**：打开"启用批量请求"开关
2. **设置批量大小**：建议值5-20，根据API并发能力调整
3. **设置最大等待时间**：建议值0.3-1.0秒，根据网络延迟调整

## 技术细节

### 批量处理策略

1. **立即触发**：当队列达到`batch_size`时立即处理
2. **超时触发**：超过`max_wait_time`时即使未达到批量大小也处理
3. **并发执行**：批次内的请求并发执行，最大化吞吐量

### 错误处理

- 单个请求失败不影响其他请求
- 失败的请求会抛出异常，由调用方处理
- 批量管理器确保所有请求都有结果（成功或异常）

### 兼容性

- 向后兼容：默认启用，但可以通过配置关闭
- 透明集成：对现有代码影响最小
- 支持所有LLM客户端：通过BaseLLMClient接口工作

## 注意事项

1. **批量大小选择**：
   - 太小：无法充分利用批量处理的优势
   - 太大：可能导致内存占用增加，延迟增加
   - 建议：根据API并发能力和网络延迟调整

2. **等待时间设置**：
   - 太短：频繁触发批量处理，增加开销
   - 太长：增加延迟，影响响应速度
   - 建议：0.3-1.0秒，根据实际场景调整

3. **特殊参数处理**：
   - 对于需要不同参数（如temperature）的请求，批量管理器会正确处理
   - 每个请求的extra_params会被独立传递

## 未来优化方向

1. **智能批量大小调整**：根据API响应时间和错误率动态调整
2. **参数分组**：将具有相同参数的请求分组处理
3. **优先级队列**：支持请求优先级，重要请求优先处理
4. **批量API支持**：如果LLM API支持真正的批量接口，可以进一步优化

---

**文档版本**：v1.0  
**最后更新**：基于批量请求优化实现  
**维护者**：GraphGen开发团队

