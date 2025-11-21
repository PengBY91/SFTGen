# GraphGen优化实现总结

本文档总结了根据`FRAMEWORK_ANALYSIS.md`中的优化建议所实现的具体优化。

## 已实现的优化

### 1. ✅ 批量LLM请求优化

**实现位置**：
- `graphgen/utils/batch_request_manager.py` - 批量请求管理器
- `graphgen/models/llm/batch_llm_wrapper.py` - LLM客户端批量包装器
- `graphgen/operators/build_kg/build_text_kg.py` - 知识提取批量处理
- `graphgen/operators/quiz.py` - 语义变体生成批量处理
- `graphgen/operators/generate/generate_qas.py` - QA生成批量处理

**功能说明**：
- 将多个LLM请求合并为批量处理，减少网络延迟
- 支持配置批量大小和最大等待时间
- 自动触发批量处理（达到批量大小或超时）
- 在知识提取、内容重述、QA生成等关键环节应用

**使用方法**：
```python
# 在配置中启用
split_config = {
    "enable_batch_requests": True,  # 启用批量请求
    "batch_size": 10,               # 批量大小
    "max_wait_time": 0.5            # 最大等待时间（秒）
}
```

**技术细节**：
- 使用`BatchRequestManager`收集请求
- 达到`batch_size`或超过`max_wait_time`时触发处理
- 批次内请求并发执行，最大化吞吐量
- 预计减少30-50%的网络等待时间

**详细文档**：参见 [批量请求优化文档](BATCH_REQUEST_OPTIMIZATION.md)

---

### 2. ✅ 实体/关系缓存机制

**实现位置**：
- `graphgen/models/kg_builder/light_rag_kg_builder.py`
- `graphgen/operators/build_kg/build_text_kg.py`
- `graphgen/operators/build_kg/build_mm_kg.py`
- `graphgen/graphgen.py`

**功能说明**：
- 在知识提取阶段，对已提取的实体和关系进行缓存（基于文本内容哈希）
- 避免重复提取相同内容的chunk，显著节省LLM调用成本
- 支持通过配置启用/禁用缓存

**使用方法**：
```python
# 在split_config中配置
split_config = {
    "chunk_size": 1024,
    "chunk_overlap": 100,
    "enable_extraction_cache": True  # 启用缓存
}
```

**技术细节**：
- 使用`JsonKVStorage`存储提取结果
- 缓存key基于chunk内容的MD5哈希
- 自动在`GraphGen.clear()`时清理缓存

---

### 2. ✅ 多模板采样

**实现位置**：
- `graphgen/templates/generation/atomic_generation.py`
- `graphgen/models/generator/atomic_generator.py`
- `graphgen/bases/base_generator.py`

**功能说明**：
- 为原子QA生成提供多个提示模板变体
- 随机采样使用不同模板，提升生成数据的多样性
- 避免模式化输出，减少同质化问题

**模板变体**：
- 英文：3个变体（TEMPLATE_EN, TEMPLATE_EN_V2, TEMPLATE_EN_V3）
- 中文：3个变体（TEMPLATE_ZH, TEMPLATE_ZH_V2, TEMPLATE_ZH_V3）

**使用方法**：
```python
# 创建生成器时启用多模板
generator = AtomicGenerator(
    llm_client=llm_client,
    use_multi_template=True,  # 启用多模板采样
    template_seed=42  # 可选：设置随机种子以保证可复现性
)
```

**技术细节**：
- 更新了`BaseGenerator`的抽象方法签名，`build_prompt`从静态方法改为实例方法
- 所有生成器（Atomic, Aggregated, MultiHop, CoT）已更新以匹配新签名

---

### 3. ✅ 动态参数调整

**实现位置**：
- `graphgen/operators/split/split_chunks.py`
- `graphgen/graphgen.py`

**功能说明**：
- 根据输入文本长度和复杂度动态调整`chunk_size`
- 复杂文本使用更小的chunk，简单文本可以使用更大的chunk
- 提升分块质量，减少信息丢失

**算法**：
- `calculate_optimal_chunk_size()`: 基于文本长度和复杂度计算最优chunk大小
- `estimate_complexity()`: 使用启发式方法估计文本复杂度（句子长度、特殊字符等）

**使用方法**：
```python
# 在split_config中启用
split_config = {
    "chunk_size": 1024,  # 基础大小
    "chunk_overlap": 100,
    "dynamic_chunk_size": True  # 启用动态调整
}
```

