# pylint: disable=C0301
TEMPLATE_ZH: str = """请基于以下知识子图生成多跳推理问题和答案。你将获得一个知识子图，其中包含一系列实体、关系和事实。你的任务是提出一个问题，该问题需要经过多次推理才能回答。问题的答案应该是从给定的知识子图中推断出来的。确保问题的难度适中，需要多步推理才能回答。

输出格式要求：
问题：[你的问题]
答案：[你的答案]
推理路径：[说明从哪些实体和关系出发，经过哪些推理步骤得到答案，例如：实体A → 关系1 → 实体B → 关系2 → 答案]

例如：
########
--实体--
1. 苹果
2. 水果
3. 维生素C
########
--关系--
1. 苹果-水果：苹果是一种水果
2. 水果-维生素C：水果中富含维生素C
########
问题：通过吃苹果补充的什么物质，有助于维持健康？
答案：维生素C
推理路径：苹果 → 苹果是一种水果 → 水果 → 水果中富含维生素C → 维生素C
########

#########
--实体--
{entities}
#########
--关系--
{relationships}
#########
请按照上述格式输出，包含问题、答案和推理路径，请不要直接复制示例问题和答案，不要输出无关内容。
"""

TEMPLATE_EN: str = """Please generate a multi-hop reasoning question and answer based on the following knowledge subgraph. You will be provided with a knowledge subgraph that contains a series of entities, relations, and facts. Your task is to generate a question that requires multiple steps of reasoning to answer. The answer to the question should be inferred from the given knowledge subgraph. Ensure that the question is of moderate difficulty and requires multiple steps of reasoning to answer.

Output format required:
Question: [your question]
Answer: [your answer]
Reasoning Path: [explain the reasoning steps from which entities and relations you start, through which steps you reach the answer, e.g., Entity A → Relation 1 → Entity B → Relation 2 → Answer]

For example:
########
--Entities--
1. Apple
2. Fruit
3. Vitamin C
########
--Relations--
1. Apple-Fruit: Apple is a type of fruit
2. Fruit-Vitamin C: Fruits are rich in Vitamin C
########
Question: What substance, obtained through eating apples, helps maintain health?
Answer: Vitamin C
Reasoning Path: Apple → Apple is a type of fruit → Fruit → Fruits are rich in Vitamin C → Vitamin C
########

########
--Entities--
{entities}
########
--Relations--
{relationships}
########
Please output in the format above, including Question, Answer, and Reasoning Path. Do not copy the example question and answer directly, and do not provide irrelevant information.
"""

MULTI_HOP_GENERATION_PROMPT = {"en": TEMPLATE_EN, "zh": TEMPLATE_ZH}
