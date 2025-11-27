# pylint: disable=C0301
TEMPLATE_ZH: str = """你是一位"多跳推理问题生成专家"。
你的任务是根据给定的知识图谱中的实体和关系，设计一个需要多步推理才能回答的问题，并提供完整的推理路径和答案。

多跳推理指问题需要通过知识图谱中的多条关系链（通常至少2步）才能找到答案，而不是直接从一个实体到另一个实体。

---步骤---
1. 实体识别
   - 准确地识别[Entities:]章节中的实体信息，包括实体名、实体描述信息。

2. 关系识别
   - 准确地识别[Relationships:]章节中的关系信息，包括来源实体名、目标实体名、关系描述信息。

3. 图结构理解
   - 正确地将关系信息中的来源实体名与实体信息关联。
   - 根据提供的关系信息还原出图结构。
   - 识别图中的多跳路径（即通过多个关系连接的实体链）。

4. 多跳问题设计
   - 设计一个问题，该问题必须通过至少2步推理才能回答（例如：实体A → 关系1 → 实体B → 关系2 → 答案）。
   - 问题必须能在图谱内部通过实体、关系和路径直接验证；避免主观判断或外部知识。
   - 问题应该充分利用图谱中的多跳路径，确保需要经过至少两个关系才能得到答案。
   - 避免过于简单的问题（仅需一步推理）或无法在图谱中找到答案的问题。

5. 推理路径设计
   - 设计清晰的推理路径，明确显示从起始实体到最终答案的每一步。
   - 推理路径应包含：起始实体 → 第一个关系 → 中间实体 → 第二个关系 → ... → 最终答案。
   - 每一步都应该在图谱中有明确的对应。

6. 答案生成
   - 根据推理路径生成准确的答案。
   - 答案应该是对推理路径最后一跳的结果的直接回答。

---约束条件---
1. 使用中文作为输出语言。
2. 不要在回答中描述你的思考过程，直接给出问题、推理路径和答案。
3. 推理路径必须清晰，每一步都要在图谱中有明确对应。
4. 问题必须需要至少2步推理（至少经过2个关系）。
5. 不要出现"识别实体"、"识别关系"这类无意义的操作描述。

---输出格式---
问题：
[你的多跳推理问题]

答案：
[你的答案]

推理路径：
[清晰的推理路径，例如：实体A → 关系描述1 → 实体B → 关系描述2 → 答案]

---真实数据---
输入:
[Entities:]:
{entities}

[Relationships:]:
{relationships}

输出:
"""

TEMPLATE_EN: str = """You are a "multi-hop reasoning question generation expert".
Your task is to design a question that requires multiple steps of reasoning to answer, based on the given entities and relationships in the knowledge graph, and provide a complete reasoning path and answer.

Multi-hop reasoning means that the question requires traversing multiple relation chains (typically at least 2 steps) in the knowledge graph to find the answer, rather than going directly from one entity to another.

--- Steps ---
1. Entity Recognition
   - Accurately recognize entity information in the [Entities:] section, including entity names and descriptions.

2. Relationship Recognition
   - Accurately recognize relationship information in the [Relationships:] section, including source_entity_name, target_entity_name, and relationship descriptions.

3. Graph Structure Understanding
   - Correctly associate the source entity name in the relationship information with the entity information.
   - Reconstruct the graph structure based on the provided relationship information.
   - Identify multi-hop paths in the graph (i.e., entity chains connected through multiple relationships).

4. Multi-hop Question Design
   - Design a question that requires at least 2 steps of reasoning to answer (e.g., Entity A → Relation 1 → Entity B → Relation 2 → Answer).
   - The question must be verifiable directly within the graph through entities, relationships, and paths; avoid subjective judgments or external knowledge.
   - The question should fully utilize multi-hop paths in the graph, ensuring that at least two relationships must be traversed to reach the answer.
   - Avoid overly simple questions (requiring only one step of reasoning) or questions that cannot be answered from the graph.

5. Reasoning Path Design
   - Design a clear reasoning path that explicitly shows each step from the starting entity to the final answer.
   - The reasoning path should include: Starting Entity → First Relation → Intermediate Entity → Second Relation → ... → Final Answer.
   - Each step should have a clear correspondence in the graph.

6. Answer Generation
   - Generate an accurate answer based on the reasoning path.
   - The answer should be a direct response to the result of the last hop in the reasoning path.

--- Constraints ---
1. Use English as the output language.
2. Do not describe your thinking process; output only the question, reasoning path, and answer.
3. The reasoning path must be clear, with each step having a clear correspondence in the graph.
4. The question must require at least 2 steps of reasoning (traversing at least 2 relationships).
5. Do not include meaningless operation descriptions like "Identify the entity" or "Identify the relationship".

--- Output Format ---
Question:
[Your multi-hop reasoning question]

Answer:
[Your answer]

Reasoning Path:
[Clear reasoning path, e.g., Entity A → Relation Description 1 → Entity B → Relation Description 2 → Answer]

--- Real Data ---
Input:
[Entities:]:
{entities}

[Relationships:]:
{relationships}

Output:
"""

MULTI_HOP_GENERATION_PROMPT = {"en": TEMPLATE_EN, "zh": TEMPLATE_ZH}
