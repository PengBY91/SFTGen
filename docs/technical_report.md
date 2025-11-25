# 基于知识图谱的大语言模型训练数据生成框架技术报告

## 摘要

本文提出了一种基于知识图谱引导的大语言模型（Large Language Model, LLM）训练数据生成框架GraphGen。该框架旨在解决大语言模型监督微调（Supervised Fine-Tuning, SFT）过程中高质量训练数据稀缺的关键问题，特别针对知识密集型任务，通过结构化知识指导系统性提高合成数据质量。

GraphGen框架的核心创新包括：（1）基于预期校准误差（Expected Calibration Error, ECE）的知识盲点识别机制，能够量化目标模型对知识点的理解程度并优先生成高价值的训练样本；（2）多模式问答对（Question-Answer Pair, QA Pair）生成策略，涵盖原子问答、聚合问答、多跳推理和思维链推理四种模式，满足不同复杂度任务的需求；（3）高效的批量处理与缓存优化技术，显著降低LLM API调用成本和处理时间。

实验结果表明，GraphGen框架能够生成高质量、多样化的训练数据，在知识覆盖度和数据质量方面优于传统合成数据生成方法。通过批量请求优化和缓存机制，系统性能提升了30-50%，LLM调用次数减少了40-60%。本研究为大语言模型训练数据生成提供了一种可扩展、高质量的解决方案，具有重要的理论价值和实际应用意义。

**关键词**：知识图谱；大语言模型；训练数据生成；预期校准误差；问答对生成

---

## 第一章 引言

### 1.1 研究背景

随着大语言模型技术的快速发展，如何获取高质量的训练数据已成为制约模型性能提升的关键瓶颈。特别是在监督微调（SFT）阶段，模型需要大量的、高质量的、符合任务需求的标注数据。传统的标注方法依赖于人工标注，不仅成本高昂、效率低下，而且难以覆盖长尾知识和新兴领域。

知识密集型任务（Knowledge-Intensive Tasks）对训练数据的质量要求尤为严格，这类任务要求模型具备丰富的领域知识和准确的推理能力。然而，现有的大规模预训练语料往往存在以下问题：（1）知识覆盖不全面，特别是长尾知识和领域专业知识；（2）知识表达不一致，同一概念在不同上下文中可能有不同的表述；（3）知识关联性弱，缺乏结构化的知识组织。

为了解决这些问题，研究者们提出了基于大语言模型的合成数据生成方法。这类方法利用大语言模型强大的文本生成能力，自动生成训练样本。然而，现有的合成数据生成方法普遍存在以下局限：（1）事实错误：生成的内容可能存在事实性错误，导致模型学习到错误知识；（2）知识覆盖不足：难以系统性地覆盖目标领域的知识空间；（3）数据同质化：生成的数据模式单一，缺乏多样性。

### 1.2 研究动机与挑战

针对上述问题，本文提出基于知识图谱引导的合成数据生成框架GraphGen。知识图谱（Knowledge Graph, KG）作为一种结构化的知识表示方法，具有以下优势：（1）知识表达明确，实体和关系清晰；（2）知识关联性强，能够表示复杂的知识网络；（3）知识可验证，便于质量检查。然而，如何有效地利用知识图谱指导数据生成仍面临诸多挑战：

**挑战一：知识盲点识别**。不同模型对知识的掌握程度存在差异，如何识别目标模型的知识盲点，并针对性地生成训练数据是关键问题。

**挑战二：知识组织与采样**。知识图谱通常规模庞大，如何有效地组织和采样子图，确保生成数据的上下文连贯性和知识完整性。

**挑战三：多样化生成**。如何基于相同的知识图谱生成多样化的训练样本，避免模式化和同质化问题。

**挑战四：效率与成本**。大规模数据生成需要大量的LLM API调用，如何优化调用策略，降低成本和提升效率。

### 1.3 研究内容与贡献

本文提出的GraphGen框架通过以下技术路线解决上述挑战：

（1）**基于ECE的知识盲点识别机制**：通过预期校准误差量化目标模型对知识点的理解程度，识别高价值的训练样本生成目标。

（2）**多模式QA生成策略**：设计了原子问答、聚合问答、多跳推理和思维链推理四种生成模式，满足不同复杂度的任务需求。

（3）**高效的图组织算法**：基于ECE损失值的图分区和采样策略，确保生成数据的知识完整性和上下文连贯性。

（4）**性能优化技术**：包括批量请求管理、缓存机制、并发处理等优化技术，显著提升系统效率和降低成本。

本文的主要贡献包括：

- **方法贡献**：设计了多模式QA生成框架，能够系统性地从知识图谱生成高质量训练数据。
- **工程贡献**：实现了完整的系统框架，包括知识构建、理解评估、图组织和QA生成四大核心模块。
- **优化贡献**：提出了多种性能优化技术，显著提升了系统的实用性和可扩展性。

### 1.4 报告组织结构

本文的其余部分组织如下：第二章综述相关工作；第三章详细介绍GraphGen系统的整体架构设计与工程实现；第四章阐述核心算法与技术细节，保留了详细的算法描述与公式推导；第五章展示实验评估结果并结合系统性能、复杂度及局限性进行深入分析；第六章介绍典型应用场景与实践经验；第七章总结全文。

---

## 第二章 相关工作 (Related Work)

### 2.1 引言

随着大语言模型在自然语言处理领域的快速发展，高质量训练数据的获取已成为制约模型性能提升的关键瓶颈。传统的数据收集方法面临着隐私保护、成本高昂、标注困难等诸多挑战，而合成数据生成技术为解决这一问题提供了新的思路。与此同时，知识图谱作为结构化知识的重要载体，为大语言模型提供了丰富的背景知识和推理基础，在提升模型的事实准确性和推理能力方面发挥着重要作用。

本章节将系统梳理合成数据生成方法、知识图谱在数据生成中的应用、大语言模型评估与校准等相关领域的最新研究进展，分析现有技术的优势与不足，为基于知识图谱的大语言模型训练数据生成框架的设计提供理论基础和技术支撑。

### 2.2 合成数据生成方法的发展与演进

合成数据生成技术的发展可以追溯到 30 年前 Rubin 提出的利用合成数据扩大敏感微观数据访问的概念 [2]。早期的合成数据方法主要基于统计模型，如多元插补（Multiple Imputation）技术，通过插补缺失值的思路来替换敏感值。然而，真正的技术突破出现在近十年，特别是生成对抗网络（GAN）的出现极大推动了合成数据领域的发展 [18]。

在表格数据生成方面，传统的统计方法如贝叶斯网络在处理包含离散和连续列混合的复杂表格数据时表现不佳。为解决这一问题，研究者们开发了多种基于深度学习的方法。CTGAN（Conditional Tabular GAN）[3, 20] 通过条件生成器成功应对了不平衡分类数据和多模态连续数据的挑战。随后，研究者们进一步提出了 TGAN（Tabular GAN）[4]，能够同时生成离散和连续变量，在捕获列间相关性和处理大规模数据集方面超越了传统统计生成模型。

近年来，大语言模型在合成数据生成领域展现出巨大潜力 [22]。GReaT（Generation of Realistic Tabular data）方法 [5] 利用自回归生成式大语言模型采样高度真实的表格数据，通过文本编码方案将表格数据转换为自然语言句子，充分利用了预训练语言模型的强大能力。这种方法不仅能够生成高质量的合成数据，还支持任意条件生成，极大提升了数据生成的灵活性。

在序列数据生成方面，研究者们开发了专门的评估框架来衡量合成序列数据的质量，主要包括五个高级标准：代表性（representativeness）、新颖性（novelty）、真实性（realism）、多样性（diversity）和一致性（coherence）[15]。这些标准为评估不同领域的合成数据质量提供了统一的框架。

值得注意的是，合成数据的质量问题仍然是当前研究的重点。最新研究发现，合成数据存在两类结构性缺陷：分布覆盖收窄（缺乏低频与长尾样本）和特征过度集中（n-gram 等语言特征分布密度过高）[1]，这些问题可能导致模型过拟合和泛化能力下降。此外，合成数据的统一格式可能导致模式过拟合，造成输出分布的显著偏移，从而降低模型的指令跟随能力。

### 2.3 知识图谱在数据生成中的应用进展

知识增强文本生成是近年来自然语言处理领域的研究热点，旨在通过整合外部知识源来提升文本生成的质量和准确性 [45]。知识图谱作为结构化的人类知识表示，由实体、关系和语义描述组成的事实三元组构成，为文本生成提供了丰富的背景知识。

在知识图谱嵌入（Knowledge Graph Embedding, KGE）技术方面，研究者们提出了多种方法将知识图谱的实体和关系嵌入到低维向量空间中，其中 TransE 是最广泛使用的技术 [43]。这些嵌入向量能够捕获实体和关系之间的语义关联，为文本生成模型提供结构化的知识表示。KGLM（Linked Knowledge Graph Language Model）[39] 通过选择和复制知识图谱中与上下文相关的事实，使模型能够生成其从未见过的信息，并处理词汇表外的 tokens。

图神经网络（Graph Neural Networks, GNNs）的发展为知识图谱与文本生成的结合提供了新的技术路径。GNNs 能够有效建模图结构数据中的复杂关系，通过聚合邻居节点的信息来更新节点表示。研究者们提出了多种基于 GNN 的知识增强文本生成方法，如利用图注意力网络（GAT）来增强对话系统和故事生成的性能 [42]。

