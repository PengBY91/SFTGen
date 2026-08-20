# KGE-Gen：知识图谱引导的 SFT 数据合成平台

> 本文档面向新用户和新手开发者，详细介绍 KGE-Gen 的功能、安装使用方法、代码架构和核心模块。
>
> 如果你只想**尽快跑起来**，直接看 [快速开始](#快速开始)；如果你是**新手开发者**想理解代码，看 [核心工作流程](#核心工作流程) 和 [代码结构](#代码结构)。

## 📋 目录

- [项目概述](#项目概述)
- [功能特性](#功能特性)
- [整体架构](#整体架构)
- [快速开始](#快速开始)
- [核心工作流程](#核心工作流程)
- [生成模式](#生成模式)
- [DA-ToG：意图树引导的数据合成](#da-tog意图树引导的数据合成)
- [数据评测](#数据评测)
- [主要模块说明](#主要模块说明)
- [代码结构](#代码结构)
- [关键概念](#关键概念)
- [配置参考](#配置参考)
- [测试与开发指南](#测试与开发指南)
- [常见问题与调试技巧](#常见问题与调试技巧)
- [总结](#总结)

---

## 项目概述

KGE-Gen 是一个**知识图谱引导的合成数据生成平台**，用于批量生产高质量的大语言模型训练数据（SFT 数据）和评测数据。它的核心能力：

1. **从文档构建知识图谱**：读取原始文档（txt / json / jsonl / csv / pdf），用 LLM 提取实体和关系，构建结构化知识图谱
2. **基于图谱生成问答数据**：对图谱分区、抽取子图，用 LLM 生成多种模式的问答对（QA pairs），用于 SFT 训练
3. **多入口使用**：命令行（CLI）、管线配置文件、Vue 3 + FastAPI Web 平台、Gradio WebUI，任选其一

### 解决什么问题

- **数据稀缺**：没有足够的人工标注语料时，自动合成大规模训练数据
- **质量可控**：知识图谱提供结构化约束，保证问答对与原文事实一致；可选的 Critic（评审）环节过滤低质量样本
- **多样性可控**：支持原子 / 聚合 / 多跳 / 链式思考 / 层次化等多种生成模式，可按比例混合；DA-ToG 模式通过意图树控制意图覆盖度

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 知识图谱构建 | 从多格式文档提取实体/关系，自动合并聚合（支持批量请求、prompt 合并、抽取缓存等优化） |
| 理解评估（可选） | 用 Trainee 模型对知识点做 quiz + judge，计算置信度、识别知识盲点，指导分区采样 |
| 多种图分区方法 | `ece`（基于理解损失）、`bfs` / `dfs` / `anchor_bfs`（遍历）、`leiden`（社区检测）、`hierarchical`（层次结构） |
| 多种生成模式 | `atomic` / `aggregated` / `multi_hop` / `cot` / `hierarchical` / `all`，可设置总量与比例 |
| 多种输出格式 | Alpaca、ShareGPT、ChatML |
| DA-ToG 管线 | 意图树（Taxonomy Tree）+ 图适配器 + 评审器的三层合成管线，控制意图覆盖率 |
| 数据评测 | 生成长度、多样性（MTLD）、Reward 模型、UniEvaluator 等指标 |
| Web 平台 | 任务创建/追踪、数据人工审核、用户认证（管理员/审核员）、DA-ToG 意图树管理页面 |
| LLM 兼容性 | 任意 OpenAI 兼容接口（DeepSeek、GPT、本地 vLLM/Ollama 等），支持 RPM/TPM 限流 |

---

## 整体架构

KGE-Gen 采用**前后端分离**的架构设计：

```
┌─────────────────────────────────────────────────────────┐
│                     前端层 (Frontend)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Vue 3 前端  │  │  Gradio WebUI│  │   CLI 工具   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
          ┌─────────────────▼─────────────────┐
          │      FastAPI 后端服务 (Backend)     │
          │  ┌──────────────────────────────┐  │
          │  │   API 路由 / 任务管理        │  │
          │   用户认证 / 数据审核 / DA-ToG  │  │
          │  └──────────────┬───────────────┘  │
          └─────────────────┼──────────────────┘
                            │
          ┌─────────────────▼─────────────────┐
          │     graphgen 核心库 (Core)        │
          │  ┌──────────────────────────────┐  │
          │  │  知识构建 / 图分区 / QA 生成  │  │
          │  │  DA-ToG 管线 / LLM 客户端    │  │
          │  │  存储管理                     │  │
          │  └──────────────────────────────┘  │
          └────────────────────────────────────┘
```

### 三层架构说明

#### 1. 前端层（`frontend/`、`webui/`）

- **Vue 3 前端**（`frontend/`）：现代化 Web 界面。包含任务管理、任务创建（SFT / 评测）、数据审核、全局配置、DA-ToG 配置与意图树查看等页面
- **Gradio WebUI**（`webui/`）：轻量交互界面，适合快速试用
- **CLI 工具**（`graphgen_cli.py` 等）：命令行接口，适合批量处理和脚本化

#### 2. 后端服务层（`backend/`）

- **FastAPI 应用**：RESTful API（路由前缀 `/api`），Swagger 文档见 `http://localhost:8000/docs`
- **任务管理**：任务创建、异步执行、状态追踪（`backend/core/task_processor.py`）
- **用户认证**：JWT Token，支持管理员（admin）和审核员（reviewer）角色
- **数据审核**：人工审核 + 自动审核（`backend/services/review_service.py`、`auto_review_service.py`）
- **DA-ToG 接口**：意图树与管线相关的 API（`backend/api/endpoints_datog.py`）

#### 3. 核心库层（`graphgen/`）

- **GraphGen 核心类**：知识图谱构建和 QA 生成的主要工作流（`graphgen/graphgen.py`）
- **DA-ToG 管线**：意图树引导的三层合成管线（`graphgen/datog_pipeline.py`）
- **存储系统**：文档、知识图谱、QA 数据的持久化（`graphgen/models/storage/`）
- **LLM 客户端**：封装 OpenAI 兼容接口，带限流与批量优化（`graphgen/models/llm/`）

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 16+（仅使用 Vue 前端时需要）
- 一个 OpenAI 兼容的 LLM API（DeepSeek、OpenAI、本地 vLLM/Ollama 等均可）

### 2. 安装

**方式一：Conda（推荐，`start.sh` 默认使用名为 `graphgen` 的环境）**

```bash
conda env create -f environment.yml
conda activate graphgen
```

**方式二：pip**

```bash
pip install -r requirements.txt
```

**前端依赖（可选）**

```bash
cd frontend
npm install
```

### 3. 配置 LLM API Key

> ⚠️ 请务必配置自己的 API Key，不要依赖代码内置的默认值。

所有 LLM/API 均可通过配置文件设置（无需改代码），支持任意 OpenAI 兼容接口。有两种方式：

**方式一：`.env` 文件（最简单）**

```bash
cp .env.example .env
# 编辑 .env，填入：
# SYNTHESIZER_MODEL=deepseek-chat
# SYNTHESIZER_BASE_URL=https://api.deepseek.com/v1
# SYNTHESIZER_API_KEY=sk-xxxx
```

**方式二：管线 YAML 顶部的 `llm` 段（推荐，配置随管线走）**

```yaml
llm:
  synthesizer:
    model: deepseek-chat              # 任意 OpenAI 兼容模型
    base_url: https://api.deepseek.com/v1
    api_key: ${SYNTHESIZER_API_KEY}   # ${VAR} 引用环境变量，密钥不必写进文件
    rpm: 1000                         # 每分钟请求数上限
    tpm: 50000                        # 每分钟 token 数上限
  trainee:                            # 置信度评估用（可选）
    enabled: false
    model: ${TRAINEE_MODEL}
    base_url: ${TRAINEE_BASE_URL}
    api_key: ${TRAINEE_API_KEY}

apis:                                 # 其他 API（搜索等）
  google_search:
    api_key: ${GOOGLE_SEARCH_API_KEY}
```

- **取值优先级**：命令行参数 > YAML 配置 > 环境变量（.env）> 内置默认值
- 未配置 `llm` 段时行为与旧版一致（全部从 `.env` 读取）
- 详见 `graphgen/configs/README.md` 与 `graphgen/configs/llm_config.py`

### 4. 运行（三选一）

#### 方式 A：CLI 快速上手（`graphgen_cli.py`）

```bash
# 最简单的用法：单个文件 + API Key
python graphgen_cli.py -i input.txt -k your_api_key

# 使用 .env / YAML 中的配置，指定输出格式
python graphgen_cli.py -i input.txt \
    --synthesizer-url https://api.deepseek.com/v1 \
    --synthesizer-model deepseek-chat \
    --output-data-type aggregated --output-data-format ChatML

# 通过 YAML 配置 LLM（推荐）
python graphgen_cli.py -i input.txt -c graphgen/configs/aggregated_config.yaml

# 批量处理多个文件
python graphgen_cli.py -b file1.txt file2.json file3.csv -k your_api_key

# 从文件列表批量处理
python graphgen_cli.py -l file_list.txt -k your_api_key

# 先测试 API 连通性
python graphgen_cli.py -i input.txt --test-connection

# 运行 DA-ToG 管线（见下文专节）
python graphgen_cli.py --datog-input input.txt --datog-config graphgen/configs/datog/cybersecurity/datog_config.yaml
```

常用参数（完整列表见 `python graphgen_cli.py --help`）：

| 参数 | 说明 |
|------|------|
| `-i / -b / -l` | 单个文件 / 多个文件 / 文件列表（三选一，必填） |
| `-k, --api-key` | API Key（优先级：命令行 > YAML > .env） |
| `-c, --config` | YAML 配置文件 |
| `-o, --output-file` | 输出文件路径 |
| `--output-data-type` | `atomic` / `multi_hop` / `aggregated` / `cot` / `all` |
| `--output-data-format` | `Alpaca` / `Sharegpt` / `ChatML` |
| `--use-trainee-model` | 启用 Trainee 模型做理解评估 |
| `--chunk-size / --chunk-overlap` | 文档分块大小 / 重叠 |
| `--qa-pair-limit` | 目标 QA 对数量（0 为不限制） |
| `--rpm / --tpm` | 每分钟请求数 / token 数限制 |
| `--test-connection` | 仅测试 API 连接 |

#### 方式 B：管线配置文件（`python -m graphgen.generate`）

一条 YAML 定义完整管线（read / split / search / quiz_and_judge / partition / generate），适合可复现的实验：

```bash
python -m graphgen.generate \
    --config_file graphgen/configs/aggregated_config.yaml \
    --output_dir ./out
```

`graphgen/configs/` 下有各模式的现成配置模板：`atomic_config.yaml`、`aggregated_config.yaml`、`multi_hop_config.yaml`、`cot_config.yaml`、`evaluation_config.yaml`、`datog_config.yaml`。输入文件路径在 YAML 的 `read.input_file` 中修改，示例输入见 `resources/input_examples/`（含 txt/json/jsonl/csv/pdf 各格式）。

#### 方式 C：Web 平台（推荐新用户）

一键启动全部服务：

```bash
./start.sh start    # 启动后端(8000) + Gradio WebUI(7860) + Vue 前端(3000)
./start.sh status   # 查看服务状态
./start.sh stop     # 停止所有服务
./start.sh restart  # 重启
```

启动后访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| Vue 前端 | http://localhost:3000 | 主界面，任务管理 / 审核 / DA-ToG |
| FastAPI 后端 | http://localhost:8000 | API 服务 |
| Swagger 文档 | http://localhost:8000/docs | 交互式 API 文档 |
| Gradio WebUI | http://localhost:7860 | 轻量交互界面 |

**默认登录账号**：用户名 `admin`，密码 `admin123`（首次登录后请修改）。

在 Web 界面中：`创建任务` 页面上传文档并配置生成参数 → `任务管理` 查看执行进度 → `数据审核` 页面人工审核生成的 QA 对 → 导出。DA-ToG 相关功能在 `DA-ToG 配置` 和 `意图树管理` 页面。

---

## 核心工作流程

KGE-Gen 的核心工作流程分为**四个主要步骤**（对应核心类 `GraphGen` 的四个方法）：

```
原始文档
    │
    ▼
┌─────────────────────────────────────────┐
│  步骤1: 知识构建 GraphGen.insert()        │
│  - 文档读取和分割                        │
│  - 实体和关系提取（LLM）                 │
│  - 知识图谱构建与合并                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  步骤2: 理解评估 GraphGen.quiz_and_judge()│
│  - 语义变体生成 (可选)                   │
│  - 置信度评估 (可选)                     │
│  - 知识盲点识别                          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  步骤3: 图组织 partition_kg()            │
│  - 知识图谱分区（多种方法）              │
│  - 子图提取                             │
│  - 批次准备                              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  步骤4: QA 生成 generate_qas()           │
│  - 按模式选择生成器                      │
│  - 问题 + 答案生成（LLM）               │
│  - 去重、过滤、格式化输出                │
└──────────────┬──────────────────────────┘
               │
               ▼
          问答对数据（SFT 训练集）
```

另有一步可选的**外部搜索** `GraphGen.search()`（在 insert 之后、评估之前），用于从 Google/Bing/Wikipedia 等补充外部知识。

### 步骤1: 知识构建（`insert()`）

**代码位置**：`graphgen/graphgen.py::GraphGen.insert()`

1. **文档读取**（`graphgen/operators/read/read_files.py`）：支持 txt、json、jsonl、csv、pdf 等格式，不同格式用不同的 Reader 类处理
2. **文档分割**（`graphgen/operators/split/split_chunks.py`）：把长文档切成 chunk（片段），配置 `chunk_size` / `chunk_overlap`
3. **实体和关系提取**（`graphgen/operators/build_kg/build_text_kg_optimized.py`）：用 Synthesizer LLM 从每个 chunk 提取实体和关系
   - 提取器：`graphgen/models/kg_builder/light_rag_kg_builder.py`
   - 提示模板：`graphgen/templates/kg/kg_extraction.py`
   - 优化：批量请求合并、自适应批大小、抽取缓存、多 chunk prompt 合并（配置见 YAML `split` 段）
4. **知识聚合**：合并各 chunk 提取出的实体/关系（相同实体描述聚合），存入 `NetworkXStorage`

### 步骤2: 理解评估（`quiz_and_judge()`，可选）

**代码位置**：`graphgen/graphgen.py::GraphGen.quiz_and_judge()`

1. **语义变体生成**（`graphgen/operators/quiz.py`）：对图中每条边生成多个语义变体（肯定/否定形式）
2. **置信度评估**（`graphgen/operators/judge.py`）：用 Trainee 模型判断变体，计算对每个知识点的置信度，识别知识盲点
3. **理解损失计算**（`graphgen/utils/calculate_confidence.py`）：基于置信度计算 Comprehension Loss，供 ECE 分区优先采样盲点

> 只有配置 `quiz_and_judge.enabled: true`（且提供 Trainee 模型）时才执行。不用 Trainee 模型时，ECE 分区的 `unit_sampling` 会自动退化为 `random`。

### 步骤3: 图组织（`partition_kg()`）

**代码位置**：`graphgen/operators/partition/partition_kg.py`

把整个知识图谱切成多个子图（批次），每个批次将作为一次 QA 生成的输入。分区方法（YAML `partition.method`）：

| 方法 | 说明 |
|------|------|
| `ece` | 基于预期校准误差/理解损失，优先采样知识盲点（**默认推荐**） |
| `bfs` / `dfs` | 广度/深度优先遍历分区 |
| `anchor_bfs` | 基于锚点节点的 BFS 分区 |
| `leiden` | 基于 Leiden 算法的社区检测 |
| `hierarchical` | 层次结构分区（识别 `is_a`/`part_of` 等层级关系，按兄弟组/祖先链组织，见 `docs/README_HIERARCHICAL.md`） |

### 步骤4: QA 生成（`generate_qas()`）

**代码位置**：`graphgen/operators/generate/generate_qas.py`

1. **选择生成器**：按 `generate.mode` 选择（见下节）
2. **问题生成**：对每个批次（子图）调用 LLM 生成问题，模板在 `graphgen/templates/generation/`
3. **答案生成**：atomic 模式支持两阶段（先生成问题并去重，再逐题生成答案）；其他模式通常一次生成问答对
4. **格式化输出**：Alpaca / ShareGPT / ChatML，附加元数据（context、graph、source_chunks 等）
5. **去重与限量**：基于问题 hash 去重；`target_qa_pairs` 限制总量；`mode_ratios` 控制各模式比例

---

## 生成模式

| 模式 | 说明 | 示例 |
|------|------|------|
| `atomic` | 原子问答：单个事实，问题直接、答案简短 | Q: "云粳26号由哪个机构育成？" A: "云南省农业科学院" |
| `aggregated` | 聚合问答：综合多个相关事实 | Q: "介绍云粳26号的品种特点" A: "..." |
| `multi_hop` | 多跳问答：需沿图谱多条边推理 | Q: "A 和 C 有什么关系？"（A→B→C） |
| `cot` | 链式思考：答案包含推理过程 | A: "首先…，然后…，因此…" |
| `hierarchical` | 层次化问答：基于层级子图（父子/兄弟关系）生成，支持 Markdown/JSON/大纲三种结构化格式，4 种推理模式（兄弟对比、继承、抽象、多层） | 见 `docs/README_HIERARCHICAL.md` |
| `all` | 按比例生成以上所有模式 | 配合 `mode_ratios` 使用 |

---

## DA-ToG：意图树引导的数据合成

**DA-ToG（Domain-Agnostic Tree-of-Graphs）** 是一条独立于经典四步流程的合成管线，目标是**控制生成数据的意图覆盖度与多样性**，而不只是事实覆盖。

### 三层结构

| 层 | 职责 | 核心代码 |
|----|------|---------|
| Macro-Intent（宏观意图） | 用**意图树（Taxonomy Tree）**组织领域内的问题意图，多样性采样保证覆盖 | `graphgen/models/taxonomy/taxonomy_tree.py`、`diversity_sampler.py` |
| Micro-Fact（微观事实） | 把采样到的意图**链接到知识图谱**，检索相关子图并序列化 | `graphgen/models/graph_adapter/` |
| Logic-Critic（逻辑评审） | 对生成的 QA 做规则/LLM 评审，过滤低分样本 | `graphgen/models/critic/` |

管线编排：`graphgen/datog_pipeline.py`（意图采样 → 子图检索 → QA 生成 → 评审校验）。

### 使用方法

**1. 准备配置和意图树**

模板配置：`graphgen/configs/datog_config.yaml`；两个完整领域示例（含意图树 `taxonomy.json` 和 `datog_config.yaml`）：

- `graphgen/configs/datog/cybersecurity/`（网络安全域）
- `graphgen/configs/datog/finance/`（金融域）

关键配置项：

```yaml
datog:
  taxonomy:
    path: graphgen/configs/datog/cybersecurity/taxonomy.json  # 意图树文件
    sampling_strategy: coverage    # uniform_branch / depth_weighted / coverage
  graph:
    max_hops: 2                    # BFS 扩展跳数
    max_nodes_per_subgraph: 20     # 每个子图最大节点数
  critic:
    type: rule                     # llm / rule / none
    min_score: 0.6                 # 通过评审的最低分
  generation:
    target_qa_pairs: 100           # 目标 QA 对数
    data_format: ChatML            # 输出格式
```

**2. 运行**

```bash
# 从输入文档构建知识图谱，再跑 DA-ToG（-i 与 --datog-input 等价）
python graphgen_cli.py --datog-input input.txt \
    --datog-config graphgen/configs/datog/cybersecurity/datog_config.yaml

# 加载已有知识图谱，跳过图谱构建（无需输入文档）
python graphgen_cli.py --datog-kg kg.json --datog-config <配置>

# 指定输出文件
python graphgen_cli.py --datog-input input.txt --datog-config <配置> --datog-output out.json
```

运行结束后会输出 QA 文件和指标报告（`*_metrics.json`），包含意图覆盖率等统计。

**3. 计算指标（可单独对已有结果文件运行）**

```bash
python graphgen_eval_cli.py --output_dir ./eval_out \
    --datog-taxonomy graphgen/configs/datog/cybersecurity/taxonomy.json \
    --datog-results out.json
```

**4. Web 界面**

Vue 前端提供 `DA-ToG 配置`、`意图树管理`、`DA-ToG 管线` 页面（`/config/datog`、`/datog/taxonomies`、`/datog/pipeline`），可在浏览器中管理意图树并触发管线。

---

## 数据评测

两套评测入口：

1. **评测数据集生成**：`graphgen_eval_cli.py`——从领域文档生成用于评测（而非训练）的数据集，配置模板 `graphgen/configs/evaluation_config.yaml`

   ```bash
   python graphgen_eval_cli.py --config_file graphgen/configs/evaluation_config.yaml --output_dir ./eval_out
   ```

2. **生成质量评估**：`python -m graphgen.evaluate`——对已有 QA 数据计算指标：
   - **Length**：长度分布
   - **MTLD**：词汇多样性
   - **Reward**：Reward 模型打分
   - **UniEvaluator**：统一评估器

   用法参考 `graphgen/evaluate.py` 的参数说明。

---

## 主要模块说明

### 1. 核心类：`GraphGen`

**位置**：`graphgen/graphgen.py`

封装经典四步工作流（insert → search → quiz_and_judge → generate）。

**主要属性**：
- `synthesizer_llm_client`：合成器 LLM 客户端（提取和生成）
- `trainee_llm_client`：训练模型 LLM 客户端（评估，可选）
- `tokenizer_instance`：分词器实例
- `graph_storage`：知识图谱存储（NetworkX）
- `chunks_storage`：文档片段存储（JSON KV）
- `qa_storage`：问答对存储（JSON List）

**主要方法**：
- `insert()`：知识构建
- `search()`：外部搜索（可选）
- `quiz_and_judge()`：理解评估（可选）
- `generate()`：QA 生成（分区 + 生成）
- `generate_evaluation()`：评测数据生成
- `clear()`：清空所有存储

### 2. DA-ToG 管线：`DAToGPipeline`

**位置**：`graphgen/datog_pipeline.py`（可用 `DAToGPipeline.from_config()` 从 YAML 构建）

编排：意图采样 → 子图检索 → QA 生成 → 评审校验。相关模块见 [DA-ToG 专节](#da-tog意图树引导的数据合成)。

### 3. 存储系统（`graphgen/models/storage/`）

| 类 | 用途 |
|----|------|
| `NetworkXStorage` | 知识图谱（节点+边），基于 NetworkX |
| `JsonKVStorage` | 键值存储（文档、片段、搜索结果） |
| `JsonListStorage` | 列表存储（问答对） |

### 4. LLM 客户端（`graphgen/models/llm/`）

| 类 | 用途 |
|----|------|
| `OpenAIClient` | OpenAI 兼容 API 封装：异步调用、token 统计、RPM/TPM 限流 |
| `BatchLLMWrapper` | 批量请求优化：合并请求、缓存、自适应批大小 |
| `limitter.RPM/TPM` | 每分钟请求数 / token 数限流器 |

### 5. 生成器（`graphgen/models/generator/`）

`AtomicGenerator`、`AggregatedGenerator`、`MultiHopGenerator`、`CoTGenerator`、`TreeGenerator`（层次化）、`DAToGGenerator`（DA-ToG 用）。均继承统一基类，实现"生成 + 格式化输出"接口。

### 6. 分区器（`graphgen/models/partitioner/`）

`ECEPartitioner`、`BFSPartitioner`、`DFSPartitioner`、`AnchorBFSPartitioner`、`LeidenPartitioner`、`HierarchicalPartitioner`。均继承 `BasePartitioner`。

### 7. 后端服务（`backend/`）

| 模块 | 职责 |
|------|------|
| `backend/core/task_processor.py` | 任务执行：初始化 GraphGen → 知识构建 → （可选）评估 → QA 生成 → 保存结果 |
| `backend/services/task_service.py` | 任务管理：创建、查询、状态更新 |
| `backend/services/review_service.py` | 数据审核：人工审核、批量审核、统计 |
| `backend/services/auto_review_service.py` | 自动审核 |
| `backend/services/auth_service.py` | 用户认证：登录、Token、权限 |
| `backend/api/endpoints.py` / `endpoints_datog.py` | API 路由（主流程 / DA-ToG） |

---

## 代码结构

```
SFTGen/
├── graphgen_cli.py          # 主 CLI 入口（单文件/批量/DA-ToG）
├── graphgen_eval_cli.py     # 评测数据生成 CLI（含 DA-ToG 指标计算）
├── start.sh                 # 一键启动/停止 Web 服务脚本
├── environment.yml          # conda 环境定义（环境名 graphgen）
├── requirements.txt         # pip 依赖
├── .env.example             # 环境变量配置模板
│
├── graphgen/                # 核心库
│   ├── graphgen.py          # GraphGen 核心类（四步工作流）
│   ├── datog_pipeline.py    # DA-ToG 管线编排
│   ├── generate.py          # 管线式 CLI 入口（--config_file）
│   ├── evaluate.py          # 生成质量评估
│   ├── bases/               # 基类和接口（BaseLLMClient、BaseCritic、数据类型等）
│   ├── configs/             # 管线 YAML 模板 + llm_config.py 配置解析
│   │   └── datog/           # DA-ToG 领域示例（cybersecurity / finance）
│   ├── models/
│   │   ├── generator/       # 生成器（atomic/aggregated/multi_hop/cot/tree/datog）
│   │   ├── partitioner/     # 分区器（ece/bfs/dfs/anchor_bfs/leiden/hierarchical）
│   │   ├── kg_builder/      # 知识图谱构建器
│   │   ├── taxonomy/        # 意图树 + 多样性采样（DA-ToG）
│   │   ├── graph_adapter/   # 意图-图谱链接与子图检索（DA-ToG）
│   │   ├── critic/          # 评审器（规则/LLM，DA-ToG）
│   │   ├── llm/             # LLM 客户端与限流
│   │   └── storage/         # 存储系统
│   ├── operators/           # 核心操作符
│   │   ├── read/            # 文档读取
│   │   ├── split/           # 文档分割
│   │   ├── build_kg/        # 实体关系提取与入图
│   │   ├── quiz.py/judge.py # 理解评估
│   │   ├── partition/       # 图分区
│   │   └── generate/        # QA 生成
│   ├── templates/           # 提示模板（kg 抽取 / 各模式生成）
│   └── utils/               # 工具函数（并发、修复、指标等）
│
├── backend/                 # FastAPI 后端
│   ├── app.py / main.py     # 应用入口（uvicorn backend.app:app）
│   ├── api/                 # 路由（endpoints.py、endpoints_datog.py）
│   ├── core/task_processor.py
│   ├── services/            # 任务/审核/认证/配置/文件服务
│   ├── schemas.py           # Pydantic 数据模型
│   └── config.py            # 后端配置
│
├── frontend/                # Vue 3 前端（Vite + Element Plus + Pinia）
│   └── src/views/           # 任务、审核、配置、DA-ToG 页面
│
├── webui/                   # Gradio WebUI（端口 7860）
├── scripts/                 # 运维/批量脚本
├── tests/                   # pytest 测试
├── docs/                    # 设计文档与技术报告
├── resources/               # 资源文件（input_examples/ 有各格式示例输入）
├── cache/                   # 运行时工作目录（日志、上传、临时图谱）
└── tasks/                   # Web 任务数据（tasks.json、outputs/、reviews/）
```

### 关键文件速查

| 文件路径 | 说明 |
|---------|------|
| `graphgen/graphgen.py` | GraphGen 核心类，主要工作流 |
| `graphgen_cli.py` | 最常用的 CLI 入口 |
| `graphgen/generate.py` | 管线式 CLI（配置文件驱动） |
| `graphgen/datog_pipeline.py` | DA-ToG 管线 |
| `graphgen/configs/llm_config.py` | LLM/API 配置解析（优先级机制） |
| `graphgen/operators/build_kg/build_text_kg_optimized.py` | 文本知识图谱构建（含优化） |
| `graphgen/operators/partition/partition_kg.py` | 图分区入口 |
| `graphgen/operators/generate/generate_qas.py` | QA 生成核心逻辑 |
| `backend/core/task_processor.py` | Web 任务执行器 |
| `backend/app.py` | FastAPI 应用（`uvicorn backend.app:app`） |

---

## 关键概念

### 1. Chunk（文档片段）

长文档分割后的小片段，是实体/关系提取的输入单位。QA 生成时作为上下文（source_chunks）引用，保证答案可溯源。

```python
@dataclass
class Chunk:
    id: str          # 唯一标识
    content: str     # 内容
    type: str        # 类型（text/image 等）
    metadata: dict   # 元数据
```

### 2. 知识图谱（Knowledge Graph）

- **节点（Node）**：实体，属性含 `name`、`description`、`entity_type` 等
- **边（Edge）**：实体间关系，属性含 `source`、`target`、`description` 等
- 存储：`NetworkXStorage`

### 3. Batch（批次）

图分区后得到的子图，是 QA 生成的输入单位：

```python
batch = (nodes, edges)  # [(node_id, node_data), ...], [(source, target, edge_data), ...]
```

### 4. Synthesizer 与 Trainee 模型

- **Synthesizer（合成器）**：干活的模型——提取实体关系、生成问答
- **Trainee（训练模型）**：被评估的模型——参与 quiz_and_judge，用于发现"训练目标模型不知道什么"，从而针对性采样。不配置时管线照常运行（ECE 采样退化为随机）

### 5. 输出格式

**Alpaca**：
```json
{"instruction": "问题", "input": "", "output": "答案"}
```

**ShareGPT**：
```json
{"conversations": [{"from": "human", "value": "问题"}, {"from": "gpt", "value": "答案"}]}
```

**ChatML**：
```json
{"messages": [{"role": "user", "content": "问题"}, {"role": "assistant", "content": "答案"}]}
```

### 6. 意图树（Taxonomy Tree，DA-ToG）

领域问题意图的层级树（JSON 格式，见 `graphgen/configs/datog/*/taxonomy.json`）。DA-ToG 管线按采样策略（`coverage` / `uniform_branch` / `depth_weighted`）从树上采样意图，保证生成数据覆盖不同类型的用户意图，并用覆盖率指标度量效果。

---

## 配置参考

### 配置优先级（重要）

```
命令行参数  >  YAML 配置文件（llm/apis 段）  >  环境变量（.env）  >  内置默认值
```

实现见 `graphgen/configs/llm_config.py`；`${VAR}` 语法可在 YAML 中引用环境变量（支持 `${VAR:-default}` 默认值），密钥无需写进文件。

### 常用环境变量（`.env`）

完整列表见 `.env.example`，最常用的：

| 变量 | 说明 |
|------|------|
| `SYNTHESIZER_MODEL` / `SYNTHESIZER_BASE_URL` / `SYNTHESIZER_API_KEY` | 合成器模型三件套 |
| `TRAINEE_MODEL` / `TRAINEE_BASE_URL` / `TRAINEE_API_KEY` | 训练模型三件套（可选） |
| `RPM` / `TPM` | 每分钟请求 / token 限制 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 文档分块参数 |
| `OUTPUT_DATA_TYPE` / `OUTPUT_DATA_FORMAT` | 默认生成模式 / 输出格式 |
| `TOKENIZER_MODEL` | 分词器（默认 cl100k_base） |

### 管线 YAML 主要段落

以 `graphgen/configs/aggregated_config.yaml` 为例：`llm` / `apis`（模型与外部 API）→ `read`（输入文件）→ `split`（分块与批量优化）→ `search`（外部搜索，默认关）→ `quiz_and_judge`（评估，可选）→ `partition`（分区方法与参数）→ `generate`（模式、格式、批量/缓存/去重优化、数量与比例）。

---

## 测试与开发指南

### 运行测试

```bash
# 全部测试（pytest，多数测试 mock 了 LLM，无需真实 API）
pytest tests/

# 单个文件
pytest tests/test_e2e_mock.py -v

# DA-ToG 相关
pytest tests/test_datog_pipeline.py tests/test_datog_generator.py tests/test_datog_metrics.py -v
```

测试覆盖：端到端冒烟（mock LLM，零 API 成本）、批量请求管理、限流器、LLM 配置解析、层次化生成、DA-ToG 管线/生成器/指标等。

### 代码风格

项目使用 **black + isort**（配置见 `pyproject.toml`，行宽 88）：

```bash
black graphgen backend webui tests
isort graphgen backend webui tests
```

注释和文档惯例为**中文**，请保持一致。

### 建议的代码阅读顺序

1. **入口**：`graphgen_cli.py::main()` 或 `graphgen/generate.py::main()`
2. **核心类**：`graphgen/graphgen.py::GraphGen`（四个方法的流程）
3. **关键操作符**：`operators/build_kg/` → `operators/partition/partition_kg.py` → `operators/generate/generate_qas.py`
4. **一个具体生成器**：`models/generator/atomic_generator.py`

### 常见修改场景

**修改/新增生成模式**：
- 在 `graphgen/models/generator/` 下新建或修改生成器类（继承现有基类）
- 提示模板放 `graphgen/templates/generation/`
- 在 `graphgen/operators/generate/generate_qas.py` 中注册新 mode
- 可参考层次化模式的完整接入：`tree_generator.py` + `hierarchical_generation.py` + `docs/README_HIERARCHICAL.md`

**添加新的分区方法**：
- 在 `graphgen/models/partitioner/` 下实现 `BasePartitioner` 子类
- 在 `graphgen/operators/partition/partition_kg.py` 中注册

**修改输出格式**：
- 编辑生成器的 `format_generation_results()` 方法

**优化 LLM 调用**：
- 批量请求：`graphgen/models/llm/batch_llm_wrapper.py`、`graphgen/utils/batch_request_manager.py`
- 响应修复：`graphgen/utils/llm_response_repair.py`

---

## 常见问题与调试技巧

**Q: API Key 怎么都不生效 / 用了别人的 key？**
配置按"命令行 > YAML > .env > 内置默认值"解析。请显式配置自己的 key（`.env` 或 YAML `llm` 段），不要依赖内置默认值。日志会打印脱敏后的生效配置（`api_key` 只显示首尾 4 字符），可据此确认。

**Q: 如何先验证 API 连通性再跑长任务？**
```bash
python graphgen_cli.py -i input.txt --test-connection
```

**Q: 任务日志和中间产物在哪？**
- Web 任务：`tasks/{task_id}/`（输出在 `tasks/outputs/`，审核在 `tasks/reviews/`）
- CLI/管线：运行日志和图谱等中间文件在 `cache/` 下工作目录中；`graphgen_cli.py` 默认输出到当前目录 `{文件名}_graphgen_output.jsonl`
- 后端/前端日志：`.backend.log`、`.frontend.log`、`.webui.log`

**Q: 生成的 QA 数量太少/太多？**
用 `--qa-pair-limit`（CLI）或 `generate.target_qa_pairs` / `generate.mode_ratios`（YAML）控制；去重开关 `enable_deduplication` 也影响最终数量。

**Q: 想省 token / 提速？**
YAML 中 `split` 和 `generate` 段的批量请求优化（`enable_batch_requests`、`use_adaptive_batching`）、`enable_extraction_cache`、`use_combined_mode`、`enable_prompt_cache` 默认已开启；可调 `batch_size` 与 RPM/TPM。

**Q: RPM/TPM 被限流？**
在 YAML `llm.synthesizer.rpm/tpm` 或 `.env` 的 `RPM`/`TPM` 中按你的 API 配额调整。

**Q: 前端无法访问？**
查看 `tail -f .frontend.log`；确认 Node.js 已安装、`frontend/node_modules` 存在（`cd frontend && npm install`）；后端 CORS 配置见 `backend/config.py` 的 `ALLOWED_ORIGINS`。

---

## 总结

KGE-Gen 的核心思想：

1. **从文档到知识图谱**：LLM 提取实体和关系，构建结构化知识图谱
2. **从知识图谱到 QA 对**：基于子图生成事实一致、可溯源的高质量问答对
3. **多样性有保障**：多种生成模式可混合；DA-ToG 用意图树显式控制意图覆盖
4. **工程可用**：异步并发、批量合并、缓存、限流、去重等优化开箱即用；CLI / 管线配置 / Web 平台多种入口

**关键设计原则**：模块化（生成器/分区器/存储均可扩展）、异步处理、配置驱动（YAML/.env/CLI 三级优先）、中英双语文档与提示模板支持。

希望这份文档能帮助你快速上手 KGE-Gen！如有疑问，建议查看 `docs/` 下的设计文档和具体代码实现。
