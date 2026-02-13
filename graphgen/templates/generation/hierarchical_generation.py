"""Hierarchical generation templates for tree-structured knowledge."""

# English templates
TEMPLATE_EN_SIBLING: str = """You are given a hierarchical knowledge structure showing concepts and their relationships. Your task is to generate a question and answer (QA) pair that focuses on comparing sibling concepts at the same level of the hierarchy.

---Strict Format Requirements---
You MUST output in the following format (do NOT add any extra explanations, preambles, or meta-descriptions):
Question: [your question content]
Answer: [your answer content]
Hierarchical Reasoning: [brief explanation of the hierarchical relationship being explored]

Important:
- Output only ONE QA pair
- Do NOT add phrases like "Based on the hierarchy" or "Here is" at the beginning
- Start directly with "Question:"

---Question Requirements---
1. Ask about differences or similarities between sibling concepts
2. Focus on distinguishing attributes or unique properties
3. Use comparative language: "How does X differ from Y?", "What distinguishes X from Y?", "Compare X and Y in terms of..."
4. Explore inherited vs. unique characteristics

---Answer Requirements---
1. Provide a clear comparison highlighting key differences and similarities
2. Mention inherited properties from the parent concept
3. Identify unique attributes specific to each sibling
4. Be comprehensive but focused on the comparison (aim for 3-5 sentences)

---Hierarchical Structure---
{context}

Generate a QA pair that explores the relationship between sibling concepts in this hierarchy.
"""

TEMPLATE_EN_INHERITANCE: str = """You are given a hierarchical knowledge structure showing concepts and their inheritance relationships. Your task is to generate a question and answer (QA) pair that explores how properties are inherited from parent to child concepts.

---Strict Format Requirements---
You MUST output in the following format (do NOT add any extra explanations, preambles, or meta-descriptions):
Question: [your question content]
Answer: [your answer content]
Hierarchical Reasoning: [brief explanation of the inheritance logic]

Important:
- Output only ONE QA pair
- Do NOT add phrases like "Based on the hierarchy" or "Here is" at the beginning
- Start directly with "Question:"

---Question Requirements---
1. Ask about why a child concept has certain properties
2. Focus on inheritance from parent concepts
3. Use language like: "Why does X have property P?", "How does X inherit...?", "Explain the relationship between X and its parent Y in terms of..."
4. Explore the logical chain of inheritance

---Answer Requirements---
1. Explain the inheritance from parent to child
2. Trace the property through the hierarchy
3. Mention which properties come from which ancestor
4. Be clear and logical (aim for 3-5 sentences)

---Hierarchical Structure---
{context}

Generate a QA pair that explores inheritance relationships in this hierarchy.
"""

TEMPLATE_EN_ABSTRACTION: str = """You are given a hierarchical knowledge structure. Your task is to generate a question and answer (QA) pair that explores abstraction and generalization - identifying parent categories from child concepts.

---Strict Format Requirements---
You MUST output in the following format (do NOT add any extra explanations, preambles, or meta-descriptions):
Question: [your question content]
Answer: [your answer content]
Hierarchical Reasoning: [brief explanation of the abstraction logic]

Important:
- Output only ONE QA pair
- Do NOT add phrases like "Based on the hierarchy" or "Here is" at the beginning
- Start directly with "Question:"

---Question Requirements---
1. Ask about categorization or generalization
2. Focus on identifying common properties across concepts
3. Use language like: "What category do X, Y, and Z belong to?", "What is the common characteristic of...?", "Classify these concepts and explain why..."
4. Explore how specific concepts relate to abstract categories

---Answer Requirements---
1. Identify the parent category or common abstraction
2. Explain the shared properties that justify the categorization
3. Mention distinguishing features if relevant
4. Be clear about the generalization logic (aim for 3-5 sentences)

---Hierarchical Structure---
{context}

Generate a QA pair that explores abstraction and categorization in this hierarchy.
"""

TEMPLATE_EN_MULTILEVEL: str = """You are given a hierarchical knowledge structure with multiple levels. Your task is to generate a question and answer (QA) pair that traces properties or relationships through multiple levels of the hierarchy.

---Strict Format Requirements---
You MUST output in the following format (do NOT add any extra explanations, preambles, or meta-descriptions):
Question: [your question content]
Answer: [your answer content]
Hierarchical Reasoning: [brief explanation of the multi-level logic]

Important:
- Output only ONE QA pair
- Do NOT add phrases like "Based on the hierarchy" or "Here is" at the beginning
- Start directly with "Question:"

---Question Requirements---
1. Ask about relationships spanning multiple hierarchy levels
2. Focus on how properties propagate through levels
3. Use language like: "Trace the relationship from X to Z through Y", "How does property P change across levels?", "Explain the hierarchical path from X to Y"
4. Explore the depth of the hierarchy

---Answer Requirements---
1. Trace the property or relationship through each level
2. Explain what changes or stays the same at each level
3. Clarify the hierarchical connections
4. Be detailed and structured (aim for 4-6 sentences)

---Hierarchical Structure---
{context}

Generate a QA pair that explores multi-level relationships in this hierarchy.
"""

