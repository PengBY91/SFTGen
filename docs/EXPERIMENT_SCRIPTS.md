# 实验数据生成脚本说明

本文档提供实验报告中所有表格数据的生成脚本和实现思路。

## 1. 文本质量指标计算

### 1.1 MTLD（词汇多样性）

**实现位置**：`graphgen/models/evaluator/mtld_evaluator.py`

**计算脚本**：

```python
from graphgen.models.evaluator import MTLDEvaluator
from graphgen.bases.datatypes import QAPair

def calculate_mtld(qa_pairs):
    """
    计算QA对的MTLD分数
    
    参数:
        qa_pairs: List[QAPair] - QA对列表
    
    返回:
        float - 平均MTLD分数
    """
    evaluator = MTLDEvaluator()
    scores = []
    for pair in qa_pairs:
        score = await evaluator.evaluate_single(pair)
        scores.append(score)
    return sum(scores) / len(scores)
```

**使用示例**：

```bash
# 使用evaluate.py脚本
python -m graphgen.evaluate \
    --folder cache/data/graphgen/1234567890/qa \
    --output cache/output \
    --tokenizer cl100k_base
```

**数据来源**：从生成的QA对JSON文件中读取，对每个答案计算MTLD分数，取平均值。

### 1.2 UniEval（自然性、连贯性、理解性）

**实现位置**：`graphgen/models/evaluator/uni_evaluator.py`

**计算脚本**：

```python
from graphgen.models.evaluator import UniEvaluator
from graphgen.bases.datatypes import QAPair

def calculate_uni_scores(qa_pairs):
    """
    计算QA对的UniEval分数
    
    返回:
        dict - 包含naturalness, coherence, understandability的平均分数
    """
    evaluator = UniEvaluator(model_name="MingZhong/unieval-sum")
    scores = evaluator.get_average_score(qa_pairs)
    return scores
```

**数据来源**：使用UniEval模型对每个QA对进行评估，计算三个维度的平均分数。

### 1.3 奖励模型评分

**实现位置**：`graphgen/models/evaluator/reward_evaluator.py`

**计算脚本**：

```python
from graphgen.models.evaluator import RewardEvaluator
from graphgen.bases.datatypes import QAPair

def calculate_reward_scores(qa_pairs, reward_model_name):
    """
    计算QA对的奖励模型分数
    
    参数:
        qa_pairs: List[QAPair]
        reward_model_name: str - 奖励模型名称
    
    返回:
        float - 平均奖励分数
    """
    evaluator = RewardEvaluator(reward_name=reward_model_name)
    return evaluator.get_average_score(qa_pairs)
```

**数据来源**：
- **Ind奖励模型**：`OpenAssistant/reward-model-deberta-v3-large-v2`
- **Deb奖励模型**：其他奖励模型（需要指定）

## 2. 知识覆盖度指标计算

### 2.1 长尾知识覆盖率

**实现思路**：

长尾知识定义为在知识图谱中出现频率较低的知识点（实体或关系）。覆盖率计算为生成的QA对中涉及的长尾知识数量占总长尾知识数量的比例。

**计算脚本**：

```python
import networkx as nx
from collections import Counter

def calculate_long_tail_coverage(graph_storage, generated_qa_pairs):
    """
    计算长尾知识覆盖率
    
    参数:
        graph_storage: NetworkXStorage - 知识图谱存储
        generated_qa_pairs: List[dict] - 生成的QA对，包含context信息
    
    返回:
        float - 长尾知识覆盖率（0-1）
    """
    # 1. 统计知识图谱中所有实体的出现频率
    nodes = await graph_storage.get_all_nodes()
    node_freq = Counter([node[0] for node in nodes])
    
    # 2. 定义长尾知识：出现频率 <= 阈值（如5次）
    long_tail_threshold = 5
    long_tail_nodes = {
        node_id for node_id, freq in node_freq.items() 
        if freq <= long_tail_threshold
    }
    
    # 3. 统计生成的QA对中涉及的长尾知识
    covered_long_tail = set()
    for qa_pair in generated_qa_pairs:
        # 从QA对的context中提取涉及的实体
        context = qa_pair.get("context", {})
        nodes_in_qa = set(context.get("nodes", []))
        covered_long_tail.update(nodes_in_qa & long_tail_nodes)
    
    # 4. 计算覆盖率
    if len(long_tail_nodes) == 0:
        return 0.0
    coverage = len(covered_long_tail) / len(long_tail_nodes)
    return coverage
```

### 2.2 复杂关系覆盖率

**实现思路**：

复杂关系定义为需要多跳推理的关系（涉及3个或更多实体）。覆盖率计算为生成的QA对中涉及的复杂关系数量占总复杂关系数量的比例。

**计算脚本**：