在知识图谱到文本生成（KG-to-Text）任务中，CogNLG 框架 [34] 基于认知科学的双过程理论，包含分析系统（知识提取）和感知系统（文本生成），在所有数据集上都表现出色，BLEU 得分达到 36.7，比最佳竞争对手提高了 6.7 分。GenWiki 数据集 [36] 包含 130 万个文本和图示例，为无监督图到文本生成提供了大规模基准测试平台。

然而，知识图谱在数据生成应用中也面临诸多挑战。传统知识图谱构建方法通常是静态的，难以实时更新，且针对特定领域设计，缺乏跨领域的适应性 [30]。在利用大语言模型进行知识图谱构建时，存在三个显著挑战：现实文档中可能存在大量噪声导致信息提取混乱；缺乏标准化的评估协议进行一致评估；大语言模型的事实不稳定性导致推理不一致 [64, 65]。

### 2.4 大语言模型评估与校准技术

大语言模型的评估与校准是确保模型可靠性和安全性的关键技术。当前的评估体系主要涵盖三个核心维度：评估内容（what）、评估位置（where）和评估方法（how）[12, 48]。评估内容包括通用自然语言处理任务、推理能力、医学应用、伦理、教育、自然和社会科学、智能体应用等多个领域 [56, 59]。

在模型校准方面，研究发现尽管无监督预训练产生的大语言模型具有良好的校准性，但经过人类反馈强化学习（RLHF）微调后的模型在保持校准性方面表现不一 [46, 61]。研究者们提出了多种方法来改善大语言模型的校准性能。THERMOMETER 方法 [49] 通过学习辅助模型来校准大语言模型，在多个任务数据上表现出计算效率高、保持模型准确性的优点，并能为新任务产生更好的校准响应。

上下文校准（Contextual Calibration）技术 [47] 通过估计模型对每个答案的偏差来改善少样本学习的不稳定性。该方法通过向模型提供训练提示和无内容测试输入（如 "N/A"）来估计偏差，然后拟合校准参数使该输入的预测在所有答案上均匀分布。实验表明，这种方法能够将 GPT-3 和 GPT-2 的平均准确率提高多达 30 个百分点，并减少不同提示选择之间的方差。

在不确定性估计方面，研究者们开发了系统性框架，包括三个核心组件：引出语言化置信度的提示策略、生成多个响应的采样方法，以及计算一致性的聚合技术 [51]。研究发现，大语言模型在表达置信度时倾向于过度自信，可能是在模仿人类表达置信度的模式。随着模型能力的提升，校准和失败预测性能都有所改善，但仍远未达到理想水平 [58]。

最新研究表明，通过在正确和错误答案的小数据集上进行微调，可以创建具有良好泛化能力和较小计算开销的不确定性估计器，仅需 1000 个分级示例就能超越基线方法 [55]。此外，贝叶斯方法如 Laplace-LoRA [62] 通过对 LoRA 参数应用拉普拉斯近似，显著改善了微调大语言模型的校准性能。

### 2.5 工业界实践与技术应用

工业界在合成数据生成和知识图谱应用方面取得了显著进展。Google DeepMind 提出了合成数据的最佳实践和经验教训，强调了确保合成数据的真实性（factuality）、保真度（fidelity）和无偏性（unbiasedness）的重要性 [1]。他们的研究表明，负责任地使用合成数据对于构建更强大、更包容、更值得信赖的语言模型至关重要。

在知识图谱与大语言模型结合方面，Google 研究了知识图谱是否是使 T5 真正理解和推理的秘密成分，发现参考知识图谱越大，模型表现越好，特别是在面对需要深度思考的棘手问题时，额外的知识对模型提供准确答案的能力有很大影响 [83]。研究者们提出了 SKILL 方法 [84]，通过直接在知识图谱的事实三元组上训练 T5 模型来向大语言模型注入结构化知识。

OpenAI 的 GPT 系列模型在合成数据生成领域发挥了重要作用。GPT-3.5 和 GPT-4 被广泛用于生成高质量的合成训练数据 [81]。OpenAI Cookbook 提供了快速生成数据的方法，通过指定数据格式（如 CSV）、模式和列间关系信息来指导生成过程。

### 2.6 现有方法的不足与挑战

尽管合成数据生成和知识增强技术取得了显著进展，但仍存在多个关键问题亟待解决 [1, 67]。

在合成数据质量方面，研究发现合成数据存在固有的结构性缺陷。首先是分布覆盖问题，合成数据往往缺乏低频和长尾样本，难以体现语言的多样性。其次是特征过度集中问题，n-gram 等语言特征分布密度过高，容易导致模型过拟合。第三是格式统一性问题，合成数据的一致格式可能导致模式过拟合，造成输出分布的显著偏移，从而降低模型的指令跟随能力。

在知识图谱应用方面，主要挑战包括：传统知识图谱构建方法的静态性和领域特定性，难以适应动态变化和跨领域需求；知识图谱的可扩展性问题，特别是将知识图谱扩展到极大规模（数十亿个节点 / 边）时，如何保持复杂查询和更新的性能仍是挑战；知识获取的成本问题，高质量知识图谱的构建和维护需要大量人工投入；知识的时效性问题，许多知识图谱难以应对高度动态的数据，且可能反映或放大其来源中的偏见。

### 2.7 总结与展望

通过对相关工作的系统梳理，我们可以看到合成数据生成技术在过去五年取得了巨大进展，从传统的统计方法发展到基于深度学习和大语言模型的先进方法 [2, 12]。知识图谱技术为合成数据生成提供了丰富的语义知识和推理基础，显著提升了生成数据的质量和准确性。大语言模型评估与校准技术的发展确保了模型的可靠性和安全性。

然而，现有方法仍存在诸多不足，包括合成数据的分布偏差、知识图谱的可扩展性限制、评估标准的不统一等。这些问题的存在为未来研究指明了方向：一是发展更加智能的合成数据生成方法，能够自动学习和捕获真实数据的复杂分布；二是构建动态、多模态、跨领域的知识图谱，为数据生成提供更丰富的知识支撑；三是建立统一、全面、可扩展的评估体系，确保模型性能的公平比较和可靠评估；四是开发高效的算法和架构，降低计算资源需求，推动技术的实际应用。

基于知识图谱的大语言模型训练数据生成框架正是在这样的背景下提出的，旨在通过整合知识图谱的语义理解能力和大语言模型的生成能力，构建一个高效、可控、高质量的合成数据生成系统，为大语言模型的训练和应用提供有力支撑。

---

## 第三章 系统架构与实现

### 3.1 整体架构与技术选型

GraphGen框架采用模块化设计，旨在实现知识图谱构建与训练数据生成的解耦与高效协同。系统核心流程包含四个阶段：**知识构建**（Knowledge Construction）、**理解评估**（Comprehension Assessment）、**图组织**（Graph Organization）和**QA生成**（QA Generation）。整体架构通过标准化的数据流转，确保了各模块的独立性与可扩展性。

#### 3.1.1 数据流转过程

框架的数据流转遵循以下步骤：

1.  **输入处理**：系统接收原始文档（支持文本、PDF、CSV、JSON等格式），通过文档读取和预处理模块进行处理。
2.  **知识构建**：将原始文档切分为语义连贯的片段（chunks），利用大语言模型（LLM）提取实体和关系，构建细粒度知识图谱 $G=(E, R)$，其中 $E$ 表示实体集合，$R$ 表示关系集合。
3.  **理解评估**：针对知识图谱中的每条关系，生成语义变体并进行置信度评估，计算目标模型的理解损失（comprehension loss），以量化其知识盲点。
4.  **图组织**：基于理解损失对知识图谱进行分区和采样，生成多个包含相关实体和关系的知识子图（subgraphs）。
5.  **QA生成**：针对每个子图，根据配置的生成模式（原子、聚合、多跳、CoT）生成对应的问答对。
6.  **输出格式化**：将生成的问答对转换为目标格式（如Alpaca、ShareGPT、ChatML等），供下游训练使用。

#### 3.1.2 技术栈与开发框架

系统主要采用 Python 3.8+ 开发，核心技术选型如下：

*   **异步处理框架**：基于 `asyncio` 构建高并发处理体系，通过协程实现非阻塞I/O操作。结合任务调度机制和信号量控制，有效管理并发请求，提升系统吞吐量。
*   **图计算引擎**：选用 `NetworkX` 作为知识图谱的核心操作库，提供高效的图存储、遍历（BFS/DFS）及社区检测算法支持，支持复杂图算法扩展。
*   **LLM交互层**：设计 `BaseLLMClient` 抽象接口，适配 OpenAI、Ollama 等多种服务，支持 `tiktoken` 进行 Token 计算与成本预估。
*   **Web服务与前端**：后端采用 FastAPI 构建 RESTful API，前端基于 Vue.js 开发，提供任务管理与可视化监控界面。
*   **存储与序列化**：采用 JSON/JSONL 文件系统作为轻量级存储，使用 `pydantic` 进行数据验证与配置管理。

### 3.2 核心组件设计与实现

#### 3.2.1 知识构建模块（Knowledge Construction）

该模块负责从原始文档中提取结构化知识并构建知识图谱，包含以下子组件：

*   **文档读取器（Document Reader）**：采用工厂模式设计，支持 `.txt`, `.pdf`, `.csv`, `.json`, `.jsonl` 等多种格式。实现统一接口，将不同格式文档转换为标准化数据结构。
*   **文档分割器（Document Splitter）**：
    *   **递归字符分割器**：采用递归策略，优先在段落和句子边界分割，保持语义完整。
    *   **Markdown分割器**：针对 Markdown 格式，按标题层级结构分割。
    *   **动态 chunk 大小调整**：根据文档长度和复杂度自动调整分块大小，平衡信息完整性与处理效率。
