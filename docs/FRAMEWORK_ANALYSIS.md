# GraphGen框架详细解析

本文档基于代码库实现，详细解析GraphGen框架的四个核心步骤及其技术实现。

## 一、GraphGen框架概述

GraphGen是一个**知识图谱引导的合成数据生成框架**，专为解决大语言模型(LLMs)监督微调(SFT)中的高质量训练数据稀缺问题而设计。该框架特别针对**知识密集型任务**，通过结构化知识指导，系统性提高合成数据质量，避免传统合成数据方法常见的事实错误、知识覆盖不足和同质化问题。

### 框架核心特点

- **针对三种关键问答(QA)场景优化**：原子QA(atomic QA)、聚合QA(aggregated QA)和多跳QA(multi-hop QA)
- **采用预期校准误差(ECE)识别模型知识盲点**，优先生成高价值、长尾知识
- **通过多跳邻域采样捕获复杂关系信息**
- **使用风格控制生成提高数据多样性**

### 代码实现位置

核心框架实现在 `graphgen/graphgen.py` 中的 `GraphGen` 类，主要包含以下方法：
- `insert()`: 知识构建
- `quiz_and_judge()`: 理解评估
- `generate()`: QA生成（包含图组织步骤）

---

## 二、GraphGen四步工作流程

### 步骤1：知识构建(Knowledge Construction)

**目标**：从原始文本构建细粒度知识图谱

**代码实现位置**：
- 主入口：`graphgen/graphgen.py::GraphGen.insert()`
- 文本知识图谱构建：`graphgen/operators/build_kg/build_text_kg.py`
- 多模态知识图谱构建：`graphgen/operators/build_kg/build_mm_kg.py`
- 知识提取器：`graphgen/models/kg_builder/light_rag_kg_builder.py`

**详细过程**：

#### 1. 文档分割

**实现位置**：`graphgen/operators/split/split_chunks.py`

- 将原始文档分割成较小的、语义连贯的片段
- 使用上下文感知分块技术
- 支持多种分割策略：
  - `RecursiveCharacterSplitter`: 递归字符分割
  - `CharacterSplitter`: 字符分割
  - `MarkdownSplitter`: Markdown分割

**配置参数**（见 `graphgen/configs/*.yaml`）：
```yaml
split:
  chunk_size: 1024      # 分块大小
  chunk_overlap: 100     # 分块重叠
```

#### 2. 实体/关系提取

**实现位置**：
- 提取逻辑：`graphgen/models/kg_builder/light_rag_kg_builder.py::LightRAGKGBuilder.extract()`
- 提示模板：`graphgen/templates/kg/kg_extraction.py`

**详细流程**：

1. **语言检测**：使用 `detect_main_language()` 检测文档语言（中文/英文）

2. **LLM提取**：使用合成器模型(Msynth，通常为能力更强的LLM，如Qwen2.5-72B)从片段中提取实体和关系
   ```python
   # graphgen/models/kg_builder/light_rag_kg_builder.py:36-41
   hint_prompt = KG_EXTRACTION_PROMPT[language]["TEMPLATE"].format(
       **KG_EXTRACTION_PROMPT["FORMAT"], input_text=content
   )
   final_result = await self.llm_client.generate_answer(hint_prompt)
   ```

3. **实体类型**：预定义实体类型包括：
   - 通用类别：日期(date)、位置(location)、事件(event)、人物(person)、组织(organization)等
   - 领域特定类别：如医疗中的基因(gene)、农业中的作物品种(work)等

4. **解析结果**：从LLM响应中解析实体和关系
   ```python
   # graphgen/models/kg_builder/light_rag_kg_builder.py:65-96
   records = split_string_by_multi_markers(final_result, ...)
   for record in records:
       entity = await handle_single_entity_extraction(attributes, chunk_id)
       relation = await handle_single_relationship_extraction(attributes, chunk_id)
   ```

#### 3. 知识聚合

**实现位置**：`graphgen/models/kg_builder/light_rag_kg_builder.py::merge_nodes()` 和 `merge_edges()`

- 当同一实体/关系出现在多个片段时，自动合并其描述
- 跨片段实体和关系聚合成完整知识图谱G=(E, R)
- 使用 `NetworkXStorage` 存储知识图谱

**优势**：
- 结合LLMs和KGs，解决长文本处理、格式噪声和知识分散分布等挑战
- 确保低幻觉率

---

### 步骤2：理解评估(Comprehension Assessment)

**目标**：识别训练模型(Mtrain)的知识盲点，确定需要针对性增强的知识点

**代码实现位置**：
- 主入口：`graphgen/graphgen.py::GraphGen.quiz_and_judge()`
- 语义变体生成：`graphgen/operators/quiz.py`
- 置信度评估：`graphgen/operators/judge.py`
- 损失计算：`graphgen/utils/calculate_confidence.py`

