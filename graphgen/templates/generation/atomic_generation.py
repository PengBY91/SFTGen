# pylint: disable=C0301
TEMPLATE_EN: str = """You are given a text passage. Your task is to generate a question and answer (QA) pair based on the content of that text.
The answer should be accurate and directly derived from the text. Make sure the QA pair is relevant to the main theme or important details of the given text.

---Strict Format Requirements---
You MUST output in the following format (do NOT add any extra explanations, preambles, or meta-descriptions):
Question: [your question content]
Answer: [your answer content]

Important:
- Output only ONE QA pair
- Do NOT add phrases like "Based on the text" or "Here is" at the beginning
- Start directly with "Question:"

---Answer Requirements---
1. The answer should be comprehensive and detailed (aim for 3-5 sentences or 100-200 words).
2. While primarily based on the provided text, you may enrich the answer with relevant background knowledge, context, or related concepts that help explain the topic more thoroughly.
3. Include relevant details, examples, or implications when appropriate to make the answer more informative and valuable.
4. Ensure the answer is well-structured, coherent, and provides sufficient depth for understanding the topic.

For example:
Question: What is the effect of overexpressing the BG1 gene on grain size and development?
Answer: Overexpression of the BG1 gene leads to significantly increased grain size, demonstrating its role in grain development. This genetic modification enhances the expression levels of BG1, which is a key regulator in the grain development pathway. The increased grain size is typically observed through enhanced cell division and expansion processes in the grain tissues. This finding has important implications for agricultural biotechnology, as it suggests potential strategies for improving crop yields through targeted genetic interventions.

Question: What role does TAC4 play in the gravitropism of rice shoots?
Answer: TAC4 is a key regulator of gravitropism in rice shoots, promoting the bending of shoots towards the gravity vector. This protein functions as part of the plant's response mechanism to gravitational forces, coordinating cellular and molecular processes that enable directional growth. The gravitropic response is essential for proper plant orientation and growth, allowing plants to optimize their positioning for light capture and resource acquisition. Understanding TAC4's role provides insights into how plants sense and respond to environmental cues.

Here is the text passage you need to generate a QA pair for:
{context}

{hierarchical_context}
"""

TEMPLATE_ZH: str = """给定一个文本段落。你的任务是根据该文本的内容生成一个问答（QA）对。
答案应准确且直接从文本中得出。确保QA对与给定文本的主题或重要细节相关。

---严格格式要求---
必须严格按照以下格式输出（不要添加任何额外的说明、前言或元描述）：
问题：[你的问题内容]
答案：[你的答案内容]

注意：
- 只输出一个问答对
- 不要在开头添加"根据文本"、"以下是"等说明性文字
- 直接从"问题："开始输出

---答案要求---
1. 答案应当全面且详细。
2. 虽然主要基于提供的文本，但你可以利用相关的背景知识、上下文或相关概念来丰富答案，使解释更加透彻。
3. 在适当的时候包含相关细节、例子或影响，使答案更具信息量和价值。
4. 确保答案结构清晰、连贯，并提供足够的深度以便理解主题。

例如：
问题：过表达BG1基因对谷粒大小和发育有什么影响？
答案：BG1基因的过表达显著增加了谷粒大小，表明其在谷物发育中的作用。这种基因修饰增强了BG1的表达水平，而BG1是谷物发育通路中的关键调节因子。增加的谷粒大小通常通过增强谷粒组织中的细胞分裂和扩张过程来体现。这一发现对农业生物技术具有重要意义，因为它表明通过定向基因干预来改善作物产量的潜在策略。

问题：TAC4在水稻茎的重力性状中扮演什么角色？
答案：TAC4是水稻茎重力性状的关键调节因子，促进茎向重力矢量弯曲。该蛋白质作为植物对重力响应机制的一部分，协调使定向生长成为可能的细胞和分子过程。重力响应对于植物的正确定向和生长至关重要，使植物能够优化其位置以捕获光线和获取资源。理解TAC4的作用为植物如何感知和响应环境线索提供了见解。

以下是你需要为其生成QA对的文本段落：
{context}

{hierarchical_context}
"""

