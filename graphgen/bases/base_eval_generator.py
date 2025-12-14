"""Base class for evaluation dataset generators"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import hashlib

from graphgen.bases.base_llm_client import BaseLLMClient
from graphgen.bases.eval_datatypes import EvaluationItem


class BaseEvaluationGenerator(ABC):
    """
    Base class for generating evaluation datasets.
    Evaluation generators create test items to assess model capabilities.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        eval_type: str,
        difficulty_levels: Optional[List[str]] = None,
    ):
        """
        Initialize the evaluation generator.
        
        :param llm_client: LLM client for generation
        :param eval_type: Type of evaluation (e.g., 'knowledge_coverage', 'reasoning_ability')
        :param difficulty_levels: List of difficulty levels to generate
        """
        self.llm_client = llm_client
        self.eval_type = eval_type
        self.difficulty_levels = difficulty_levels or ["easy", "medium", "hard"]

    @abstractmethod
    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]],
        difficulty: str = "medium",
    ) -> str:
        """
        Build prompt for LLM based on the given batch and difficulty level.
        
        :param batch: tuple of (nodes, edges) from knowledge graph
        :param difficulty: difficulty level for the evaluation item
        :return: prompt string
        """

    @staticmethod
    @abstractmethod
    def parse_response(response: str, eval_type: str) -> Dict[str, EvaluationItem]:
        """
        Parse the LLM response and return evaluation items.
        
        :param response: LLM response string
        :param eval_type: evaluation type
        :return: dictionary of evaluation items
        """

    async def generate(
        self,
        batch: tuple[
            list[tuple[str, dict]], list[tuple[Any, Any, dict] | tuple[Any, Any, Any]]
        ],
        difficulty: str = "medium",
        chunks_storage=None,
        full_docs_storage=None,
    ) -> Dict[str, EvaluationItem]:
        """
        Generate evaluation items based on a given batch.
        
        :param batch: tuple of (nodes, edges)
        :param difficulty: difficulty level
        :param chunks_storage: chunks storage instance
        :param full_docs_storage: full documents storage instance
        :return: dictionary of evaluation items
        """
        prompt = self.build_prompt(batch, difficulty)
        response = await self.llm_client.generate_answer(prompt)
        eval_items = self.parse_response(response, self.eval_type)
        
        # Add metadata from batch
        await self._add_metadata(eval_items, batch, chunks_storage, full_docs_storage, difficulty)
        
        return eval_items

    async def _add_metadata(
        self,
        eval_items: Dict[str, EvaluationItem],
        batch: tuple,
        chunks_storage=None,
        full_docs_storage=None,
        difficulty: str = "medium",
    ) -> None:
        """
        Add metadata to evaluation items including knowledge graph info and source chunks.
        
        :param eval_items: dictionary of evaluation items
        :param batch: tuple of (nodes, edges)
        :param chunks_storage: chunks storage instance
        :param full_docs_storage: full documents storage instance
        :param difficulty: difficulty level
        """
        nodes, edges = batch
        
        # Collect chunk IDs
        chunk_ids = set()
        for node_id, node_data in nodes:
            chunk_id = node_data.get("chunk_id") or node_data.get("source_id")
            if chunk_id:
                if isinstance(chunk_id, (list, tuple)):
                    chunk_ids.update(chunk_id)
                else:
                    chunk_ids.add(chunk_id)
        
        for edge in edges:
            edge_data = edge[2] if len(edge) > 2 else {}
            chunk_id = edge_data.get("chunk_id") or edge_data.get("source_id")
            if chunk_id:
                if isinstance(chunk_id, (list, tuple)):
                    chunk_ids.update(chunk_id)
                else:
                    chunk_ids.add(chunk_id)
        
        # Add metadata to each evaluation item
        for item_id, item in eval_items.items():
            # Set difficulty
            item.difficulty = difficulty
            
            # Add knowledge graph metadata
            item.metadata["knowledge_nodes"] = [node[0] for node in nodes]
            item.metadata["knowledge_edges"] = [
                {"source": edge[0], "target": edge[1], "description": edge[2].get("description", "")}
                for edge in edges
            ]
            item.metadata["entity_count"] = len(nodes)
            item.metadata["relationship_count"] = len(edges)
            item.metadata["source_chunk_ids"] = list(chunk_ids)
            
            # Calculate reasoning hops (for reasoning-based evaluations)
            item.metadata["reasoning_hops"] = self._calculate_reasoning_hops(batch)

    def _calculate_reasoning_hops(self, batch: tuple) -> int:
        """
        Calculate the number of reasoning hops required based on the batch.
        
        :param batch: tuple of (nodes, edges)
        :return: number of hops
        """
        nodes, edges = batch
        # Simple heuristic: number of edges indicates reasoning complexity
        return min(len(edges), 5)  # Cap at 5 hops

    @staticmethod
    def format_evaluation_results(
        results: List[EvaluationItem],
        output_format: str = "benchmark",
    ) -> List[Dict[str, Any]]:
        """
        Format evaluation results into the specified output format.
        
        :param results: list of evaluation items
        :param output_format: output format (benchmark, qa_pair, multiple_choice)
        :return: formatted results
        """
        if output_format == "benchmark":
            # Standard benchmark format
            return [item.to_dict() for item in results]
        
        elif output_format == "qa_pair":
            # Simple QA pair format
            return [
                {
                    "id": item.id,
                    "question": item.question,
                    "answer": item.reference_answer,
                    "type": item.type,
                    "difficulty": item.difficulty,
                    "metadata": item.metadata,
                }
                for item in results
            ]
        
        elif output_format == "multiple_choice":
            # Multiple choice format with distractors
            return [
                {
                    "id": item.id,
                    "question": item.question,
                    "correct_answer": item.reference_answer,
                    "options": [item.reference_answer] + item.distractors,
                    "type": item.type,
                    "difficulty": item.difficulty,
                    "explanation": item.evaluation_criteria.get("explanation", ""),
                    "metadata": item.metadata,
                }
                for item in results
                if item.distractors  # Only include items with distractors
            ]
        
        else:
            raise ValueError(f"Unknown output format: {output_format}")

    @staticmethod
    def generate_item_id(question: str, eval_type: str) -> str:
        """
        Generate a unique ID for an evaluation item.
        
        :param question: question text
        :param eval_type: evaluation type
        :return: unique ID
        """
        content = f"{eval_type}:{question}"
        hash_value = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"eval_{eval_type[:4]}_{hash_value}"
