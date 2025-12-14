# LLM评测集生成使用指南

## 概述

本指南介绍如何使用SFTGen框架生成LLM评测集，用于系统化地评测领域模型的知识问答能力。

## 评测集的作用

评测集与训练集的主要区别：

| 维度 | SFT训练集 | LLM评测集 |
|------|----------|----------|
| **目的** | 训练模型学习知识 | 测试模型已有能力 |
| **数量** | 大量（数千到数万） | 适中（数百到数千） |
| **多样性** | 可以有重复模式 | 需要高度多样化 |
| **难度** | 渐进式 | 分层设计，覆盖各难度 |
| **标准答案** | 可以灵活 | 需要明确的评分标准 |

## 评测维度

本框架支持四种评测维度：

### 1. 知识覆盖度评测 (Knowledge Coverage)
- **目的**：测试模型对领域知识的广度掌握
- **问题类型**：事实性问答、定义解释
- **示例**：
  ```json
  {
    "question": "什么是知识图谱？",
    "reference_answer": "知识图谱是一种结构化的语义知识库...",
    "key_points": ["结构化", "语义", "实体关系"]
  }
  ```

### 2. 推理能力评测 (Reasoning Ability)
- **目的**：测试模型的逻辑推理和多跳推理能力
- **问题类型**：多跳问答、因果推理、类比推理
- **示例**：
  ```json
  {
    "question": "如果A导致B，B导致C，那么A和C有什么关系？",
    "reference_answer": "A间接导致C...",
    "reasoning_path": ["A", "导致", "B", "导致", "C"]
  }
  ```

### 3. 事实准确性评测 (Factual Accuracy)
- **目的**：测试模型是否会产生幻觉或错误信息
- **问题类型**：真假判断、错误检测、选择题
- **示例**：
  ```json
  {
    "question": "以下哪个关于知识图谱的描述是正确的？",
    "reference_answer": "知识图谱使用图结构存储实体和关系",
    "distractors": ["知识图谱只能存储文本", "知识图谱不支持推理"]
  }
  ```

### 4. 综合应用评测 (Comprehensive Application)
- **目的**：测试模型综合运用知识解决复杂问题的能力
- **问题类型**：场景应用、问题解决、分析总结
- **示例**：
  ```json
  {
    "question": "如何设计一个知识图谱系统来管理企业知识？",
    "reference_answer": "需要考虑实体建模、关系抽取、知识存储...",
    "required_knowledge_points": ["知识建模", "数据存储", "查询接口"]
  }
  ```

## 快速开始

### 方法1：使用CLI工具

```bash
# 生成评测集（包含知识图谱构建）
python graphgen_eval_cli.py \
  --config_file graphgen/configs/evaluation_config.yaml \
  --output_dir ./output

# 使用已有知识图谱生成评测集
python graphgen_eval_cli.py \
  --config_file graphgen/configs/evaluation_config.yaml \
  --output_dir ./output \
  --skip_kg_build
```

### 方法2：使用Python API

```python
from graphgen.graphgen import GraphGen
import yaml

# 加载配置
with open("graphgen/configs/evaluation_config.yaml") as f:
    config = yaml.safe_load(f)

# 初始化GraphGen
graph_gen = GraphGen(unique_id=12345, working_dir="./output")

# 构建知识图谱
graph_gen.insert(
    read_config=config["read"],
    split_config=config["split"]
)

# 生成评测集
graph_gen.generate_evaluation(
    partition_config=config["partition"],
    evaluation_config=config["evaluation"]
)
```

### 方法3：集成到现有流程

在 `graphgen/generate.py` 的主流程中添加：

```python
# 生成训练数据
graph_gen.generate(
    partition_config=config["partition"],
    generate_config=config["generate"],
)

# 生成评测集
if config.get("evaluation", {}).get("enabled"):
    graph_gen.generate_evaluation(
        partition_config=config["partition"],
        evaluation_config=config["evaluation"],
    )
```

## 配置说明

### 基本配置

```yaml
evaluation:
  enabled: true
  dataset_name: "Domain Knowledge Evaluation Dataset"
  description: "Evaluation dataset for domain model assessment"
  
  # 目标数量
  target_eval_items: 200
  
  # 类型分布（总和必须为1.0）
  type_distribution:
    knowledge_coverage: 0.3
    reasoning_ability: 0.3
    factual_accuracy: 0.2
    comprehensive: 0.2
  
  # 难度分布（总和必须为1.0）
  difficulty_distribution:
    easy: 0.3
    medium: 0.5
    hard: 0.2
  
  # 输出格式
  output_format: "benchmark"  # benchmark, qa_pair, multiple_choice
  
  # 质量控制
  min_quality_score: 0.5
```

### 高级配置

```yaml
evaluation:
  # 知识覆盖度配置
  knowledge_coverage:
    include_definitions: true
    include_relationships: true
    coverage_strategy: "balanced"
  
  # 推理能力配置
  reasoning_ability:
    max_hops: 3
    include_causal: true
    include_analogical: true
  
  # 事实准确性配置
  factual_accuracy:
    include_true_false: true
    include_error_detection: true
    distractor_count: 3
  
  # 综合应用配置
  comprehensive:
    min_knowledge_points: 3
    include_scenarios: true
```