TEMPLATE_ZH_CHINESE_ONLY: str = """给定一个文本段落。你的任务是根据该文本的内容生成一个问答（QA）对。
答案应准确且直接从文本中得出。确保QA对与给定文本的主题或重要细节相关。

---严格语言要求---
【重要】你生成的问题和答案必须完全使用中文，不能包含任何英文单词或字母（除非是专有名词、缩写或无法翻译的术语）。
如果原文包含英文内容，必须将其翻译成中文后再使用。

---严格格式要求---
必须严格按照以下格式输出（不要添加任何额外的说明、前言或元描述）：
问题：[你的中文问题内容]
答案：[你的中文答案内容]

注意：
- 只输出一个问答对
- 不要在开头添加"根据文本"、"以下是"等说明性文字
- 直接从"问题："开始输出
- 问题和答案必须完全使用中文

---答案要求---
1. 答案应当全面且详细。
2. 虽然主要基于提供的文本，但你可以利用相关的背景知识、上下文或相关概念来丰富答案，使解释更加透彻。
3. 在适当的时候包含相关细节、例子或影响，使答案更具信息量和价值。
4. 确保答案结构清晰、连贯，并提供足够的深度以便理解主题。
5. 答案必须使用中文表述。

例如：
问题：过表达BG1基因对谷粒大小和发育有什么影响？
答案：BG1基因的过表达显著增加了谷粒大小，表明其在谷物发育中的作用。这种基因修饰增强了BG1的表达水平，而BG1是谷物发育通路中的关键调节因子。增加的谷粒大小通常通过增强谷粒组织中的细胞分裂和扩张过程来体现。这一发现对农业生物技术具有重要意义，因为它表明通过定向基因干预来改善作物产量的潜在策略。

问题：TAC4在水稻茎的重力性状中扮演什么角色？
答案：TAC4是水稻茎重力性状的关键调节因子，促进茎向重力矢量弯曲。该蛋白质作为植物对重力响应机制的一部分，协调使定向生长成为可能的细胞和分子过程。重力响应对于植物的正确定向和生长至关重要，使植物能够优化其位置以捕获光线和获取资源。理解TAC4的作用为植物如何感知和响应环境线索提供了见解。

以下是你需要为其生成QA对的文本段落：
{context}

{hierarchical_context}
"""


# Alternative templates for diversity
TEMPLATE_EN_V2: str = """Based on the following text, create a question-answer pair that captures key information.

---Strict Format Requirements---
Output directly in this format (do NOT add explanatory text):
Question: [your question]
Answer: [your comprehensive answer]

Guidelines:
- The question should be clear and specific
- The answer must be factual and primarily based on the text, but you may enrich it with relevant background knowledge
- Focus on important details or relationships mentioned
- The answer should be comprehensive, providing sufficient detail and context
- Include relevant examples, implications, or related concepts when appropriate to enhance understanding

Text:
{context}

{hierarchical_context}
"""

TEMPLATE_EN_V3: str = """Extract the most important information from this text and formulate it as a question-answer pair.

---Strict Format Requirements---
Output directly in this format (do NOT add meta-descriptions or explanations):
Question: [your question]
Answer: [your answer]

Requirements:
- Question should test understanding of the main content
- Answer should be detailed, comprehensive, and accurate (aim for 3-5 sentences or 100-200 words)
- While based on the text, enrich the answer with relevant background knowledge, context, or related concepts
- Include relevant details, examples, or implications to make the answer more informative and valuable
- Ensure the QA pair is informative and provides sufficient depth

Text content:
{context}

{hierarchical_context}
"""

TEMPLATE_ZH_V2: str = """根据以下文本，创建一个捕获关键信息的问答对。

---严格格式要求---
直接输出以下格式（不要添加说明性文字）：
问题：[你的问题]
答案：[你的全面答案]

要求：
- 问题应清晰具体
- 答案必须基于文本事实，但可以利用相关背景知识丰富答案
- 关注文本中提到的重要细节或关系
- 答案应当全面，提供足够的细节和上下文
- 在适当的时候包含相关例子、影响或相关概念，以增强理解

文本：
{context}

{hierarchical_context}
"""

TEMPLATE_ZH_V3: str = """从这段文本中提取最重要的信息，并将其表述为一个问答对。

---严格格式要求---
必须直接输出以下格式（不要添加任何元描述或说明）：
问题：[你的问题]
答案：[你的答案]

要求：
- 问题应测试对主要内容的理解
- 答案应详细、全面且准确
- 虽然基于文本，但可以利用相关背景知识、上下文或相关概念来丰富答案
- 包含相关细节、例子或影响，使答案更具信息量和价值
- 确保问答对具有信息量并提供足够的深度

文本内容：
{context}

{hierarchical_context}
"""

TEMPLATE_ZH_V2_CHINESE_ONLY: str = """根据以下文本，创建一个捕获关键信息的问答对。

---严格语言要求---
【重要】你生成的问题和答案必须完全使用中文，不能包含任何英文单词或字母（除非是专有名词、缩写或无法翻译的术语）。

---严格格式要求---
直接输出以下格式（不要添加说明性文字）：
问题：[你的中文问题]
答案：[你的中文全面答案]

要求：
- 问题应清晰具体
- 答案必须基于文本事实，但可以利用相关背景知识丰富答案
- 关注文本中提到的重要细节或关系
- 答案应当全面，提供足够的细节和上下文
- 在适当的时候包含相关例子、影响或相关概念，以增强理解
- 问题和答案必须完全使用中文

文本：
{context}

{hierarchical_context}
"""