**调整规则**：
- 文本长度 > 100,000：使用2048
- 文本长度 > 50,000：使用1536
- 文本长度 < 10,000：使用512
- 复杂度 > 0.8：减少20%
- 复杂度 < 0.3：增加20%
- 最终范围：256-4096

---

### 4. ✅ 温度调度器

**实现位置**：
- `graphgen/utils/temperature_scheduler.py`

**功能说明**：
- 支持动态调整生成温度，平衡多样性和准确性
- 提供多种调度策略：线性衰减、指数衰减、余弦衰减
- 可在QA生成过程中逐步降低温度，从高多样性到高准确性

**使用方法**：
```python
from graphgen.utils import TemperatureScheduler

# 创建调度器
scheduler = TemperatureScheduler(
    initial_temp=1.0,      # 初始温度（高多样性）
    final_temp=0.3,        # 最终温度（高准确性）
    decay_type="exponential",  # 衰减类型
    decay_rate=0.1,        # 衰减率
    total_steps=100        # 总步数
)

# 在生成过程中使用
for step in range(100):
    temperature = scheduler.get_temperature()
    # 使用temperature调用LLM
    scheduler.step()
```

**支持的衰减类型**：
- `linear`: 线性衰减
- `exponential`: 指数衰减（默认）
- `cosine`: 余弦衰减

---

## 配置示例

### 完整配置示例

```yaml
# configs/optimized_config.yaml
read:
  input_file: resources/input_examples/example.txt

split:
  chunk_size: 1024
  chunk_overlap: 100
  dynamic_chunk_size: true  # 启用动态chunk大小调整

quiz_and_judge:
  enabled: true
  quiz_samples: 2
  re_judge: false

partition:
  method: ece
  method_params:
    max_units_per_community: 20
    min_units_per_community: 5
    max_tokens_per_community: 10240
    unit_sampling: max_loss

generate:
  mode: atomic
  data_format: Alpaca
  # 注意：多模板采样在代码中启用，无需配置
```

### Python代码示例

```python
from graphgen.graphgen import GraphGen
from graphgen.models import OpenAIClient, Tokenizer, AtomicGenerator

# 初始化GraphGen（自动启用缓存）
graph_gen = GraphGen(
    working_dir="./cache",
    tokenizer_instance=Tokenizer(),
    synthesizer_llm_client=OpenAIClient(...),
    trainee_llm_client=OpenAIClient(...)
)

# 插入文档（启用动态chunk大小和缓存）
read_config = {"input_file": "data/example.txt"}
split_config = {
    "chunk_size": 1024,
    "chunk_overlap": 100,
    "dynamic_chunk_size": True,  # 启用动态调整
    "enable_extraction_cache": True  # 启用缓存
}
await graph_gen.insert(read_config, split_config)

# 生成QA（使用多模板采样）
generator = AtomicGenerator(
    llm_client=graph_gen.synthesizer_llm_client,
    use_multi_template=True  # 启用多模板采样
)
```

---

## 性能提升预期

### 效率优化

1. **缓存机制**：
   - 减少重复LLM调用：预计节省30-50%的API调用（取决于数据重复度）
   - 加速处理速度：缓存命中时跳过提取步骤

2. **动态参数调整**：
   - 提升分块质量：减少信息丢失，提高后续提取准确率
   - 优化资源使用：根据文本特性调整处理策略

### 生成质量优化

1. **多模板采样**：
   - 提升多样性：预计增加20-30%的QA对多样性
   - 减少模式化：避免生成相似的问题格式

2. **温度调度器**：
   - 平衡多样性和准确性：在生成过程中逐步优化
   - 可应用于需要高质量输出的场景

---

## 后续优化建议

以下优化建议已在文档中提出，但尚未实现（可作为后续工作）：

1. **批量LLM调用优化** - 需要LLM API支持批量请求
2. **启发式采样（优先级队列）** - 需要算法优化
3. **多源验证** - 需要集成外部知识源API
4. **一致性检查** - 需要训练判别模型
5. **主动学习** - 需要复杂的信息增益计算
6. **分布式存储** - 需要架构重构

---

## 兼容性说明

所有优化都向后兼容：
- 默认情况下，新功能处于关闭状态（`enable_cache=False`, `dynamic_chunk_size=False`等）
- 现有代码无需修改即可继续工作
- 新功能通过配置参数启用

---

**文档版本**：v1.0  
**最后更新**：基于优化实现  
**维护者**：GraphGen开发团队

