"""
DA-ToG Main Pipeline.

Assembles the three DA-ToG layers:
1. Macro-Intent (TaxonomyTree + DiversitySampler)
2. Micro-Fact (GraphAdapter)
3. Logic-Critic (BaseCritic)

And orchestrates end-to-end SFT data synthesis.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import yaml

from graphgen.bases.base_critic import BaseCritic, CriticResult
from graphgen.bases.base_llm_client import BaseLLMClient
from graphgen.models.critic.llm_critic import LLMCritic
from graphgen.models.critic.rule_critic import (
    RuleCritic,
    answer_contains_keywords,
    answer_not_identical_to_question,
    min_answer_length,
    min_question_length,
)
from graphgen.models.generator.datog_generator import DAToGGenerator
from graphgen.models.graph_adapter.intent_graph_linker import IntentGraphLinker
from graphgen.models.graph_adapter.networkx_adapter import NetworkXGraphAdapter
from graphgen.models.taxonomy.diversity_sampler import DiversitySampler
from graphgen.models.taxonomy.taxonomy_tree import TaxonomyTree

logger = logging.getLogger(__name__)


class DAToGPipeline:
    """
    Domain-Agnostic Tree-of-Graphs data synthesis pipeline.

    Orchestrates: intent sampling → subgraph retrieval → QA generation → critic validation.
    """

    def __init__(
        self,
        taxonomy_tree: TaxonomyTree,
        graph_adapter: NetworkXGraphAdapter,
        llm_client: BaseLLMClient,
        critic: Optional[BaseCritic] = None,
        sampling_strategy: str = "coverage",
        max_hops: int = 2,
        max_nodes_per_subgraph: int = 20,
        serialization_format: str = "natural_language",
        min_critic_score: float = 0.6,
        seed: Optional[int] = None,
        max_concurrent_intents: int = 8,
    ):
        self.taxonomy_tree = taxonomy_tree
        self.graph_adapter = graph_adapter
        self.llm_client = llm_client
        self.critic = critic
        self.sampler = DiversitySampler(taxonomy_tree, seed=seed)
        self.sampling_strategy = sampling_strategy
        self.max_hops = max_hops
        self.max_nodes_per_subgraph = max_nodes_per_subgraph
        self.serialization_format = serialization_format
        self.min_critic_score = min_critic_score
        self.max_concurrent_intents = max_concurrent_intents

        # Initialize generator
        self.generator = DAToGGenerator(llm_client)

    @classmethod
    def from_config(
        cls,
        config_path: str,
        llm_client: BaseLLMClient,
        graph_storage,
    ) -> "DAToGPipeline":
        """
        Create a DA-ToG pipeline from a YAML config file.

        :param config_path: Path to datog_config.yaml
        :param llm_client: LLM client for generation and critic
        :param graph_storage: Graph storage (BaseGraphStorage)
        """
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        datog_config = config.get("datog", config)

        # Load taxonomy
        taxonomy_config = datog_config.get("taxonomy", {})
        taxonomy_path = taxonomy_config.get("path")
        if taxonomy_path and os.path.exists(taxonomy_path):
            tree = TaxonomyTree.load(taxonomy_path)
        else:
            raise ValueError(
                f"Taxonomy path not found: {taxonomy_path}. "
                "Set datog.taxonomy.path in config."
            )

        # Create graph adapter
        graph_config = datog_config.get("graph", {})
        linker = IntentGraphLinker(min_score=graph_config.get("min_link_score", 0.1))
        adapter = NetworkXGraphAdapter(
            graph_storage=graph_storage,
            linker=linker,
        )

        # Create critic
        critic_config = datog_config.get("critic", {})
        critic_type = critic_config.get("type", "llm")
        critic = cls._create_critic(critic_type, llm_client, critic_config)

        return cls(
            taxonomy_tree=tree,
            graph_adapter=adapter,
            llm_client=llm_client,
            critic=critic,
            sampling_strategy=taxonomy_config.get("sampling_strategy", "coverage"),
            max_hops=graph_config.get("max_hops", 2),
            max_nodes_per_subgraph=graph_config.get("max_nodes_per_subgraph", 20),
            serialization_format=graph_config.get("serialization_format", "natural_language"),
            min_critic_score=critic_config.get("min_score", 0.6),
        )

    @staticmethod
    def _create_critic(
        critic_type: str,
        llm_client: BaseLLMClient,
        critic_config: dict,
    ) -> Optional[BaseCritic]:
        """Create the appropriate critic based on config."""
        if critic_type == "llm":
            return LLMCritic(
                llm_client=llm_client,
                min_score=critic_config.get("min_score", 0.6),
            )
        elif critic_type == "rule":
            critic = RuleCritic()
            critic.add_rule("min_answer_length", min_answer_length(10), weight=1.0)
            critic.add_rule("min_question_length", min_question_length(5), weight=1.0)
            critic.add_rule("not_identical", answer_not_identical_to_question(), weight=2.0)
            critic.add_rule("keyword_overlap", answer_contains_keywords(1), weight=1.0)
            return critic
        elif critic_type == "none":
            return None
        else:
            logger.warning("Unknown critic type '%s', disabling critic", critic_type)
            return None

    async def run(
        self,
        target_count: int = 100,
        batch_size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Execute the full DA-ToG synthesis pipeline.

        :param target_count: Target number of QA pairs to generate
        :param batch_size: Number of intents to sample per batch
        :return: List of validated QA pair dicts
        """
        logger.info(
            "DA-ToG pipeline starting: target=%d, strategy=%s, tree=%s",
            target_count, self.sampling_strategy, self.taxonomy_tree.name,
        )

        all_qa_pairs: List[Dict[str, Any]] = []
        max_iterations = target_count * 3  # Allow for rejection
        iteration = 0

        while len(all_qa_pairs) < target_count and iteration < max_iterations:
            # How many more do we need?
            remaining = target_count - len(all_qa_pairs)
            sample_size = min(batch_size, remaining * 2)

            # Step 1: Sample intents from taxonomy tree
            intents = self.sampler.sample(sample_size, strategy=self.sampling_strategy)
            if not intents:
                logger.warning("No intents available for sampling")
                break

            # Step 2: For each intent, retrieve subgraph + generate QA
            # （旧实现逐个 intent 串行 await，每个 intent 还有 1-2 次 LLM 调用；
            #   改为有界并发，吞吐随并发度提升）
            semaphore = asyncio.Semaphore(self.max_concurrent_intents)

            async def _process_intent(intent_node):
                async with semaphore:
                    try:
                        return await self._generate_for_intent(intent_node)
                    except Exception as e:  # pylint: disable=broad-except
                        logger.warning(
                            "Failed to generate for intent '%s': %s",
                            intent_node.name, e,
                        )
                        return None

            batch_results = await asyncio.gather(
                *(_process_intent(node) for node in intents)
            )
            for qa_pair in batch_results:
                if qa_pair and len(all_qa_pairs) < target_count:
                    all_qa_pairs.append(qa_pair)

            iteration += len(intents)

        logger.info(
            "DA-ToG pipeline complete: generated %d/%d QA pairs, "
            "coverage=%.1f%%",
            len(all_qa_pairs), target_count,
            self.sampler.coverage_ratio * 100,
        )
        return all_qa_pairs

    async def _generate_for_intent(
        self,
        intent_node,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate one QA pair for a single intent node.

        Pipeline: intent → subgraph → prompt → LLM → parse → critic → output
        """
        intent_dict = {
            "id": intent_node.id,
            "name": intent_node.name,
            "description": intent_node.description,
            "cognitive_dimension": intent_node.cognitive_dimension,
        }

        # Step 2a: Retrieve subgraph
        text, nodes, edges = await self.graph_adapter.retrieve_and_serialize(
            intent_dict,
            max_hops=self.max_hops,
            max_nodes=self.max_nodes_per_subgraph,
            format=self.serialization_format,
        )

        if not text.strip():
            logger.debug("Empty subgraph for intent '%s'", intent_node.name)
            return None

        # Step 2b: Generate using DAToGGenerator
        # We use a custom method for intent-aware generation
        qa_results = await self.generator.generate_with_intent(
            intent=intent_dict,
            subgraph_text=text,
            nodes=nodes,
            edges=edges,
        )
        
        if not qa_results:
            return None
            
        # Get the first (and usually only) QA pair
        qa_pair = list(qa_results.values())[0]

        # Step 2c: Critic validation
        if self.critic:
            context = {
                "subgraph_text": text,
                "intent": intent_dict,
            }
            result = await self.critic.validate(qa_pair, context)
            if not result.passed or result.score < self.min_critic_score:
                logger.debug(
                    "Critic rejected QA (score=%.2f): %s",
                    result.score, result.reason,
                )
                return None

        # Add more pipeline-specific metadata
        qa_pair["metadata"].update({
            "intent_id": intent_node.id,
            "source_nodes": [n[0] for n in nodes[:5]],
            "pipeline": "datog",
        })

        return qa_pair

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "taxonomy": self.taxonomy_tree.get_statistics(),
            "coverage": {
                "overall": self.sampler.coverage_ratio,
                "by_dimension": self.sampler.get_coverage_by_dimension(),
                "by_depth": self.sampler.get_coverage_by_depth(),
                "uncovered_nodes": self.sampler.uncovered_count,
            },
        }