```python
def calculate_complex_relation_coverage(graph_storage, generated_qa_pairs):
    """
    计算复杂关系覆盖率
    
    参数:
        graph_storage: NetworkXStorage - 知识图谱存储
        generated_qa_pairs: List[dict] - 生成的QA对
    
    返回:
        float - 复杂关系覆盖率（0-1）
    """
    # 1. 识别复杂关系：需要多跳推理的关系路径
    edges = await graph_storage.get_all_edges()
    
    # 构建图用于路径查找
    G = nx.Graph()
    for u, v, data in edges:
        G.add_edge(u, v, **data)
    
    # 2. 找出所有长度>=2的路径（复杂关系）
    complex_relations = set()
    for node in G.nodes():
        # 找出从该节点出发的所有2跳路径
        paths = nx.single_source_shortest_path(G, node, cutoff=2)
        for target, path in paths.items():
            if len(path) >= 3:  # 至少3个节点，2条边
                for i in range(len(path) - 1):
                    complex_relations.add((path[i], path[i+1]))
    
    # 3. 统计生成的QA对中涉及的复杂关系
    covered_complex = set()
    for qa_pair in generated_qa_pairs:
        context = qa_pair.get("context", {})
        edges_in_qa = set(context.get("edges", []))
        covered_complex.update(edges_in_qa & complex_relations)
    
    # 4. 计算覆盖率
    if len(complex_relations) == 0:
        return 0.0
    coverage = len(covered_complex) / len(complex_relations)
    return coverage
```

### 2.3 平均跳数

**实现思路**：

平均跳数计算为生成的QA对对应的子图中，从种子节点到最远节点的平均最短路径长度。

**计算脚本**：

```python
def calculate_average_hops(graph_storage, generated_qa_pairs):
    """
    计算平均跳数
    
    参数:
        graph_storage: NetworkXStorage - 知识图谱存储
        generated_qa_pairs: List[dict] - 生成的QA对，包含context信息
    
    返回:
        float - 平均跳数
    """
    hops = []
    
    for qa_pair in generated_qa_pairs:
        context = qa_pair.get("context", {})
        nodes = context.get("nodes", [])
        edges = context.get("edges", [])
        
        if len(nodes) < 2:
            hops.append(0)
            continue
        
        # 构建子图
        subgraph = nx.Graph()
        for u, v in edges:
            subgraph.add_edge(u, v)
        
        # 计算子图中所有节点对之间的最短路径长度
        path_lengths = []
        node_list = list(subgraph.nodes())
        for i, u in enumerate(node_list):
            for v in node_list[i+1:]:
                if nx.has_path(subgraph, u, v):
                    length = nx.shortest_path_length(subgraph, u, v)
                    path_lengths.append(length)
        
        if path_lengths:
            avg_hops = sum(path_lengths) / len(path_lengths)
            hops.append(avg_hops)
    
    return sum(hops) / len(hops) if hops else 0.0
```

## 3. 效率指标计算

### 3.1 LLM调用次数统计

**实现思路**：

在LLM客户端中维护调用计数器，记录每次API调用的信息。

**计算脚本**：

```python
class LLMCallCounter:
    """LLM调用次数统计器"""
    
    def __init__(self):
        self.call_count = 0
        self.call_details = []
    
    def record_call(self, stage, model_name, tokens_used):
        """记录一次LLM调用"""
        self.call_count += 1
        self.call_details.append({
            "stage": stage,  # "extract", "quiz", "judge", "generate"
            "model": model_name,
            "tokens": tokens_used,
            "timestamp": time.time()
        })
    
    def get_total_calls(self):
        """获取总调用次数"""
        return self.call_count
    
    def get_calls_by_stage(self):
        """按阶段统计调用次数"""
        stage_counts = {}
        for detail in self.call_details:
            stage = detail["stage"]
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        return stage_counts

# 在OpenAIClient中集成
class OpenAIClient(BaseLLMClient):
    def __init__(self, ..., call_counter=None):
        super().__init__(...)
        self.call_counter = call_counter or LLMCallCounter()
    
    async def generate_answer(self, ...):
        # 记录调用
        self.call_counter.record_call("generate", self.model_name, tokens)
        # ... 实际调用逻辑
```

**使用示例**：

```python
# 在GraphGen中使用
call_counter = LLMCallCounter()
graph_gen = GraphGen(
    synthesizer_llm_client=OpenAIClient(..., call_counter=call_counter),
    trainee_llm_client=OpenAIClient(..., call_counter=call_counter)
)

# 执行生成流程
await graph_gen.insert(...)
await graph_gen.quiz_and_judge(...)
await graph_gen.generate(...)

# 获取统计信息
total_calls = call_counter.get_total_calls()
calls_by_stage = call_counter.get_calls_by_stage()
```

