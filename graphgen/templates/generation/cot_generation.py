COT_GENERATION_ZH = """根据给定的知识图谱原始信息及已生成的推理路径，产出一条符合模板要求、可直接用于下游训练或推理的 CoT 数据。\
CoT（Chain-of-Thought，思维链）指在回答复杂问题时，把中间推理步骤一步一步显式写出来，使推理过程透明、可追溯，而不是直接给出最终答案。

-输入格式-
[Entities:]
(实体名:实体描述)
...

[Relationships:]
(来源实体)-[关系描述]->(目标实体)
...

[Question and Reasoning Path:]
(问题)
(推理路径)

-输出要求-
1. 使用自然的思考语言，如"好的，让我们来思考一下"、"现在来分析"、"想想看"等开头。
2. 采用第一人称或引导性视角，模拟真实的思考过程。
3. 使用自然的过渡性语句（如"现在"、"那么"、"因此"、"这意味着"）连接思路。
4. 展现推理过程中的分析和判断（如"这表明..."、"很可能..."、"如果...那么..."）。
5. 不要使用有序列表或编号，保持段落式的自然流动。
6. 使用中文，采用口语化、日常思考的表达方式。
7. 答案应当全面且详细，提供足够的深度和细节。
8. 在遵循推理路径的基础上，可以利用相关背景知识、上下文或相关概念来丰富答案。
9. 在适当的时候包含相关细节、例子、影响或更广泛的联系，使答案更具信息量和价值。
10. 确保每一步推理都充分展开，像在向他人解释你的思考过程一样自然流畅。

-真实数据-
输入:
[Entities:]:
{entities}

[Relationships:]:
{relationships}

[Question:]:
{question}

[Reasoning_Template:]:
{reasoning_template}

输出：

"""

COT_GENERATION_EN = """Given the raw knowledge graph information and the provided reasoning-path, \
produce one Chain-of-Thought (CoT) sample that strictly follows the template \
and can be directly used for downstream training or inference.
CoT (Chain-of-Thought) means that when answering a complex question, the intermediate reasoning steps are \
explicitly written out one by one, making the reasoning process transparent and traceable instead of giving \
only the final answer.

-Input Format-
[Entities:]:
(ENTITY_NAME: ENTITY_DESCRIPTION)
...

[Relationships:]:
(ENTITY_SOURCE)-[RELATIONSHIP_DESCRIPTION]->(ENTITY_TARGET)
...

[Question and Reasoning Path:]:
(QUESTION)
(REASONING_PATH)

-Output Requirements-
1. Use natural thinking language, starting with phrases like "Okay, let me think about this", "Let's analyze", "Let's consider".
2. Adopt a first-person or guiding perspective to simulate a real thought process.
3. Use natural transitional phrases (e.g., "Now", "So", "Therefore", "This means") to connect ideas.
4. Show analysis and judgment in the reasoning process (e.g., "This suggests...", "It's likely that...", "If... then...").
5. Do not use ordered lists or numbering; maintain natural paragraph flow.
6. Use English with a conversational, everyday thinking style.
7. The answer should be comprehensive and detailed, providing sufficient depth and detail.
8. While following the reasoning path, enrich the answer with relevant background knowledge, context, or related concepts.
9. Include relevant details, examples, implications, or broader connections when appropriate to make the answer more informative and valuable.
10. Ensure each reasoning step is fully developed, as if naturally explaining your thought process to someone.

-Real Data-
Input:
[Entities:]:
{entities}

[Relationships:]:
{relationships}

[Question:]:
{question}

[Reasoning_Template:]:
{reasoning_template}

Output:
"""