**详细过程**：

#### 1. 声明处理

**实现位置**：`graphgen/operators/quiz.py::quiz()`

- 将知识图谱中每条边的描述视为一个声明性陈述Ri
- 该陈述代表一个无条件为真的知识点Ki(P(Ri is true)=1)
- 对每个节点和边的描述进行处理

#### 2. 语义变体生成

**实现位置**：`graphgen/operators/quiz.py::_process_single_quiz()`

- 使用Msynth生成多个Ri的释义版本(Ri1, Ri2,..., Rin)及其否定形式(¬Ri1,¬Ri2,...,¬Rin)
- 提示模板：`graphgen/templates/description_rephrasing.py`
- 支持中英文两种语言

**代码示例**：
```python
# graphgen/operators/quiz.py:59-80
for i in range(max_samples):
    if i > 0:
        # 生成释义版本（ground truth: "yes"）
        tasks.append(_process_single_quiz(
            description,
            DESCRIPTION_REPHRASING_PROMPT[language]["TEMPLATE"].format(
                input_sentence=description
            ),
            "yes",
        ))
    # 生成否定形式（ground truth: "no"）
    tasks.append(_process_single_quiz(
        description,
        DESCRIPTION_REPHRASING_PROMPT[language]["ANTI_TEMPLATE"].format(
            input_sentence=description
        ),
        "no",
    ))
```

#### 3. 置信度评估

**实现位置**：`graphgen/operators/judge.py::judge_statement()`

- 通过二元是/否问题提示获取Mtrain对每个陈述的置信度
- 提示模板：`graphgen/templates/statement_judgement.py`
- 使用 `generate_topk_per_token()` 获取模型对"yes"/"no"的token概率

**代码示例**：
```python
# graphgen/operators/judge.py:56-64
for description, gt in descriptions:
    judgement = await trainee_llm_client.generate_topk_per_token(
        STATEMENT_JUDGEMENT_PROMPT["TEMPLATE"].format(
            statement=description
        )
    )
    judgements.append(judgement[0].top_candidates)
```

#### 4. 理解损失计算

**实现位置**：`graphgen/utils/calculate_confidence.py::yes_no_loss_entropy()`

- 通过计算真实分布与预测分布间的交叉熵定义理解损失
- 公式实现：
  ```python
  # graphgen/utils/calculate_confidence.py:52-64
  def yes_no_loss_entropy(tokens_list, ground_truth):
      losses = []
      for i, tokens in enumerate(tokens_list):
          token = tokens[0]
          if token.text == ground_truth[i]:
              losses.append(-math.log(token.prob))
          else:
              losses.append(-math.log(1 - token.prob))
      return sum(losses) / len(losses)
  ```

- 该损失衡量模型当前理解与完全掌握知识点间的差距，高损失值表示知识盲点
- 损失值存储在知识图谱的边属性中：`edge_data["loss"]`

**配置参数**：
```yaml
quiz_and_judge:
  enabled: true
  quiz_samples: 2        # 每个边生成的语义变体数量
  re_judge: false        # 是否重新评估已有样本
```

---

### 步骤3：图组织(Graph Organization)

**目标**：通过子图采样捕获复杂关系信息，确保生成数据的上下文连贯性

**代码实现位置**：
- 主入口：`graphgen/graphgen.py::GraphGen.generate()` -> `graphgen/operators/partition/partition_kg.py`
- ECE分区器：`graphgen/models/partitioner/ece_partitioner.py`
- BFS分区器：`graphgen/models/partitioner/bfs_partitioner.py`
- DFS分区器：`graphgen/models/partitioner/dfs_partitioner.py`

**详细过程**：

#### 1. 子图提取

**实现位置**：`graphgen/models/partitioner/ece_partitioner.py::ECEPartitioner.partition()`

- 使用k-hop子图提取算法组织知识
- 以高损失边为起点，扩展相关知识
- 邻居边根据遍历策略选择

**核心算法**：
```python
# graphgen/models/partitioner/ece_partitioner.py:80-141
async def _grow_community(seed_unit):
    # 使用BFS扩展社区
    while not queue.empty():
        cur_type, cur_id, _ = await queue.get()
        # 获取邻居单元
        neighbors = get_neighbors(cur_type, cur_id)
        # 根据采样策略排序
        neighbors = self._sort_units(neighbors, unit_sampling)
        # 添加邻居到社区
        for nb in neighbors:
            if await _add_unit(nb):
                await queue.put(nb)
```

#### 2. 遍历策略

**实现位置**：`graphgen/models/partitioner/ece_partitioner.py::_sort_units()`

