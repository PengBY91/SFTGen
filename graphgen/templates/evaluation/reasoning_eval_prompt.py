"""Prompt templates for reasoning ability evaluation generation"""


REASONING_EVAL_SYSTEM_PROMPT = """You are an expert at creating evaluation questions to test reasoning abilities.
Your task is to generate questions that require multi-hop reasoning, logical inference, and analytical thinking.
The questions should test whether a model can reason over knowledge graphs and make logical connections."""


def get_reasoning_eval_prompt(nodes: list, edges: list, difficulty: str = "medium") -> str:
    """
    Generate prompt for reasoning ability evaluation.
    
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
    
    # Calculate reasoning complexity
    num_hops = min(len(edges), 3)
    
    difficulty_guidance = {
        "easy": f"Generate questions requiring {max(1, num_hops-1)}-hop reasoning. Questions should involve simple logical connections.",
        "medium": f"Generate questions requiring {num_hops}-hop reasoning. Questions should involve moderate logical inference and connecting multiple facts.",
        "hard": f"Generate questions requiring {num_hops+1}-hop reasoning or complex logical inference. Questions should be challenging and require deep analytical thinking.",
    }
    
    prompt = f"""{REASONING_EVAL_SYSTEM_PROMPT}

## Knowledge Graph

### Entities:
{entities_desc}

### Relationships:
{relationships_desc}

## Task

Difficulty Level: {difficulty}
{difficulty_guidance.get(difficulty, difficulty_guidance["medium"])}

Generate 2-3 evaluation questions that test reasoning abilities over the above knowledge graph.

For each question, provide:
1. The question itself (should require reasoning, not just recall)
2. A reference answer with reasoning steps
3. The reasoning path (which entities and relationships are involved)
4. A scoring rubric that evaluates both the answer and the reasoning process

## Output Format

Return your response in the following JSON format:

```json
{{
  "eval_1": {{
    "question": "A question requiring multi-hop reasoning",
    "reference_answer": "The answer with explicit reasoning steps",
    "reasoning_path": ["Entity A", "Relationship 1", "Entity B", "Relationship 2", "Entity C"],
    "key_reasoning_steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
    "scoring_rubric": "How to evaluate the reasoning quality"
  }},
  "eval_2": {{
    "question": "Another reasoning question",
    "reference_answer": "The answer with reasoning",
    "reasoning_path": ["Entity X", "Relationship Y", "Entity Z"],
    "key_reasoning_steps": ["Step 1: ...", "Step 2: ..."],
    "scoring_rubric": "Evaluation criteria"
  }}
}}
```

Generate the evaluation questions now:"""
    
    return prompt
