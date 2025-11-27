# pylint: disable=C0301
ANSWER_REPHRASING_CONTEXT_EN: str = """---Role---
You are an NLP expert responsible for generating a logically structured and coherent rephrased version of the TEXT based on ENTITIES and RELATIONSHIPS provided below. You may refer to the original text to assist in generating the rephrased version, but ensure that the final output text meets the requirements.
Use English as output language.

---Goal---
To generate a version of the text that is rephrased and conveys the same meaning as the original entity and relationship descriptions, while:
1. Following a clear logical flow and structure
2. Establishing proper cause-and-effect relationships
3. Ensuring temporal and sequential consistency
4. Creating smooth transitions between ideas using conjunctions and appropriate linking words like "firstly," "however," "therefore," etc.
5. Providing comprehensive and detailed explanations (aim for 200-400 words or 5-10 sentences)
6. Enriching the content with relevant background knowledge, context, or related concepts when appropriate
7. Including relevant details, examples, implications, or broader connections to enhance understanding

---Instructions---
1. Analyze the provided ENTITIES and RELATIONSHIPS carefully to identify:
   - Key concepts and their hierarchies
   - Temporal sequences and chronological order
   - Cause-and-effect relationships
   - Dependencies between different elements

2. Organize the information in a logical sequence by:
   - Starting with foundational concepts
   - Building up to more complex relationships
   - Grouping related ideas together
   - Creating clear transitions between sections

3. Rephrase the text while maintaining:
   - Logical flow and progression
   - Clear connections between ideas
   - Proper context and background
   - Coherent narrative structure
   - Comprehensive detail and depth (200-400 words or 5-10 sentences)
   - Integration of relevant background knowledge or related concepts when appropriate

4. Enrich the text by:
   - Adding relevant details, examples, or implications
   - Providing broader context or connections to related topics
   - Explaining underlying mechanisms, processes, or relationships in more detail
   - Including practical implications or real-world applications when relevant

5. Review and refine the text to ensure:
   - Logical consistency throughout
   - Clear cause-and-effect relationships
   - Sufficient depth and comprehensiveness

################
-ORIGINAL TEXT-
################
{original_text}

################
-ENTITIES-
################
{entities}

################
-RELATIONSHIPS-
################
{relationships}

"""

ANSWER_REPHRASING_CONTEXT_ZH: str = """---角色---
你是一位NLP专家，负责根据下面提供的实体和关系生成逻辑结构清晰且连贯的文本重述版本。你可以参考原始文本辅助生成，但需要确保最终输出的文本符合要求。
使用中文作为输出语言。

---目标---
生成文本的重述版本，使其传达与原始实体和关系描述相同的含义，同时：
1. 遵循清晰的逻辑流和结构
2. 建立适当的因果关系
3. 确保时间和顺序的一致性
4. 使用连词和适当的连接词(如"首先"、"然而"、"因此"等)创造流畅的过渡
5. 提供全面且详细的解释
6. 在适当的时候利用相关背景知识、上下文或相关概念来丰富内容
7. 包含相关细节、例子、影响或更广泛的联系，以增强理解

---说明---
1. 仔细分析提供的实体和关系，以识别：
    - 关键概念及其层级关系
    - 时间序列和时间顺序
    - 因果关系
    - 不同元素之间的依赖关系
2. 通过以下方式将信息组织成逻辑顺序：
    - 从基础概念开始
    - 逐步建立更复杂的关系
    - 将相关的想法分组在一起
    - 在各部分之间创建清晰的过渡
3. 重述文本时保持：
    - 逻辑流畅
    - 概念之间的清晰联系
    - 适当的上下文和背景
    - 连贯的叙述结构
    - 全面详细的深度（200-400字或5-10句话）
    - 在适当的时候整合相关背景知识或相关概念

4. 通过以下方式丰富文本：
    - 添加相关细节、例子或影响
    - 提供更广泛的上下文或与相关主题的联系
    - 更详细地解释潜在的机制、过程或关系
    - 在相关时包含实际影响或现实应用

5. 检查和完善文本以确保：
    - 整体逻辑一致性
    - 清晰的因果关系
    - 足够的深度和全面性

################
-原始文本-
################
{original_text}

################
-实体-
################
{entities}

################
-关系-
################
{relationships}

"""

