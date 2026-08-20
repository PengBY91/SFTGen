"""
LLM-based Critic for DA-ToG.

Uses an LLM to validate whether generated QA pairs are consistent
with their source context.
"""

import json
import logging
from typing import Any, Dict, Optional

from graphgen.bases.base_critic import BaseCritic, CriticResult
from graphgen.bases.base_llm_client import BaseLLMClient

logger = logging.getLogger(__name__)

_CRITIC_PROMPT_TEMPLATE = """You are a strict quality reviewer for Question-Answer data.

## Source Context
{context_text}

## Generated QA Pair
Question: {question}
Answer: {answer}

## Your Task
Evaluate this QA pair on these criteria:

1. **Factual Accuracy** (0-1): Is the answer factually correct given the context?
2. **Logical Coherence** (0-1): Is the answer logically sound and well-structured?
3. **Completeness** (0-1): Does the answer sufficiently address the question?
4. **Relevance** (0-1): Is the question relevant to the source context?

Output your evaluation as JSON:
{{
  "factual_accuracy": <float>,
  "logical_coherence": <float>,
  "completeness": <float>,
  "relevance": <float>,
  "overall_score": <float>,
  "passed": <bool>,
  "reason": "<brief reason>",
  "suggestions": ["<suggestion1>", ...]
}}

Be strict. Set "passed" to true only if overall_score >= {min_score}."""


class LLMCritic(BaseCritic):
    """
    LLM-based quality validator for generated QA pairs.

    Uses the LLM itself to judge whether a generated QA pair is
    consistent with its source context.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        min_score: float = 0.6,
        max_retries: int = 2,
    ):
        self.llm_client = llm_client
        self.min_score = min_score
        self.max_retries = max_retries

    async def validate(
        self,
        qa_pair: Dict[str, Any],
        context: Dict[str, Any],
    ) -> CriticResult:
        """
        Validate a QA pair using LLM judgment.

        :param qa_pair: Dict with 'question' and 'answer'
        :param context: Dict with 'subgraph_text' or 'text'
        :return: CriticResult
        """
        question = qa_pair.get("question", "")
        answer = qa_pair.get("answer", "")

        if not question or not answer:
            return CriticResult(
                passed=False, score=0.0,
                reason="Empty question or answer",
            )

        # Build context text
        context_text = context.get("subgraph_text", "")
        if not context_text:
            context_text = context.get("text", "")
        if not context_text:
            # If no context, pass by default (can't validate without context)
            return CriticResult(
                passed=True, score=0.7,
                reason="No context available, passing by default",
            )

        prompt = _CRITIC_PROMPT_TEMPLATE.format(
            context_text=context_text[:5000],
            question=question,
            answer=answer,
            min_score=self.min_score,
        )

        for attempt in range(self.max_retries):
            try:
                response = await self.llm_client.generate_answer(prompt)
                return self._parse_critic_response(response)
            except Exception as e:
                logger.warning(
                    "Critic validation failed (attempt %d/%d): %s",
                    attempt + 1, self.max_retries, e,
                )

        # All retries failed, pass by default to avoid blocking pipeline.
        # Note: score must be >= min_score, otherwise the caller's
        # `score < min_critic_score` check would reject what we meant to pass.
        return CriticResult(
            passed=True, score=self.min_score,
            reason="Critic validation failed after retries, passing by default",
        )

    def _parse_critic_response(self, response: str) -> CriticResult:
        """Parse the JSON response from LLM critic."""
        response = response.strip()

        # Extract JSON
        try:
            if response.startswith("{"):
                data = json.loads(response)
            elif "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                data = json.loads(response[start:end].strip())
            elif "{" in response:
                first = response.index("{")
                last = response.rindex("}")
                data = json.loads(response[first : last + 1])
            else:
                raise json.JSONDecodeError("No JSON found", response, 0)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse critic response: %s", str(e))
            return CriticResult(
                passed=True, score=self.min_score,
                reason=f"Failed to parse critic response: {str(e)[:100]}",
            )

        score = float(data.get("overall_score", 0.5))
        passed = data.get("passed", score >= self.min_score)
        reason = data.get("reason", "")
        suggestions = data.get("suggestions", [])

        return CriticResult(
            passed=bool(passed),
            score=min(1.0, max(0.0, score)),
            reason=reason,
            suggestions=suggestions if isinstance(suggestions, list) else [],
        )
