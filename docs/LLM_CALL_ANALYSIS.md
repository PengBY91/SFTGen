# 大模型调用分析与优化方案

## 📊 整体流程中的LLM调用

### 1. 图谱抽取阶段（Knowledge Graph Extraction）

#### 调用点分析

**文件**: `graphgen/operators/build_kg/build_text_kg.py` 和 `build_mm_kg.py`

```
文本处理流程:
1. 读取文档 → 2. 分块 → 3. KG抽取 → 4. 节点合并 → 5. 边合并
                              ↓ LLM调用
                        每个chunk一次LLM调用
```

**关键代码**:
```python
kg_builder = LightRAGKGBuilder(
    llm_client=llm_client,
    enable_batch_requests=True,      # 默认启用
    batch_size=10,                    # 默认批量大小
    max_wait_time=0.5,               # 最大等待时间
)

# 并发处理所有chunks
results = await run_concurrent(
    kg_builder.extract,
    chunks,  # N个chunks
    desc="[2/4]Extracting entities and relationships",
)
```

**LLM调用次数**: 
- 基础调用: **N个chunks = N次LLM调用**
- 如果启用iterative refinement (当前注释掉): **N × (1 + max_loop) 次调用**

#### 节点/边合并阶段

**文件**: `graphgen/models/kg_builder/light_rag_kg_builder.py`

```python
async def merge_nodes(node_data, kg_instance):
    # 1. 实体消歧 (deduplication)
    # 2. 描述合并 (summarization) - 需要LLM调用
    if len(existing_descriptions) > 1 and len(existing_descriptions) <= 10:
        # LLM调用：合并描述
        summary_prompt = KG_SUMMARIZATION_PROMPT[language].format(...)
        if self.batch_manager:
            summary = await self.batch_manager.add_request(summary_prompt)
```

**LLM调用次数**:
- **M个需要合并的节点 = M次LLM调用** (M通常 << N)

---

### 2. 问答对生成阶段（QA Generation）

#### 调用点分析

**文件**: `graphgen/operators/generate/generate_qas.py`

不同模式的LLM调用次数：

| 模式 | 阶段 | LLM调用次数 | 说明 |
|------|------|------------|------|
| **Atomic (单阶段)** | 问题+答案生成 | K次 | K = batch数量 |
| **Atomic (两阶段)** | 1. 问题生成<br>2. 答案生成 | K + Q次 | Q = 生成的问题数 |
| **Aggregated (原始)** | 1. 重述文本<br>2. 问题生成 | K + K = 2K次 | 两次独立调用 |
| **Aggregated (合并)** | 重述+问题 | K次 | 减少50%调用 |
| **Multi-hop** | 问题+答案+路径 | K次 | 一次生成全部 |
| **CoT (原始)** | 1. 模板设计<br>2. 答案生成 | K + K = 2K次 | 两次独立调用 |
| **CoT (合并)** | 模板+答案 | K次 | 减少50%调用 |
| **All模式** | 所有模式并发 | 4K次 | 四种模式独立生成 |

**关键优化点**:
1. **合并模式** (`use_combined_mode`): Aggregated和CoT可以一次生成多个字段
2. **批量处理** (`enable_batch_requests`): 多个batch并发处理
3. **Prompt缓存** (`enable_prompt_cache`): 避免重复相同的prompt调用

---

## 🎯 当前已实现的优化

### 1. 批量请求管理器 (BatchRequestManager)

**文件**: `graphgen/utils/batch_request_manager.py`

**工作原理**:
```
请求1 ──┐
请求2 ──┤
请求3 ──┼──> 收集到batch_size个 ──> 并发发送 ──> 分发结果
...     │    或等待max_wait_time
请求N ──┘
```

**配置参数**:
- `batch_size`: 10 (默认) - 每批处理的请求数
- `max_wait_time`: 0.5秒 (默认) - 最大等待时间
- `enable_batching`: True (默认)

**效果**:
- ✅ 减少网络往返次数
- ✅ 提高并发处理效率
- ⚠️ 单个批次内部仍然是多次独立API调用

### 2. 自适应批量管理器 (AdaptiveBatchRequestManager)

**文件**: `graphgen/utils/adaptive_batch_manager.py`

**特性**:
- 根据API响应时间动态调整批量大小
- 根据错误率自动降低批量
- `min_batch_size`: 5, `max_batch_size`: 50

### 3. Prompt缓存 (PromptCache)

**文件**: `graphgen/utils/prompt_cache.py`

**作用**:
- LRU缓存，避免重复相同prompt的调用
- `cache_max_size`: 10000条
- `cache_ttl`: 可配置过期时间

### 4. 合并模式 (Combined Mode)

**位置**: Aggregated和CoT生成器

**效果**:
- Aggregated: 2次调用 → 1次调用 (减少50%)
- CoT: 2次调用 → 1次调用 (减少50%)

### 5. 抽取结果缓存