ANSWER_REPHRASING_EN: str = """---Role---
You are an NLP expert responsible for generating a logically structured and coherent rephrased version of the TEXT based on ENTITIES and RELATIONSHIPS provided below.
Use English as output language.

---Goal---
To generate a version of the text that is rephrased and conveys the same meaning as the original entity and relationship descriptions, while:
1. Following a clear logical flow and structure
2. Establishing proper cause-and-effect relationships
3. Ensuring temporal and sequential consistency
4. Creating smooth transitions between ideas using conjunctions and appropriate linking words like "firstly," "however," "therefore," etc.
5. Providing comprehensive and detailed explanations
6. Enriching the content with relevant background knowledge, context, or related concepts when appropriate
7. Including relevant details, examples, implications, or broader connections to enhance understanding

---Instructions---
1. Analyze the provided ENTITIES and RELATIONSHIPS carefully to identify:
   - Key concepts and their hierarchies
   - Temporal sequences and chronological order
   - Cause-and-effect relationships
   - Dependencies between different elements

2. Organize the information in a logical sequence by:
   - Starting with foundational concepts
   - Building up to more complex relationships
   - Grouping related ideas together
   - Creating clear transitions between sections

3. Rephrase the text while maintaining:
   - Logical flow and progression
   - Clear connections between ideas
   - Proper context and background
   - Coherent narrative structure
   - Comprehensive detail and depth (200-400 words or 5-10 sentences)
   - Integration of relevant background knowledge or related concepts when appropriate

4. Enrich the text by:
   - Adding relevant details, examples, or implications
   - Providing broader context or connections to related topics
   - Explaining underlying mechanisms, processes, or relationships in more detail
   - Including practical implications or real-world applications when relevant

5. Review and refine the text to ensure:
   - Logical consistency throughout
   - Clear cause-and-effect relationships
   - Sufficient depth and comprehensiveness

################
-ENTITIES-
################
{entities}

################
-RELATIONSHIPS-
################
{relationships}

"""

ANSWER_REPHRASING_ZH: str = """---角色---
你是一位NLP专家，负责根据下面提供的实体和关系生成逻辑结构清晰且连贯的文本重述版本。
使用中文作为输出语言。

---目标---
生成文本的重述版本，使其传达与原始实体和关系描述相同的含义，同时：
1. 遵循清晰的逻辑流和结构
2. 建立适当的因果关系
3. 确保时间和顺序的一致性
4. 使用连词和适当的连接词(如"首先"、"然而"、"因此"等)创造流畅的过渡
5. 提供全面且详细的解释
6. 在适当的时候利用相关背景知识、上下文或相关概念来丰富内容
7. 包含相关细节、例子、影响或更广泛的联系，以增强理解

---说明---
1. 仔细分析提供的实体和关系，以识别：
    - 关键概念及其层级关系
    - 时间序列和时间顺序
    - 因果关系
    - 不同元素之间的依赖关系
2. 通过以下方式将信息组织成逻辑顺序：
    - 从基础概念开始
    - 逐步建立更复杂的关系
    - 将相关的想法分组在一起
    - 在各部分之间创建清晰的过渡
3. 重述文本时保持：
    - 逻辑流畅
    - 概念之间的清晰联系
    - 适当的上下文和背景
    - 连贯的叙述结构
    - 全面详细的深度
    - 在适当的时候整合相关背景知识或相关概念

4. 通过以下方式丰富文本：
    - 添加相关细节、例子或影响
    - 提供更广泛的上下文或与相关主题的联系
    - 更详细地解释潜在的机制、过程或关系
    - 在相关时包含实际影响或现实应用

5. 检查和完善文本以确保：
    - 整体逻辑一致性
    - 清晰的因果关系
    - 足够的深度和全面性

################
-实体-
################
{entities}

################
-关系-
################
{relationships}

"""

REQUIREMENT_ZH = """
################
请在下方直接输出连贯的重述文本，不要输出任何额外的内容。

重述文本:
"""

REQUIREMENT_EN = """
################
Please directly output the coherent rephrased text below, without any additional content.

Rephrased Text:
"""

QUESTION_GENERATION_EN: str = """The answer to a question is provided. Please generate a question that corresponds to the answer.

################
Answer:
{answer}
################
Question:
"""

QUESTION_GENERATION_ZH: str = """下面提供了一个问题的答案，请生成一个与答案对应的问题。

################
答案：
{answer}
################
问题：
"""

