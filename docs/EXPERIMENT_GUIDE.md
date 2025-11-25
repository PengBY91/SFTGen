# 实验复现指南

本文档提供GraphGen实验的完整复现步骤，包括数据生成、评估和结果分析。

## 目录

1. [环境准备](#环境准备)
2. [数据准备](#数据准备)
3. [运行GraphGen](#运行graphgen)
4. [运行基线方法](#运行基线方法)
5. [评估指标计算](#评估指标计算)
6. [结果汇总](#结果汇总)

## 环境准备

### 依赖安装

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装评估模型依赖（如需要）
pip install transformers torch sentence-transformers
```

### 环境变量配置

创建 `.env` 文件，配置LLM API密钥：

```bash
# 合成器模型（用于知识提取和QA生成）
SYNTHESIZER_MODEL=Qwen/Qwen2.5-72B-Instruct
SYNTHESIZER_API_KEY=your_api_key
SYNTHESIZER_BASE_URL=https://api.example.com/v1

# 训练模型（用于ECE评估）
TRAINEE_MODEL=Qwen/Qwen2.5-7B-Instruct
TRAINEE_API_KEY=your_api_key
TRAINEE_BASE_URL=https://api.example.com/v1

# 分词器
TOKENIZER_MODEL=cl100k_base
```

## 数据准备

### 输入数据格式

准备输入文档，支持以下格式：

- **文本文件**：`.txt` 格式，UTF-8编码
- **JSON格式**：包含 `content` 字段的JSON文件
- **JSONL格式**：每行一个JSON对象

示例输入文件位于 `resources/input_examples/`。

### 数据集统计

实验使用的数据集应包含：
- 文档总数：300篇（可根据实际情况调整）
- 总词元数：约90万词元
- 领域分布：技术（30%）、医学（25%）、历史（20%）、其他（25%）

## 运行GraphGen

### 1. 生成问答对

```bash
# 设置随机种子以确保可复现性
export PYTHONHASHSEED=42

# 运行GraphGen
python -m graphgen.generate \
    --config_file graphgen/configs/aggregated_config.yaml \
    --output_dir cache/experiments/graphgen
```

### 2. 检查输出

生成的QA对位于：
```
cache/experiments/graphgen/data/graphgen/<timestamp>/qa/*.json
```

知识图谱存储位置：
```
cache/experiments/graphgen/graph/
```

## 运行基线方法

### 直接生成方法

```bash
# 需要实现 scripts/baselines/direct_generation.py
python scripts/baselines/direct_generation.py \
    --input_dir resources/input_examples \
    --output_dir cache/experiments/direct_gen \
    --model Qwen/Qwen2.5-72B-Instruct \
    --num_samples 800
```

### 模板填充方法

```bash
# 需要实现 scripts/baselines/template_filling.py
python scripts/baselines/template_filling.py \
    --input_dir resources/input_examples \
    --output_dir cache/experiments/template_fill \
    --num_samples 800
```

### RAG方法

```bash
# 需要实现 scripts/baselines/rag_generation.py
python scripts/baselines/rag_generation.py \
    --input_dir resources/input_examples \
    --output_dir cache/experiments/rag_gen \
    --model Qwen/Qwen2.5-72B-Instruct \
    --num_samples 800
```

**注意**：基线方法的实现脚本需要单独开发，确保输出格式与GraphGen一致（Alpaca/ShareGPT/ChatML格式）。

## 评估指标计算

### 文本质量指标

对所有方法运行评估脚本：

```bash
# GraphGen
python -m graphgen.evaluate \
    --folder cache/experiments/graphgen/data/graphgen/<timestamp>/qa \
    --output cache/experiments/results/graphgen \
    --tokenizer cl100k_base \
    --reward "OpenAssistant/reward-model-deberta-v3-large-v2" \
    --uni "MingZhong/unieval-sum"

# 直接生成
python -m graphgen.evaluate \
    --folder cache/experiments/direct_gen/qa \
    --output cache/experiments/results/direct_gen \
    --tokenizer cl100k_base \
    --reward "OpenAssistant/reward-model-deberta-v3-large-v2" \
    --uni "MingZhong/unieval-sum"

# 模板填充
python -m graphgen.evaluate \
    --folder cache/experiments/template_fill/qa \
    --output cache/experiments/results/template_fill \
    --tokenizer cl100k_base \
    --reward "OpenAssistant/reward-model-deberta-v3-large-v2" \
    --uni "MingZhong/unieval-sum"

# RAG
python -m graphgen.evaluate \
    --folder cache/experiments/rag_gen/qa \
    --output cache/experiments/results/rag_gen \
    --tokenizer cl100k_base \
    --reward "OpenAssistant/reward-model-deberta-v3-large-v2" \
    --uni "MingZhong/unieval-sum"
```

评估结果保存在 `cache/experiments/results/<method>/evaluation.csv`。

### 知识覆盖指标

使用 `scripts/coverage_metrics.py` 计算知识覆盖指标：

```bash
# GraphGen
python scripts/coverage_metrics.py \
    --kg_dir cache/experiments/graphgen \
    --qa_folder cache/experiments/graphgen/data/graphgen/<timestamp>/qa \
    --output cache/experiments/results/graphgen/coverage_metrics.json \
    --long_tail_threshold 5 \
    --min_path_length 2

# 直接生成（使用相同的知识图谱）
python scripts/coverage_metrics.py \
    --kg_dir cache/experiments/graphgen \
    --qa_folder cache/experiments/direct_gen/qa \
    --output cache/experiments/results/direct_gen/coverage_metrics.json \
    --long_tail_threshold 5 \
    --min_path_length 2

# 模板填充
python scripts/coverage_metrics.py \
    --kg_dir cache/experiments/graphgen \
    --qa_folder cache/experiments/template_fill/qa \
    --output cache/experiments/results/template_fill/coverage_metrics.json \
    --long_tail_threshold 5 \
    --min_path_length 2

# RAG
python scripts/coverage_metrics.py \
    --kg_dir cache/experiments/graphgen \
    --qa_folder cache/experiments/rag_gen/qa \
    --output cache/experiments/results/rag_gen/coverage_metrics.json \
    --long_tail_threshold 5 \
    --min_path_length 2
```

**重要**：所有方法的知识覆盖指标计算必须使用**相同的知识图谱**（GraphGen构建的图谱），以确保公平对比。

## 结果汇总

### 提取文本质量指标

从 `evaluation.csv` 文件中提取以下指标：

- MTLD：`mtld` 列
- 自然度：`uni_naturalness` 列
- 连贯性：`uni_coherence` 列
- 可理解性：`uni_understandability` 列
- Ind奖励：`reward-model-deberta-v3-large-v2` 列（或对应的奖励模型列名）
- Deb奖励：另一个奖励模型的列名

### 提取知识覆盖指标

从 `coverage_metrics.json` 文件中提取：

- 长尾知识覆盖率：`long_tail_coverage` 字段（乘以100转换为百分比）
- 复杂关系覆盖率：`complex_relation_coverage` 字段（乘以100转换为百分比）
- 平均跳数：`average_hops` 字段

### 生成对比表格

可以使用以下Python脚本汇总所有结果：

```python
import json
import pandas as pd
import os

methods = ['graphgen', 'direct_gen', 'template_fill', 'rag_gen']
results_dir = 'cache/experiments/results'

# 文本质量指标
text_quality = {}
for method in methods:
    csv_path = os.path.join(results_dir, method, 'evaluation.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # 取平均值（如果有多个文件）
        text_quality[method] = {
            'MTLD': df['mtld'].mean(),
            'Naturalness': df['uni_naturalness'].mean(),
            'Coherence': df['uni_coherence'].mean(),
            'Understandability': df['uni_understandability'].mean(),
            'Ind Reward': df['reward-model-deberta-v3-large-v2'].mean(),
        }

# 知识覆盖指标
coverage_metrics = {}
for method in methods:
    json_path = os.path.join(results_dir, method, 'coverage_metrics.json')
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            coverage_metrics[method] = {
                'Long-tail Coverage': data['long_tail_coverage'] * 100,
                'Complex Relation Coverage': data['complex_relation_coverage'] * 100,
                'Average Hops': data['average_hops'],
            }

# 打印表格
print("文本质量对比：")
print(pd.DataFrame(text_quality).T)

print("\n知识覆盖对比：")
print(pd.DataFrame(coverage_metrics).T)
```

## 多次运行与统计

为确保结果的可复现性和统计显著性，建议：

1. **多次运行**：每种方法运行3次，使用不同的随机种子
2. **结果平均**：计算3次运行的平均值和标准差
3. **统计检验**：使用t检验等方法验证显著性差异

示例脚本：

```bash
# 运行3次GraphGen
for seed in 42 123 456; do
    export PYTHONHASHSEED=$seed
    python -m graphgen.generate \
        --config_file graphgen/configs/aggregated_config.yaml \
        --output_dir cache/experiments/graphgen_seed${seed}
done

# 评估3次运行
for seed in 42 123 456; do
    python -m graphgen.evaluate \
        --folder cache/experiments/graphgen_seed${seed}/data/graphgen/<timestamp>/qa \
        --output cache/experiments/results/graphgen_seed${seed}
done

# 计算平均值和标准差
python scripts/aggregate_results.py \
    --results_dir cache/experiments/results \
    --method graphgen \
    --output cache/experiments/results/graphgen_final.csv
```

## 常见问题

### Q: 基线方法如何实现？

A: 基线方法需要单独实现，确保：
1. 输出格式与GraphGen一致（JSON格式，包含question和answer字段）
2. 使用相同的评估脚本进行评估
3. 生成相同数量的QA对（约800个）

### Q: 知识覆盖指标计算失败？

A: 检查：
1. QA对的metadata是否包含`node_ids`和`edge_ids`字段
2. 知识图谱路径是否正确
3. NetworkX版本是否兼容

### Q: 评估模型加载失败？

A: 确保：
1. 已安装transformers和torch
2. 有足够的GPU内存（评估模型需要GPU）
3. 网络连接正常（需要下载模型）

## 参考

- GraphGen核心实现：`graphgen/graphgen.py`
- 评估器实现：`graphgen/models/evaluator/`
- 知识覆盖计算：`scripts/coverage_metrics.py`
- 评估脚本：`graphgen/evaluate.py`