### 3.2 处理时间统计

**实现思路**：

使用时间戳记录各个阶段的开始和结束时间。

**计算脚本**：

```python
import time
from contextlib import contextmanager

class TimeTracker:
    """处理时间跟踪器"""
    
    def __init__(self):
        self.stage_times = {}
        self.total_time = 0
    
    @contextmanager
    def track_stage(self, stage_name):
        """跟踪某个阶段的执行时间"""
        start_time = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start_time
            self.stage_times[stage_name] = elapsed
            self.total_time += elapsed
    
    def get_total_time(self):
        """获取总处理时间"""
        return self.total_time
    
    def get_stage_times(self):
        """获取各阶段时间"""
        return self.stage_times

# 使用示例
tracker = TimeTracker()

with tracker.track_stage("knowledge_construction"):
    await graph_gen.insert(...)

with tracker.track_stage("comprehension_assessment"):
    await graph_gen.quiz_and_judge(...)

with tracker.track_stage("qa_generation"):
    await graph_gen.generate(...)

total_time = tracker.get_total_time()
```

### 3.3 缓存命中率统计

**实现思路**：

在缓存存储中维护命中/未命中统计。

**计算脚本**：

```python
class CacheStats:
    """缓存统计"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
    
    def record_hit(self):
        self.hits += 1
    
    def record_miss(self):
        self.misses += 1
    
    def get_hit_rate(self):
        """获取命中率"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

# 在LightRAGKGBuilder中集成
class LightRAGKGBuilder:
    def __init__(self, ..., cache_stats=None):
        self.cache_stats = cache_stats or CacheStats()
    
    async def extract(self, chunk):
        if self.enable_cache:
            cached_result = await self.cache_storage.get_by_id(chunk_hash)
            if cached_result:
                self.cache_stats.record_hit()
                return cached_result
            else:
                self.cache_stats.record_miss()
        
        # ... 实际提取逻辑
```

## 4. 完整实验数据生成脚本

### 4.1 主实验脚本