TEMPLATE_ZH_V3_CHINESE_ONLY: str = """从这段文本中提取最重要的信息，并将其表述为一个问答对。

---严格语言要求---
【重要】你生成的问题和答案必须完全使用中文，不能包含任何英文单词或字母（除非是专有名词、缩写或无法翻译的术语）。

---严格格式要求---
必须直接输出以下格式（不要添加任何元描述或说明）：
问题：[你的中文问题]
答案：[你的中文答案]

要求：
- 问题应测试对主要内容的理解
- 答案应详细、全面且准确
- 虽然基于文本，但可以利用相关背景知识、上下文或相关概念来丰富答案
- 包含相关细节、例子或影响，使答案更具信息量和价值
- 确保问答对具有信息量并提供足够的深度
- 问题和答案必须完全使用中文

文本内容：
{context}

{hierarchical_context}
"""

ATOMIC_GENERATION_PROMPT = {
    "en": TEMPLATE_EN,
    "zh": TEMPLATE_ZH,
}

# Prompt for Chinese-only generation
ATOMIC_GENERATION_PROMPT_CHINESE_ONLY = {
    "zh": TEMPLATE_ZH_CHINESE_ONLY,
}

# Multiple template variants for diversity
ATOMIC_GENERATION_PROMPT_VARIANTS = {
    "en": [TEMPLATE_EN, TEMPLATE_EN_V2, TEMPLATE_EN_V3],
    "zh": [TEMPLATE_ZH, TEMPLATE_ZH_V2, TEMPLATE_ZH_V3],
}

# Chinese-only variants
ATOMIC_GENERATION_PROMPT_VARIANTS_CHINESE_ONLY = {
    "zh": [TEMPLATE_ZH_CHINESE_ONLY, TEMPLATE_ZH_V2_CHINESE_ONLY, TEMPLATE_ZH_V3_CHINESE_ONLY],
}

# Question-only prompts for two-stage generation
ATOMIC_QUESTION_PROMPT = {
    "en": """You are given a text passage. Create ONE concise question that captures the most important fact from the text.
Important Guidelines:
- MUST only output a single line starting with `Question:`
- Do NOT provide the answer
- Do NOT output `Answer:` or `A:` markers
- Avoid repeating previously generated questions
- Only output the question, nothing else

Text:
{context}

{hierarchical_context}
""",
    "zh": """给定一段文本。请提出一个能够体现关键信息的简洁问题。
重要要求：
- 必须仅输出以"问题："开头的一行
- 绝对不要提供答案
- 不要输出"答案："或"Answer:"标记
- 尽量避免与已生成的问题重复
- 只输出问题，不要输出其他内容

文本：
{context}

{hierarchical_context}
""",
}

# Chinese-only question prompts
ATOMIC_QUESTION_PROMPT_CHINESE_ONLY = {
    "zh": """给定一段文本。请提出一个能够体现关键信息的简洁问题。
【重要】问题必须完全使用中文，不能包含任何英文单词或字母（除非是专有名词、缩写或无法翻译的术语）。

重要要求：
- 必须仅输出以"问题："开头的一行
- 绝对不要提供答案
- 不要输出"答案："或"Answer:"标记
- 尽量避免与已生成的问题重复
- 只输出问题，不要输出其他内容
- 问题必须使用中文

文本：
{context}

{hierarchical_context}
""",
}

# Answer-only prompts for two-stage generation
ATOMIC_ANSWER_PROMPT = {
    "en": """You are given a question that should be answered based on the following text.
While primarily based on the provided text, you may enrich your answer with relevant background knowledge, context, or related concepts to provide a more comprehensive response.

Requirements:
- Start with `Answer:` followed by a comprehensive answer (3-5 sentences or 100-200 words)
- The answer should be detailed, well-structured, and provide sufficient depth
- Include relevant details, examples, or implications when appropriate
- Ensure the answer is coherent and informative

Text:
{context}

{hierarchical_context}

Question: {question}
""",
    "zh": """你将根据下面的文本回答给定的问题。
虽然主要基于提供的文本，但你可以利用相关背景知识、上下文或相关概念来丰富答案，提供更全面的回答。

要求：
- 以"答案："开头，后跟全面的答案（3-5句话或100-200字）
- 答案应当详细、结构清晰，并提供足够的深度
- 在适当的时候包含相关细节、例子或影响
- 确保答案连贯且具有信息量

文本：
{context}

{hierarchical_context}

问题：{question}
""",
}

# Chinese-only answer prompts
ATOMIC_ANSWER_PROMPT_CHINESE_ONLY = {
    "zh": """你将根据下面的文本回答给定的问题。
【重要】答案必须完全使用中文，不能包含任何英文单词或字母（除非是专有名词、缩写或无法翻译的术语）。
虽然主要基于提供的文本，但你可以利用相关背景知识、上下文或相关概念来丰富答案，提供更全面的回答。

要求：
- 以"答案："开头，后跟全面的答案（3-5句话或100-200字）
- 答案应当详细、结构清晰，并提供足够的深度
- 在适当的时候包含相关细节、例子或影响
- 确保答案连贯且具有信息量
- 答案必须使用中文

文本：
{context}

{hierarchical_context}

问题：{question}
""",
}

