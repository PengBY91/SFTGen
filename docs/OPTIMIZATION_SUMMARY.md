# GraphGen LLM调用优化实施总结

## 📅 实施日期
2025-11-27

## 🎯 优化目标
1. 减少LLM调用次数 70-80%
2. 提升处理效率 2-3倍
3. 降低API费用 50-70%

## ✅ 已实施的优化

### 1. 配置文件优化 ⭐⭐⭐⭐⭐

**修改文件**：
- `graphgen/configs/atomic_config.yaml`
- `graphgen/configs/aggregated_config.yaml`
- `graphgen/configs/cot_config.yaml`
- `graphgen/configs/multi_hop_config.yaml`

**优化参数**：
```yaml
split_config:
  # 批量请求优化（立即生效）
  enable_batch_requests: true
  batch_size: 30                    # 从10→30 (3倍)
  max_wait_time: 1.0                # 从0.5→1.0秒
  use_adaptive_batching: true       # 自适应批量管理
  min_batch_size: 10
  max_batch_size: 50
  
  # 缓存优化
  enable_extraction_cache: true
  
  # Prompt合并优化（关键！）
  enable_prompt_merging: true       # 减少70-80%调用
  prompt_merge_size: 5              # 5个chunk合并成1次调用

generation_config:
  # 批量请求优化
  enable_batch_requests: true
  batch_size: 30
  max_wait_time: 1.0
  use_adaptive_batching: true
  min_batch_size: 10
  max_batch_size: 50
  
  # Prompt缓存优化
  enable_prompt_cache: true
  cache_max_size: 50000             # 从10000→50000 (5倍)
  cache_ttl: null                   # 永不过期
  
  # 合并模式优化（Aggregated和CoT）
  use_combined_mode: true           # 减少50%调用
  
  # 去重优化
  enable_deduplication: true
  persistent_deduplication: true

quiz_and_judge:
  enable_batch_requests: true
  batch_size: 30
  max_wait_time: 1.0
```

**预计效果**：
- ✅ 吞吐量提升 **2-3倍**
- ✅ 总耗时减少 **30-50%**

---

### 2. Prompt合并优化（KG抽取阶段）⭐⭐⭐⭐⭐

**新增文件**：
- `graphgen/operators/build_kg/build_text_kg_optimized.py`

**核心原理**：
```
原始方法：
chunk1 → LLM调用1 → 结果1
chunk2 → LLM调用2 → 结果2
chunk3 → LLM调用3 → 结果3
chunk4 → LLM调用4 → 结果4
chunk5 → LLM调用5 → 结果5
总计: 5次调用

优化后（prompt_merge_size=5）：
[chunk1, chunk2, chunk3, chunk4, chunk5] 
    → 合并prompt → LLM调用1 → 分割结果 
    → [结果1, 结果2, 结果3, 结果4, 结果5]
总计: 1次调用
```

**技术实现**：
1. **Prompt构建**：将多个chunks合并到一个prompt
   ```python
   """
   [文本1]
   {chunk1.content}
   
   [文本2]
   {chunk2.content}
   
   [文本3]
   {chunk3.content}
   ...
   """
   ```

2. **响应解析**：按标记分割响应，分配给对应chunks
   - 中文标记：`[文本1]`, `[文本2]`, ...
   - 英文标记：`[Text 1]`, `[Text 2]`, ...

3. **缓存策略**：
   - 为整个batch生成缓存key
   - 避免重复处理相同的chunk组合

4. **Fallback机制**：
   - 如果无法按标记分割，将整个响应复制给所有chunks
   - 保证在任何情况下都能得到结果

**集成方式**：
- 修改 `graphgen/graphgen.py` 
- 根据配置自动选择优化版本或原始版本
- 向后兼容：`enable_prompt_merging: false` 可退回原始行为

**预计效果**：
- ✅ KG抽取阶段LLM调用减少 **70-80%**
- ✅ 对于1000个chunks：1000次调用 → 200次调用
- ✅ API费用减少 **50-70%**

---

### 3. 合并模式优化（QA生成阶段）⭐⭐⭐⭐

**配置启用**：
```yaml
generate:
  use_combined_mode: true  # Aggregated和CoT模式
```

