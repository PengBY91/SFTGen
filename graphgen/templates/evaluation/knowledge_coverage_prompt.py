"""Prompt templates for knowledge coverage evaluation generation"""


KNOWLEDGE_COVERAGE_SYSTEM_PROMPT = """You are an expert at creating evaluation questions to test knowledge coverage.
Your task is to generate high-quality evaluation questions based on the provided knowledge graph.
The questions should test whether a model has learned and can recall specific facts and concepts."""


def get_knowledge_coverage_prompt(nodes: list, edges: list, difficulty: str = "medium") -> str:
    """
    Generate prompt for knowledge coverage evaluation.
    
    :param nodes: list of (node_id, node_data) tuples
    :param edges: list of (source, target, edge_data) tuples
    :param difficulty: difficulty level (easy, medium, hard)
    :return: prompt string
    """
    
    # Build knowledge graph description
    entities_desc = "\n".join([
        f"- {node[0]}: {node[1].get('description', 'No description')}"
        for node in nodes
    ])
    
    relationships_desc = "\n".join([
        f"- {edge[0]} -> {edge[1]}: {edge[2].get('description', 'No description')}"
        for edge in edges
    ])
    
    difficulty_guidance = {
        "easy": "Generate simple, direct questions that test basic recall of facts. Questions should be straightforward and require minimal reasoning.",
        "medium": "Generate questions that require understanding of concepts and relationships. Questions may involve connecting multiple pieces of information.",
        "hard": "Generate complex questions that require deep understanding and synthesis of multiple concepts. Questions should be challenging and nuanced.",
    }
    
    prompt = f"""{KNOWLEDGE_COVERAGE_SYSTEM_PROMPT}

## Knowledge Graph

### Entities:
{entities_desc}

### Relationships:
{relationships_desc}

## Task

Difficulty Level: {difficulty}
{difficulty_guidance.get(difficulty, difficulty_guidance["medium"])}

Generate 2-3 evaluation questions that test knowledge coverage of the above information.

For each question, provide:
1. The question itself
2. A reference answer (the correct, complete answer)
3. Key points that must be included in a correct answer
4. A scoring rubric (how to evaluate the answer)

## Output Format

Return your response in the following JSON format:

```json
{{
  "eval_1": {{
    "question": "The evaluation question",
    "reference_answer": "The complete, correct answer",
    "key_points": ["point 1", "point 2", "point 3"],
    "scoring_rubric": "Description of how to score the answer"
  }},
  "eval_2": {{
    "question": "Another evaluation question",
    "reference_answer": "The complete, correct answer",
    "key_points": ["point 1", "point 2"],
    "scoring_rubric": "Description of how to score the answer"
  }}
}}
```

Generate the evaluation questions now:"""
    
    return prompt
