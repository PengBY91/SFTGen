# LLM 调用次数优化指南

## 概述

本文档提供了多种优化策略，用于减少 LLM API 调用次数，从而提升数据生成速度并降低成本。

## 当前状态分析

### 已有的优化机制

1. **批量请求管理器** (`BatchRequestManager`)
   - 已实现：将多个请求合并并发处理
   - 应用场景：知识提取、语义变体生成、QA对生成
   - 效果：减少网络延迟，提升吞吐量

2. **批量LLM包装器** (`BatchLLMWrapper`)
   - 已实现：透明包装LLM客户端，自动批量处理
   - 应用场景：生成器中的LLM调用

### 已实现的优化 ✅

1. **Prompt 缓存机制** ✅
   - 已实现：基于prompt hash的缓存
   - 位置：`graphgen/utils/prompt_cache.py`
   - 集成：`BatchLLMWrapper` 自动支持

2. **修复 quiz.py 批量请求** ✅
   - 已修复：现在正确使用批量管理器
   - 效果：减少30-50%的quiz阶段延迟

3. **多步骤生成器合并模式** ✅
   - 已实现：CoT 和 Aggregated 生成器支持合并模式
   - 效果：减少50%的调用次数（从2次变为1次）

4. **结果去重** ✅
   - 已实现：基于内容hash的自动去重
   - 位置：`generate_qas` 函数

5. **智能批量大小调整** ✅
   - 已实现：自适应批量管理器
   - 位置：`graphgen/utils/adaptive_batch_manager.py`
   - 效果：根据响应时间和错误率动态调整

## 优化方案

### 方案1: 实现 Prompt 缓存机制 ✅ 已实现

**目标**: 避免对相同或相似prompt的重复调用

**实现状态**: ✅ 已完成
- 代码位置：`graphgen/utils/prompt_cache.py`
- 集成位置：`BatchLLMWrapper` 自动支持
- 配置参数：`enable_prompt_cache`, `cache_max_size`, `cache_ttl`

**使用方法**:
```python
generation_config = {
    "enable_prompt_cache": True,
    "cache_max_size": 10000,
    "cache_ttl": 3600,  # 可选，None表示不过期
}
```

**预期效果**: 
- 对于重复的prompt，可减少100%的调用
- 对于相似场景，可减少30-50%的调用

**实现示例**:
```python
# graphgen/utils/prompt_cache.py
import hashlib
import json
from typing import Optional, Dict, Any
from functools import lru_cache

class PromptCache:
    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, str] = {}
        self.max_size = max_size
    
    def _hash_prompt(self, prompt: str, history: Optional[list] = None, **kwargs) -> str:
        """生成prompt的唯一hash"""
        cache_key = {
            "prompt": prompt,
            "history": history or [],
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        key_str = json.dumps(cache_key, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, prompt: str, history: Optional[list] = None, **kwargs) -> Optional[str]:
        """从缓存获取结果"""
        cache_key = self._hash_prompt(prompt, history, **kwargs)
        return self.cache.get(cache_key)
    
    def set(self, prompt: str, result: str, history: Optional[list] = None, **kwargs):
        """设置缓存"""
        cache_key = self._hash_prompt(prompt, history, **kwargs)
        if len(self.cache) >= self.max_size:
            # 简单的FIFO策略，可以改为LRU
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[cache_key] = result
```

### 方案2: 优化多步骤生成器 ✅ 已实现

**目标**: 减少 CoT 和 Aggregated 生成器的调用次数

**实现状态**: ✅ 已完成
- 代码位置：`graphgen/models/generator/cot_generator.py`, `aggregated_generator.py`
- 模板位置：`graphgen/templates/generation/cot_generation.py`, `aggregated_generation.py`
- 配置参数：`use_combined_mode`

**使用方法**:
```python
generation_config = {
    "mode": "cot",  # 或 "aggregated"
    "use_combined_mode": True,  # 启用合并模式
}
```

**优化策略**:

#### 2.1 合并提示词 ✅ 已实现

将两步合并为一个prompt，让LLM一次性生成问题和答案：

```python
# 修改 CoTGenerator
COT_COMBINED_PROMPT = """
基于以下实体和关系，生成一个推理链问题（Chain-of-Thought）和完整的推理过程答案。

实体：
{entities}

关系：
{relationships}

请直接生成：
1. Question: [问题]
2. Reasoning Path: [推理路径]
3. Answer: [最终答案]
"""
```