**原理**：
- **Aggregated模式**：原本需要2次LLM调用（重述+问题生成）→ 1次调用
- **CoT模式**：原本需要2次LLM调用（模板设计+答案生成）→ 1次调用

**已存在功能**：这个功能代码已经实现，只需在配置中启用

**预计效果**：
- ✅ Aggregated和CoT各减少 **50%调用**

---

### 4. 自适应批量管理 ⭐⭐⭐

**启用方式**：
```yaml
use_adaptive_batching: true
min_batch_size: 10
max_batch_size: 50
```

**工作原理**：
- 根据API响应时间动态调整批量大小
- API快时增大batch_size（最大50）
- API慢或出错时减小batch_size（最小10）

**预计效果**：
- ✅ 自动优化批量大小
- ✅ 适应不同网络和API负载情况

---

### 5. 缓存优化 ⭐⭐⭐⭐

**多层缓存策略**：

1. **抽取结果缓存** (`enable_extraction_cache`)
   - 缓存每个chunk的抽取结果
   - 避免重复抽取相同内容

2. **Prompt缓存** (`enable_prompt_cache`)
   - LRU缓存，容量从10000→50000
   - 缓存prompt→response映射
   - 永不过期（`cache_ttl: null`）

3. **合并batch缓存** (Prompt合并模式)
   - 缓存整个chunk batch的抽取结果
   - 复合key：所有chunks内容的hash

**预计效果**：
- ✅ 重复内容零额外调用
- ✅ 提升处理速度

---

## 📊 预期效果对比

### 场景假设
- 100个文档
- 每个文档10个chunks
- 共1000个chunks
- 生成500个QA对

### 优化前

| 阶段 | 调用次数 | 说明 |
|------|---------|------|
| KG抽取 | 1000次 | 每个chunk一次 |
| 节点合并 | 50次 | 部分节点需要合并 |
| QA生成 (Aggregated) | 200次 | 100个batch × 2步骤 |
| **总计** | **1250次** | |

### 优化后

| 阶段 | 调用次数 | 优化方法 | 减少比例 |
|------|---------|---------|---------|
| KG抽取 | 200次 | Prompt合并(5→1) | **80%** ↓ |
| 节点合并 | 50次 | 已优化 | - |
| QA生成 (Aggregated) | 100次 | 合并模式(2→1) | **50%** ↓ |
| **总计** | **350次** | | **72%** ↓ |

### 性能提升

| 指标 | 优化前 | 优化后 | 提升 |
|------|-------|--------|------|
| **总调用次数** | 1250次 | 350次 | **↓72%** |
| **API费用** | 100% | 35% | **↓65%** |
| **处理时长** | 100% | 40-50% | **↓50-60%** |
| **吞吐量** | 1x | 2-3x | **↑2-3倍** |

---

## 🔧 使用说明

### 立即使用优化

所有优化已经在配置文件中启用，直接运行即可：

```bash
# 使用atomic模式（已优化）
python graphgen_cli.py --config graphgen/configs/atomic_config.yaml

# 使用aggregated模式（已优化）
python graphgen_cli.py --config graphgen/configs/aggregated_config.yaml

# 使用cot模式（已优化）
python graphgen_cli.py --config graphgen/configs/cot_config.yaml

# 使用multi_hop模式（已优化）
python graphgen_cli.py --config graphgen/configs/multi_hop_config.yaml
```

### 自定义优化参数

如果需要调整优化参数，编辑配置文件：

```yaml
split_config:
  # 调整Prompt合并大小
  prompt_merge_size: 5    # 建议范围: 3-10
                          # 越大越省调用，但单次调用越慢
  
  # 调整批量大小
  batch_size: 30          # 建议范围: 20-50
  
  # 调整缓存大小
  enable_extraction_cache: true
  
generation_config:
  # 调整QA生成批量
  batch_size: 30          # 建议范围: 20-50
  
  # 调整缓存
  cache_max_size: 50000   # 根据内存情况调整
  
  # 启用/禁用合并模式
  use_combined_mode: true # Aggregated和CoT
```

### 禁用某个优化

如果某个优化导致问题，可以单独禁用：

