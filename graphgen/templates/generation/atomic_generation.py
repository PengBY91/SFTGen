# pylint: disable=C0301
TEMPLATE_EN: str = """You are given a text passage. Your task is to generate a question and answer (QA) pair based on the content of that text.
The answer should be accurate and directly derived from the text. Make sure the QA pair is relevant to the main theme or important details of the given text. 
For example:
Question: What is the effect of overexpressing the BG1 gene on grain size and development?
Answer: Overexpression of the BG1 gene leads to significantly increased grain size, demonstrating its role in grain development.

Question: What role does TAC4 play in the gravitropism of rice shoots?
Answer: TAC4 is a key regulator of gravitropism in rice shoots, promoting the bending of shoots towards the gravity vector.

Here is the text passage you need to generate a QA pair for:
{context}
"""

TEMPLATE_ZH: str = """给定一个文本段落。你的任务是根据该文本的内容生成一个问答（QA）对。
答案应准确且直接从文本中得出。确保QA对与给定文本的主题或重要细节相关。
例如：
问题：过表达BG1基因对谷粒大小和发育有什么影响？
答案：BG1基因的过表达显著增加了谷粒大小，表明其在谷物发育中的作用。

问题：TAC4在水稻茎的重力性状中扮演什么角色？
答案：TAC4是水稻茎重力性状的关键调节因子，促进茎向重力矢量弯曲。

以下是你需要为其生成QA对的文本段落：
{context}
"""


# Alternative templates for diversity
TEMPLATE_EN_V2: str = """Based on the following text, create a question-answer pair that captures key information.

Guidelines:
- The question should be clear and specific
- The answer must be factual and based solely on the text
- Focus on important details or relationships mentioned

Text:
{context}

Generate one QA pair following this format:
Question: [your question]
Answer: [your answer]
"""

TEMPLATE_EN_V3: str = """Extract the most important information from this text and formulate it as a question-answer pair.

Requirements:
- Question should test understanding of the main content
- Answer should be concise and accurate
- Ensure the QA pair is informative

Text content:
{context}

Provide your QA pair:
Question: 
Answer: 
"""

TEMPLATE_ZH_V2: str = """根据以下文本，创建一个捕获关键信息的问答对。

要求：
- 问题应清晰具体
- 答案必须基于文本事实
- 关注文本中提到的重要细节或关系

文本：
{context}

生成一个问答对，格式如下：
问题：[你的问题]
答案：[你的答案]
"""

TEMPLATE_ZH_V3: str = """从这段文本中提取最重要的信息，并将其表述为一个问答对。

要求：
- 问题应测试对主要内容的理解
- 答案应简洁准确
- 确保问答对具有信息量

文本内容：
{context}

提供你的问答对：
问题：
答案：
"""

ATOMIC_GENERATION_PROMPT = {
    "en": TEMPLATE_EN,
    "zh": TEMPLATE_ZH,
}

# Multiple template variants for diversity
ATOMIC_GENERATION_PROMPT_VARIANTS = {
    "en": [TEMPLATE_EN, TEMPLATE_EN_V2, TEMPLATE_EN_V3],
    "zh": [TEMPLATE_ZH, TEMPLATE_ZH_V2, TEMPLATE_ZH_V3],
}