**深度策略**：
- 控制k-hop深度，确保子图跨越预定义跳数
- 通过BFS算法实现

**长度策略**：
- 限制前提长度(pre_length，子图中实体和关系描述的总token数)
- 参数：`max_tokens_per_community`

**选择策略**：三种选项控制边选择
- `max_loss`：优先选择高损失边(更大不确定性)
- `min_loss`：优先选择低损失边(更稳定关系)
- `random`：随机选择边

**代码实现**：
```python
# graphgen/models/partitioner/ece_partitioner.py:29-52
@staticmethod
def _sort_units(units: list, edge_sampling: str) -> list:
    if edge_sampling == "random":
        random.shuffle(units)
    elif edge_sampling == "min_loss":
        units = sorted(units, key=lambda x: x[-1]["loss"])
    elif edge_sampling == "max_loss":
        units = sorted(units, key=lambda x: x[-1]["loss"], reverse=True)
    return units
```

#### 3. 约束检查

**实现位置**：`graphgen/models/partitioner/ece_partitioner.py::_grow_community()`

- 当子图满足预设约束条件时停止扩展
- 约束条件：
  - `max_units_per_community`: 最大单元数（节点+边）
  - `min_units_per_community`: 最小单元数
  - `max_tokens_per_community`: 最大token数

**配置参数**（见 `graphgen/configs/aggregated_config.yaml`）：
```yaml
partition:
  method: ece
  method_params:
    max_units_per_community: 20
    min_units_per_community: 5
    max_tokens_per_community: 10240
    unit_sampling: max_loss  # random, min_loss, max_loss
```

---

### 步骤4：QA生成(QA Generation)

**目标**：将采样子图转换为多样化的QA对，适应不同场景

**代码实现位置**：
- 主入口：`graphgen/operators/generate/generate_qas.py`
- 原子生成器：`graphgen/models/generator/atomic_generator.py`
- 聚合生成器：`graphgen/models/generator/aggregated_generator.py`
- 多跳生成器：`graphgen/models/generator/multi_hop_generator.py`
- 提示模板：`graphgen/templates/generation/`

**详细过程**：

#### 1. 原子QA生成

**实现位置**：`graphgen/models/generator/atomic_generator.py`

- 适用于单节点/边的子图
- 生成代表基本知识的简单QA对
- 提示模板：`graphgen/templates/generation/atomic_generation.py`

**代码示例**：
```python
# graphgen/models/generator/atomic_generator.py:10-22
def build_prompt(batch):
    nodes, edges = batch
    context = ""
    for node in nodes:
        context += f"- {node[0]}: {node[1]['description']}\n"
    for edge in edges:
        context += f"- {edge[0]} - {edge[1]}: {edge[2]['description']}\n"
    prompt = ATOMIC_GENERATION_PROMPT[language].format(context=context)
    return prompt
```

**配置**（见 `graphgen/configs/atomic_config.yaml`）：
```yaml
partition:
  method: dfs
  method_params:
    max_units_per_community: 1  # 原子分区，每个社区一个节点或边
generate:
  mode: atomic
```

#### 2. 聚合QA生成

**实现位置**：`graphgen/models/generator/aggregated_generator.py`

- 分析、总结子图中多个实体和关系
- 先将知识组织成连贯文本(答案)，再生成对应问题
- 适用于需要整合多源信息的场景

**代码流程**：
```python
# graphgen/models/generator/aggregated_generator.py:98-127
async def generate(batch):
    # 1. 构建重述提示，将子图转换为连贯文本
    rephrasing_prompt = self.build_prompt(batch)
    response = await self.llm_client.generate_answer(rephrasing_prompt)
    context = self.parse_rephrased_text(response)
    
    # 2. 基于连贯文本生成问题
    question_generation_prompt = self._build_prompt_for_question_generation(context)
    response = await self.llm_client.generate_answer(question_generation_prompt)
    question = self.parse_response(response)["question"]
```

**配置**（见 `graphgen/configs/aggregated_config.yaml`）：
```yaml
generate:
  mode: aggregated
```

#### 3. 多跳QA生成

**实现位置**：`graphgen/models/generator/multi_hop_generator.py`

- 澄清实体间关系路径
- 生成需要多步推理的QA对
- 例："Ed Wood电影的导演是谁，他还导演了哪些知名电影？"

**配置**（见 `graphgen/configs/multi_hop_config.yaml`）：
```yaml
partition:
  method: ece
  method_params:
    max_units_per_community: 3  # 多跳推荐设置为3
    min_units_per_community: 3
    unit_sampling: random
generate:
  mode: multi_hop
```

#### 4. 输出格式

**实现位置**：`graphgen/bases/base_generator.py::format_generation_results()`