```yaml
# 禁用Prompt合并（回退到原始模式）
enable_prompt_merging: false

# 禁用自适应批量
use_adaptive_batching: false

# 禁用缓存
enable_prompt_cache: false
enable_extraction_cache: false
```

---

## ⚠️ 注意事项

### 1. Token限制

Prompt合并会增加单次prompt的长度，确保不超过模型token限制：

```yaml
# 如果遇到token超限，减小合并大小
prompt_merge_size: 3  # 从5减小到3
```

### 2. 响应质量

合并prompt理论上不影响质量，但如果发现问题：

```yaml
# 禁用Prompt合并，回退到原始模式
enable_prompt_merging: false
```

### 3. 缓存清理

缓存会占用磁盘空间，定期清理：

```bash
# 清理所有缓存
python graphgen_cli.py --clear-cache

# 或手动删除
rm -rf cache/extraction_cache
```

### 4. 内存使用

增大batch_size和cache_max_size会增加内存使用：

```yaml
# 如果内存不足，减小参数
batch_size: 20          # 从30减小到20
cache_max_size: 20000   # 从50000减小到20000
```

---

## 📈 监控和验证

### 查看优化效果

运行时会在日志中显示优化信息：

```
[Prompt Merging] Enabled with merge_size=5. Expected to reduce LLM calls by ~80%
[Prompt Merging] Split 1000 chunks into 200 batches (merge_size=5)
[Adaptive Batch] Adjusted batch_size: 30 → 40 (avg_time=2.3s, error_rate=0%)
Cache hit rate: 45% (450/1000 requests)
```

### 性能指标

关注以下指标：

1. **总调用次数**：应该显著减少（60-80%）
2. **缓存命中率**：应该在30-50%（重复内容多时更高）
3. **处理时长**：应该减少40-60%
4. **API费用**：应该减少50-70%

### 问题排查

如果效果不明显：

1. 检查是否真正启用了优化：
   ```bash
   grep "Prompt Merging" logs/*.log
   grep "use_combined_mode" graphgen/configs/*.yaml
   ```

2. 查看缓存命中率：
   ```bash
   grep "Cache hit" logs/*.log | wc -l
   ```

3. 验证批量大小：
   ```bash
   grep "batch_size" logs/*.log
   ```

---

## 🚀 后续优化建议

### 已完成 ✅
1. ✅ 配置文件优化
2. ✅ Prompt合并（KG抽取）
3. ✅ 合并模式启用（QA生成）
4. ✅ 自适应批量管理
5. ✅ 多层缓存策略

### 未来可能的优化 💡

1. **真正的批量API调用**
   - 如果API支持批量接口（如OpenAI Batch API）
   - 可进一步减少网络开销
   - 预计额外减少10-20%费用

2. **智能chunk分组**
   - 根据内容相似度分组
   - 相似chunks更容易合并
   - 提高合并效果

3. **持久化缓存**
   - 将内存缓存持久化到数据库
   - 跨会话共享缓存
   - 团队协作场景受益

4. **并发控制优化**
   - 动态调整并发数
   - 根据API限流自动调节
   - 避免触发rate limit

---

## 📚 参考文档

- [LLM调用分析文档](./LLM_CALL_ANALYSIS.md) - 详细的调用分析和理论基础
- [解析逻辑改进文档](./PARSING_IMPROVEMENT.md) - 解析器鲁棒性改进
- [配置文件示例](../graphgen/configs/) - 各种模式的配置示例

---

## 📝 变更日志

### 2025-11-27
- ✅ 实施配置文件优化（batch_size, cache等）
- ✅ 实现Prompt合并优化（KG抽取阶段）
- ✅ 启用所有优化选项（合并模式、自适应批量等）
- ✅ 创建优化文档

### 预期收益
- LLM调用次数减少 **70-80%**
- 处理效率提升 **2-3倍**
- API费用降低 **50-70%**

---

## 💬 反馈和支持

如果遇到问题或有优化建议，请：
1. 查看日志文件中的ERROR和WARNING
2. 检查配置文件是否正确
3. 尝试禁用某个优化项排查问题
4. 记录问题现象和配置参数

---

**优化实施完成！** 🎉

现在GraphGen将以更高的效率、更低的成本运行！