COT_TEMPLATE_DESIGN_ZH = """你是一位“元推理架构师”。你的任务不是回答问题，\
而是根据给定的知识图谱中的实体和关系的名称以及描述信息，设计一条可复用、可泛化的 CoT 推理路径模板。\

-步骤-
1. 实体识别
- 准确地识别[Entities:]章节中的实体信息，包括实体名、实体描述信息。
- 实体信息的一般格式为:
(实体名:实体描述)

2. 关系识别
- 准确地识别[Relationships:]章节中的关系信息，包括来源实体名、目标实体名、关系描述信息。
- 关系信息的一般格式为:
(来源实体名)-[关系描述]->(目标实体名)

3. 图结构理解
- 正确地将关系信息中的来源实体名与实体信息关联。
- 根据提供的关系信息还原出图结构。

4. 问题设计
- 围绕知识图谱所表达的“核心主题”设计一个问题。
- 问题必须能在图谱内部通过实体、关系或属性直接验证；避免主观判断。
- 问题应该能够模型足够的思考，充分利用图谱中的实体和关系，避免过于简单或无关的问题。

5. 推理路径生成
- 根据问题设计一个**可被后续模型直接执行的推理蓝图**。
- 保持步骤最小化：每一步只解决一个“不可分割”的子问题。 

-约束条件-
1. 不要在回答中描述你的思考过程，直接给出回复，只给出问题和推理路径设计，不要生成无关信息。
2. 如果提供的描述信息相互矛盾，请解决矛盾并提供一个单一、连贯的逻辑。
3. 避免使用停用词和过于常见的词汇。
4. 不要出现具体数值或结论，不要出现“识别实体”、“识别关系”这类无意义的操作描述。
5. 使用中文作为输出语言。
6. 输出格式为：
问题：
推理路径设计：

-真实数据-
输入:
[Entities:]:
{entities}

[Relationships:]:
{relationships}

输出:
"""


COT_TEMPLATE_DESIGN_EN = """You are a “meta-reasoning architect”. \
Your task is NOT to answer the question, but to design a reusable, generalizable CoT reasoning-path \
template based solely on the names and descriptions of entities and \
relationships in the provided knowledge graph.

- Steps -
1. Entity Recognition
- Accurately recognize entity information in the [Entities:] section, including entity names and descriptions.
- The general formats for entity information are:
(ENTITY_NAME: ENTITY_DESCRIPTION)

2. Relationship Recognition
- Accurately recognize relationship information in the [Relationships:] section, including source_entity_name, target_entity_name, and relationship descriptions.
- The general formats for relationship information are:
(SOURCE_ENTITY_NAME)-[RELATIONSHIP_DESCRIPTION]->(TARGET_ENTITY_NAME)

3. Graph Structure Understanding
- Correctly associate the source entity name in the relationship information with the entity information.
- Reconstruct the graph structure based on the provided relationship information.

4. Question Design
- Design a question around the "core theme" expressed by the knowledge graph.
- The question must be verifiable directly within the graph through entities, relationships, or attributes; avoid subjective judgments.
- The question should allow the model to think sufficiently, fully utilizing the entities and relationships in the graph, avoiding overly simple or irrelevant questions.

5. Reasoning-Path Design 
- Output a **blueprint that any later model can directly execute**.
- Keep steps minimal: each step solves one indivisible sub-problem.


- Constraints -
1. Do NOT describe your thinking; output only the reasoning-path design.
2. If the provided descriptions are contradictory, resolve conflicts and provide a single coherent logic.
3. Avoid using stop words and overly common words.
4. Do not include specific numerical values or conclusions, \
and DO NOT describing meaningless operations like "Identify the entity" or "Identify the relationship".
5. Use English as the output language.
6. The output format is:
Question:
Reasoning-Path Design:

Please summarize the information expressed by the knowledge graph based on the following [Entities:] and [Relationships:] provided.

- Real Data -
Input:
[Entities:]:
{entities}

[Relationships:]:
{relationships}

Output:
"""

