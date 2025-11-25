# 算法模块验证文档

本文档验证技术报告中描述的算法模块与代码实现的对应关系。

## 1. 核心算法模块验证

### 1.1 知识构建模块

**报告描述**：从原始文档构建细粒度知识图谱，包括文档分割、实体/关系提取、知识聚合三个步骤。

**代码实现验证**：

✅ **文档分割**：
- 报告位置：3.3节步骤1、4.2.1节
- 代码位置：`graphgen/operators/split/split_chunks.py`
- 实现类：`RecursiveCharacterSplitter`, `CharacterSplitter`, `MarkdownSplitter`
- 验证：代码中存在对应实现，支持动态chunk大小调整

✅ **实体/关系提取**：
- 报告位置：3.3节步骤1、4.2.2节
- 代码位置：`graphgen/models/kg_builder/light_rag_kg_builder.py`
- 实现类：`LightRAGKGBuilder`
- 关键方法：`extract()` - 从chunk中提取实体和关系
- 验证：代码中存在对应实现，支持缓存和批量请求

✅ **知识聚合**：
- 报告位置：3.3节步骤1、4.2.3节
- 代码位置：`graphgen/models/kg_builder/light_rag_kg_builder.py`
- 关键方法：`merge_nodes()`, `merge_edges()` - 合并相同实体和关系
- 验证：代码中存在对应实现，支持实体类型选择、描述合并、知识总结

### 1.2 理解评估模块

**报告描述**：通过语义变体生成和置信度评估识别知识盲点，计算理解损失。

**代码实现验证**：

✅ **语义变体生成**：
- 报告位置：3.3节步骤2、4.3.1节
- 代码位置：`graphgen/operators/quiz.py`
- 关键函数：`quiz()` - 为知识图谱中的每条边和节点生成语义变体
- 验证：代码中存在对应实现，支持批量请求优化

✅ **置信度评估**：
- 报告位置：3.3节步骤2、4.3.2节
- 代码位置：`graphgen/operators/judge.py`
- 关键函数：`judge_statement()` - 评估训练模型对知识点的理解程度
- 验证：代码中存在对应实现，使用 `generate_topk_per_token()` 获取置信度

✅ **理解损失计算**：
- 报告位置：3.2.2节、4.3.3节
- 代码位置：`graphgen/utils/calculate_confidence.py`
- 关键函数：`yes_no_loss_entropy()` - 计算交叉熵损失
- 验证：代码中存在对应实现，公式与报告描述一致

### 1.3 图组织模块

**报告描述**：通过子图采样捕获复杂关系信息，使用ECE分区器进行BFS扩展。

**代码实现验证**：

✅ **ECE分区器**：
- 报告位置：3.3节步骤3、4.4.1节
- 代码位置：`graphgen/models/partitioner/ece_partitioner.py`
- 实现类：`ECEPartitioner`（继承自 `BFSPartitioner`）
- 关键方法：`partition()` - 基于ECE进行子图采样
- 验证：代码中存在对应实现，支持BFS扩展和约束检查

✅ **边选择策略**：
- 报告位置：3.2.4节、4.4.2节
- 代码位置：`graphgen/models/partitioner/ece_partitioner.py`
- 关键方法：`_sort_units()` - 根据采样策略排序单元
- 验证：代码中存在对应实现，支持max_loss、min_loss、random三种策略

✅ **约束检查**：
- 报告位置：3.3节步骤3、4.4.3节
- 代码位置：`graphgen/models/partitioner/ece_partitioner.py::_grow_community()`
- 验证：代码中存在对应实现，检查单元数约束和token数约束

### 1.4 QA生成模块

**报告描述**：将采样子图转换为多样化的QA对，支持原子、聚合、多跳三种模式。

**代码实现验证**：

✅ **原子生成器**：
- 报告位置：3.3节步骤4、4.5.2节
- 代码位置：`graphgen/models/generator/atomic_generator.py`
- 实现类：`AtomicGenerator`
- 关键方法：`build_prompt()`, `parse_response()` - 构建提示和解析结果
- 验证：代码中存在对应实现，支持多模板采样

✅ **聚合生成器**：
- 报告位置：3.3节步骤4、4.5.3节
- 代码位置：`graphgen/models/generator/aggregated_generator.py`
- 实现类：`AggregatedGenerator`
- 关键方法：`generate()` - 支持两步生成和合并模式
- 验证：代码中存在对应实现，支持合并模式减少50%调用

✅ **多跳生成器**：
- 报告位置：3.3节步骤4、4.5.4节
- 代码位置：`graphgen/models/generator/multi_hop_generator.py`
- 实现类：`MultiHopGenerator`
- 关键方法：`build_prompt()`, `parse_response()` - 构建多跳提示和解析推理路径
- 验证：代码中存在对应实现，支持推理路径提取

## 2. 数学模型验证

### 2.1 知识图谱定义

**报告公式**：$G = (E, R)$，其中 $E$ 为实体集合，$R$ 为关系集合

**代码验证**：
- ✅ 实现位置：`graphgen/models/storage/networkx_storage.py`
- ✅ 数据结构：使用NetworkX图库存储，节点表示实体，边表示关系
- ✅ 属性存储：节点和边都包含描述、类型、损失值等属性