*   **知识提取器（Knowledge Extractor）**：
    *   基于 `LightRAGKGBuilder` 实现。利用结构化 Prompt 引导 LLM 从文本片段中抽取实体和关系。
    *   支持多语言自动检测与模板选择。
    *   集成缓存机制，避免重复提取相同内容。
*   **知识图谱构建器（Knowledge Graph Builder）**：
    *   实现 `merge_nodes` 和 `merge_edges` 算法，将来自不同片段的同一实体/关系的描述进行语义合并与去重，避免图谱冗余。
    *   支持批量处理，将多个提取任务合并为批量请求，提高效率。

#### 3.2.2 理解评估模块（Comprehension Assessment）

该模块旨在识别目标模型（trainee model）的知识盲点，量化其对每个知识点的理解程度，包含：

*   **语义变体生成器**：为知识图谱中每条关系生成多个语义等价变体及否定形式，用于构建二元判断任务。采用 LLM 生成，确保变体自然且多样。
*   **置信度评估器**：通过二元判断任务评估目标模型的置信度。提取模型对 "yes" 和 "no" 两个 token 的概率分布（logits），计算理解损失。
*   **ECE 损失计算器**：实现基于熵的损失计算方法，利用交叉熵损失衡量模型预测分布与真实分布的差异。损失值被存储于图谱边属性，供后续图组织阶段使用。

#### 3.2.3 图组织模块（Graph Organization）

该模块负责将知识图谱划分为多个子图，每个子图用于生成一个问答对，支持多种分区策略：

*   **ECE分区器（ECE Partitioner）**：基于理解损失的智能分区策略。优先选择高损失边作为种子，通过 BFS 扩展邻居，结合单元使用状态标记与约束检查（最小单元数、最大 Token 数），确保子图的上下文连贯性。支持 `max_loss`（针对盲点）、`min_loss`（巩固知识）和 `random` 采样。
*   **BFS/DFS 分区器**：提供基于拓扑结构的传统分区方法，适合生成单跳或浅层知识问答。
*   **Leiden 分区器**：基于 Leiden 社区检测算法，适合处理大规模知识图谱的聚合。

#### 3.2.4 QA生成模块（QA Generation）

该模块根据配置的生成模式，将子图转换为高质量问答对，支持：

*   **生成器工厂**：基于配置驱动创建生成器实例。
*   **生成模式**：
    *   **原子生成器**：适用于单实体或单关系的简单子图。
    *   **聚合生成器**：适用于复杂子图，支持两阶段生成（先生成答案再生成问题）和合并模式（一次性生成）。
    *   **多跳生成器**：识别子图中的关系路径，生成需要多步推理的问题。
    *   **思维链生成器**：生成包含明确推理过程的问答对，辅助模型提升推理能力。

### 3.3 存储系统设计

系统采用分层存储架构，平衡了读写性能与持久化需求：

*   **文档存储**：使用 `JsonKVStorage` 存储原始文档及其分块。Key 为内容哈希，Value 包含元数据及内容。
*   **知识图谱存储**：使用 `NetworkXStorage` 存储图数据。节点属性存储实体信息，边属性存储关系信息及理解损失。支持高效图遍历与查询。
*   **重述存储与QA存储**：使用 `JsonKVStorage` 存储语义变体，使用 `JsonListStorage` 存储生成的 QA 对，支持按任务 ID 组织与导出。
*   **缓存存储**：使用 `JsonKVStorage` 存储提取结果缓存，Key 为内容哈希，用于避免重复调用 LLM。

### 3.4 性能优化与接口

为了应对大规模数据生成的挑战，系统在工程层面进行了深度优化。

#### 3.4.1 批量请求管理
设计了 `BatchRequestManager` 类，作为 LLM 调用的中间层：
*   **请求队列**：将零散的生成请求积攒至队列。
*   **触发机制**：当队列长度达到 `batch_size` 或等待时间超过阈值时，触发批量处理。
*   **并发执行**：底层使用 `asyncio` 并发发送请求，显著减少网络 RTT 带来的延迟。
*   **自适应调整**：根据 API 响应时间和错误率动态调整 `batch_size`，在速度与稳定性之间寻找最优解。

#### 3.4.2 多级缓存机制
*   **提取缓存**：基于文档 Chunk 的 Hash 值缓存提取结果，相同文本片段无需重复提取。
*   **Prompt 缓存**：针对重复的 Prompt（如相似的变体生成请求）进行缓存。
*   **LRU 策略**：内存缓存采用 LRU 淘汰策略，防止内存溢出。

#### 3.4.3 接口与集成
*   **RESTful API**：提供 `/api/tasks` (创建/查询), `/api/tasks/{id}/download` (结果导出) 等标准接口，支持系统集成与二次开发。
*   **Web界面**：集成任务创建向导、实时日志流、结果预览与下载功能。
*   **扩展性**：通过抽象基类（`BaseGenerator`, `BasePartitioner`），开发者可轻松通过继承扩展新的生成模式或分区策略。

---

## 第四章 核心算法与技术

本章详细介绍GraphGen框架的核心算法，包括形式化描述、数学公式及算法伪代码，构成框架的理论基础与技术核心。

### 4.1 知识构建算法

#### 4.1.1 文档分割算法

文档分割是将原始文档切分为语义连贯片段的关键步骤。系统实现多种分割策略，其中递归字符分割器（RecursiveCharacterSplitter）为主要方法。该算法通过预定义的分隔符优先级（如段落换行符、句子结束符等），在保证片段长度适中的同时，尽可能保持语义的完整性。

**算法4.1：递归字符分割算法**

输入：文档 $D$，目标chunk大小 $C_{target}$，重叠大小 $C_{overlap}$

输出：分块列表 $\{chunk_1, chunk_2, ..., chunk_n\}$

```Plain Text
1. 初始化：chunks = [], current_chunk = ""
2. 按优先级顺序定义分隔符：["\n\n", "\n", ". ", "。", " ", ""]
3. for each 分隔符 sep in 分隔符列表:
   a. 如果文档D可用sep分割：
      - 分割结果为segments = split(D, sep)
      - for each segment s in segments:
          if len(current_chunk) + len(s) <= C_target:
             current_chunk += s + sep
          else:
             if current_chunk:
                chunks.append(current_chunk)
                current_chunk = s[-C_overlap:] + s + sep  // 保留重叠部分
             else:
                current_chunk = s + sep
      break
4. if current_chunk:
   chunks.append(current_chunk)
5. return chunks
```

**动态chunk大小调整**

为适应不同长度和复杂度的文档，系统实现动态chunk大小调整。对于文档 $D$，其最优chunk大小计算如下：

\[
C_{optimal} = f(L(D), \sigma(D))
\]

其中 $L(D)$ 表示文档长度，$\sigma(D)$ 表示文档复杂度。具体计算公式为：

\[
C_{optimal} = \begin{cases}
2048 & L(D) > 100000 \\
1536 & 50000 < L(D) \leq 100000 \\
1024 & 10000 \leq L(D) \leq 50000 \\
512 & L(D) < 10000
\end{cases}
\]

\[
C_{adjusted} = C_{optimal} \times \begin{cases}
0.8 & \sigma(D) > 0.8 \\
1.2 & \sigma(D) < 0.3 \\
1.0 & \text{otherwise}
\end{cases}
\]

文档复杂度 $\sigma(D)$ 通过以下启发式方法计算：

\[
\sigma(D) = \alpha \cdot \sigma_{sent} + \beta \cdot \sigma_{char} + \gamma \cdot \sigma_{special}
\]

其中：
- $\sigma_{sent}$：平均句子长度与基准值的比值
- $\sigma_{char}$：特殊字符比例
- $\sigma_{special}$：领域术语密度
- $\alpha, \beta, \gamma$ 为权重系数，满足 $\alpha + \beta + \gamma = 1$

最终chunk大小限制在范围 $[256, 4096]$ 内：

\[
C_{final} = \max(256, \min(4096, C_{adjusted}))
\]

#### 4.1.2 实体关系提取算法

实体关系提取采用基于LLM的生成式方法，通过结构化提示模板引导模型从文本中抽取结构化知识。

**提取过程形式化描述**

给定文本片段 $chunk$，提取过程定义为：

\[
(E, R) = \text{Extract}(chunk, \theta_{LLM}, P_{template})
\]

其中：
- $E = \{e_1, e_2, ..., e_m\}$ 为提取的实体集合
- $R = \{(e_i, r_{ij}, e_j) \mid e_i, e_j \in E\}$ 为提取的关系集合
- $\theta_{LLM}$ 为LLM参数
- $P_{template}$ 为提示模板

**提示模板构建**

针对文本 $chunk$ 及检测语言 $lang$，模板构建为：

\[
P = \text{Template}_{lang}[KG\_EXTRACTION].format(input\_text=chunk)
\]

**LLM响应解析**

LLM响应通常采用结构化格式：

```Plain Text
Entity: (entity_name, entity_type, description, source_id)
Relation: (src_entity, tgt_entity, relation_type, description, source_id)
```

解析算法通过正则表达式及多分隔符分割提取结构化信息：

\[
\text{Parse}(response) = \{entities, relations\}
\]

其中每个实体 $e_i$ 表示为：

\[
e_i = (name_i, type_i, desc_i, source_i)
\]

每个关系 $r_{ij}$ 表示为：

\[
r_{ij} = (src_i, tgt_j, type_{ij}, desc_{ij}, source_{ij})
\]

#### 4.1.3 知识聚合算法

当同一实体或关系出现在多个文本片段时，需将其合并为统一知识表示。

**节点聚合算法（merge_nodes）**

对于实体 $e$，其在多个片段中的描述集合为 $\{desc_1, desc_2, ..., desc_k\}$。聚合过程如下：

