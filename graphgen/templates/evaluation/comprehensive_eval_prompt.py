"""Prompt templates for comprehensive application evaluation generation"""


COMPREHENSIVE_EVAL_SYSTEM_PROMPT = """You are an expert at creating comprehensive evaluation questions that test the ability to apply knowledge.
Your task is to generate complex questions that require synthesizing multiple concepts, applying knowledge to scenarios,
and demonstrating deep understanding through practical application."""


def get_comprehensive_eval_prompt(nodes: list, edges: list, difficulty: str = "medium") -> str:
    """
    Generate prompt for comprehensive application evaluation.
    
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
    
    min_knowledge_points = 2 if difficulty == "easy" else 3 if difficulty == "medium" else 4
    
    difficulty_guidance = {
        "easy": f"Generate questions that require combining {min_knowledge_points} knowledge points. Questions should involve basic application of concepts.",
        "medium": f"Generate questions that require synthesizing {min_knowledge_points} or more knowledge points. Questions should involve moderate complexity and practical scenarios.",
        "hard": f"Generate questions that require deep synthesis of {min_knowledge_points}+ knowledge points. Questions should involve complex scenarios, analysis, or problem-solving.",
    }
    
    prompt = f"""{COMPREHENSIVE_EVAL_SYSTEM_PROMPT}

## Knowledge Graph

### Entities:
{entities_desc}

### Relationships:
{relationships_desc}

## Task

Difficulty Level: {difficulty}
{difficulty_guidance.get(difficulty, difficulty_guidance["medium"])}

Generate 1-2 comprehensive evaluation questions that test the ability to apply and synthesize the above knowledge.

For each question, provide:
1. The question itself (should be scenario-based or require synthesis)
2. A comprehensive reference answer
3. The knowledge points that must be integrated
4. Detailed scoring criteria with partial credit guidelines
5. Example of an excellent answer and a mediocre answer

## Output Format

Return your response in the following JSON format:

```json
{{
  "eval_1": {{
    "question": "A comprehensive question requiring synthesis and application",
    "reference_answer": "A detailed, comprehensive answer",
    "required_knowledge_points": [
      "Knowledge point 1",
      "Knowledge point 2",
      "Knowledge point 3"
    ],
    "scoring_criteria": {{
      "excellent": "Criteria for full marks",
      "good": "Criteria for partial credit",
      "poor": "Criteria for minimal credit"
    }},
    "example_excellent_answer": "An example of a top-quality answer",
    "example_mediocre_answer": "An example of an average answer"
  }},
  "eval_2": {{
    "question": "Another comprehensive question",
    "reference_answer": "Detailed answer",
    "required_knowledge_points": ["Point 1", "Point 2", "Point 3"],
    "scoring_criteria": {{
      "excellent": "Full marks criteria",
      "good": "Partial credit criteria",
      "poor": "Minimal credit criteria"
    }},
    "example_excellent_answer": "Example excellent answer",
    "example_mediocre_answer": "Example mediocre answer"
  }}
}}
```

Generate the evaluation questions now:"""
    
    return prompt