### 2.2 理解损失计算

**报告公式**：$L(r_i) = -\frac{1}{n}\sum_{j=1}^{n}\log P_{M_{train}}(y_j | desc_i^j)$

**代码验证**：
- ✅ 实现位置：`graphgen/utils/calculate_confidence.py::yes_no_loss_entropy()`
- ✅ 公式对应：代码实现与公式一致，计算交叉熵损失
- ✅ 存储位置：损失值存储在边的属性中 `edge_data["loss"]`

### 2.3 子图采样策略

**报告公式**：$S(G, seed, k, \tau) = \{v \in V | d(seed, v) \leq k \land \sum_{u \in S} tokens(u) \leq \tau\}$

**代码验证**：
- ✅ 实现位置：`graphgen/models/partitioner/ece_partitioner.py::_grow_community()`
- ✅ BFS扩展：使用BFS算法实现k-hop扩展
- ✅ 约束检查：检查距离约束和token数约束

## 3. 性能优化模块验证

### 3.1 批量请求管理

**报告描述**：将多个LLM请求合并为批量处理，减少网络延迟

**代码验证**：
- ✅ 实现位置：`graphgen/utils/batch_request_manager.py`
- ✅ 关键类：`BatchRequestManager`
- ✅ 应用位置：`build_text_kg.py`, `quiz.py`, `generate_qas.py`

### 3.2 提取结果缓存

**报告描述**：基于chunk内容哈希缓存提取结果，避免重复提取

**代码验证**：
- ✅ 实现位置：`graphgen/models/kg_builder/light_rag_kg_builder.py::extract()`
- ✅ 缓存存储：`extraction_cache_storage`（JsonKVStorage）
- ✅ 缓存key：基于chunk内容的MD5哈希

### 3.3 Prompt缓存

**报告描述**：基于prompt hash的缓存机制

**代码验证**：
- ✅ 实现位置：`graphgen/utils/prompt_cache.py`
- ✅ 集成位置：`BatchLLMWrapper` 自动支持

## 4. 评估模块验证

### 4.1 MTLD评估器

**报告描述**：计算词汇多样性指标

**代码验证**：
- ✅ 实现位置：`graphgen/models/evaluator/mtld_evaluator.py`
- ✅ 实现类：`MTLDEvaluator`
- ✅ 计算方法：计算向前和向后MTLD，取平均值

### 4.2 UniEval评估器

**报告描述**：多维文本质量评估（自然性、连贯性、理解性）

**代码验证**：
- ✅ 实现位置：`graphgen/models/evaluator/uni_evaluator.py`
- ✅ 实现类：`UniEvaluator`
- ✅ 模型：使用 `MingZhong/unieval-sum` 模型

### 4.3 奖励模型评估器

**报告描述**：使用奖励模型对QA对进行评分

**代码验证**：
- ✅ 实现位置：`graphgen/models/evaluator/reward_evaluator.py`
- ✅ 实现类：`RewardEvaluator`
- ✅ 默认模型：`OpenAssistant/reward-model-deberta-v3-large-v2`

## 5. 验证总结

### 5.1 算法模块对应关系

| 报告模块 | 代码位置 | 验证状态 |
|---------|---------|---------|
| 知识构建 | `graphgen/operators/build_kg/`, `graphgen/models/kg_builder/` | ✅ 完全对应 |
| 理解评估 | `graphgen/operators/quiz.py`, `graphgen/operators/judge.py` | ✅ 完全对应 |
| 图组织 | `graphgen/models/partitioner/ece_partitioner.py` | ✅ 完全对应 |
| QA生成 | `graphgen/models/generator/` | ✅ 完全对应 |
| 性能优化 | `graphgen/utils/batch_request_manager.py` 等 | ✅ 完全对应 |
| 评估模块 | `graphgen/models/evaluator/` | ✅ 完全对应 |

### 5.2 数学模型对应关系

| 报告公式 | 代码实现 | 验证状态 |
|---------|---------|---------|
| 知识图谱定义 | `NetworkXStorage` | ✅ 完全对应 |
| 理解损失计算 | `yes_no_loss_entropy()` | ✅ 完全对应 |
| 子图采样策略 | `ECEPartitioner.partition()` | ✅ 完全对应 |
| 边选择策略 | `_sort_units()` | ✅ 完全对应 |

### 5.3 注意事项

1. **Baseline方法**：报告中提到的baseline方法（直接生成、模板填充、检索增强）不在GraphGen代码库中，需要单独实现用于对比实验。

2. **实验数据**：报告中的实验数据为示例数据，实际使用时需要通过 `docs/EXPERIMENT_SCRIPTS.md` 中的脚本生成。

3. **统计功能**：部分统计功能（如LLM调用次数、处理时间）需要在代码中添加统计逻辑，当前代码库中可能尚未完全实现。

4. **知识覆盖度计算**：长尾知识覆盖率和复杂关系覆盖率的计算逻辑需要根据 `docs/EXPERIMENT_SCRIPTS.md` 中的实现思路进行开发。

---

**验证结论**：报告中描述的所有核心算法模块在代码中都有对应实现，且实现细节与报告描述一致。数学模型和公式在代码中都有对应的实现。实验数据需要通过提供的脚本生成，部分统计功能需要额外开发。