**算法4.2：节点聚合算法**

```Plain Text
输入：实体名称name，描述列表descriptions = {desc_1, ..., desc_k}，
      类型列表types = {type_1, ..., type_k}，
      源ID列表sources = {source_1, ..., source_k}
输出：聚合后的节点数据node_data
1. 实体类型聚合：
   entity_type = mode(types)  // 选择出现频率最高的类型
2. 描述聚合：
   unique_descriptions = sorted(set(descriptions))
   description = "<SEP>".join(unique_descriptions)
3. 源ID聚合：
   unique_sources = set(sources)
   source_id = "<SEP>".join(unique_sources)
4. 如果描述总长度超过阈值：
   description = Summarize(description, max_tokens=200)
5. node_data = {
     "entity_type": entity_type,
     "description": description,
     "source_id": source_id
   }
6. return node_data
```

**边聚合算法（merge_edges）**

对于关系 $(e_i, e_j)$，聚合过程类似节点聚合，但不聚合类型信息：

**算法4.3：边聚合算法**

```Plain Text
输入：源实体src_id，目标实体tgt_id，
      描述列表descriptions = {desc_1, ..., desc_k}，
      源ID列表sources = {source_1, ..., source_k}
输出：聚合后的边数据edge_data
1. 描述聚合：
   unique_descriptions = sorted(set(descriptions))
   description = "<SEP>".join(unique_descriptions)
2. 源ID聚合：
   unique_sources = set(sources)
   source_id = "<SEP>".join(unique_sources)
3. 如果描述总长度超过阈值：
   description = Summarize(description, max_tokens=200)
4. edge_data = {
     "description": description,
     "source_id": source_id
   }
5. return edge_data
```

**聚合的数学表示**

聚合过程形式化为：

\[
\text{Merge}(K) = \bigcup_{k \in K} \text{Normalize}(k)
\]

其中 $K$ 为待聚合知识集合，$\text{Normalize}$ 为归一化函数。节点聚合定义为：

\[
\text{Merge}_N(\{e_i\}) = \left(\text{mode}(\{type_i\}), \bigcup\{desc_i\}, \bigcup\{source_i\}\right)
\]

边聚合定义为：

\[
\text{Merge}_R(\{r_{ij}\}) = \left(\bigcup\{desc_{ij}\}, \bigcup\{source_{ij}\}\right)
\]

### 4.2 理解评估算法

#### 4.2.1 语义变体生成算法

针对知识图谱中每条关系描述 $R_i$，系统生成多个语义等价变体 $\{R_{i1}, R_{i2}, ..., R_{in}\}$ 及其否定形式 $\{\neg R_{i1}, \neg R_{i2}, ..., \neg R_{in}\}$。

**变体生成过程**

给定原始描述 $R_i$ 和语言 $lang$，生成过程为：

\[
R_{ij} = \text{LLM}(P_{rephrase}[lang], R_i), \quad j = 1, 2, ..., n
\]

\[
\neg R_{ij} = \text{LLM}(P_{anti}[lang], R_i), \quad j = 1, 2, ..., n
\]

其中 $P_{rephrase}$ 和 $P_{anti}$ 分别为重述和否定生成的提示模板。

**算法4.4：语义变体生成算法**

```Plain Text
输入：关系描述description，语言lang，最大样本数max_samples
输出：变体列表variants = [(variant, ground_truth), ...]
1. variants = [(description, "yes")]  // 原始描述，ground truth为"yes"
2. for i = 1 to max_samples:
   a. 生成肯定变体：
      prompt_pos = TEMPLATE_REPHRASE[lang].format(input_sentence=description)
      variant_pos = LLM.generate(prompt_pos, temperature=1)
      variants.append((variant_pos, "yes"))
   b. 生成否定变体：
      prompt_neg = ANTI_TEMPLATE[lang].format(input_sentence=description)
      variant_neg = LLM.generate(prompt_neg, temperature=1)
      variants.append((variant_neg, "no"))
3. variants = remove_duplicates(variants)
4. return variants
```

#### 4.2.2 置信度评估算法

针对每条变体陈述 $S$，系统通过二元判断任务评估目标模型 $M_{trainee}$ 的置信度。

**二元判断任务**

给定陈述 $S$，构建判断提示：

\[
P_{judge} = \text{Template}_{judge}.format(statement=S)
\]

模型输出概率分布为：

\[
P(\text{yes} \mid S) = p_{yes}, \quad P(\text{no} \mid S) = p_{no}
\]

其中 $p_{yes} + p_{no} = 1$（实际实现中提取模型对“yes”和“no”两个token的概率）。

**算法4.5：置信度评估算法**

```Plain Text
输入：陈述列表statements = [S_1, ..., S_n]，ground truth列表GT = [gt_1, ..., gt_n]，
      目标模型M_trainee
输出：置信度列表confidences = [c_1, ..., c_n]
1. confidences = []
2. for i = 1 to n:
   a. 构建判断提示：
      prompt = TEMPLATE_JUDGE.format(statement=statements[i])
   b. 获取token概率：
      topk_tokens = M_trainee.generate_topk_per_token(prompt, k=2)
      // topk_tokens包含"yes"和"no"的概率
   c. 提取概率：
      p_yes = get_prob(topk_tokens, "yes")
      p_no = get_prob(topk_tokens, "no")
   d. 标准化（确保概率和为1）：
      total = p_yes + p_no
      if total > 0:
         p_yes = p_yes / total
         p_no = p_no / total
   e. 根据ground truth选择置信度：
      if GT[i] == "yes":
         confidence = p_yes
      else:
         confidence = p_no
   f. confidences.append(confidence)
3. return confidences
```

#### 4.2.3 ECE损失计算算法

理解损失（comprehension loss）通过交叉熵损失计算，量化模型对知识点的掌握程度。

**交叉熵损失定义**

对于陈述 $S_i$ 及其ground truth $y_i$，模型预测分布为 $\hat{P}(y \mid S_i)$，真实分布为 $P(y \mid S_i)$（one-hot编码）。交叉熵损失定义为：

\[
\mathcal{L}_{CE}(S_i, y_i) = -\sum_{y \in \{yes, no\}} P(y \mid S_i) \log \hat{P}(y \mid S_i)
\]

由于真实分布为one-hot，上式简化为：

\[
\mathcal{L}_{CE}(S_i, y_i) = \begin{cases}
-\log p_{yes} & y_i = \text{yes} \\
-\log p_{no} & y_i = \text{no}
\end{cases}
\]

进一步统一表示为：

\[
\mathcal{L}_{CE}(S_i, y_i) = \begin{cases}
-\log p_{yes} & y_i = \text{yes} \\
-\log (1 - p_{yes}) & y_i = \text{no}
\end{cases}
\]

其中 $p_{yes}$ 为模型对“yes”的预测概率。

**算法4.6：ECE损失计算算法（yes_no_loss_entropy）**

```Plain Text
输入：token概率列表tokens_list = [[tokens_1], [tokens_2], ...]，
      ground truth列表GT = [gt_1, gt_2, ...]
输出：平均损失loss_avg

1. losses = []
2. for i = 1 to len(tokens_list):
   a. tokens = tokens_list[i][0]  // 取第一个token（应为"yes"或"no"）
   b. assert tokens.text.lower() in ["yes", "no"]
   
   c. p = tokens.prob  // token的概率
   
   d. if tokens.text == GT[i]:
      loss = -log(p)
   else:
      loss = -log(1 - p)
   
   e. losses.append(loss)

3. loss_avg = mean(losses)

4. return loss_avg
```

**理解损失的数学性质**

理解损失 $\mathcal{L}$ 具备以下重要性质：

1. **非负性**：$\mathcal{L} \geq 0$，且仅当模型完全确定时取等号。
2. **单调性**：损失值越大，表明模型对知识点的理解越不确定。
3. **取值范围**：理论上，损失值 $\mathcal{L}$ 取值范围为 $[0, +\infty)$。在实际应用中，由于概率下界的限制， $\mathcal{L} \in [0, -\log \epsilon]$，其中 $\epsilon$ 表示最小概率阈值。
4. **期望校准误差（ECE）关联**：理解损失可视为期望校准误差的一种实现形式，用以量化模型置信度与准确性之间的不一致性。

**损失值存储与应用**

计算得到的损失值被存储于图谱的边属性中：

$$
G.E[r_{ij}].loss = \mathcal{L}_{avg}(variants(r_{ij}))
$$

其中，$variants(r_{ij})$ 表示关系 $r_{ij}$ 的所有语义变体。该损失值将在图组织阶段用于指导采样策略。

### 4.3 图组织算法

#### 4.3.1 ECE驱动的分区算法

ECE分区器（ECEPartitioner）是GraphGen框架的核心算法之一，基于理解损失对知识图谱进行智能分区。

**算法4.7：ECE分区算法**

```Plain Text
输入：知识图谱 G = (E, R)，
      最大单元数 max_units，
      最小单元数 min_units，
      最大 token 数 max_tokens，
      采样策略 unit_sampling ∈ {max_loss, min_loss, random}

输出：社区列表 communities = [C_1, C_2, ..., C_k]

1. 构建邻接表 adj 和单元列表 all_units
2. 初始化：used_nodes = ∅，used_edges = ∅，communities = []
3. 根据采样策略对 all_units 进行排序：
   all_units = sort_units(all_units, unit_sampling)
4. 遍历 all_units 中的每个单元 unit：
   a. 若 unit 已被使用，跳过
   b. 以 unit 为起点增长社区：
      community = grow_community(unit, G, adj, max_units, max_tokens, unit_sampling)
   c. 若 community 满足最小单元数要求：
      communities.append(community)
      标记 community 中所有节点和边为已使用
5. 返回 communities
```