**文件**: `graphgen/graphgen.py`

**作用**:
- 缓存chunk的抽取结果
- 避免重复抽取相同内容的chunk

---

## 💡 可以进一步优化的点

### ❌ 当前限制

**重要发现**: 
当前的 `BatchRequestManager` **不是真正的批量调用**！

查看代码：
```python:graphgen/utils/batch_request_manager.py
async def _process_batch(self):
    # 取出当前批次
    batch = self.request_queue[:self.batch_size]
    
    # 并发处理批次中的请求（但每个请求仍是独立调用）
    tasks = []
    for request in batch:
        task = self._process_single_request(request)
        tasks.append(task)
    
    # 等待所有请求完成
    await asyncio.gather(*tasks)
```

**问题**: 每个request仍然调用一次 `llm_client.generate_answer()`

### ✅ 优化方案

#### 方案1: 真正的批量API调用 ⭐⭐⭐⭐⭐

**适用场景**: API支持批量请求（如OpenAI Batch API）

**实现思路**:
```python
# 伪代码
async def process_batch_with_real_batching(requests):
    # 将多个prompt合并成一个批量请求
    batch_payload = {
        "requests": [
            {"id": i, "prompt": req.prompt}
            for i, req in enumerate(requests)
        ]
    }
    
    # 一次API调用处理多个请求
    batch_response = await llm_client.batch_generate(batch_payload)
    
    # 分发结果
    for i, response in enumerate(batch_response["responses"]):
        set_result(requests[i].index, response["text"])
```

**优点**:
- ✅ 真正减少API调用次数
- ✅ 降低API费用（某些API批量调用有折扣）
- ✅ 减少网络开销

**缺点**:
- ⚠️ 需要API支持批量模式
- ⚠️ 可能增加单次请求延迟

**预计效果**:
- **调用次数**: N次 → N/batch_size次
- **费用**: 可能减少10-30%（取决于API定价）

---

#### 方案2: 增大batch_size和并发数 ⭐⭐⭐⭐

**配置文件调整**:

```yaml
# 当前默认值
split_config:
  enable_batch_requests: true
  batch_size: 10              # 可以增大到 20-50
  max_wait_time: 0.5          # 可以增大到 1.0-2.0
  
generation_config:
  enable_batch_requests: true
  batch_size: 10              # 可以增大到 20-50
  max_wait_time: 0.5          # 可以增大到 1.0-2.0
```

**建议调整**:
```yaml
# 优化后
split_config:
  batch_size: 30              # 增大3倍
  max_wait_time: 1.0          # 增大等待时间，收集更多请求
  use_adaptive_batching: true # 启用自适应
  max_batch_size: 50          # 自适应上限
  
generation_config:
  batch_size: 30
  max_wait_time: 1.0
  use_adaptive_batching: true
  max_batch_size: 50
```

**效果**:
- ✅ 提高并发处理效率
- ✅ 更好地利用API并发限制
- ⚠️ 可能增加内存使用

**预计提升**:
- **吞吐量**: 提升 2-3倍
- **总耗时**: 减少 30-50%

---

#### 方案3: Prompt合并 ⭐⭐⭐

**思路**: 将多个小的KG抽取任务合并成一个大的prompt

**示例**:
```python
# 当前: 每个chunk一次调用
for chunk in chunks:
    prompt = f"Extract entities from: {chunk.content}"
    result = await llm_client.generate(prompt)

# 优化后: 合并多个chunks
combined_prompt = """
Extract entities from the following texts:

Text 1:
{chunk1.content}

Text 2:
{chunk2.content}

Text 3:
{chunk3.content}

...
"""
result = await llm_client.generate(combined_prompt)
```

**优点**:
- ✅ 显著减少API调用次数
- ✅ 降低API费用

**缺点**:
- ⚠️ 可能超过token限制
- ⚠️ 需要更复杂的响应解析
- ⚠️ 错误传播（一个chunk失败可能影响整批）

**预计效果**:
- **调用次数**: N次 → N/merge_factor次
- 如果merge_factor=5: **减少80%调用**

---

#### 方案4: 启用更多缓存 ⭐⭐⭐⭐

**当前状态**:
```python
# 已启用
enable_extraction_cache: true  # 抽取结果缓存
enable_prompt_cache: true       # Prompt缓存
```

**额外优化**:
1. **增大缓存大小**:
```python
cache_max_size: 10000  # 默认
# 改为
cache_max_size: 50000  # 5倍容量
```

2. **持久化缓存** (当前是内存缓存):
```python
# 将缓存持久化到磁盘
cache_storage = JsonKVStorage(working_dir, namespace="llm_cache")
```

3. **跨会话缓存**:
```python
# 不同任务之间共享缓存
cache_ttl: null  # 永不过期
# 或设置较长的过期时间
cache_ttl: 86400  # 24小时
```

