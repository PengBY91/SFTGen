"""Comprehensive Application Evaluation Generator"""

import json
import re
from typing import Any, Dict

from graphgen.bases.base_eval_generator import BaseEvaluationGenerator
from graphgen.bases.eval_datatypes import EvaluationItem
from graphgen.templates.evaluation import get_comprehensive_eval_prompt


class ComprehensiveEvalGenerator(BaseEvaluationGenerator):
    """
    Generator for comprehensive application evaluation items.
    Tests the ability to synthesize and apply knowledge to complex scenarios.
    """

    def __init__(self, llm_client, difficulty_levels=None):
        super().__init__(
            llm_client=llm_client,
            eval_type="comprehensive",
            difficulty_levels=difficulty_levels,
        )

    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]],
        difficulty: str = "medium",
    ) -> str:
        """
        Build prompt for comprehensive application evaluation.
        
        :param batch: tuple of (nodes, edges)
        :param difficulty: difficulty level
        :return: prompt string
        """
        nodes, edges = batch
        return get_comprehensive_eval_prompt(nodes, edges, difficulty)

    @staticmethod
    def parse_response(response: str, eval_type: str) -> Dict[str, EvaluationItem]:
        """
        Parse the LLM response and return evaluation items.
        
        :param response: LLM response string
        :param eval_type: evaluation type
        :return: dictionary of evaluation items
        """
        eval_items = {}
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response
            
            parsed_data = json.loads(json_str)
            
            # Convert parsed data to EvaluationItem objects
            for item_id, item_data in parsed_data.items():
                question = item_data.get("question", "")
                reference_answer = item_data.get("reference_answer", "")
                
                if not question or not reference_answer:
                    continue
                
                # Generate unique ID
                eval_id = BaseEvaluationGenerator.generate_item_id(question, eval_type)
                
                # Create evaluation criteria with detailed scoring
                evaluation_criteria = {
                    "required_knowledge_points": item_data.get("required_knowledge_points", []),
                    "scoring_criteria": item_data.get("scoring_criteria", {}),
                    "example_excellent_answer": item_data.get("example_excellent_answer", ""),
                    "example_mediocre_answer": item_data.get("example_mediocre_answer", ""),
                }
                
                # Add comprehensive metadata
                metadata = {
                    "knowledge_points_count": len(item_data.get("required_knowledge_points", [])),
                    "has_examples": bool(item_data.get("example_excellent_answer")),
                }
                
                eval_item = EvaluationItem(
                    id=eval_id,
                    type=eval_type,
                    difficulty="medium",  # Will be set later
                    question=question,
                    reference_answer=reference_answer,
                    evaluation_criteria=evaluation_criteria,
                    metadata=metadata,
                    distractors=[],
                )
                
                eval_items[eval_id] = eval_item
        
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}. Attempting manual extraction.")
            eval_id = BaseEvaluationGenerator.generate_item_id(response[:100], eval_type)
            eval_items[eval_id] = EvaluationItem(
                id=eval_id,
                type=eval_type,
                difficulty="medium",
                question="Failed to parse question",
                reference_answer=response[:500],
                evaluation_criteria={"error": "Failed to parse response"},
                metadata={"raw_response": response},
                distractors=[],
            )
        
        return eval_items