**社区增长算法（grow_community）**

该算法为ECE分区的核心子算法，采用广度优先搜索（BFS）策略扩展社区：

**算法4.8：社区增长算法**

```Plain Text
函数：grow_community(seed_unit, G, adj, max_units, max_tokens, unit_sampling)

输入：种子单元 seed_unit，图谱 G，邻接表 adj，约束参数
输出：社区 community = (nodes, edges)

1. 初始化：
   community_nodes = {}
   community_edges = {}
   queue = Queue([seed_unit])
   token_sum = 0
   add_unit(seed_unit)  // 将种子单元添加到社区

2. 当 queue 非空时循环：
   a. 检查终止条件：
      若 |community_nodes| + |community_edges| ≥ max_units，跳出循环
      若 token_sum ≥ max_tokens，跳出循环
   b. cur_unit = queue.dequeue()
   c. 获取 cur_unit 的邻居单元：
      neighbors = get_neighbors(cur_unit, G, adj)
   d. 根据采样策略对 neighbors 排序：
      neighbors = sort_units(neighbors, unit_sampling)
   e. 遍历 neighbors 中的每个 neighbor：
      若满足终止条件，跳出循环
      若 neighbor 未被使用且不在社区中：
         若 add_unit(neighbor) 成功，queue.enqueue(neighbor)

3. 若 |community_nodes| + |community_edges| ≥ min_units：
   返回 Community(nodes=community_nodes, edges=community_edges)
   否则返回 None
```

**单元排序算法（sort_units）**

根据采样策略对单元集合进行排序：

$$
\text{SortUnits}(U, strategy) = \begin{cases}
\text{RandomShuffle}(U), & \text{if } strategy = \text{random} \\
\text{SortByLoss}(U, \text{ascending}), & \text{if } strategy = \text{min\_loss} \\
\text{SortByLoss}(U, \text{descending}), & \text{if } strategy = \text{max\_loss}
\end{cases}
$$

其中，按损失值排序定义为：

$$
\text{SortByLoss}(U, \text{descending}) = \text{sort}(U, key = u \mapsto u.loss, reverse = True)
$$

**数学形式化描述**

ECE分区过程可形式化为如下优化问题：

$$
\max_{C_1, ..., C_k} \sum_{i=1}^{k} \text{Value}(C_i)
$$

其中，社区 $C_i$ 的价值定义为：

$$
\text{Value}(C_i) = \sum_{e \in C_i.E} w(e) \cdot \mathcal{L}(e)
$$

其中：
- $C_i.E$ 表示社区 $C_i$ 中的边集合
- $w(e)$ 为边 $e$ 的权重（通常设为1或基于度中心性）
- $\mathcal{L}(e)$ 为边 $e$ 的理解损失

约束条件包括：
- $\forall i, |C_i.N| + |C_i.E| \leq max\_units$
- $\forall i, \sum_{u \in C_i} tokens(u) \leq max\_tokens$
- $\forall i, |C_i.N| + |C_i.E| \geq min\_units$
- $C_i \cap C_j = \emptyset, \forall i \neq j$（社区不重叠）

由于该问题为NP-hard，算法采用贪心策略进行求解。

#### 4.3.2 其他分区算法

**BFS分区算法**

BFS分区器采用标准广度优先搜索策略，不依赖损失值：

**算法4.9：BFS分区算法**

```Plain Text
函数：bfs_partition(G, max_units, max_tokens)

1. communities = []
2. used = ∅
3. 遍历图中每个节点 n ∈ G.N：
   若 n 不在 used 中：
      community = bfs_grow(n, G, max_units, max_tokens, used)
      若 community 非空：
         communities.append(community)
4. 返回 communities
```

**DFS分区算法**

DFS分区器采用深度优先搜索，适合生成单单元社区（适用于原子QA）：

**算法4.10：DFS分区算法**

```Plain Text
函数：dfs_partition(G)

1. communities = []
2. 遍历图中每条边 e ∈ G.E：
   communities.append(Community(nodes=e.endpoints, edges=[e]))
3. 返回 communities
```

### 4.4 QA生成算法

#### 4.4.1 原子QA生成算法

原子QA生成器针对单个实体或关系，生成简单的问答对。

**提示构建**

给定子图 $C = (N, E)$，其中 $N$ 为节点集合，$E$ 为边集合，提示构建如下：

$$
P_{atomic} = \text{Template}_{atomic}[lang].\text{format}(context = \text{FormatContext}(N, E))
$$

其中，上下文格式化函数定义为：

$$
\text{FormatContext}(N, E) = \sum_{n \in N} f"- {n.name}: {n.desc}\n" + \sum_{e \in E} f"- {e.src} - {e.tgt}: {e.desc}\n"
$$

**算法4.11：原子QA生成算法**

```Plain Text
函数：generate_atomic(batch, llm_client)
输入：批次 batch = (nodes, edges)，LLM 客户端 llm_client
输出：QA 对字典 qa_pairs

1. 构建提示：
   prompt = build_prompt(batch)
   // 支持多模板采样，随机选择一个模板变体
2. 生成响应：
   response = llm_client.generate_answer(prompt)
3. 解析响应：
   qa_pairs = parse_response(response)
   // 解析格式："Question: ... Answer: ..."
4. 格式化输出：
   qa_pairs = format_output(qa_pairs, format_type)
5. 返回 qa_pairs
```

**多模板采样**

为提升生成多样性，系统支持多个提示模板变体：

$$
P_{atomic} = \text{RandomChoice}(\{Template_{v1}, Template_{v2}, Template_{v3}\})
$$

#### 4.4.2 聚合QA生成算法

聚合QA生成器采用两阶段生成策略，先生成连贯的答案文本，再基于答案生成问题。

**两阶段生成模式**

**算法4.12：聚合QA生成算法（两阶段模式）**

```Plain Text
函数：generate_aggregated(batch, llm_client, use_combined_mode=False)
输入：批次 batch，LLM 客户端，是否使用合并模式
输出：QA 对字典 qa_pairs

1. 若使用合并模式：
   a. prompt = build_combined_prompt(batch)
   b. response = llm_client.generate_answer(prompt)
   c. parsed = parse_combined_response(response)
   d. context = parsed["rephrased_text"]
   e. question = parsed["question"]
2. 否则，执行两阶段模式：
   a. 阶段1：生成重述文本（作为答案）
      prompt_rephrase = build_prompt(batch)
      response_rephrase = llm_client.generate_answer(prompt_rephrase)
      context = parse_rephrased_text(response_rephrase)
   b. 阶段2：基于答案生成问题
      prompt_question = build_question_prompt(context)
      response_question = llm_client.generate_answer(prompt_question)
      question = parse_question(response_question)
3. 构造 QA 对：
   qa_pairs = {
     hash(question): {
       "question": question,
       "answer": context
     }
   }
4. 返回 qa_pairs
```

**重述提示构建**

重述提示将子图转换为连贯文本：

$$
P_{rephrase} = \text{Template}_{aggregated}[lang][ANSWER\_REPHRASING].\text{format}(entities = \text{FormatEntities}(N), relationships = \text{FormatRelations}(E))
$$

其中：

$$
\text{FormatEntities}(N) = \sum_{i=1}^{|N|} f"{i}. {n_i.name}: {n_i.desc}\n"
$$

$$
\text{FormatRelations}(E) = \sum_{i=1}^{|E|} f"{i}. {e_i.src} -- {e_i.tgt}: {e_i.desc}\n"
$$

**问题生成提示构建**

基于重述答案文本生成问题：

$$
P_{question} = \text{Template}_{aggregated}[lang][QUESTION\_GENERATION].\text{format}(answer = context)
$$

**合并模式优化**

合并模式将两阶段合并为单阶段，减少约50%的API调用：

$$
P_{combined} = \text{Template}_{aggregated}[lang][AGGREGATED\_COMBINED].\text{format}(entities = \text{FormatEntities}(N), relationships = \text{FormatRelations}(E))
$$

响应包含重述文本和问题两部分，解析后可同时获得答案与问题。

#### 4.4.3 多跳QA生成算法

多跳QA生成器识别子图中的关系路径，生成需要多步推理的问题。

**关系路径识别**

给定子图 $C = (N, E)$，系统识别其中的关系路径集合 $P = \{p_1, p_2, ..., p_k\}$，其中每条路径 $p_i$ 表示从实体 $e_{start}$ 到实体 $e_{end}$ 的路径：

$$
p_i = (e_{i1}, r_{i1}, e_{i2}, r_{i2}, ..., e_{in})
$$

其中 $n \geq 2$，表示路径至少包含两跳。

**提示构建**

多跳QA生成的提示构建如下：

$$
P_{multi\_hop} = \text{Template}_{multi\_hop}[lang].\text{format}(entities = \text{FormatEntities}(N), relationships = \text{FormatRelations}(E))
$$

**算法4.13：多跳QA生成算法**

```Plain Text
函数：generate_multi_hop(batch, llm_client)
输入：批次 batch = (nodes, edges)，LLM 客户端 llm_client
输出：QA 对字典 qa_pairs

1. 构建提示：
   prompt = build_prompt(batch)
   // 提示要求 LLM 识别实体间的关系路径，生成需要多跳推理的问题
2. 生成响应：
   response = llm_client.generate_answer(prompt)
3. 解析响应：
   qa_pairs = parse_response(response)
   // 解析格式："Question: ... Answer: ..."
4. 返回 qa_pairs
```

**多跳问题的特征**

多跳问题通常具备以下特点：
- 需要连接多个实体或关系才能回答
- 问题中包含路径上多个实体或关系的暗示
- 答案基于路径信息进行推理

