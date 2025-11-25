import random
from typing import Any, Optional, Tuple

from graphgen.bases import BaseGenerator
from graphgen.templates import (
    ATOMIC_GENERATION_PROMPT,
    ATOMIC_GENERATION_PROMPT_VARIANTS,
    ATOMIC_QUESTION_PROMPT,
)
from graphgen.utils import compute_content_hash, detect_main_language, logger


def _extract_question_and_answer(response: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse response and return (language_marker, question, answer)
    """
    if not response or not response.strip():
        logger.warning("Empty response received")
        return None, None, None
    
    # Try various marker combinations
    markers = [
        ("Question:", "Answer:", "en"),
        ("问题：", "答案：", "zh"),
        ("Q:", "A:", "en"),
        ("问：", "答：", "zh"),
    ]
    
    for question_marker, answer_marker, lang in markers:
        if question_marker in response:
            try:
                if answer_marker in response:
                    question = response.split(question_marker, 1)[1].split(answer_marker, 1)[0].strip()
                    answer = response.split(answer_marker, 1)[1].strip()
                    # Remove any trailing markers or extra content
                    answer = answer.split("\n")[0].strip() if "\n" in answer else answer
                else:
                    question = response.split(question_marker, 1)[1].strip()
                    answer = None
                
                # Clean up question and answer
                question = question.strip('"').strip("'").strip()
                if answer:
                    answer = answer.strip('"').strip("'").strip()
                
                if question:  # At least question should be present
                    return lang, question, answer
            except (IndexError, ValueError) as e:
                logger.debug("Error parsing with markers %s/%s: %s", question_marker, answer_marker, e)
                continue
    
    # If no standard markers found, try to extract as plain text (fallback)
    response_clean = response.strip()
    if len(response_clean) > 10:  # Only log if response has meaningful content
        logger.warning(
            "Failed to parse response (no standard markers found): %s",
            response_clean[:200] if len(response_clean) > 200 else response_clean
        )
    return None, None, None


class AtomicGenerator(BaseGenerator):
    def __init__(self, llm_client, use_multi_template: bool = True, template_seed: Optional[int] = None):
        """
        Initialize AtomicGenerator with optional multi-template support.
        
        :param llm_client: LLM client instance
        :param use_multi_template: Whether to use multiple template variants for diversity
        :param template_seed: Optional seed for template selection (for reproducibility)
        """
        super().__init__(llm_client)
        self.use_multi_template = use_multi_template
        self.template_seed = template_seed
        if template_seed is not None:
            random.seed(template_seed)
        self._generation_mode = "atomic"

    @staticmethod
    def _build_context(batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]) -> tuple[str, str]:
        nodes, edges = batch
        context = ""
        for node in nodes:
            context += f"- {node[0]}: {node[1]['description']}\n"
        for edge in edges:
            context += f"- {edge[0]} - {edge[1]}: {edge[2]['description']}\n"
        language = detect_main_language(context)
        return context, language

    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        """
        Build prompt for LLM based on the given batch.
        Supports multi-template sampling for diversity.
        """
        context, language = self._build_context(batch)

        # Use multi-template sampling if enabled
        if self.use_multi_template and language in ATOMIC_GENERATION_PROMPT_VARIANTS:
            templates = ATOMIC_GENERATION_PROMPT_VARIANTS[language]
            selected_template = random.choice(templates)
            logger.debug("Selected template variant for language %s", language)
        else:
            selected_template = ATOMIC_GENERATION_PROMPT[language]

        prompt = selected_template.format(context=context)
        return prompt

    @staticmethod
    def parse_response(response: str) -> dict:
        """
        Parse response that may contain multiple QA pairs.
        Supports multiple formats:
        - Single QA pair: "Question: ... Answer: ..."
        - Multiple QA pairs separated by "** **" or similar markers
        :param response:
        :return:
        """
        result = {}
        
        # Try to split by common separators first
        separators = ["** **", "**", "\n\n", "---"]
        parts = [response]
        for sep in separators:
            if sep in response:
                parts = response.split(sep)
                break
        
        # Parse each part
        for part in parts:
            part = part.strip()
            if not part:
                continue
            lang, question, answer = _extract_question_and_answer(part)
            if question and answer:
                q_hash = compute_content_hash(question)
                if q_hash not in result:
                    result[q_hash] = {
                        "question": question,
                        "answer": answer,
                    }
                    logger.debug("Parsed QA pair: Q=%s, A=%s", question[:50], answer[:50])
            elif question:
                # Only question found, might be from question-only stage
                q_hash = compute_content_hash(question)
                if q_hash not in result:
                    result[q_hash] = {
                        "question": question,
                        "answer": "",
                    }
        
        if not result:
            logger.warning("Failed to parse any QA pairs from response: %s", response[:200])
        
        return result


class AtomicQuestionGenerator(AtomicGenerator):
    """
    Generator that only produces questions (used for two-phase generation).
    """

    def __init__(self, llm_client, use_multi_template: bool = True, template_seed: Optional[int] = None):
        super().__init__(llm_client, use_multi_template, template_seed)
        self._generation_mode = "atomic_question"

    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        context, language = self._build_context(batch)
        template = ATOMIC_QUESTION_PROMPT.get(language, ATOMIC_QUESTION_PROMPT["en"])
        return template.format(context=context)

    @staticmethod
    def parse_response(response: str) -> dict:
        _, question, _ = _extract_question_and_answer(response)
        if not question:
            return {}
        logger.debug("Question (question-only stage): %s", question)
        return {
            compute_content_hash(question): {
                "question": question,
                "answer": "",
            }
        }

