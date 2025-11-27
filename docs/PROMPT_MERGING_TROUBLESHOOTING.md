# Prompt合并功能故障排查指南

## 问题背景

在实施Prompt合并优化后，发现任务失败，错误表现为：
- 成功抽取到10个节点
- 但抽取到0条边
- 导致图谱分区生成0个社区
- 最终无法生成QA对

## 问题根源分析

### 1. Prompt合并的潜在问题

**问题**：合并多个chunks到一个prompt后，LLM可能：
- 没有理解为每个文本片段分别抽取
- 抽取结果混乱，标记不规范
- 只抽取了实体，忽略了关系

**日志证据**：
```
[Prompt Merging] Split 10 chunks into 2 batches (merge_size=5)
Writing graph with 10 nodes, 0 edges  ← 只有节点，没有边
```

### 2. 响应分割逻辑问题

**问题**：`parse_merged_extraction_response` 无法正确分割响应：
- LLM可能没有添加 `[文本1]`, `[Text 1]` 等标记
- 导致 `text_sections` 为空
- Fallback逻辑不够健壮

### 3. 无边图的处理

**问题**：当图谱没有边时，分区算法返回0个社区：
- ECE等算法依赖边来构建社区
- 孤立节点无法形成社区
- 导致后续生成流程中断

## 已实施的修复

### 修复1: 增强调试日志

在关键位置添加详细日志：
```python
# 记录响应长度和预览
logger.debug("Response preview: %s", response[:500])

# 记录解析进度
logger.info("Chunk %s extraction complete: %d nodes, %d edges", ...)

# 记录分割结果
logger.info("Found %d text sections for %d chunks", ...)
```

**文件**：`graphgen/operators/build_kg/build_text_kg_optimized.py`

### 修复2: 改进Fallback策略

**原始**：没有找到标记时，为每个chunk重复解析整个响应
```python
for chunk in chunk_batch:
    nodes, edges = await parse_single_extraction(response, chunk.id)
    results.append((nodes, edges))  # 重复数据
```

**优化后**：解析一次，然后复制给所有chunks
```python
# 解析一次
nodes, edges = await parse_single_extraction(response, chunk_batch[0].id)

# 为每个chunk创建副本，更新source_id
for chunk in chunk_batch:
    chunk_nodes = {k: [{**n, "source_id": chunk.id} for n in v] for k, v in nodes.items()}
    chunk_edges = {k: [{**e, "source_id": chunk.id} for e in v] for k, v in edges.items()}
    results.append((chunk_nodes, chunk_edges))
```

**好处**：
- 避免重复解析
- 正确设置每个chunk的source_id
- 保留所有抽取结果

### 修复3: 无边图的社区生成

**位置**：`graphgen/operators/partition/partition_kg.py`

**逻辑**：
```python
if len(communities) == 0:
    nodes = await kg_instance.get_all_nodes()
    edges = await kg_instance.get_all_edges()
    
    if len(nodes) > 0:
        if method == "ece":
            # 检查是否所有节点可以合并为一个社区
            total_tokens = sum(node[1].get("length", 100) for node in nodes)
            if total_tokens <= max_tokens:
                communities = [[node[0] for node in nodes]]  # 单个大社区
            else:
                communities = [[node[0]] for node in nodes]  # 每个节点一个社区
        else:
            communities = [[node[0]] for node in nodes]  # 每个节点一个社区
```

**效果**：
- ✅ 即使没有边，也能生成社区
- ✅ 孤立节点可以形成单节点社区
- ✅ 确保后续流程能继续执行

## 使用建议

### 1. 启用调试日志

运行任务时启用DEBUG级别日志：
```bash
export LOG_LEVEL=DEBUG
python graphgen_cli.py --config ...
```

查看日志：
```bash
tail -f cache/logs/*.log | grep "Prompt Merging\|extraction\|communities"
```

### 2. 调整Prompt合并大小

如果发现边抽取效果差，减小合并大小：
```yaml
split:
  prompt_merge_size: 3  # 从5减小到3
```

或完全禁用：
```yaml
split:
  enable_prompt_merging: false  # 回退到原始模式
```

