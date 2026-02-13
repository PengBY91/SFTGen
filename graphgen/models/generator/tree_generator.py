"""Tree structure generator for hierarchical knowledge."""

import json
import re
from typing import Any, List, Optional, Tuple
import networkx as nx

from graphgen.bases import BaseGenerator
from graphgen.templates import HIERARCHICAL_GENERATION_PROMPT
from graphgen.utils import compute_content_hash, detect_main_language, logger


class TreeStructureGenerator(BaseGenerator):
    """
    Generator for hierarchical knowledge structures.

    Serializes knowledge subgraphs into tree formats (Markdown, JSON, Outline)
    and generates QA pairs focused on hierarchical reasoning.
    """

    def __init__(
        self,
        llm_client,
        structure_format: str = "markdown",
        hierarchical_relations: List[str] = None,
        chinese_only: bool = False,
    ):
        """
        Initialize TreeStructureGenerator.

        :param llm_client: LLM client instance
        :param structure_format: Output format - "markdown", "json", or "outline"
        :param hierarchical_relations: List of relation types indicating hierarchy
        :param chinese_only: Whether to generate only Chinese QA pairs
        """
        super().__init__(llm_client)
        self.structure_format = structure_format
        self.hierarchical_relations = hierarchical_relations or [
            "is_a",
            "subclass_of",
            "part_of",
            "includes",
            "type_of",
        ]
        self.chinese_only = chinese_only
        self._generation_mode = "hierarchical"
        
        # Initialize the shared serializer
        from graphgen.utils.hierarchy_utils import HierarchySerializer
        self.hierarchy_serializer = HierarchySerializer(self.hierarchical_relations)

    def build_prompt(
        self,
        batch: Tuple[List[Tuple[str, dict]], List[Tuple[Any, Any, dict]]]
    ) -> str:
        """
        Build prompt with hierarchical structure.

        :param batch: Tuple of (nodes, edges)
        :return: Formatted prompt string
        """
        # Build hierarchical structure using shared serializer
        nodes, edges = batch
        hierarchy_text = self.hierarchy_serializer.serialize(
            nodes, 
            edges, 
            structure_format=self.structure_format
        )

        # Detect language
        language = "zh" if self.chinese_only else detect_main_language(hierarchy_text)

        # Select reasoning pattern (randomly for diversity)
        import random
        reasoning_patterns = ["sibling", "inheritance", "abstraction", "multilevel"]
        selected_pattern = random.choice(reasoning_patterns)

        # Get appropriate template
        templates = HIERARCHICAL_GENERATION_PROMPT.get(language, HIERARCHICAL_GENERATION_PROMPT["en"])
        template = templates.get(selected_pattern, templates["sibling"])

        prompt = template.format(context=hierarchy_text)
        logger.debug(
            f"Built hierarchical prompt with format={self.structure_format}, "
            f"pattern={selected_pattern}, language={language}"
        )

        return prompt

    @staticmethod
    def parse_response(response: str) -> dict:
        """
        Parse response containing hierarchical QA pair.

        Expected format:
        Question: ...
        Answer: ...
        Hierarchical Reasoning: ... (optional)

        :param response: LLM response string
        :return: Dictionary with QA pair
        """
        result = {}

        if not response or not response.strip():
            logger.warning("Empty response received")
            return result

        # Clean response
        response_clean = response.strip()

        # Pre-processing: Remove meta-descriptions
        meta_prefixes = [
            r"^根据您提供的层次结构[，,]\s*以下是.*?[：:]\s*",
            r"^根据.*?层次[，,]\s*以下是.*?[：:]\s*",
            r"^Based on the (?:hierarchical|tree) structure.*?here is.*?[：:]\s*",
            r"^Here is (?:a|the) (?:QA|question-answer) pair.*?[：:]\s*",
        ]

        for pattern in meta_prefixes:
            response_clean = re.sub(pattern, "", response_clean, flags=re.IGNORECASE)

        response_clean = response_clean.strip()

        # Try to extract Question, Answer, and Hierarchical Reasoning
        question = None
        answer = None
        reasoning = None

        # Pattern 1: Full format with all three components
        pattern_full = re.compile(
            r"(?:Question|问题)[：:]\s*(.+?)(?=(?:Answer|答案)[：:])"
            r".*?(?:Answer|答案)[：:]\s*(.+?)(?=(?:Hierarchical Reasoning|层次推理)[：:]|$)"
            r"(?:.*?(?:Hierarchical Reasoning|层次推理)[：:]\s*(.+))?$",
            re.DOTALL | re.IGNORECASE
        )

        match = pattern_full.search(response_clean)
        if match:
            question = match.group(1).strip().strip('"').strip("'")
            answer = match.group(2).strip().strip('"').strip("'")
            reasoning = match.group(3).strip().strip('"').strip("'") if match.lastindex >= 3 and match.group(3) else None
        else:
            # Pattern 2: Standard QA format (no hierarchical reasoning)
            markers = [
                ("Question:", "Answer:", "en"),
                ("问题：", "答案：", "zh"),
                ("Q:", "A:", "en"),
                ("问：", "答：", "zh"),
            ]

            for q_marker, a_marker, lang in markers:
                if q_marker in response_clean:
                    try:
                        q_pos = response_clean.find(q_marker)
                        a_pos = response_clean.find(a_marker, q_pos + len(q_marker))

                        if a_pos > q_pos:
                            question = response_clean[q_pos + len(q_marker):a_pos].strip()
                            remaining = response_clean[a_pos + len(a_marker):].strip()

                            # Check for hierarchical reasoning
                            reasoning_markers = ["Hierarchical Reasoning:", "层次推理："]
                            for r_marker in reasoning_markers:
                                if r_marker in remaining:
                                    r_pos = remaining.find(r_marker)
                                    answer = remaining[:r_pos].strip()
                                    reasoning = remaining[r_pos + len(r_marker):].strip()
                                    break
                            else:
                                answer = remaining

                            question = question.strip('"').strip("'")
                            answer = answer.strip('"').strip("'")
                            break
                    except (IndexError, ValueError) as e:
                        logger.debug(f"Error parsing with markers {q_marker}/{a_marker}: {e}")
                        continue

        if question and answer:
            q_hash = compute_content_hash(question)
            result[q_hash] = {
                "question": question,
                "answer": answer,
            }
            if reasoning:
                result[q_hash]["hierarchical_reasoning"] = reasoning

            logger.debug(
                f"Parsed hierarchical QA pair: Q={question[:50]}, "
                f"reasoning={'included' if reasoning else 'none'}"
            )
        elif question:
            logger.warning(f"Question found but no answer extracted: {question[:100]}")
        else:
            logger.warning(
                f"Failed to parse hierarchical QA pair from response: "
                f"{response_clean[:200] if len(response_clean) > 200 else response_clean}"
            )

        return result