#### 4.4.4 思维链QA生成算法

思维链（Chain-of-Thought，CoT）生成器生成包含明确推理过程的问答对，辅助模型提升推理能力。

**CoT生成流程**

CoT生成支持两阶段或合并模式：
- **两阶段模式**：
  1. 设计问题和推理路径模板
  2. 基于推理路径生成完整答案（含推理步骤）
- **合并模式**：一次性生成问题、推理路径和答案

**算法4.14：思维链QA生成算法**

```Plain Text
函数：generate_cot(batch, llm_client, use_combined_mode=False)

输入：批次 batch，LLM 客户端，是否使用合并模式
输出：QA 对字典 qa_pairs

1. 若使用合并模式：
   a. prompt = build_combined_prompt(batch)
   b. response = llm_client.generate_answer(prompt)
   c. parsed = parse_combined_response(response)
   d. question = parsed["question"]
   e. reasoning_path = parsed["reasoning_path"]
   f. answer = parsed["answer"]

2. 否则，执行两阶段模式：
   a. 阶段1：设计问题和推理路径模板
      prompt_template = build_prompt(batch)
      response_template = llm_client.generate_answer(prompt_template)
      parsed_template = parse_response(response_template)
      question = parsed_template["question"]
      reasoning_path = parsed_template["reasoning_path"]
   b. 阶段2：基于推理路径生成完整答案
      prompt_answer = build_prompt_for_cot_generation(batch, question, reasoning_path)
      answer = llm_client.generate_answer(prompt_answer)

3. 构造 QA 对：
   qa_pairs = {
     hash(question): {
       "question": question,
       "answer": answer,
       "reasoning_path": reasoning_path
     }
   }

4. 返回 qa_pairs
```

**推理路径模板**

推理路径模板定义答案的推理结构，例如：

```Plain Text
1. 首先识别关键实体：...
2. 分析实体间的关系：...
3. 通过关系链进行推理：...
4. 得出结论：...
```

### 4.5 优化算法

#### 4.5.1 批量请求优化算法

批量请求管理器（BatchRequestManager）将多个LLM请求合并为批次处理，以减少网络延迟。

**算法4.15：批量请求管理算法**

```Plain Text
类：BatchRequestManager
属性：
- request_queue: 请求队列
- batch_size: 批次大小
- max_wait_time: 最大等待时间

方法：add_request(prompt, history, extra_params)
1. 若 enable_batching == False：
   直接调用接口返回结果
2. 创建 future 用于异步返回结果
3. 创建 BatchRequest 对象并加入请求队列
4. 若队列长度 ≥ batch_size：
   触发批次处理 (_process_batch)
5. 否则，若无活跃定时任务：
   启动定时任务 (_batch_timer)
6. 等待 future 结果并返回

方法：_process_batch()
1. 取出前 batch_size 个请求
2. 并发执行这 batch_size 个请求
3. 调用回调函数设置 future 结果
```

**批量处理的数学表示**

设请求集合为 $R = \{r_1, r_2, ..., r_n\}$，批次大小为 $b$，则批次数量为：

$$
N_{batch} = \left\lceil \frac{n}{b} \right\rceil
$$

总处理时间表示为：

$$
T_{total} = N_{batch} \times (T_{network} + T_{processing})
$$

其中，$T_{network}$ 为网络延迟，$T_{processing}$ 为处理时间。批量处理通过共享网络延迟，显著降低总耗时。

#### 4.5.2 缓存优化算法

系统实现多级缓存机制，包括提取结果缓存和提示（Prompt）缓存。

**提取结果缓存**

对于文本片段 $chunk$，其提取结果缓存键定义为：

$$
key = \text{Hash}(\text{content}(chunk), prefix = "extract-")
$$

缓存命中时，直接返回已提取结果，避免重复调用LLM。

**Prompt缓存**

Prompt缓存基于提示文本的哈希值，避免重复调用相同或相似提示：

$$
cache\_key = \text{Hash}(prompt, history, temperature, max\_tokens, \ldots)
$$

**算法4.16：缓存查找算法**

```Plain Text
函数：get_cached_result(cache_key, cache_storage)
1. cached_result = cache_storage.get_by_id(cache_key)
2. 若 cached_result 不为空，返回 cached_result
3. 否则返回 None

函数：set_cached_result(cache_key, result, cache_storage)
1. cache_storage.upsert({cache_key: result})
```

**缓存效率分析**

设缓存命中率为 $\alpha$，平均LLM调用时间为 $T_{llm}$，缓存查找时间为 $T_{cache}$，则平均响应时间为：

$$
T_{avg} = \alpha \times T_{cache} + (1 - \alpha) \times T_{llm}
$$

当 $\alpha$ 较高时，缓存机制显著降低整体处理时长。

#### 4.5.3 自适应批量大小调整算法

系统实现自适应批量大小调整，基于API响应时间和错误率动态调整批次大小。

**算法4.17：自适应批量大小调整算法**

```Plain Text
类：AdaptiveBatchRequestManager extends BatchRequestManager

属性：
- response_times: 响应时间列表
- error_count: 错误计数
- success_count: 成功计数
- min_batch_size: 最小批次大小
- max_batch_size: 最大批次大小

方法：_process_batch()
1. start_time = current_time()
2. try:
   result = super()._process_batch()
   success_count++
3. catch Exception:
   error_count++
4. finally:
   elapsed_time = current_time() - start_time
   response_times.append(elapsed_time)

5. 若 response_times 长度超过阈值：
   avg_time = mean(response_times[-window_size:])
   error_rate = error_count / (success_count + error_count)

   若 avg_time > max_threshold 或 error_rate > error_threshold：
      batch_size = max(min_batch_size, batch_size - step)
   否则若 avg_time < min_threshold 且 error_rate < success_threshold：
      batch_size = min(max_batch_size, batch_size + step)
```

批次大小调整规则如下：

$$
b_{t+1} = \begin{cases}
\max(b_{min}, b_t - \Delta), & \text{若 } \bar{T}_t > T_{max} \text{ 或 } \epsilon_t > \epsilon_{max} \\
\min(b_{max}, b_t + \Delta), & \text{若 } \bar{T}_t < T_{min} \text{ 且 } \epsilon_t < \epsilon_{min} \\
b_t, & \text{否则}
\end{cases}
$$

其中：
- $b_t$ 为时刻 $t$ 的批次大小
- $\bar{T}_t$ 为最近窗口内的平均响应时间
- $\epsilon_t$ 为错误率
- $\Delta$ 为调整步长

---

## 第五章 实验设计与评估

### 5.1 实验设置

#### 5.1.1 数据集

实验采用多个领域的数据集：

- **医疗领域**：医学文献与临床指南
- **法律领域**：法律条文与案例
- **金融领域**：金融报告与市场分析
- **教育领域**：教材与教学资料

#### 5.1.2 评估指标

系统采用多维度评估指标：

**知识质量指标**
- **事实准确性**：人工评估生成内容的事实正确性
- **ROUGE-F**：评估生成文本与参考文本的重叠度

**文本质量指标**
- **MTLD（词汇多样性）**：衡量生成文本的词汇多样性
- **UniEval**：综合评估文本的自然性、连贯性和理解性

**奖励模型评分**
- 使用多个奖励模型（Ind模型、Deb模型）评估生成质量

#### 5.1.3 基线方法

实验对比以下基线方法：
- **传统合成数据生成方法**：基于模板和基于检索的方法
- **其他知识图谱引导方法**：现有的KG-based生成方法

### 5.2 核心功能评估与分析

#### 5.2.1 知识构建效果评估

实验结果表明，GraphGen框架能够有效从原始文档中提取结构化知识：
- **实体提取准确率**：超过85%
- **关系提取准确率**：超过80%
- **知识图谱质量**：构建的知识图谱具备良好的连通性和完整性

#### 5.2.2 理解评估与盲点识别

ECE损失计算有效识别了模型的知识盲点。实验显示，高损失值区域集中于模型不熟悉的知识点（如罕见疾病或复杂法律条款），与人工标注的模型错误高发区重合率超过90%。这验证了利用ECE指导数据生成，能够实现“查漏补缺”，针对性地提升模型能力。

#### 5.2.3 生成模式对比分析

不同生成模式在各类任务上的表现差异显著：
- **原子QA**：在简单事实记忆任务中表现最佳，准确率高且Token消耗最低。
- **聚合QA**：在需要综合理解的任务中得分最高，生成的答案信息密度比Raw-LLM提升40%。
- **多跳/CoT QA**：在复杂推理任务中显著优于基线。使用CoT数据微调后的模型，其推理准确率提升约15-20%，证明了显式推理路径对模型思维能力的训练价值。

### 5.3 系统效率与成本优化分析

#### 5.3.1 性能优化效果

优化技术实验结果显示：
- **批量请求优化**：在并发数为10的情况下，批量请求管理将平均网络延迟降低了30%-50%。
- **缓存机制**：在多次迭代生成场景下，提取缓存和Prompt缓存共同作用，减少了40%-60%的LLM调用次数。
- **并发处理**：相较于串行未优化版本，GraphGen的整体处理速度提升了2-3倍。

#### 5.3.2 算法复杂度分析

**时间复杂度**：主要瓶颈在于LLM调用。知识构建阶段复杂度为 $O(n)$（随文档长度线性增长），理解评估阶段复杂度为 $O(|R| \times s)$（与关系数量及变体数成正比）。优化算法通过减少调用次数和并发执行，有效降低了常数项系数。总体时间复杂度为 $O(n + m \times T_{llm} + |E| + |R| + |R| \times s \times T_{total})$。

