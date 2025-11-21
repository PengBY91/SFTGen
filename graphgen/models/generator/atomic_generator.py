import random
from typing import Any, Optional

from graphgen.bases import BaseGenerator
from graphgen.templates import ATOMIC_GENERATION_PROMPT, ATOMIC_GENERATION_PROMPT_VARIANTS
from graphgen.utils import compute_content_hash, detect_main_language, logger


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

    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        """
        Build prompt for LLM based on the given batch.
        Supports multi-template sampling for diversity.
        """
        nodes, edges = batch
        context = ""
        for node in nodes:
            context += f"- {node[0]}: {node[1]['description']}\n"
        for edge in edges:
            context += f"- {edge[0]} - {edge[1]}: {edge[2]['description']}\n"
        language = detect_main_language(context)

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
        AtomicGenerator normally generates one QA pair per response.
        So we just need to parse one QA pair from the response.
        :param response:
        :return:
        """
        if "Question:" in response and "Answer:" in response:
            question = response.split("Question:")[1].split("Answer:")[0].strip()
            answer = response.split("Answer:")[1].strip()
        elif "问题：" in response and "答案：" in response:
            question = response.split("问题：")[1].split("答案：")[0].strip()
            answer = response.split("答案：")[1].strip()
        else:
            logger.warning("Failed to parse response: %s", response)
            return {}
        question = question.strip('"')
        answer = answer.strip('"')
        logger.debug("Question: %s", question)
        logger.debug("Answer: %s", answer)
        return {
            compute_content_hash(question): {
                "question": question,
                "answer": answer,
            }
        }