# 合并的 CoT 提示词（一次性生成问题和答案）
COT_COMBINED_EN = """You are a "meta-reasoning architect" and a "CoT data generator". 
Your task is to design a Chain-of-Thought (CoT) reasoning path template AND generate a complete CoT answer based on the provided knowledge graph.

Chain-of-Thought (CoT) means that when answering a complex question, the intermediate reasoning steps are explicitly written out one by one, making the reasoning process transparent and traceable instead of giving only the final answer.

--- Steps ---
1. Entity Recognition
   - Accurately recognize entity information in the [Entities:] section, including entity names and descriptions.

2. Relationship Recognition
   - Accurately recognize relationship information in the [Relationships:] section, including source_entity_name, target_entity_name, and relationship descriptions.

3. Graph Structure Understanding
   - Correctly associate the source entity name in the relationship information with the entity information.
   - Reconstruct the graph structure based on the provided relationship information.

4. Question Design
   - Design a question around the "core theme" expressed by the knowledge graph.
   - The question must be verifiable directly within the graph through entities, relationships, or attributes; avoid subjective judgments.
   - The question should allow the model to think sufficiently, fully utilizing the entities and relationships in the graph, avoiding overly simple or irrelevant questions.

5. Reasoning-Path Design
   - Design a concise reasoning blueprint that outlines the key steps to solve the problem.
   - Keep steps minimal: each step solves one indivisible sub-problem.

6. CoT Thinking Process Generation (Important: Simulate natural thinking process)
   - Start with first-person or guiding language (e.g., "Okay, let me think about this", "Let's analyze this").
   - Use natural transitional phrases to connect ideas (e.g., "Now", "So", "Let's think about", "Therefore", "This means").
   - Adopt a conversational, everyday thinking style rather than mechanical step listings.
   - Show the reasoning and analysis in your thought process (e.g., "This suggests...", "It's likely that...", "If... then...").
   - Do not use ordered lists or numbering; maintain natural paragraph flow.
   - The thinking process should be comprehensive and detailed, providing sufficient depth and detail.
   - While following the reasoning path, enrich the thinking with relevant background knowledge, context, or related concepts when appropriate.
   - Include relevant details, examples, implications, or broader connections to make the thinking more informative and valuable.
   - Ensure each reasoning step is fully developed, as if naturally explaining your thought process to someone.

7. Final Answer Generation
   - After the thinking process, provide a complete final answer.
   - The final answer should directly answer the question without including the thinking process.
   - The length of the answer should be determined by the complexity of the question and the depth of thinking.
   - The answer should be clear, accurate, and complete, fully addressing all aspects of the question.
   - It can be a brief conclusion or a detailed explanation, as long as it is comprehensive and accurate.

--- Constraints ---
1. Use English as the output language.
2. Do not describe your thinking process; output only the question, reasoning path, and answer.
3. Avoid using stop words and overly common words in the reasoning path.
4. Do not include specific numerical values or conclusions in the reasoning path, and DO NOT describe meaningless operations like "Identify the entity" or "Identify the relationship".

--- Strict Output Format ---
You MUST output in the following format (do NOT add any extra explanations, preambles, or meta-descriptions):

Question:
[Your question here]

Reasoning-Path Design:
[Your reasoning path template here]

Thinking Process:
[Detailed thinking process following the reasoning path, using natural thinking language like "Okay, let me think about this...", "Let's analyze...", showing the complete reasoning]

Final Answer:
[Complete answer that directly addresses the question, without the thinking process. The length should be determined by the complexity of the question and the depth of thinking, ranging from brief to detailed as needed. The key is to provide an accurate and complete answer]

Important:
- Start directly with "Question:"
- Do NOT add phrases like "Here is", "Based on", or "Below is" at the beginning
- The thinking process should simulate a real thought process using conversational, first-person expressions
- The final answer length should be determined by the question and thinking, ensuring completeness and accuracy

--- Real Data ---
Input:
[Entities:]:
{entities}

[Relationships:]:
{relationships}

Output:
"""