**效果**:
- ✅ 重复文档零额外调用
- ✅ 相似内容命中率提升

---

#### 方案5: 并发控制优化 ⭐⭐⭐

**当前**: `run_concurrent` 使用默认并发设置

**优化**:
```python
# 当前
results = await run_concurrent(
    kg_builder.extract,
    chunks,
    desc="[2/4]Extracting entities",
)

# 优化后：增加并发数
from asyncio import Semaphore

async def run_concurrent_with_limit(coro_fn, items, max_concurrent=50):
    semaphore = Semaphore(max_concurrent)
    
    async def limited_coro(item):
        async with semaphore:
            return await coro_fn(item)
    
    tasks = [limited_coro(item) for item in items]
    return await asyncio.gather(*tasks)

# 使用
results = await run_concurrent_with_limit(
    kg_builder.extract,
    chunks,
    max_concurrent=50,  # 增加并发数
)
```

**效果**:
- ✅ 更好地利用API并发限制
- ✅ 显著减少总耗时

---

## 📈 综合优化建议

### 立即可实施（无需代码修改）

1. **调整配置参数**:
```yaml
# graphgen/configs/*.yaml
split_config:
  batch_size: 30                     # 从10增大到30
  max_wait_time: 1.0                 # 从0.5增大到1.0
  use_adaptive_batching: true        # 启用自适应
  max_batch_size: 50
  
generation_config:
  batch_size: 30
  max_wait_time: 1.0
  use_adaptive_batching: true
  max_batch_size: 50
  enable_prompt_cache: true
  cache_max_size: 50000              # 增大缓存
```

**预计效果**: 
- 调用效率提升 **2-3倍**
- 总耗时减少 **30-50%**

---

### 中期优化（需要少量代码修改）

2. **使用合并模式**:
```python
# 在generation_config中启用
use_combined_mode: true  # Aggregated和CoT减少50%调用
```

3. **增大并发数**:
```python
# 修改run_concurrent，增加max_concurrent参数
max_concurrent: 50  # 默认是无限制
```

**预计效果**:
- 额外减少 **20-30%调用**
- 吞吐量提升 **50-100%**

---

### 长期优化（需要较大改动）

4. **实现真正的批量API调用**:
- 需要根据使用的API提供商实现批量接口
- OpenAI: 使用 Batch API
- 其他: 实现自定义批量协议

5. **Prompt合并策略**:
- 将多个小chunk合并成一个大prompt
- 需要实现智能分组和响应解析

**预计效果**:
- 调用次数减少 **70-80%**
- API费用减少 **50-70%**

---

## 📊 优化效果预测

假设当前场景：
- 100个文档
- 每个文档分成10个chunks
- 总共1000个chunks
- 生成500个QA对

### 当前状态

| 阶段 | 调用次数 | 说明 |
|------|---------|------|
| KG抽取 | 1000次 | 每个chunk一次 |
| 节点合并 | ~50次 | 部分节点需要合并 |
| QA生成 (Atomic) | 100次 | 假设100个batch |
| **总计** | **~1150次** | |

### 优化后（立即可实施）

| 阶段 | 调用次数 | 优化方法 | 减少比例 |
|------|---------|---------|---------|
| KG抽取 | 1000次 → 1000次 | 并发优化，不减少调用次数 | 0% |
| 节点合并 | 50次 → 50次 | 已经是批量 | 0% |
| QA生成 | 100次 → 100次 | 已经是批量 | 0% |
| **总耗时** | **100%** → **40-50%** | 批量大小增大+并发增加 | **减少50-60%** |

### 优化后（长期）

| 阶段 | 调用次数 | 优化方法 | 减少比例 |
|------|---------|---------|---------|
| KG抽取 | 1000次 → 200次 | Prompt合并(5合1) | 80% |
| 节点合并 | 50次 → 50次 | 不变 | 0% |
| QA生成 | 100次 → 20次 | 真正批量API(batch=5) | 80% |
| **总计** | **1150次** → **270次** | | **减少76%** |

---

## 🚀 实施建议

### 阶段1：立即优化（1天）

1. 修改配置文件，增大batch_size和max_wait_time
2. 启用use_adaptive_batching
3. 增大cache_max_size

### 阶段2：中期优化（3-5天）

1. 修改run_concurrent，增加并发控制参数
2. 全面启用use_combined_mode
3. 实现持久化缓存

### 阶段3：长期优化（1-2周）

1. 研究API的批量调用接口
2. 实现真正的批量API调用
3. 实现Prompt合并策略
4. 性能测试和调优

---

## 📝 总结

1. **当前的BatchRequestManager是伪批量**，只是并发处理，不是真正减少调用次数
2. **立即可实施的优化**主要是提高并发和吞吐量，不直接减少调用次数
3. **真正减少调用次数**需要实现批量API或Prompt合并
4. **最大优化潜力**: 减少 70-80%的LLM调用次数和50-70%的API费用