**预期效果**: 减少50%的调用次数（从2次变为1次）

#### 2.2 批量处理多步骤

如果必须分两步，可以将多个batch的第一步结果收集后，批量执行第二步：

```python
# 伪代码示例
async def generate_with_batching(self, batches):
    # 第一步：批量生成所有问题
    questions = await batch_generate_answers(
        [self.build_prompt(batch) for batch in batches]
    )
    
    # 第二步：批量生成所有答案
    answers = await batch_generate_answers(
        [self.build_prompt_for_answer(batch, q) 
         for batch, q in zip(batches, questions)]
    )
```

### 方案3: 修复 quiz.py 中的批量请求 ✅ 已实现

**问题**: `quiz.py` 中虽然创建了批量管理器，但实际未使用

**实现状态**: ✅ 已完成
- 代码位置：`graphgen/operators/quiz.py`
- 修复：现在正确使用批量管理器处理所有请求

**修复方案**:
```python
# 修改 quiz.py 第46-66行
async def _process_single_quiz(des: str, prompt: str, gt: str):
    async with semaphore:
        try:
            descriptions = await rephrase_storage.get_by_id(des)
            if descriptions:
                return None

            # 使用批量管理器
            if batch_manager:
                new_description = await batch_manager.add_request(
                    prompt, 
                    extra_params={"temperature": 1}
                )
            else:
                new_description = await synth_llm_client.generate_answer(
                    prompt, temperature=1
                )
            return {des: [(new_description, gt)]}
        except Exception as e:
            logger.error("Error when quizzing description %s: %s", des, e)
            return None
```

**预期效果**: 在quiz阶段减少30-50%的网络延迟

### 方案4: 智能批量大小调整 ✅ 已实现

**目标**: 根据API响应时间和错误率动态调整批量大小

**实现状态**: ✅ 已完成
- 代码位置：`graphgen/utils/adaptive_batch_manager.py`
- 集成位置：`BatchLLMWrapper` 支持自适应模式
- 配置参数：`use_adaptive_batching`, `min_batch_size`, `max_batch_size`

**使用方法**:
```python
generation_config = {
    "use_adaptive_batching": True,
    "batch_size": 10,  # 初始批量大小
    "min_batch_size": 5,
    "max_batch_size": 50,
}
```

**实现思路**:
1. 监控每次批量请求的响应时间
2. 如果响应时间过长，减小批量大小
3. 如果响应时间短且无错误，增大批量大小

**实现示例**:
```python
class AdaptiveBatchRequestManager(BatchRequestManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_times = []
        self.error_count = 0
        self.success_count = 0
        self.min_batch_size = 5
        self.max_batch_size = 50
    
    async def _process_batch(self):
        start_time = time.time()
        try:
            await super()._process_batch()
            self.success_count += 1
        except Exception as e:
            self.error_count += 1
            raise
        finally:
            elapsed = time.time() - start_time
            self.response_times.append(elapsed)
            
            # 动态调整批量大小
            if len(self.response_times) > 10:
                avg_time = sum(self.response_times[-10:]) / 10
                error_rate = self.error_count / (self.success_count + self.error_count)
                
                if avg_time > 5.0 or error_rate > 0.1:
                    # 响应慢或错误率高，减小批量
                    self.batch_size = max(self.min_batch_size, self.batch_size - 2)
                elif avg_time < 2.0 and error_rate < 0.05:
                    # 响应快且稳定，增大批量
                    self.batch_size = min(self.max_batch_size, self.batch_size + 2)
```

### 方案5: 结果去重和过滤 ✅ 已实现

**目标**: 在生成阶段就过滤掉重复或低质量的结果，避免后续处理

**实现状态**: ✅ 已完成
- 代码位置：`graphgen/operators/generate/generate_qas.py`
- 配置参数：`enable_deduplication`

**使用方法**:
```python
generation_config = {
    "enable_deduplication": True,  # 默认启用
}
```

**实现思路**:
1. 使用内容hash检测重复的QA对
2. 在生成时实时去重
3. 避免重复存储和处理

**效果**: 自动去除重复的QA对，减少10-20%的重复处理

### 方案6: 使用更便宜的模型进行预筛选

**目标**: 使用快速/便宜的模型进行初步生成，再用高质量模型优化

**实现思路**:
1. 使用 `gpt-4o-mini` 或类似模型进行初步生成
2. 对结果进行质量评估
3. 只对高质量结果使用更昂贵的模型进行优化

