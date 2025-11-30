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
    
    import re
    response_clean = response.strip()
    
    # Pre-processing: Remove common meta-descriptions and preambles that LLMs often add
    meta_prefixes = [
        r"^根据您提供的文本段落[，,]\s*以下是.*?[：:]\s*",
        r"^根据.*?文本[，,]\s*以下是.*?[：:]\s*",
        r"^以下是.*?生成.*?问答对.*?[：:]\s*",
        r"^根据.*?以下是.*?[：:]\s*",
        r"^Based on the (?:text|passage|content).*?here is.*?[：:]\s*",
        r"^Here is (?:a|the) (?:QA|question-answer) pair.*?[：:]\s*",
        r"^(?:好的|好|OK)[，,。.]\s*",
        r"^\s*[\*\-]\s*",  # Remove leading bullets
    ]
    
    for pattern in meta_prefixes:
        response_clean = re.sub(pattern, "", response_clean, flags=re.IGNORECASE)
    
    response_clean = response_clean.strip()
    
    # First, check if response only has answer marker (no question marker)
    # This happens when LLM only returns answer without question
    answer_only_markers = ["答案：", "Answer:", "A:", "答："]
    question_markers = ["问题：", "Question:", "Q:", "问："]
    
    has_answer_marker = any(marker in response_clean for marker in answer_only_markers)
    has_question_marker = any(marker in response_clean for marker in question_markers)
    
    # If only answer marker exists, extract answer only
    if has_answer_marker and not has_question_marker:
        for answer_marker in answer_only_markers:
            if answer_marker in response_clean:
                try:
                    answer = response_clean.split(answer_marker, 1)[1].strip()
                    # Clean up answer
                    answer = answer.strip('"').strip("'").strip()
                    # Remove trailing markers if any
                    for q_marker in question_markers:
                        if q_marker in answer:
                            answer = answer.split(q_marker, 1)[0].strip()
                    if answer:
                        logger.debug("Extracted answer-only response: %s", answer[:100])
                        return "zh" if "答案" in answer_marker or "答" in answer_marker else "en", None, answer
                except (IndexError, ValueError):
                    continue
    
    # Try various marker combinations for full QA pairs
    markers = [
        ("Question:", "Answer:", "en"),
        ("问题：", "答案：", "zh"),
        ("Q:", "A:", "en"),
        ("问：", "答：", "zh"),
    ]
    
    for question_marker, answer_marker, lang in markers:
        if question_marker in response_clean:
            try:
                # Find positions of markers
                q_pos = response_clean.find(question_marker)
                a_pos = response_clean.find(answer_marker, q_pos + len(question_marker))
                
                if a_pos > q_pos:  # Answer marker comes after question marker
                    # Extract question (between question marker and answer marker)
                    question = response_clean[q_pos + len(question_marker):a_pos].strip()
                    # Extract answer (after answer marker)
                    answer = response_clean[a_pos + len(answer_marker):].strip()
                    
                    # Clean up question - remove any answer markers that might be inside
                    for am in answer_only_markers:
                        if am in question:
                            question = question.split(am, 1)[0].strip()
                    
                    # Clean up answer - remove any question markers that might be inside
                    for qm in question_markers:
                        if qm in answer:
                            answer = answer.split(qm, 1)[0].strip()
                    
                    # Remove trailing markers or extra content
                    question = question.strip('"').strip("'").strip()
                    answer = answer.strip('"').strip("'").strip()
                    
                    # Remove newlines and extra whitespace, but keep meaningful content
                    if "\n" in answer:
                        # Take first paragraph or until next major marker
                        answer_lines = answer.split("\n")
                        answer = answer_lines[0].strip()
                        # If first line is very short, try to get more
                        if len(answer) < 20 and len(answer_lines) > 1:
                            answer = " ".join(answer_lines[:2]).strip()
                    
                    if question and not question.startswith("答案") and not question.startswith("Answer"):
                        if answer:
                            return lang, question, answer
                        else:
                            # Question found but no answer
                            return lang, question, None
                else:
                    # Question marker found but answer marker comes before it or not found
                    question = response_clean[q_pos + len(question_marker):].strip()
                    # Remove any answer markers from question
                    for am in answer_only_markers:
                        if am in question:
                            question = question.split(am, 1)[0].strip()
                    question = question.strip('"').strip("'").strip()
                    if question and not question.startswith("答案") and not question.startswith("Answer"):
                        return lang, question, None
            except (IndexError, ValueError) as e:
                logger.debug("Error parsing with markers %s/%s: %s", question_marker, answer_marker, e)
                continue
    
    # If no standard markers found, try to extract as plain text (fallback)
    # Try to extract question and answer from plain text format
    response_clean = response.strip()
    
    # Try to find question and answer in plain text format (e.g., "Q: ... A: ..." or just "Question: ... Answer: ...")
    # Look for common patterns
    import re
    
    # Pattern 1: Question and Answer on separate lines
    qa_patterns = [
        (r"(?:Question|问题)[：:]\s*(.+?)(?:\n\s*(?:Answer|答案)[：:]\s*(.+?))?$", re.DOTALL),
        (r"Q[：:]\s*(.+?)(?:\n\s*A[：:]\s*(.+?))?$", re.DOTALL),
        (r"问[：:]\s*(.+?)(?:\n\s*答[：:]\s*(.+?))?$", re.DOTALL),
    ]
    
    for pattern, flags in qa_patterns:
        match = re.search(pattern, response_clean, flags)
        if match:
            question = match.group(1).strip().strip('"').strip("'")
            answer = match.group(2).strip().strip('"').strip("'") if match.lastindex >= 2 and match.group(2) else None
            if question:
                return "en", question, answer
    
    # If still no match, try to extract as single question-answer pair
    # Assume the entire response might be an answer if it's reasonably long
    if len(response_clean) > 10:
        # Try to split by common separators
        parts = re.split(r"[。\n]+", response_clean)
        if len(parts) >= 2:
            # First part might be question, rest is answer
            potential_q = parts[0].strip()
            potential_a = "。".join(parts[1:]).strip()
            if len(potential_q) > 5 and len(potential_a) > 5:
                return "zh", potential_q, potential_a
        
        # Last resort: treat entire response as answer if no question marker found
        # This handles cases where LLM only returns answer
        logger.warning(
            "No question marker found, treating entire response as answer: %s",
            response_clean[:200] if len(response_clean) > 200 else response_clean
        )
        # Return None for question to indicate parsing failure
        return None, None, None
    
    return None, None, None