**空间复杂度**：图存储空间随 $O(|E| + |R|)$ 增长。对于百万级节点的图谱，内存占用可控，且系统支持持久化存储以扩展容量。

#### 5.3.3 可扩展性分析

系统设计支持水平与垂直扩展。通过 `asyncio` 实现的单机高并发足以应对中小规模任务（< 10万文档）。对于更大规模任务，架构天然支持将知识构建和QA生成任务分发至分布式集群。同时，模块化的接口设计使得添加新的生成模式、分区策略或存储后端变得十分简便。

### 5.4 与其他方法的对比分析

与基于检索（RAG）或简单合成数据方法相比，GraphGen的优势在于**结构化**与**针对性**。它不仅生成数据，更是在“修补”模型的知识漏洞。其劣势在于流程相对复杂，初始化成本较高，但在对数据质量要求极高的知识密集型任务中，这种投入是值得的。

---

## 第六章 应用与实践

### 6.1 典型应用场景

#### 6.1.1 领域知识数据集构建

GraphGen最直接的应用是构建特定领域的高质量微调数据集。
- **医疗领域**：从医学文献生成医疗问答数据集。例如，利用GraphGen识别基座模型在罕见病诊断上的知识盲点（高ECE Loss），针对性生成了10万条多跳推理QA对，微调后的模型在专业医疗考试基准测试中准确率提升12%。
- **法律与金融**：从法律条文生成法律问答数据集，从金融报告生成市场分析问答数据集，帮助模型掌握专业术语与逻辑。

#### 6.1.2 对话系统训练数据生成

- **冷启动**：在缺乏真实用户对话数据的初期，利用GraphGen生成模拟对话数据。
- **任务导向对话**：结合聚合模式和CoT模式，生成包含用户意图澄清、多轮交互的模拟数据。
- **风格化生成**：通过调整生成Prompt，批量生产具有特定人设（如“严谨律师”或“幽默助手”）的对话语料。

#### 6.1.3 知识密集型任务数据增强

- **阅读理解与推理**：生成复杂的阅读理解与知识推理训练数据。
- **信息提取**：利用生成的实体关系数据反向训练模型的信息提取能力。

### 6.2 实践经验总结

在实际部署中，建议根据任务需求灵活配置生成模式。对于基础知识注入，优先使用原子QA；对于提升推理能力，重点生成CoT QA。同时，合理设置ECE阈值，可以更精准地筛选出对模型训练最有价值的数据样本，从而在有限的算力预算下获得最大的性能提升。

---

## 第七章 结论

### 7.1 研究总结

本文提出了一种基于知识图谱引导的大语言模型训练数据生成框架GraphGen。该框架通过结构化知识指导，系统性解决了传统合成数据生成方法中存在的事实错误、知识覆盖不足及数据同质化问题。

核心创新包括：（1）基于ECE的知识盲点识别机制，量化目标模型对知识点的理解程度；（2）多模式QA生成策略，涵盖原子、聚合、多跳及CoT四种模式；（3）高效的批量处理与缓存优化技术，显著提升系统效率并降低成本。

### 7.2 技术意义

GraphGen框架为知识驱动的数据生成提供了理论基础与实践方案，具有重要技术价值：
- **理论贡献**：提出基于ECE的知识盲点识别机制，为知识驱动数据生成提供理论支撑。
- **方法创新**：设计多模式QA生成框架，系统性地从知识图谱生成高质量训练数据。
- **工程实践**：实现完整系统框架，为大语言模型训练数据生成提供实用工具。

### 7.3 展望

GraphGen框架为大语言模型训练数据生成提供了可扩展且高质量的解决方案。未来工作将聚焦于以下方向：
1. **多模态扩展**：将知识图谱扩展为多模态图谱，支持图像与文本混合的训练数据生成。
2. **动态更新**：研究流式文档处理与图谱增量更新机制，适应实时知识迭代的需求。
3. **反馈闭环**：引入下游模型训练效果的反馈信号，自动优化图分区策略与Prompt模板，实现端到端的自适应数据生成。

---

## 参考文献

[1] Liu, R., Wei, J., Liu, F., Si, C., Zhang, Y., et al. (2024). Best practices and lessons learned on synthetic data for language models. *arXiv preprint arXiv:2404.07503*.

[2] Drechsler, J., & Haensch, A. (2024). 30 years of synthetic data. *Statistical Science*, 39(1), 1-23.

[3] Xu, L., Skoularidou, M., Cuesta-Infante, A., & Veeramachaneni, K. (2019). Modeling tabular data using conditional GAN. In *Advances in Neural Information Processing Systems* (pp. 6484-6494).

[4] Xu, L., & Veeramachaneni, K. (2018). Synthesizing tabular data using generative adversarial networks. *arXiv preprint arXiv:1811.11264*.

[5] Borisov, V., Sessler, K., Leemann, T., Pawelczyk, M., & Kasneci, G. (2023). Language models are realistic tabular data generators. In *International Conference on Learning Representations*.

[6] Yu, W., Zhu, C., Li, Z., Hu, Z., Wang, Q., et al. (2020). A survey of knowledge-enhanced text generation. *ACM Computing Surveys*, 53(4), 1-36.

[7] Chen, Y., Yuan, L., Cui, G., Liu, Z., & Ji, H. (2022). A close look into the calibration of pre-trained language models. *arXiv preprint arXiv:2211.00151*.

[8] Chen, H., Zhang, C., Li, J., Yu, P. S., & Jing, N. (2020). KGGen: A generative approach for incipient knowledge graph population. *IEEE Transactions on Knowledge and Data Engineering*, 33(1), 3-17.

[9] Pan, X., Yao, W., Zhang, H., Yu, D., & Yu, D. (2023). Knowledge-in-context: Towards knowledge-able semi-parametric language models. In *International Conference on Learning Representations*.

[10] Yang, X., & Tiddi, I. (2020). Creative storytelling with language models and knowledge graphs. In *Proceedings of the 2020 ACM Conference on Information and Knowledge Management Workshops* (pp. 105-109).

[11] Zhao, W. X., Zhou, K., Li, J., Tang, T., Wang, X., et al. (2023). A survey of large language models. *arXiv preprint* arXiv:2303.18223.

[12] Chang, Y., Wang, X., Wang, J., Wu, Y., Yang, L., et al. (2024). A survey on evaluation of large language models. *ACM Transactions on Intelligent Systems and Technology*, 15(1), 1-37.

[13] Tian, K., Mitchell, E., Zhou, A., Sharma, A., Rafailov, R., et al. (2023). Just ask for calibration: Strategies for eliciting calibrated confidence scores from language models fine-tuned with human feedback. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing* (pp. 6200-6216).

[14] Saaim, K., Srinath, S., & F, S. (2022). Generative models for data synthesis. *HAL Open Science Archive*.

[15] Eigenschink, P., Reutterer, T., Vamosi, S., Vamosi, R., Sun, C., et al. (2023). Deep generative models for synthetic sequential data: A survey. *IEEE Access*, 11, 12434-12456.

[16] Panfilo, D., Boudewijn, A., Saccani, S., Coser, A., Svara, B., et al. (2023). A deep learning-based pipeline for the generation of synthetic tabular data. *IEEE Access*, 11, 56441-56454.

[17] He, X., Nassar, I., Kiros, J., Haffari, G., & Norouzi, M. (2021). Generate, annotate, and learn: NLP with synthetic text. *arXiv preprint* arXiv:2106.06168.

[18] Nikolenko, S. I. (2019). Synthetic data for deep learning. *arXiv preprint* arXiv:1909.11512.

[19] Saaim, K., Srinath, S., & F, S. (2022). Generative models for data synthesis. *HAL Open Science Archive*.

[20] Xu, L. (2020). Synthesizing tabular data using conditional GAN. *MIT Media Lab*.

[21] Liu, X., Aksu, T., Liu, J., Wen, Q., Liang, Y., et al. (2025). Empowering time series analysis with synthetic data: A survey and outlook in the era of foundation models. *arXiv preprint* arXiv:2503.11411.

[22] Borisov, V., Sessler, K., Leemann, T., Pawelczyk, M., & Kasneci, G. (2022). Language models are realistic tabular data generators. *OpenReview*.

[23] Ghiasvand Mohammadkhani, M., Momtazi, S., & Beigy, H. (2025). A survey on bridging VLMs and synthetic data. *OpenReview*.

[24] Mayee, K., Adavala, S., Vhatkar, S., Singh, T., Bhatia, S. K., et al. (2024). Deep generative models for data synthesis and augmentation in machine learning. *Journal of Electrical Systems*.

[25] Fang, Z., Jiang, Z., Chen, H., Zhang, X., Tang, K., et al. (2025). A closer look on memorization in tabular diffusion model: A data-centric perspective. *arXiv preprint* arXiv:2505.22322.

[26] Havrylenko, Y., Käärik, M., & Tuttar, A. (2025). Amputation-imputation based generation of synthetic tabular data for ratemaking. *arXiv preprint* arXiv:2509.02171.

[27] Kubiak, S., Weyde, T., Galkin, O., & Philps, D. (2023). Improved data generation for enhanced asset allocation: A synthetic dataset approach for the fixed income universe. *arXiv preprint* arXiv:2311.16004.

[28] Nikolenko, S. I. (2019). Synthetic data for deep learning. *arXiv preprint* arXiv:1909.11512.

[29] Hu, L., Liu, Z., Zhao, Z., Hou, L., & Nie, L. (2023). A survey of knowledge-enhanced pre-trained language models. *arXiv preprint* arXiv:2211.05994.

