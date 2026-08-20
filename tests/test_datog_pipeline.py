"""
Tests for DA-ToG Phase 3: Critic and Pipeline Integration.

Tests cover:
- RuleCritic: built-in rules, custom rules, scoring
- LLMCritic: response parsing, validation with mock LLM
- DAToGPipeline: end-to-end generation with all layers mocked
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from graphgen.bases.base_critic import CriticResult
from graphgen.models.critic.llm_critic import LLMCritic
from graphgen.models.critic.rule_critic import (
    RuleCritic,
    answer_contains_keywords,
    answer_not_identical_to_question,
    min_answer_length,
    min_question_length,
)
from graphgen.models.graph_adapter.networkx_adapter import NetworkXGraphAdapter
from graphgen.models.taxonomy.taxonomy_tree import TaxonomyTree
from graphgen.datog_pipeline import DAToGPipeline


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

SAMPLE_TREE = {
    "name": "test_domain",
    "domain": "testing",
    "nodes": [
        {
            "id": "root",
            "name": "Test Topic",
            "description": "A topic for testing",
            "cognitive_dimension": "concept_explanation",
            "children": [
                {
                    "id": "sub1",
                    "name": "Sub-Topic 1",
                    "description": "First sub-topic for concept explanation",
                    "cognitive_dimension": "concept_explanation",
                    "children": [],
                },
                {
                    "id": "sub2",
                    "name": "Sub-Topic 2",
                    "description": "Second sub-topic for relational reasoning",
                    "cognitive_dimension": "relational_reasoning",
                    "children": [],
                },
            ],
        }
    ],
}


class MockGraphStorage:
    """Minimal mock graph storage."""

    def __init__(self):
        self._nodes = {
            "entity_a": {"description": "Entity A description", "entity_type": "concept"},
            "entity_b": {"description": "Entity B description", "entity_type": "concept"},
            "entity_c": {"description": "Entity C related to test", "entity_type": "concept"},
        }
        self._edges = {
            ("entity_a", "entity_b"): {"description": "A relates to B", "relation_type": "related_to"},
            ("entity_b", "entity_c"): {"description": "B connects to C", "relation_type": "connects_to"},
        }

    async def get_all_nodes(self):
        return [(k, v) for k, v in self._nodes.items()]

    async def get_all_edges(self):
        return [(s, t, d) for (s, t), d in self._edges.items()]

    async def get_node(self, node_id):
        return self._nodes.get(node_id)

    async def get_node_edges(self, node_id):
        result = []
        for (s, t) in self._edges:
            if s == node_id or t == node_id:
                result.append((s, t))
        return result or None

    async def get_edge(self, src, tgt):
        return self._edges.get((src, tgt))


# ═══════════════════════════════════════════════════════════════════
# RuleCritic Tests
# ═══════════════════════════════════════════════════════════════════

class TestRuleCritic:
    def test_all_rules_pass(self):
        async def _run():
            critic = RuleCritic()
            critic.add_rule("min_answer", min_answer_length(5), weight=1.0)
            critic.add_rule("min_question", min_question_length(5), weight=1.0)
            critic.add_rule("not_identical", answer_not_identical_to_question(), weight=1.0)

            qa = {"question": "What is credit risk?", "answer": "Credit risk is the potential for loss."}
            result = await critic.validate(qa, {})

            assert result.passed
            assert result.score == 1.0

        asyncio.run(_run())

    def test_rule_fails(self):
        async def _run():
            critic = RuleCritic()
            critic.add_rule("min_answer", min_answer_length(100), weight=1.0)

            qa = {"question": "What?", "answer": "Short."}
            result = await critic.validate(qa, {})

            assert not result.passed
            assert result.score < 1.0

        asyncio.run(_run())

    def test_identical_qa_fails(self):
        async def _run():
            critic = RuleCritic()
            critic.add_rule("not_identical", answer_not_identical_to_question(), weight=1.0)

            qa = {"question": "Some text", "answer": "Some text"}
            result = await critic.validate(qa, {})

            assert not result.passed

        asyncio.run(_run())

    def test_keyword_overlap_rule(self):
        async def _run():
            critic = RuleCritic()
            critic.add_rule("keywords", answer_contains_keywords(1))

            qa = {"question": "Q?", "answer": "The credit risk is high."}
            ctx = {"subgraph_text": "Credit risk assessment is important."}

            result = await critic.validate(qa, ctx)
            assert result.passed

        asyncio.run(_run())

    def test_no_rules_passes(self):
        async def _run():
            critic = RuleCritic()
            result = await critic.validate({}, {})
            assert result.passed
            assert result.score == 1.0

        asyncio.run(_run())

    def test_custom_rule(self):
        async def _run():
            critic = RuleCritic()
            critic.add_rule(
                "has_period",
                lambda qa, ctx: qa.get("answer", "").endswith("."),
                weight=1.0,
                description="Answer must end with a period",
            )

            result1 = await critic.validate(
                {"question": "Q?", "answer": "Answer text."}, {},
            )
            assert result1.passed

            result2 = await critic.validate(
                {"question": "Q?", "answer": "No period"}, {},
            )
            assert not result2.passed

        asyncio.run(_run())


# ═══════════════════════════════════════════════════════════════════
# LLMCritic Tests
# ═══════════════════════════════════════════════════════════════════

class TestLLMCritic:
    def test_parse_valid_response(self):
        async def _run():
            mock_llm = AsyncMock()
            critic_response = json.dumps({
                "factual_accuracy": 0.9,
                "logical_coherence": 0.8,
                "completeness": 0.85,
                "relevance": 0.9,
                "overall_score": 0.86,
                "passed": True,
                "reason": "Well-formed QA pair",
                "suggestions": [],
            })
            mock_llm.generate_answer = AsyncMock(return_value=critic_response)

            critic = LLMCritic(llm_client=mock_llm)
            qa = {"question": "What is credit risk?", "answer": "It is the risk of default."}
            ctx = {"subgraph_text": "Credit risk relates to default probability."}

            result = await critic.validate(qa, ctx)
            assert result.passed
            assert result.score > 0.8

        asyncio.run(_run())

    def test_parse_failing_response(self):
        async def _run():
            mock_llm = AsyncMock()
            critic_response = json.dumps({
                "overall_score": 0.2,
                "passed": False,
                "reason": "Answer is factually incorrect",
                "suggestions": ["Check the context"],
            })
            mock_llm.generate_answer = AsyncMock(return_value=critic_response)

            critic = LLMCritic(llm_client=mock_llm)
            result = await critic.validate(
                {"question": "Q?", "answer": "Wrong answer"},
                {"subgraph_text": "Some context"},
            )
            assert not result.passed

        asyncio.run(_run())

    def test_empty_qa_fails(self):
        async def _run():
            critic = LLMCritic(llm_client=AsyncMock())
            result = await critic.validate({"question": "", "answer": ""}, {})
            assert not result.passed
            assert result.score == 0.0

        asyncio.run(_run())

    def test_no_context_passes_by_default(self):
        async def _run():
            critic = LLMCritic(llm_client=AsyncMock())
            result = await critic.validate(
                {"question": "Q?", "answer": "A."},
                {},  # No context
            )
            assert result.passed

        asyncio.run(_run())


# ═══════════════════════════════════════════════════════════════════
# DAToGPipeline Tests
# ═══════════════════════════════════════════════════════════════════

class TestDAToGPipeline:
    def _make_pipeline(self, llm_response: str = None):
        tree = TaxonomyTree.from_dict(SAMPLE_TREE)
        graph = MockGraphStorage()
        adapter = NetworkXGraphAdapter(graph_storage=graph)

        mock_llm = AsyncMock()
        if llm_response is None:
            llm_response = "Question: What is entity A?\nAnswer: Entity A is a concept that relates to B and is described as Entity A description."
        mock_llm.generate_answer = AsyncMock(return_value=llm_response)

        # Use rule critic (no LLM needed)
        critic = RuleCritic()
        critic.add_rule("min_answer", min_answer_length(5), weight=1.0)
        critic.add_rule("not_identical", answer_not_identical_to_question(), weight=1.0)

        return DAToGPipeline(
            taxonomy_tree=tree,
            graph_adapter=adapter,
            llm_client=mock_llm,
            critic=critic,
            sampling_strategy="coverage",
            seed=42,
        )

    def test_pipeline_run(self):
        async def _run():
            pipeline = self._make_pipeline()
            results = await pipeline.run(target_count=3, batch_size=5)
            assert len(results) > 0
            for qa in results:
                assert "question" in qa
                assert "answer" in qa
                assert "metadata" in qa
                assert qa["metadata"]["pipeline"] == "datog"

        asyncio.run(_run())

    def test_pipeline_stats(self):
        async def _run():
            pipeline = self._make_pipeline()
            await pipeline.run(target_count=2, batch_size=3)
            stats = pipeline.get_statistics()
            assert "taxonomy" in stats
            assert "coverage" in stats
            assert stats["coverage"]["overall"] > 0

        asyncio.run(_run())

    def test_pipeline_metadata(self):
        async def _run():
            pipeline = self._make_pipeline()
            results = await pipeline.run(target_count=1, batch_size=3)
            if results:
                meta = results[0]["metadata"]
                assert "intent_id" in meta
                assert "intent_name" in meta
                assert "cognitive_dimension" in meta

        asyncio.run(_run())

    def test_pipeline_critic_rejection(self):
        """Pipeline with very strict critic should reject short answers."""
        async def _run():
            pipeline = self._make_pipeline()
            # LLM returns very short answer
            pipeline.llm_client.generate_answer = AsyncMock(return_value="Question: Q?\nAnswer: A.")

            strict_critic = RuleCritic()
            strict_critic.add_rule("min_answer", min_answer_length(100), weight=1.0)

            pipeline.critic = strict_critic
            results = await pipeline.run(target_count=5, batch_size=5)
            # Strict critic should reject short answers
            assert len(results) == 0

        asyncio.run(_run())

    def test_pipeline_no_critic(self):
        """Pipeline without critic should accept everything."""
        async def _run():
            pipeline = self._make_pipeline()
            pipeline.llm_client.generate_answer = AsyncMock(return_value="Question: What?\nAnswer: Some answer text here.")

            pipeline.critic = None  # No critic
            results = await pipeline.run(target_count=2, batch_size=3)
            assert len(results) > 0

        asyncio.run(_run())

    def test_parse_qa_response(self):
        pipeline = self._make_pipeline()

        # English format
        qa = pipeline.generator.parse_response("Question: What is A?\nAnswer: A is B.")
        assert qa is not None
        key = list(qa.keys())[0]
        assert qa[key]["question"] == "What is A?"
        assert qa[key]["answer"] == "A is B."

        # Chinese format
        qa_cn = pipeline.generator.parse_response("问题：信用风险是什么？\n答案：信用风险是指违约的可能性。")
        assert qa_cn is not None
        key = list(qa_cn.keys())[0]
        assert "信用风险" in qa_cn[key]["question"]

    def test_parse_qa_response_fallback(self):
        pipeline = self._make_pipeline()
        # No markers, fallback to first-line = question (if double newline present)
        qa = pipeline.generator.parse_response("First line\n\nSecond line\nThird line")
        assert qa is not None
        key = list(qa.keys())[0]
        assert qa[key]["question"] == "First line"
        assert "Second line" in qa[key]["answer"]