### 3. 使用更适合的分区方法

对于小规模或稀疏图谱，使用DFS或BFS而不是ECE：
```yaml
partition:
  method: dfs  # 或 bfs
```

### 4. 验证测试文本

确保测试文本包含明确的实体和关系：

**好的示例**：
```
张三是一名工程师，他在ABC公司工作。ABC公司成立于2020年。
```
明确的关系：
- 张三 -- 职业是 --> 工程师
- 张三 -- 工作于 --> ABC公司
- ABC公司 -- 成立时间 --> 2020年

**不好的示例**：
```
今天天气很好。我很开心。
```
缺少明确的实体关系。

## 监控指标

关注以下日志输出：

### 1. Prompt合并是否启用
```
[Prompt Merging] Enabled with merge_size=5. Expected to reduce LLM calls by ~80%
```

### 2. 响应分割情况
```
Found 5 text sections for 5 chunks  ← 成功分割
Found 0 text sections for 5 chunks  ← 分割失败，使用fallback
```

### 3. 抽取结果统计
```
Chunk xxx extraction complete: 5 nodes, 3 edges  ← 正常
Chunk xxx extraction complete: 2 nodes, 0 edges  ← 可能有问题
```

### 4. 社区生成情况
```
Partitioned the graph into 10 communities.  ← 正常
Partitioned the graph into 0 communities.  ← 有问题，触发fallback
```

### 5. Fallback是否触发
```
Creating fallback communities with isolated nodes.  ← Fallback已触发
Created 10 single-node communities  ← Fallback成功
```

## 性能权衡

### Prompt合并的优缺点

**优点**：
- ✅ 显著减少API调用次数（80%）
- ✅ 降低API费用
- ✅ 提高吞吐量

**缺点**：
- ⚠️ 单次prompt更长，token使用增加
- ⚠️ LLM可能不完全遵循格式
- ⚠️ 响应解析更复杂
- ⚠️ 边抽取质量可能下降

### 建议配置

**小规模任务**（< 100 chunks）：
```yaml
enable_prompt_merging: false  # 不合并，质量优先
```

**中等规模任务**（100-1000 chunks）：
```yaml
enable_prompt_merging: true
prompt_merge_size: 3  # 保守的合并大小
```

**大规模任务**（> 1000 chunks）：
```yaml
enable_prompt_merging: true
prompt_merge_size: 5  # 激进的合并，成本优先
```

## 回退方案

如果Prompt合并导致质量问题，立即回退：

```yaml
# graphgen/configs/*.yaml
split:
  enable_prompt_merging: false
```

或在代码中禁用：
```python
# graphgen/graphgen.py
enable_prompt_merging = False  # 强制禁用
```

## 下一步优化

### 1. 改进Prompt格式

让LLM更清楚地理解任务：
```
你将看到5个文本片段，标记为[文本1]到[文本5]。
对于每个文本片段，你必须：
1. 抽取实体和关系
2. 在每个输出前添加对应的标记

重要：不要混淆不同文本的实体和关系！
```

### 2. 后处理验证

在解析后验证结果：
```python
# 检查每个chunk是否都有抽取结果
# 如果某个chunk为空，重新单独抽取
```

### 3. 自适应合并

根据chunk内容长度动态调整合并大小：
```python
# 短chunk可以合并更多
# 长chunk减少合并数量
```

### 4. 质量监控

记录合并前后的质量对比：
```
原始方法：平均每chunk 2.3个实体, 1.5个关系
合并方法：平均每chunk 2.1个实体, 1.2个关系
质量下降：8.7% 实体, 20% 关系
```

## 总结

通过以上修复，系统现在：
- ✅ 添加了详细的调试日志，便于排查问题
- ✅ 改进了Fallback策略，确保有抽取结果
- ✅ 处理了无边图的情况，生成fallback社区
- ✅ 确保即使在边缘情况下也能完成任务

建议：
1. 先在小规模数据上测试
2. 观察日志，确认优化效果
3. 根据实际情况调整参数
4. 如有问题，立即回退到原始模式