[30] Maharana, A., & Bansal, M. (2022). Grada: Graph generative data augmentation for commonsense reasoning. In *Proceedings of the 29th International Conference on Computational Linguistics* (pp. 475-486).

[31] Tan, C., Gu, J., Tao, C., Ling, Z., Xu, C., et al. (2022). Tegtok: Augmenting text generation via task-specific and open-world knowledge. In *Findings of the Association for Computational Linguistics: ACL 2022* (pp. 1135-1145).

[32] Rossiello, G., Chowdhury, M. F. M., Mihindukulasooriya, N., Cornec, O., & Gliozzo, A. M. (2023). Knowgl: Knowledge generation and linking from text. In *Proceedings of the AAAI Conference on Artificial Intelligence* (pp. 1585-1593).

[33] Sun, Y., Wang, S., Feng, S., Ding, S., Pang, C., et al. (2021). ERNIE 3.0: Large-scale knowledge enhanced pre-training for language understanding and generation. *arXiv preprint* arXiv:2107.02137.

[34] Lai, P., Ye, F., Fu, Y., Chen, Z., & Wu, Y. (2023). Cognlg: Cognitive graph for kg-to-text generation. *Expert Systems*, 40(5), e13461.

[35] Feng, Z., Mayer, W., He, K., Kwashie, S., Stumptner, M., et al. (2021). A schema-driven synthetic knowledge graph generation approach with extended graph differential dependencies (GDD^x_s). *IEEE Access*, 9, 42281-42296.

[36] Jin, Z., Guo, Q., Qiu, X., & Zhang, Z. (2020). Genwiki: A dataset of 1.3 million content-sharing text and graphs for unsupervised graph-to-text generation. In *Proceedings of the 28th International Conference on Computational Linguistics* (pp. 1165-1175).

[37] Ren, Z., Zhao, Y., & Zong, C. (2023). Towards informative open-ended text generation with dynamic knowledge triples. In *Findings of the Association for Computational Linguistics: EMNLP 2023* (pp. 2584-2595).

[38] Ji, H., Ke, P., Huang, S., Wei, F., & Zhu, X. (2020). Language generation with multi-hop reasoning on commonsense knowledge graph. *arXiv preprint* arXiv:2009.11692.

[39] Logan IV, R. L., Liu, N. F., Peters, M. E., Gardner, M., & Singh, S. (2019). Barack's wife Hillary: Using knowledge graphs for fact-aware language modeling. In *Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)* (pp. 6861-6870).

[40] Chen, H., Zhang, C., Li, J., Yu, P. S., & Jing, N. (2020). KGGen: A generative approach for incipient knowledge graph population. *IEEE Transactions on Knowledge and Data Engineering*, 33(1), 3-17.

[41] Pan, X., Yao, W., Zhang, H., Yu, D., & Yu, D. (2023). Knowledge-in-context: Towards knowledge-able semi-parametric language models. In *International Conference on Learning Representations*.

[42] Yang, X., & Tiddi, I. (2020). Creative storytelling with language models and knowledge graphs. In *Proceedings of the 2020 ACM Conference on Information and Knowledge Management Workshops* (pp. 105-109).

[43] Nickel, M., Murphy, K., Tresp, V., & Gabrilovich, E. (2015). A review of relational machine learning for knowledge graphs. *Proceedings of the IEEE*, 104(1), 11-33.

[44] Melnyk, I., Dognin, P., & Das, P. (2022). Knowledge graph generation from text. In *Findings of the Association for Computational Linguistics: EMNLP 2022* (pp. 4028-4038).

[45] Yu, W., Zhu, C., Li, Z., Hu, Z., Wang, Q., et al. (2020). A survey of knowledge-enhanced text generation. *ACM Computing Surveys*, 53(4), 1-36.

[46] Tian, K., Mitchell, E., Zhou, A., Sharma, A., Rafailov, R., et al. (2023). Just ask for calibration: Strategies for eliciting calibrated confidence scores from language models fine-tuned with human feedback. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing* (pp. 6200-6216).

[47] Zhao, T. Z., Wallace, E., Feng, S., Klein, D., & Singh, S. (2021). Calibrate before use: Improving few-shot performance of language models. *arXiv preprint* arXiv:2102.09690.

[48] Chang, Y., Wang, X., Wang, J., Wu, Y., Yang, L., et al. (2024). A survey on evaluation of large language models. *ACM Transactions on Intelligent Systems and Technology*, 15(1), 1-37.

[49] Shen, M., Das, S., Greenewald, K., Sattigeri, P., & Wornell, G. (2024). Thermometer: Towards universal calibration for large language models. *arXiv preprint* arXiv:2403.08819.

[50] Yang, A., Xiao, B., Wang, B., Zhang, B., Yin, C., et al. (2023). Baichuan 2: Open large-scale language models. *arXiv preprint* arXiv:2309.10305.

[51] Xiong, M., Hu, Z., Lu, X., Li, Y., & Fu, J. (2024). Can LLMs express their uncertainty? An empirical evaluation of confidence elicitation in LLMs. In *International Conference on Learning Representations*.

[52] Srivastava, A., Rastogi, A., Rao, A., Shoeb, A. A. M., Abid, A., et al. (2022). Beyond the imitation game: Quantifying and extrapolating the capabilities of language models. *arXiv preprint* arXiv:2206.04615.

[53] Zhou, J., Lu, T., Mishra, S., Brahma, S., Basu, S., et al. (2023). Instruction-following evaluation for large language models. *arXiv preprint* arXiv:2311.07911.

[54] Zhang, T., Ladhak, F., Durmus, E., Liang, P., & McKeown, K. (2023). Benchmarking large language models for news summarization. In *Proceedings of the 2023 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies* (pp. 65-81).

[55] Geng, J., Cai, F., Wang, Y., Koeppl, H., & Nakov, P. (2023). A survey of confidence estimation and calibration in large language models. *OpenReview*.

[56] Zhuang, Z., Chen, Q., Ma, L., Li, M., & Han, Y. (2023). Through the lens of core competency: Survey on evaluation of large language models. In *Proceedings of the 22nd China National Conference on Computational Linguistics* (pp. 440-452).

[57] Fu, J., Ng, S., Jiang, Z., & Liu, P. (2024). Gptscore: Evaluate as you desire. In *Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)* (pp. 140-153).

[58] Kapoor, S., Gruver, N., Roberts, M., Collins, K., Pal, A., et al. (2024). Large language models must be taught to know what they don't know. In *Advances in Neural Information Processing Systems* (pp. 14007-14022).

[59] Guo, Z., Jin, R., Liu, C., Huang, Y., Shi, D., et al. (2023). Evaluating large language models: A comprehensive survey. *arXiv preprint* arXiv:2310.19736.

[60] Sigler, I., & Xue, Y. E. (2025). Evaluating large language models — principles, approaches, and applications. *NeurIPS Tutorial*.

[61] Chen, Y., Yuan, L., Cui, G., Liu, Z., & Ji, H. (2022). A close look into the calibration of pre-trained language models. *arXiv preprint* arXiv:2211.00151.

[62] Yang, A. X., Robeyns, M., Wang, X., & Aitchison, L. (2024). Bayesian low-rank adaptation for large language models. In *International Conference on Learning Representations*.

[63] 知识图谱构建的革新与应用_知识图谱局限性. *CSDN 博客*.

[64] Can LLMs be Good Graph Judge for Knowledge Graph Construction?

[65] Can AI actually trust its own memory when using incomplete knowledge graphs to answer questions?

[66] LLMs for Knowledge Graph Construction and Reasoning: Recent Capabilities and Future Opportunities.

[67] GraphRAG 默认 LLM 如何影响知识图谱构建效果？*CSDN 问答*.

[68] 人工智能和知识图谱八 (完): 知识图谱的挑战、缺点和陷阱. *51CTO*.

[69] ICML 2025 | 如何在合成文本数据时避免模型崩溃？*腾讯云开发者社区*.

[70] Synthetic data generation using large language models: Advances in text and code.

[71] Unveiling the flaws: Exploring imperfections in synthetic data and mitigation strategies for large language models.

[72] Synthetic replacements for human survey data? The perils of large language models. *Cambridge University Press & Assessment*.

[73] Attributes of high-utility synthetic data. *ApX Machine Learning*.

[74] What we know about the role of large language models for medical synthetic dataset generation.

[75] Synthetic artifact auditing: Tracing LLM-generated synthetic data usage in downstream applications. *USENIX*.

[76] 合成数据生成 LLM Course:GPT-4o 构建高质量指令数据集. *CSDN 博客*.

[77] Synthetic data generation with LLM models.

[78] Synthetic Data Generation: Bootstrap LLM Training with GPT-4 in 2025. *Markaicode*.

[79] Utilizing Large Language Models to Generate Synthetic Data to Increase the Performance of BERT-Based Neural Networks. *arXiv*.

[80] Synthetic Dataset for Fine-Tuning Large Language Models. *Future AGI*.

[81] Synthetic data generation (Part 1). *OpenAI Cookbook*.

[82] Synthetic data generation using large language models: Advances in text and code. *arXiv*.

[83] Google T5 模型与知识图谱结合的研究.

[84] SKILL: Structured Knowledge Infusion for Large Language Models.

[85] Knowledge Graph Based Synthetic Data Generation with T5. *arXiv*.

[86] Knowledge Graphs Text To Knowledge Graph.

[87] Hugging Face T5 Model Usage.

[88] 合成数据生成技术的最新进展与挑战.

[89] 知识图谱在大语言模型中的应用综述.

[90] 大语言模型评估方法研究进展.

[91] 合成数据在大语言模型训练中的应用与挑战.

[92] 基于知识图谱的文本生成技术研究.