COT_COMBINED_ZH = """你是一位"元推理架构师"和"CoT数据生成器"。
你的任务是设计一条可复用、可泛化的 CoT 推理路径模板，并基于提供的知识图谱生成完整的 CoT 答案。

CoT（Chain-of-Thought，思维链）指在回答复杂问题时，把中间推理步骤一步一步显式写出来，使推理过程透明、可追溯，而不是直接给出最终答案。

---步骤---
1. 实体识别
   - 准确地识别[Entities:]章节中的实体信息，包括实体名、实体描述信息。

2. 关系识别
   - 准确地识别[Relationships:]章节中的关系信息，包括来源实体名、目标实体名、关系描述信息。

3. 图结构理解
   - 正确地将关系信息中的来源实体名与实体信息关联。
   - 根据提供的关系信息还原出图结构。

4. 问题设计
   - 围绕知识图谱所表达的"核心主题"设计一个问题。
   - 问题必须能在图谱内部通过实体、关系或属性直接验证；避免主观判断。
   - 问题应该能够模型足够的思考，充分利用图谱中的实体和关系，避免过于简单或无关的问题。

5. 推理路径设计
   - 设计一个简洁的推理蓝图，概括解题的关键步骤。
   - 保持步骤最小化：每一步只解决一个"不可分割"的子问题。

6. CoT思考过程生成（重要：模拟真实思考过程）
   - 使用第一人称或引导性语言开始（如"好的，让我们来思考一下"、"让我分析一下"）。
   - 使用自然的过渡性语句连接思路（如"现在"、"那么"、"想想看"、"因此"、"这意味着"）。
   - 采用口语化、日常思考的表达方式，而不是机械的步骤列表。
   - 展现思考过程中的推理和分析（如"这表明..."、"很可能..."、"如果...那么..."）。
   - 不要使用有序列表或编号，保持段落式的自然流动。
   - 思考过程应当全面且详细，提供足够的深度和细节。
   - 在遵循推理路径的基础上，可以利用相关背景知识、上下文或相关概念来丰富思考。
   - 在适当的时候包含相关细节、例子、影响或更广泛的联系，使思考更具信息量和价值。
   - 确保每一步推理都充分展开，像在向他人解释你的思考过程一样自然流畅。

7. 最终答案生成
   - 在思考过程之后，给出完整的最终答案。
   - 最终答案应该直接回答问题，不包含思考过程。
   - 答案的长度应根据问题的复杂度和思考过程的深度来决定。
   - 答案要清晰、准确、完整，充分回答问题的所有方面。
   - 可以是简短的结论，也可以是详细的解释，关键是要全面且准确。

---约束条件---
1. 使用中文作为输出语言。
2. 不要在回答中描述你的思考过程，直接给出问题、推理路径和答案。
3. 推理路径中避免使用停用词和过于常见的词汇。
4. 推理路径中不要出现具体数值或结论，不要出现"识别实体"、"识别关系"这类无意义的操作描述。

---严格输出格式---
必须严格按照以下格式输出（不要添加任何额外的说明、前言或元描述）：

问题：
[你的问题]

推理路径设计：
[你的推理路径模板]

思考过程：
[遵循推理路径的详细思考过程，使用自然的思考语言，如"好的，让我们来思考一下..."、"现在来分析..."等，展现完整的推理过程]

最终答案：
[直接回答问题的完整答案，不包含思考过程。答案的长度应根据问题的复杂度和思考过程的深度来决定，可以详细也可以简洁，重点是准确、完整地回答问题]

注意：
- 直接从"问题："开始输出
- 不要添加"以下是"、"根据"等说明性文字
- 思考过程要模拟真实的思考过程，使用口语化、第一人称的表达
- 最终答案的长度应根据问题和思考来决定，确保答案完整、准确

---真实数据---
输入:
[Entities:]:
{entities}

[Relationships:]:
{relationships}

输出:
"""

COT_GENERATION_PROMPT = {
    "en": {
        "COT_GENERATION": COT_GENERATION_EN,
        "COT_TEMPLATE_DESIGN": COT_TEMPLATE_DESIGN_EN,
        "COT_COMBINED": COT_COMBINED_EN,  # 新增：合并模式
    },
    "zh": {
        "COT_GENERATION": COT_GENERATION_ZH,
        "COT_TEMPLATE_DESIGN": COT_TEMPLATE_DESIGN_ZH,
        "COT_COMBINED": COT_COMBINED_ZH,  # 新增：合并模式
    },
}