支持多种输出格式：
- **Alpaca格式**：用于Alpaca数据集
- **ShareGPT格式**：用于对话数据集
- **ChatML格式**：用于OpenAI格式

---

## 三、技术实现细节

### 模型配置

**代码位置**：`graphgen/graphgen.py::GraphGen.__post_init__()`

- **合成器模型(Msynth)**：Qwen2.5-72B-Instruct（负责知识提取和重述）
  - 通过环境变量 `SYNTHESIZER_MODEL`、`SYNTHESIZER_BASE_URL`、`SYNTHESIZER_API_KEY` 配置
  
- **训练模型(Mtrain)**：Qwen2.5-7B-Instruct（目标优化模型）
  - 通过环境变量 `TRAINEE_MODEL`、`TRAINEE_BASE_URL`、`TRAINEE_API_KEY` 配置

### 参数设置

**默认配置**（见各配置文件）：
- 图组织策略：
  - `pre_length=256`（通过 `max_tokens_per_community` 控制）
  - `max_depth=2`（通过BFS算法隐式控制）
  - `bidirectional=True`（BFS自然支持）
  
- 边选择策略：默认 `max_loss`（优先高损失边）
  ```yaml
  partition:
    method_params:
      unit_sampling: max_loss  # random, min_loss, max_loss
  ```

- 生成参数：
  - `temperature=0`（确定性生成，在 `judge_statement` 中使用）
  - `repetition_penalty=1.05`（在LLM客户端配置）

### 评估指标

**代码位置**：`graphgen/evaluate.py`

- **知识质量**：
  - ROUGE-F：评估生成文本与参考文本的重叠度
  - 事实准确性：评估生成内容的事实正确性

- **文本质量**：
  - MTLD（词汇多样性）：`graphgen/models/evaluator/mtld_evaluator.py`
  - UniEval（自然性、连贯性、理解性）：`graphgen/models/evaluator/uni_evaluator.py`

- **奖励模型评分**：
  - Ind和Deb两个奖励模型：`graphgen/models/evaluator/reward_evaluator.py`

### 存储系统

**代码位置**：`graphgen/models/storage/`

- **文档存储**：`JsonKVStorage` - 存储原始文档和分块
- **图谱存储**：`NetworkXStorage` - 使用NetworkX存储知识图谱
- **重述存储**：`JsonKVStorage` - 存储语义变体
- **QA存储**：`JsonListStorage` - 存储生成的QA对

---

## 四、工作流程总结

### 完整流程代码调用链

```
GraphGen.insert()
  ├── read_files()                    # 读取文件
  ├── chunk_documents()               # 文档分割
  └── build_text_kg() / build_mm_kg() # 知识提取
      └── LightRAGKGBuilder.extract() # LLM提取实体关系
          └── merge_nodes() / merge_edges() # 知识聚合

GraphGen.quiz_and_judge()
  ├── quiz()                          # 生成语义变体
  └── judge_statement()               # 评估置信度
      └── yes_no_loss_entropy()       # 计算理解损失

GraphGen.generate()
  ├── partition_kg()                  # 图组织
  │   └── ECEPartitioner.partition()  # ECE分区算法
  └── generate_qas()                 # QA生成
      ├── AtomicGenerator.generate()
      ├── AggregatedGenerator.generate()
      └── MultiHopGenerator.generate()
```

### 关键设计模式

1. **异步并发处理**：使用 `asyncio` 和 `run_concurrent()` 实现高并发
2. **存储抽象**：通过 `BaseStorage` 接口支持多种存储后端
3. **生成器模式**：通过 `BaseGenerator` 接口支持多种QA生成模式
4. **分区器模式**：通过 `BasePartitioner` 接口支持多种图分区策略

---

## 五、扩展与定制

### 添加新的QA生成模式

1. 继承 `BaseGenerator` 类
2. 实现 `build_prompt()` 和 `parse_response()` 方法
3. 在 `generate_qas()` 中注册新生成器

### 添加新的图分区策略

1. 继承 `BasePartitioner` 类
2. 实现 `partition()` 方法
3. 在 `partition_kg()` 中注册新分区器

### 添加新的评估指标

1. 继承 `BaseEvaluator` 类
2. 实现评估逻辑
3. 在 `evaluate.py` 中集成

---

## 六、参考资料

- 核心代码：`graphgen/graphgen.py`
- 配置文件：`graphgen/configs/*.yaml`
- 提示模板：`graphgen/templates/`
- 评估工具：`graphgen/evaluate.py`
- CLI工具：`graphgen_cli.py`
- Web界面：`webui/app.py`
- API服务：`backend/main.py`

---

**文档版本**：v1.0  
**最后更新**：基于代码库当前实现  
**维护者**：GraphGen开发团队

