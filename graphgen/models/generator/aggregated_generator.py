from typing import Any

from graphgen.bases import BaseGenerator
from graphgen.templates import AGGREGATED_GENERATION_PROMPT
from graphgen.utils import compute_content_hash, detect_main_language, logger


class AggregatedGenerator(BaseGenerator):
    """
    Aggregated Generator follows a TWO-STEP process:
    1. rephrase: Rephrase the input nodes and edges into a coherent text that maintains the original meaning.
                 The rephrased text is considered as answer to be used in the next step.
    2. question generation: Generate relevant questions based on the rephrased text.
    
    Can also use COMBINED mode to generate both in one step (reduces 50% of API calls).
    """
    
    def __init__(self, llm_client, use_combined_mode: bool = False):
        """
        初始化 Aggregated 生成器
        
        :param llm_client: LLM客户端
        :param use_combined_mode: 是否使用合并模式（一次性生成重述文本和问题，减少50%调用）
        """
        super().__init__(llm_client)
        self.use_combined_mode = use_combined_mode

    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        """
        Build prompts for REPHRASE.
        :param batch
        :return:
        """
        nodes, edges = batch
        entities_str = "\n".join(
            [
                f"{index + 1}. {node[0]}: {node[1]['description']}"
                for index, node in enumerate(nodes)
            ]
        )
        relations_str = "\n".join(
            [
                f"{index + 1}. {edge[0]} -- {edge[1]}: {edge[2]['description']}"
                for index, edge in enumerate(edges)
            ]
        )
        language = detect_main_language(entities_str + relations_str)

        # TODO: configure add_context
        #     if add_context:
        #         original_ids = [
        #             node["source_id"].split("<SEP>")[0] for node in _process_nodes
        #         ] + [edge[2]["source_id"].split("<SEP>")[0] for edge in _process_edges]
        #         original_ids = list(set(original_ids))
        #         original_text = await text_chunks_storage.get_by_ids(original_ids)
        #         original_text = "\n".join(
        #             [
        #                 f"{index + 1}. {text['content']}"
        #                 for index, text in enumerate(original_text)
        #             ]
        #         )
        prompt = AGGREGATED_GENERATION_PROMPT[language]["ANSWER_REPHRASING"].format(
            entities=entities_str, relationships=relations_str
        )
        return prompt

    @staticmethod
    def parse_rephrased_text(response: str) -> str:
        """
        Parse the rephrased text from the response.
        :param response:
        :return: rephrased text
        """
        if "Rephrased Text:" in response:
            rephrased_text = response.split("Rephrased Text:")[1].strip()
        elif "重述文本:" in response:
            rephrased_text = response.split("重述文本:")[1].strip()
        else:
            rephrased_text = response.strip()
        return rephrased_text.strip('"')

    @staticmethod
    def build_combined_prompt(
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        """
        构建合并模式的提示词（一次性生成重述文本和问题）
        """
        nodes, edges = batch
        entities_str = "\n".join(
            [
                f"{index + 1}. {node[0]}: {node[1]['description']}"
                for index, node in enumerate(nodes)
            ]
        )
        relations_str = "\n".join(
            [
                f"{index + 1}. {edge[0]} -- {edge[1]}: {edge[2]['description']}"
                for index, edge in enumerate(edges)
            ]
        )
        language = detect_main_language(entities_str + relations_str)
        prompt = AGGREGATED_GENERATION_PROMPT[language]["AGGREGATED_COMBINED"].format(
            entities=entities_str, relationships=relations_str
        )
        return prompt
    
    @staticmethod
    def parse_combined_response(response: str) -> dict:
        """
        解析合并模式的响应（包含重述文本和问题）
        """
        import re
        
        # Pre-processing: Remove common meta-descriptions and preambles
        response_clean = response.strip()
        meta_prefixes = [
            r"^(?:Here is|This is|Below is).*?(?:rephrased text|question).*?[：:]\s*",
            r"^(?:以下是|这是).*?(?:重述|问题).*?[：:]\s*",
            r"^根据.*?(?:以下是|如下)[：:]\s*",
            r"^Based on.*?(?:here is|as follows)[：:]\s*",
            r"^(?:好的|好|OK)[，,。.]\s*",
        ]
        for pattern in meta_prefixes:
            response_clean = re.sub(pattern, "", response_clean, flags=re.IGNORECASE)
        response_clean = response_clean.strip()
        
        result = {}
        
        # 尝试解析重述文本
        if "Rephrased Text:" in response_clean:
            rephrased_part = response_clean.split("Rephrased Text:")[1]
            if "Question:" in rephrased_part:
                rephrased_text = rephrased_part.split("Question:")[0].strip()
            else:
                rephrased_text = rephrased_part.strip()
        elif "重述文本:" in response_clean:
            rephrased_part = response_clean.split("重述文本:")[1]
            if "问题：" in rephrased_part or "问题:" in rephrased_part:
                # 处理中文冒号和英文冒号的情况
                if "问题：" in rephrased_part:
                    rephrased_text = rephrased_part.split("问题：")[0].strip()
                else:
                    rephrased_text = rephrased_part.split("问题:")[0].strip()
            else:
                rephrased_text = rephrased_part.strip()
        else:
            logger.warning("Failed to parse rephrased text from combined response (length: %d): %s", 
                         len(response_clean), response_clean[:300])
            return {}
        
        # 尝试解析问题
        if "Question:" in response_clean:
            question = response_clean.split("Question:")[1].strip()
        elif "问题：" in response_clean:
            question = response_clean.split("问题：")[1].strip()
        elif "问题:" in response_clean:
            question = response_clean.split("问题:")[1].strip()
        else:
            logger.warning("Failed to parse question from combined response (length: %d): %s",
                         len(response_clean), response_clean[:300])
            return {}
        
        rephrased_text = rephrased_text.strip('"')
        question = question.strip('"')
        
        logger.debug("Aggregated Combined - Rephrased Text: %s", rephrased_text)
        logger.debug("Aggregated Combined - Question: %s", question)
        
        return {
            "rephrased_text": rephrased_text,
            "question": question,
        }
    
    @staticmethod
    def _build_prompt_for_question_generation(answer: str) -> str:
        """
        Build prompts for QUESTION GENERATION.
        :param answer:
        :return:
        """
        language = detect_main_language(answer)
        prompt = AGGREGATED_GENERATION_PROMPT[language]["QUESTION_GENERATION"].format(
            answer=answer
        )
        return prompt

    @staticmethod
    def parse_response(response: str) -> dict:
        if response.startswith("Question:"):
            question = response[len("Question:") :].strip()
        elif response.startswith("问题："):
            question = response[len("问题：") :].strip()
        else:
            question = response.strip()
        return {
            "question": question,
        }

    async def generate(
        self,
        batch: tuple[
            list[tuple[str, dict]], list[tuple[Any, Any, dict] | tuple[Any, Any, Any]]
        ],
        chunks_storage=None,
        full_docs_storage=None,
    ) -> dict[str, Any]:
        """
        Generate QAs based on a given batch.
        :param batch
        :param chunks_storage: chunks storage instance
        :param full_docs_storage: full documents storage instance
        :return: QA pairs
        """
        result = {}
        
        if self.use_combined_mode:
            # 合并模式：一次性生成重述文本和问题（减少50%调用）
            prompt = self.build_combined_prompt(batch)
            response = await self.llm_client.generate_answer(prompt)
            parsed = self.parse_combined_response(response)
            
            if not parsed or "question" not in parsed or "rephrased_text" not in parsed:
                logger.warning("Failed to parse combined Aggregated response, falling back to two-step mode")
                # 回退到两步模式
                rephrasing_prompt = self.build_prompt(batch)
                response = await self.llm_client.generate_answer(rephrasing_prompt)
                context = self.parse_rephrased_text(response)
                question_generation_prompt = self._build_prompt_for_question_generation(context)
                response = await self.llm_client.generate_answer(question_generation_prompt)
                question = self.parse_response(response)["question"]
            else:
                question = parsed["question"]
                context = parsed["rephrased_text"]
        else:
            # 原始两步模式
            rephrasing_prompt = self.build_prompt(batch)
            response = await self.llm_client.generate_answer(rephrasing_prompt)
            context = self.parse_rephrased_text(response)
            question_generation_prompt = self._build_prompt_for_question_generation(context)
            response = await self.llm_client.generate_answer(question_generation_prompt)
            question = self.parse_response(response)["question"]
        
        logger.debug("Question: %s", question)
        logger.debug("Answer: %s", context)
        qa_pairs = {
            compute_content_hash(question): {
                "question": question,
                "answer": context,
            }
        }
        
        # Add context and source information using helper function
        from graphgen.bases.base_generator import _add_context_and_source_info
        await _add_context_and_source_info(
            qa_pairs,
            batch,
            chunks_storage,
            full_docs_storage,
            "aggregated"
        )
        
        result.update(qa_pairs)
        return result