## 输出格式

### Benchmark格式（推荐）

完整的评测基准格式，包含所有元数据：

```json
{
  "name": "Domain Knowledge Evaluation Dataset",
  "description": "...",
  "items": [
    {
      "id": "eval_know_abc123",
      "type": "knowledge_coverage",
      "difficulty": "medium",
      "question": "什么是知识图谱？",
      "reference_answer": "...",
      "evaluation_criteria": {
        "key_points": ["结构化", "语义", "实体关系"],
        "scoring_rubric": "..."
      },
      "metadata": {
        "knowledge_nodes": ["知识图谱", "实体", "关系"],
        "reasoning_hops": 0
      }
    }
  ],
  "statistics": {
    "total_items": 200,
    "type_distribution": {...},
    "difficulty_distribution": {...}
  }
}
```

### QA Pair格式

简化的问答对格式：

```json
{
  "items": [
    {
      "id": "eval_001",
      "question": "什么是知识图谱？",
      "answer": "...",
      "type": "knowledge_coverage",
      "difficulty": "medium"
    }
  ]
}
```

### Multiple Choice格式

选择题格式（仅包含有干扰项的题目）：

```json
{
  "items": [
    {
      "id": "eval_001",
      "question": "以下哪个描述是正确的？",
      "correct_answer": "知识图谱使用图结构",
      "options": ["知识图谱使用图结构", "知识图谱只能存储文本", "..."],
      "explanation": "..."
    }
  ]
}
```

## 质量控制

### 自动质量检查

系统会自动检查：
- 问题长度（5-200词）
- 答案长度（3-500词）
- 问题格式（是否以问号结尾）
- 评分标准完整性
- 知识节点信息

### 难度评分

基于多个因素自动评分：
- 推理跳数
- 知识点数量
- 问题长度
- 答案复杂度
- 干扰项数量

### 过滤低质量项目

```python
from graphgen.operators.evaluate import filter_low_quality_items

# 过滤质量分数低于0.6的项目
high_quality_items = filter_low_quality_items(items, min_quality_score=0.6)
```

## 最佳实践

### 1. 合理设置目标数量

- 小规模评测：50-100个项目
- 中等规模：200-500个项目
- 大规模评测：500-1000个项目

### 2. 平衡类型分布

推荐分布：
- 知识覆盖度：30%
- 推理能力：30%
- 事实准确性：20%
- 综合应用：20%

### 3. 设置合适的难度分布

- 初级模型评测：easy 50%, medium 40%, hard 10%
- 中级模型评测：easy 30%, medium 50%, hard 20%
- 高级模型评测：easy 20%, medium 50%, hard 30%

### 4. 质量优先于数量

- 设置较高的 `min_quality_score`（建议0.6-0.7）
- 人工审核关键评测项
- 定期更新和优化评测集

## 使用评测集

### 评测模型

```python
import json

# 加载评测集
with open("output/data/evaluation/12345_eval.json") as f:
    eval_dataset = json.load(f)

# 对每个评测项进行测试
for item in eval_dataset["items"]:
    question = item["question"]
    reference_answer = item["reference_answer"]
    
    # 使用你的模型生成答案
    model_answer = your_model.generate(question)
    
    # 评分（可以使用LLM辅助评分）
    score = evaluate_answer(model_answer, reference_answer, item["evaluation_criteria"])
    
    print(f"Question: {question}")
    print(f"Score: {score}")
```

### 生成评测报告

```python
from graphgen.operators.evaluate import EvalQualityChecker

checker = EvalQualityChecker()
quality_report = checker.check_dataset_quality(eval_dataset["items"])

print(f"Overall Quality: {quality_report['overall_quality']}")
print(f"Diversity Score: {quality_report['diversity_score']}")
```

## 故障排除

### 问题1：生成的评测项数量不足

**原因**：知识图谱规模太小或质量过滤太严格

**解决方案**：
- 增加输入文档
- 降低 `min_quality_score`
- 增加 `target_eval_items`

### 问题2：评测项质量不高

**原因**：LLM模型能力不足或提示词不够清晰

**解决方案**：
- 使用更强的LLM模型
- 调整评测配置中的具体参数
- 增加人工审核环节

### 问题3：类型分布不均衡

**原因**：某些类型的生成失败率较高

**解决方案**：
- 检查日志查看具体错误
- 调整 `type_distribution` 比例
- 确保知识图谱包含足够的推理路径

## 总结

通过本指南，你可以：
1. ✅ 理解评测集的作用和评测维度
2. ✅ 使用CLI或API生成评测集
3. ✅ 配置评测集的类型和难度分布
4. ✅ 进行质量控制和过滤
5. ✅ 使用评测集测试模型能力

更多信息请参考：
- [实现方案](../implementation_plan.md)
- [配置示例](../resources/examples/evaluation_example.yaml)
- [API文档](http://localhost:8000/docs)