# 合并的 Aggregated 提示词（一次性生成重述文本和问题）
AGGREGATED_COMBINED_EN = """You are an NLP expert responsible for generating a logically structured and coherent rephrased version of the text based on ENTITIES and RELATIONSHIPS provided below, and then generating a relevant question based on the rephrased text.

---Goal---
1. Generate a rephrased version of the text that conveys the same meaning as the original entity and relationship descriptions, while:
   - Following a clear logical flow and structure
   - Establishing proper cause-and-effect relationships
   - Ensuring temporal and sequential consistency
   - Creating smooth transitions between ideas using conjunctions and appropriate linking words
   - Providing comprehensive and detailed explanations
   - Enriching the content with relevant background knowledge, context, or related concepts when appropriate
   - Including relevant details, examples, implications, or broader connections to enhance understanding

2. Generate a relevant question that corresponds to the rephrased text (which serves as the answer).

---Instructions---
1. Analyze the provided ENTITIES and RELATIONSHIPS carefully to identify:
   - Key concepts and their hierarchies
   - Temporal sequences and chronological order
   - Cause-and-effect relationships
   - Dependencies between different elements

2. Organize the information in a logical sequence by:
   - Starting with foundational concepts
   - Building up to more complex relationships
   - Grouping related ideas together
   - Creating clear transitions between sections

3. Rephrase the text while maintaining:
   - Logical flow and progression
   - Clear connections between ideas
   - Proper context and background
   - Coherent narrative structure
   - Comprehensive detail and depth
   - Integration of relevant background knowledge or related concepts when appropriate

4. Enrich the rephrased text by:
   - Adding relevant details, examples, or implications
   - Providing broader context or connections to related topics
   - Explaining underlying mechanisms, processes, or relationships in more detail
   - Including practical implications or real-world applications when relevant

5. Generate a question that:
   - Corresponds to the rephrased text (answer)
   - Is clear and specific
   - Can be answered using the rephrased text

---Strict Output Format---
You MUST output in the following format (do NOT add any extra explanations, preambles, or meta-descriptions):

Rephrased Text:
[Your rephrased text here]

Question:
[Your question here]

Important:
- Start directly with "Rephrased Text:"
- Do NOT add phrases like "Here is", "Based on", or "Below is" at the beginning

---Input---
################
-ENTITIES-
################
{entities}

################
-RELATIONSHIPS-
################
{relationships}
"""

AGGREGATED_COMBINED_ZH = """你是一位NLP专家，负责根据下面提供的实体和关系生成逻辑结构清晰且连贯的文本重述版本，然后基于重述文本生成相关问题。

---目标---
1. 生成文本的重述版本，使其传达与原始实体和关系描述相同的含义，同时：
   - 遵循清晰的逻辑流和结构
   - 建立适当的因果关系
   - 确保时间和顺序的一致性
   - 使用连词和适当的连接词创造流畅的过渡
   - 提供全面且详细的解释
   - 在适当的时候利用相关背景知识、上下文或相关概念来丰富内容
   - 包含相关细节、例子、影响或更广泛的联系，以增强理解

2. 生成一个与重述文本（作为答案）对应的问题。

---说明---
1. 仔细分析提供的实体和关系，以识别：
   - 关键概念及其层级关系
   - 时间序列和时间顺序
   - 因果关系
   - 不同元素之间的依赖关系

2. 通过以下方式将信息组织成逻辑顺序：
   - 从基础概念开始
   - 逐步建立更复杂的关系
   - 将相关的想法分组在一起
   - 在各部分之间创建清晰的过渡

3. 重述文本时保持：
   - 逻辑流畅
   - 概念之间的清晰联系
   - 适当的上下文和背景
   - 连贯的叙述结构
   - 全面详细的深度
   - 在适当的时候整合相关背景知识或相关概念

4. 通过以下方式丰富重述文本：
   - 添加相关细节、例子或影响
   - 提供更广泛的上下文或与相关主题的联系
   - 更详细地解释潜在的机制、过程或关系
   - 在相关时包含实际影响或现实应用

5. 生成问题时确保：
   - 与重述文本（答案）对应
   - 清晰具体
   - 可以用重述文本回答

---严格输出格式---
必须严格按照以下格式输出（不要添加任何额外的说明、前言或元描述）：

重述文本:
[你的重述文本]

问题:
[你的问题]

注意：
- 直接从"重述文本:"开始输出
- 不要添加"以下是"、"根据"等说明性文字

---输入---
################
-实体-
################
{entities}

################
-关系-
################
{relationships}
"""

AGGREGATED_GENERATION_PROMPT = {
    "en": {
        "ANSWER_REPHRASING": ANSWER_REPHRASING_EN + REQUIREMENT_EN,
        "ANSWER_REPHRASING_CONTEXT": ANSWER_REPHRASING_CONTEXT_EN + REQUIREMENT_EN,
        "QUESTION_GENERATION": QUESTION_GENERATION_EN,
        "AGGREGATED_COMBINED": AGGREGATED_COMBINED_EN,  # 新增：合并模式
    },
    "zh": {
        "ANSWER_REPHRASING": ANSWER_REPHRASING_ZH + REQUIREMENT_ZH,
        "ANSWER_REPHRASING_CONTEXT": ANSWER_REPHRASING_CONTEXT_ZH + REQUIREMENT_ZH,
        "QUESTION_GENERATION": QUESTION_GENERATION_ZH,
        "AGGREGATED_COMBINED": AGGREGATED_COMBINED_ZH,  # 新增：合并模式
    },
}