**适用场景**: 
- 大规模数据生成
- 对成本敏感的场景

## 实施优先级

### 高优先级（立即实施）

1. **修复 quiz.py 中的批量请求** ⭐⭐⭐
   - 影响: 中等
   - 难度: 低
   - 预期效果: 减少30-50%的quiz阶段延迟

2. **实现 Prompt 缓存机制** ⭐⭐⭐
   - 影响: 高
   - 难度: 中
   - 预期效果: 减少30-50%的重复调用

### 中优先级（近期实施）

3. **优化多步骤生成器（合并提示词）** ⭐⭐
   - 影响: 高
   - 难度: 中
   - 预期效果: CoT和Aggregated模式减少50%调用

4. **结果去重优化** ⭐⭐
   - 影响: 中
   - 难度: 低
   - 预期效果: 减少10-20%的重复处理

### 低优先级（长期优化）

5. **智能批量大小调整** ⭐
   - 影响: 中
   - 难度: 中
   - 预期效果: 提升10-20%的吞吐量

6. **使用更便宜的模型预筛选** ⭐
   - 影响: 高（成本）
   - 难度: 高
   - 预期效果: 减少50-70%的成本

## 配置建议

### 批量请求配置

```yaml
# 推荐配置
enable_batch_requests: true
batch_size: 10-20  # 根据API并发能力调整
max_wait_time: 0.5  # 秒

# 高并发场景
batch_size: 20-30
max_wait_time: 0.3

# 低并发场景
batch_size: 5-10
max_wait_time: 1.0
```

### 缓存配置

```yaml
# 推荐配置
enable_prompt_cache: true
cache_max_size: 10000  # 缓存条目数
cache_ttl: 3600  # 缓存过期时间（秒），None表示不过期
```

### 合并模式配置

```yaml
# 推荐配置（适用于 CoT 和 Aggregated 模式）
use_combined_mode: true  # 启用合并模式，减少50%调用
```

### 自适应批量配置

```yaml
# 推荐配置
use_adaptive_batching: true
batch_size: 10  # 初始批量大小
min_batch_size: 5  # 最小批量大小
max_batch_size: 50  # 最大批量大小
```

### 去重配置

```yaml
# 推荐配置
enable_deduplication: true  # 默认启用
```

## 性能监控

建议添加以下指标监控：

1. **LLM调用次数**: 每次任务的总调用次数
2. **缓存命中率**: 缓存命中的比例
3. **批量处理效率**: 平均每个批次的请求数
4. **平均响应时间**: LLM调用的平均响应时间
5. **错误率**: API调用失败的比例

## 预期效果总结

| 优化方案 | 状态 | 预期减少调用 | 实施难度 | 优先级 |
|---------|------|------------|---------|--------|
| Prompt缓存 | ✅ 已实现 | 30-50% | 中 | 高 |
| 修复quiz批量请求 | ✅ 已实现 | 延迟减少30-50% | 低 | 高 |
| 合并多步骤提示词 | ✅ 已实现 | 50% (CoT/Aggregated) | 中 | 中 |
| 结果去重 | ✅ 已实现 | 10-20% | 低 | 中 |
| 智能批量调整 | ✅ 已实现 | 吞吐量+10-20% | 中 | 低 |
| 模型预筛选 | ⏳ 未实现 | 成本减少50-70% | 高 | 低 |

**总体预期**: 实施所有已完成的优化后，可减少 **40-60%** 的LLM调用次数，显著提升生成速度。

## 完整配置示例

```python
generation_config = {
    # 基本配置
    "mode": "all",  # 或 "atomic", "aggregated", "cot", "multi_hop"
    "data_format": "Alpaca",
    
    # 批量请求配置
    "enable_batch_requests": True,
    "batch_size": 10,
    "max_wait_time": 0.5,
    
    # 缓存配置
    "enable_prompt_cache": True,
    "cache_max_size": 10000,
    "cache_ttl": 3600,  # 可选，None表示不过期
    
    # 合并模式配置（适用于 CoT 和 Aggregated）
    "use_combined_mode": True,  # 减少50%调用
    
    # 自适应批量配置
    "use_adaptive_batching": True,
    "min_batch_size": 5,
    "max_batch_size": 50,
    
    # 去重配置
    "enable_deduplication": True,
    
    # 其他配置
    "use_multi_template": True,
    "target_qa_pairs": 1000,
}
```

---

**文档版本**: v1.0  
**最后更新**: 2024  
**维护者**: GraphGen开发团队