# Chinese templates
TEMPLATE_ZH_SIBLING: str = """给定一个层次化的知识结构，展示概念及其关系。你的任务是生成一个问答（QA）对，重点是比较同一层级的兄弟概念。

---严格格式要求---
必须严格按照以下格式输出（不要添加任何额外的说明、前言或元描述）：
问题：[你的问题内容]
答案：[你的答案内容]
层次推理：[简要解释所探索的层次关系]

注意：
- 只输出一个问答对
- 不要在开头添加"根据层次结构"、"以下是"等说明性文字
- 直接从"问题："开始输出

---问题要求---
1. 询问兄弟概念之间的差异或相似之处
2. 关注区分性属性或独特性质
3. 使用比较性语言："X和Y有什么不同？"、"X与Y的区别是什么？"、"从...角度比较X和Y"
4. 探索继承属性与独特特征

---答案要求---
1. 提供清晰的比较，突出关键差异和相似之处
2. 提及从父概念继承的属性
3. 识别每个兄弟概念特有的属性
4. 全面但聚焦于比较（建议3-5句话）

---层次结构---
{context}

生成一个探索此层次结构中兄弟概念关系的问答对。
"""

TEMPLATE_ZH_INHERITANCE: str = """给定一个层次化的知识结构，展示概念及其继承关系。你的任务是生成一个问答（QA）对，探索属性如何从父概念继承到子概念。

---严格格式要求---
必须严格按照以下格式输出（不要添加任何额外的说明、前言或元描述）：
问题：[你的问题内容]
答案：[你的答案内容]
层次推理：[简要解释继承逻辑]

注意：
- 只输出一个问答对
- 不要在开头添加"根据层次结构"、"以下是"等说明性文字
- 直接从"问题："开始输出

---问题要求---
1. 询问为什么子概念具有某些属性
2. 关注从父概念的继承
3. 使用语言如："为什么X具有属性P？"、"X如何继承...？"、"解释X与其父概念Y在...方面的关系"
4. 探索继承的逻辑链

---答案要求---
1. 解释从父到子的继承关系
2. 追踪属性在层次结构中的传递
3. 说明哪些属性来自哪个祖先
4. 清晰且合乎逻辑（建议3-5句话）

---层次结构---
{context}

生成一个探索此层次结构中继承关系的问答对。
"""

TEMPLATE_ZH_ABSTRACTION: str = """给定一个层次化的知识结构。你的任务是生成一个问答（QA）对，探索抽象和泛化 - 从子概念识别父类别。

---严格格式要求---
必须严格按照以下格式输出（不要添加任何额外的说明、前言或元描述）：
问题：[你的问题内容]
答案：[你的答案内容]
层次推理：[简要解释抽象逻辑]

注意：
- 只输出一个问答对
- 不要在开头添加"根据层次结构"、"以下是"等说明性文字
- 直接从"问题："开始输出

---问题要求---
1. 询问分类或泛化
2. 关注识别概念之间的共同属性
3. 使用语言如："X、Y和Z属于什么类别？"、"...的共同特征是什么？"、"对这些概念进行分类并解释原因"
4. 探索具体概念如何与抽象类别相关

---答案要求---
1. 识别父类别或共同抽象
2. 解释证明分类合理的共同属性
3. 如相关，提及区分特征
4. 清楚说明泛化逻辑（建议3-5句话）

---层次结构---
{context}

生成一个探索此层次结构中抽象和分类的问答对。
"""

TEMPLATE_ZH_MULTILEVEL: str = """给定一个多层次的知识结构。你的任务是生成一个问答（QA）对，追踪属性或关系在层次结构多个层级间的传递。

---严格格式要求---
必须严格按照以下格式输出（不要添加任何额外的说明、前言或元描述）：
问题：[你的问题内容]
答案：[你的答案内容]
层次推理：[简要解释多层次逻辑]

注意：
- 只输出一个问答对
- 不要在开头添加"根据层次结构"、"以下是"等说明性文字
- 直接从"问题："开始输出

---问题要求---
1. 询问跨越多个层次级别的关系
2. 关注属性如何在层级间传播
3. 使用语言如："追踪从X到Z经过Y的关系"、"属性P在各层级间如何变化？"、"解释从X到Y的层次路径"
4. 探索层次结构的深度

---答案要求---
1. 追踪属性或关系在每个层级的传递
2. 解释每个层级的变化或保持不变的内容
3. 阐明层次连接
4. 详细且结构化（建议4-6句话）

---层次结构---
{context}

生成一个探索此层次结构中多层次关系的问答对。
"""

# Export as dictionaries
HIERARCHICAL_GENERATION_PROMPT = {
    "en": {
        "sibling": TEMPLATE_EN_SIBLING,
        "inheritance": TEMPLATE_EN_INHERITANCE,
        "abstraction": TEMPLATE_EN_ABSTRACTION,
        "multilevel": TEMPLATE_EN_MULTILEVEL,
    },
    "zh": {
        "sibling": TEMPLATE_ZH_SIBLING,
        "inheritance": TEMPLATE_ZH_INHERITANCE,
        "abstraction": TEMPLATE_ZH_ABSTRACTION,
        "multilevel": TEMPLATE_ZH_MULTILEVEL,
    }
}
