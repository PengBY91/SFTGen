"""Prompt templates for factual accuracy evaluation generation"""


FACTUAL_ACCURACY_SYSTEM_PROMPT = """You are an expert at creating evaluation questions to test factual accuracy.
Your task is to generate questions that test whether a model can distinguish between correct and incorrect information.
Include true/false questions, error detection tasks, and questions with plausible but incorrect distractors."""


def get_factual_accuracy_prompt(nodes: list, edges: list, difficulty: str = "medium") -> str:
    """
    Generate prompt for factual accuracy evaluation.
    
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
        "easy": "Generate simple true/false questions or questions with obvious incorrect distractors.",
        "medium": "Generate questions with plausible but incorrect distractors that require careful fact-checking.",
        "hard": "Generate questions with subtle errors or highly plausible incorrect information that requires deep knowledge to detect.",
    }
    
    prompt = f"""{FACTUAL_ACCURACY_SYSTEM_PROMPT}

## Knowledge Graph

### Entities:
{entities_desc}

### Relationships:
{relationships_desc}

## Task

Difficulty Level: {difficulty}
{difficulty_guidance.get(difficulty, difficulty_guidance["medium"])}

Generate 2-3 evaluation questions that test factual accuracy based on the above knowledge.

For each question, provide:
1. The question itself
2. The correct answer
3. 2-3 plausible but incorrect distractors (wrong answers that seem reasonable)
4. An explanation of why the correct answer is right and why distractors are wrong
5. A scoring rubric

## Output Format

Return your response in the following JSON format:

```json
{{
  "eval_1": {{
    "question": "A question testing factual accuracy",
    "reference_answer": "The correct answer",
    "distractors": [
      "Plausible but incorrect answer 1",
      "Plausible but incorrect answer 2",
      "Plausible but incorrect answer 3"
    ],
    "explanation": "Why the correct answer is right and why distractors are wrong",
    "scoring_rubric": "How to evaluate the answer"
  }},
  "eval_2": {{
    "question": "Another factual accuracy question",
    "reference_answer": "The correct answer",
    "distractors": [
      "Incorrect answer 1",
      "Incorrect answer 2"
    ],
    "explanation": "Explanation of correct vs incorrect",
    "scoring_rubric": "Evaluation criteria"
  }}
}}
```

Generate the evaluation questions now:"""
    
    return prompt