```python
"""
完整实验数据生成脚本
用于生成报告中所有表格的数据
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List

from graphgen.graphgen import GraphGen
from graphgen.models.evaluator import (
    MTLDEvaluator,
    RewardEvaluator,
    UniEvaluator,
    LengthEvaluator
)
from graphgen.bases.datatypes import QAPair
from graphgen.utils import logger

class ExperimentRunner:
    """实验运行器"""
    
    def __init__(self, config):
        self.config = config
        self.results = {}
        self.call_counter = LLMCallCounter()
        self.time_tracker = TimeTracker()
        self.cache_stats = CacheStats()
    
    async def run_baseline_direct_generation(self, documents):
        """运行直接生成baseline"""
        logger.info("Running Direct Generation baseline...")
        
        # 实现直接生成逻辑
        # 使用LLM直接从文档生成QA对
        qa_pairs = await self._direct_generate(documents)
        
        # 评估
        metrics = await self._evaluate_qa_pairs(qa_pairs)
        
        # 统计
        stats = {
            "llm_calls": self.call_counter.get_total_calls(),
            "time": self.time_tracker.get_total_time(),
            "metrics": metrics
        }
        
        return stats
    
    async def run_baseline_template_filling(self, documents):
        """运行模板填充baseline"""
        logger.info("Running Template Filling baseline...")
        # 类似实现
        ...
    
    async def run_baseline_retrieval_augmented(self, documents):
        """运行检索增强baseline"""
        logger.info("Running Retrieval-Augmented baseline...")
        # 类似实现
        ...
    
    async def run_graphgen(self, documents, enable_optimization=True):
        """运行GraphGen"""
        logger.info(f"Running GraphGen (optimization={enable_optimization})...")
        
        # 初始化GraphGen
        graph_gen = GraphGen(
            working_dir=self.config.working_dir,
            synthesizer_llm_client=OpenAIClient(
                ...,
                call_counter=self.call_counter
            ),
            trainee_llm_client=OpenAIClient(
                ...,
                call_counter=self.call_counter
            )
        )
        
        # 配置优化选项
        split_config = {
            "chunk_size": 1024,
            "chunk_overlap": 100,
            "enable_extraction_cache": enable_optimization,
            "enable_batch_requests": enable_optimization,
            "batch_size": 10,
            "max_wait_time": 0.5
        }
        
        # 执行流程
        with self.time_tracker.track_stage("knowledge_construction"):
            await graph_gen.insert(
                read_config={"input_file": documents},
                split_config=split_config
            )
        
        with self.time_tracker.track_stage("comprehension_assessment"):
            await graph_gen.quiz_and_judge(
                quiz_and_judge_config={
                    "enabled": True,
                    "quiz_samples": 2,
                    "enable_batch_requests": enable_optimization
                }
            )
        
        with self.time_tracker.track_stage("qa_generation"):
            await graph_gen.generate(
                partition_config={
                    "method": "ece",
                    "method_params": {
                        "max_units_per_community": 20,
                        "unit_sampling": "max_loss"
                    }
                },
                generate_config={
                    "mode": "all",
                    "enable_batch_requests": enable_optimization
                }
            )
        
        # 获取生成的QA对
        qa_pairs = await self._load_qa_pairs(graph_gen.qa_storage)
        
        # 评估
        metrics = await self._evaluate_qa_pairs(qa_pairs)
        
        # 计算知识覆盖度
        coverage_metrics = await self._calculate_coverage_metrics(
            graph_gen.graph_storage,
            qa_pairs
        )
        
        # 统计
        stats = {
            "llm_calls": self.call_counter.get_total_calls(),
            "time": self.time_tracker.get_total_time(),
            "cache_hit_rate": self.cache_stats.get_hit_rate(),
            "metrics": metrics,
            "coverage": coverage_metrics
        }
        
        return stats
    
    async def _evaluate_qa_pairs(self, qa_pairs: List[QAPair]) -> Dict:
        """评估QA对的质量"""
        metrics = {}
        
        # MTLD
        mtld_evaluator = MTLDEvaluator()
        metrics["mtld"] = mtld_evaluator.get_average_score(qa_pairs)
        
        # UniEval
        uni_evaluator = UniEvaluator()
        uni_scores = uni_evaluator.get_average_score(qa_pairs)
        metrics["naturalness"] = uni_scores["naturalness"]
        metrics["coherence"] = uni_scores["coherence"]
        metrics["understandability"] = uni_scores["understandability"]
        
        # Reward Models
        reward_evaluator_ind = RewardEvaluator(
            reward_name="OpenAssistant/reward-model-deberta-v3-large-v2"
        )
        metrics["ind_reward"] = reward_evaluator_ind.get_average_score(qa_pairs)
        
        # 长度
        length_evaluator = LengthEvaluator()
        length_scores = length_evaluator.get_average_score(qa_pairs)
        metrics["avg_length"] = length_scores.get("answer", 0)
        
        return metrics
    
    async def _calculate_coverage_metrics(self, graph_storage, qa_pairs):
        """计算知识覆盖度指标"""
        return {
            "long_tail_coverage": await calculate_long_tail_coverage(
                graph_storage, qa_pairs
            ),
            "complex_relation_coverage": await calculate_complex_relation_coverage(
                graph_storage, qa_pairs
            ),
            "avg_hops": await calculate_average_hops(graph_storage, qa_pairs)
        }
    
    async def run_all_experiments(self):
        """运行所有实验"""
        documents = self._load_documents()
        
        results = {}
        
        # Baseline方法
        results["direct_generation"] = await self.run_baseline_direct_generation(documents)
        results["template_filling"] = await self.run_baseline_template_filling(documents)
        results["retrieval_augmented"] = await self.run_baseline_retrieval_augmented(documents)
        
        # GraphGen（无优化）
        results["graphgen_no_opt"] = await self.run_graphgen(
            documents, enable_optimization=False
        )
        
        # GraphGen（优化后）
        results["graphgen_optimized"] = await self.run_graphgen(
            documents, enable_optimization=True
        )
        
        # 不同生成模式
        results["modes"] = await self._run_mode_comparison(documents)
        
        # 消融实验
        results["ablation"] = await self._run_ablation_studies(documents)
        
        # 保存结果
        self._save_results(results)
        
        return results

# 使用示例
if __name__ == "__main__":
    config = {
        "working_dir": "cache/experiments",
        "documents": "data/test_documents"
    }
    
    runner = ExperimentRunner(config)
    results = asyncio.run(runner.run_all_experiments())
    
    # 生成报告表格
    generate_tables(results)
```

## 5. 数据说明和注意事项

### 5.1 数据集要求

- **文档数量**：建议100-500篇文档，确保统计显著性
- **文档规模**：平均1000-5000 tokens，覆盖不同长度
- **领域多样性**：包含科技、医疗、历史等多个领域

### 5.2 实验环境

- **硬件**：建议使用GPU加速评估模型（UniEval、Reward Model）
- **软件**：Python 3.8+，PyTorch，Transformers
- **API配置**：需要配置LLM API密钥（OpenAI兼容）

### 5.3 可复现性

- 使用固定随机种子确保可复现性
- 记录所有配置参数
- 保存中间结果以便后续分析

### 5.4 数据验证

- 检查数据范围是否合理（如MTLD应在合理范围内）
- 验证统计显著性（使用t-test等）
- 检查异常值和离群点

---

**注意**：以上脚本为示例实现思路，实际使用时需要根据具体代码结构进行调整。