class AtomicGenerator(BaseGenerator):
    def __init__(self, llm_client, use_multi_template: bool = True, template_seed: Optional[int] = None, chinese_only: bool = False):
        """
        Initialize AtomicGenerator with optional multi-template support.
        
        :param llm_client: LLM client instance
        :param use_multi_template: Whether to use multiple template variants for diversity
        :param template_seed: Optional seed for template selection (for reproducibility)
        :param chinese_only: Whether to generate only Chinese QA pairs
        """
        super().__init__(llm_client)
        self.use_multi_template = use_multi_template
        self.template_seed = template_seed
        self.chinese_only = chinese_only
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
        Supports multi-template sampling for diversity and Chinese-only mode.
        """
        context, language = self._build_context(batch)

        # Use Chinese-only templates if enabled
        if self.chinese_only:
            if self.use_multi_template:
                from graphgen.templates import ATOMIC_GENERATION_PROMPT_VARIANTS_CHINESE_ONLY
                if "zh" in ATOMIC_GENERATION_PROMPT_VARIANTS_CHINESE_ONLY:
                    templates = ATOMIC_GENERATION_PROMPT_VARIANTS_CHINESE_ONLY["zh"]
                    selected_template = random.choice(templates)
                    logger.debug("Selected Chinese-only template variant")
                else:
                    from graphgen.templates import ATOMIC_GENERATION_PROMPT_CHINESE_ONLY
                    selected_template = ATOMIC_GENERATION_PROMPT_CHINESE_ONLY.get("zh")
            else:
                from graphgen.templates import ATOMIC_GENERATION_PROMPT_CHINESE_ONLY
                selected_template = ATOMIC_GENERATION_PROMPT_CHINESE_ONLY.get("zh")
        # Use multi-template sampling if enabled
        elif self.use_multi_template and language in ATOMIC_GENERATION_PROMPT_VARIANTS:
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
        
        # First try to parse the whole response as a single QA pair
        # This is more robust than splitting first, as splitting can break up valid QA pairs
        lang, question, answer = _extract_question_and_answer(response)
        
        if question and answer:
            # Successfully parsed as single QA pair, return it
            q_hash = compute_content_hash(question)
            result[q_hash] = {
                "question": question,
                "answer": answer,
            }
            logger.debug("Parsed single QA pair: Q=%s, A=%s", question[:50], answer[:50])
            return result
        
        # If single parse failed, try splitting by common separators
        separators = ["** **", "**", "\n\n---\n\n", "---"]
        parts = [response]
        for sep in separators:
            if sep in response:
                parts = response.split(sep)
                logger.debug("Split response by separator '%s' into %d parts", sep, len(parts))
                break
        
        # Parse each part
        for idx, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            lang, question, answer = _extract_question_and_answer(part)
            
            # Handle answer-only responses (from two-stage generation where question is already known)
            if not question and answer:
                # This is an answer-only response, which is valid in two-stage generation
                # We'll skip it here as it should be handled by the answer generation stage
                logger.debug("Answer-only response found in part %d (skipping, should be handled by answer stage): %s", idx, answer[:100])
                continue
            
            if question and answer:
                q_hash = compute_content_hash(question)
                if q_hash not in result:
                    result[q_hash] = {
                        "question": question,
                        "answer": answer,
                    }
                    logger.debug("Parsed QA pair from part %d: Q=%s, A=%s", idx, question[:50], answer[:50])
            elif question:
                # Only question found, might be from question-only stage
                # Check if question actually contains answer marker (parsing error)
                answer_markers_in_q = ["答案：", "Answer:", "A:", "答："]
                for am in answer_markers_in_q:
                    if am in question:
                        # This is actually an answer, not a question
                        # Try to extract properly
                        try:
                            actual_answer = question.split(am, 1)[1].strip()
                            actual_answer = actual_answer.strip('"').strip("'").strip()
                            if actual_answer:
                                logger.debug("Corrected: extracted answer from misparsed question: %s", actual_answer[:100])
                                # This is answer-only, skip it as we don't have a question
                                continue
                        except:
                            pass
                
                # Try to extract answer from the remaining text
                remaining_text = part.replace(question, "").strip()
                # Remove question markers and clean up
                for marker in ["Question:", "问题：", "Q:", "问："]:
                    remaining_text = remaining_text.replace(marker, "").strip()
                
                # Remove answer markers that might be in remaining text
                for marker in ["答案：", "Answer:", "A:", "答："]:
                    if marker in remaining_text:
                        remaining_text = remaining_text.split(marker, 1)[1].strip()
                        break
                
                # If there's substantial remaining text, treat it as answer
                answer = remaining_text if len(remaining_text) > 10 else ""
                
                # Final validation: question should not start with answer markers
                if question.startswith("答案") or question.startswith("Answer") or question.startswith("A:") or question.startswith("答："):
                    logger.warning("Question appears to be misparsed (starts with answer marker): %s", question[:100])
                    continue
                
                q_hash = compute_content_hash(question)
                if q_hash not in result:
                    result[q_hash] = {
                        "question": question,
                        "answer": answer,
                    }
                    if not answer:
                        logger.warning("Question found but no answer extracted from part %d: %s", idx, question[:100])
                    else:
                        logger.debug("Parsed question with answer from part %d: Q=%s", idx, question[:50])
        
        if not result:
            logger.warning("Failed to parse any QA pairs from response (length: %d): %s", len(response), response[:300])
        
        return result


class AtomicQuestionGenerator(AtomicGenerator):
    """
    Generator that only produces questions (used for two-phase generation).
    """

    def __init__(self, llm_client, use_multi_template: bool = True, template_seed: Optional[int] = None, chinese_only: bool = False):
        super().__init__(llm_client, use_multi_template, template_seed, chinese_only)
        self._generation_mode = "atomic_question"

    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        context, language = self._build_context(batch)
        
        # Use Chinese-only templates if enabled
        if self.chinese_only:
            from graphgen.templates import ATOMIC_QUESTION_PROMPT_CHINESE_ONLY
            template = ATOMIC_QUESTION_PROMPT_CHINESE_ONLY.get("zh", ATOMIC_QUESTION_PROMPT["zh"])
        else:
            template = ATOMIC_QUESTION_PROMPT.get(language, ATOMIC_QUESTION_PROMPT["en"])
        return template.format(context=context)

    @staticmethod
    def parse_response(response: str) -> dict:
        """
        Parse response from question generation stage.
        Expected: Only question (starting with "问题：" or "Question:")
        But LLM might return: Full QA pair or answer-only response
        """
        lang, question, answer = _extract_question_and_answer(response)
        
        # Case 1: Question found (expected case)
        if question:
            logger.debug("Question (question-only stage): %s", question)
            return {
                compute_content_hash(question): {
                    "question": question,
                    "answer": "",
                }
            }
        
        # Case 2: Only answer found (LLM misunderstood the prompt)
        # We should try to generate a question from the answer, or skip it
        if answer and not question:
            logger.warning(
                "LLM returned answer instead of question in question generation stage. "
                "Answer: %s. This will be skipped as we cannot infer the question.",
                answer[:100]
            )
            # Skip this response - we cannot generate a question from an answer reliably
            return {}
        
        # Case 3: Neither question nor answer found (parsing failure)
        logger.warning(
            "Failed to parse question from response in question generation stage: %s",
            response[:200] if len(response) > 200 else response
        )
        return {}

