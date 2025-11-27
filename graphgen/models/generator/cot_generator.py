from typing import Any

from graphgen.bases import BaseGenerator
from graphgen.templates import COT_GENERATION_PROMPT
from graphgen.utils import compute_content_hash, detect_main_language, logger


class CoTGenerator(BaseGenerator):
    def __init__(self, llm_client, use_combined_mode: bool = False):
        """
        初始化 CoT 生成器
        
        :param llm_client: LLM客户端
        :param use_combined_mode: 是否使用合并模式（一次性生成问题和答案，减少50%调用）
        """
        super().__init__(llm_client)
        self.use_combined_mode = use_combined_mode
    
    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        """
        Build prompts for COT Template Design.
        :param batch:
        :return:
        """
        nodes, edges = batch
        entities_str = "\n".join(
            [
                f"{index + 1}. {node[0]}: {node[1]['description']}"
                for index, node in enumerate(nodes)
            ]
        )
        relationships_str = "\n".join(
            [
                f"{index + 1}. {edge[0]} -- {edge[1]}: {edge[2]['description']}"
                for index, edge in enumerate(edges)
            ]
        )
        language = detect_main_language(entities_str + relationships_str)
        prompt = COT_GENERATION_PROMPT[language]["COT_TEMPLATE_DESIGN"].format(
            entities=entities_str, relationships=relationships_str
        )
        return prompt

    @staticmethod
    def build_combined_prompt(
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        """
        构建合并模式的提示词（一次性生成问题和答案）
        """
        nodes, edges = batch
        entities_str = "\n".join(
            [
                f"{index + 1}. {node[0]}: {node[1]['description']}"
                for index, node in enumerate(nodes)
            ]
        )
        relationships_str = "\n".join(
            [
                f"{index + 1}. {edge[0]} -- {edge[1]}: {edge[2]['description']}"
                for index, edge in enumerate(edges)
            ]
        )
        language = detect_main_language(entities_str + relationships_str)
        prompt = COT_GENERATION_PROMPT[language]["COT_COMBINED"].format(
            entities=entities_str, relationships=relationships_str
        )
        return prompt
    
    @staticmethod
    def parse_combined_response(response: str) -> dict:
        """
        解析合并模式的响应（包含问题、推理路径和答案）
        """
        import re
        
        # Pre-processing: Remove common meta-descriptions and preambles
        response_clean = response.strip()
        meta_prefixes = [
            r"^(?:Here is|This is|Below is).*?(?:question|reasoning|answer).*?[：:]\s*",
            r"^(?:以下是|这是).*?(?:问题|推理|答案).*?[：:]\s*",
            r"^根据.*?(?:以下是|如下)[：:]\s*",
            r"^Based on.*?(?:here is|as follows)[：:]\s*",
            r"^(?:好的|好|OK)[，,。.]\s*",
        ]
        for pattern in meta_prefixes:
            response_clean = re.sub(pattern, "", response_clean, flags=re.IGNORECASE)
        response_clean = response_clean.strip()
        
        result = {}
        
        # 尝试解析问题
        if "Question:" in response_clean:
            question_part = response_clean.split("Question:")[1]
            if "Reasoning-Path Design:" in question_part:
                question = question_part.split("Reasoning-Path Design:")[0].strip()
            elif "Answer:" in question_part:
                question = question_part.split("Answer:")[0].strip()
            else:
                question = question_part.split("\n")[0].strip()
        elif "问题：" in response_clean:
            question_part = response_clean.split("问题：")[1]
            if "推理路径设计：" in question_part:
                question = question_part.split("推理路径设计：")[0].strip()
            elif "答案：" in question_part:
                question = question_part.split("答案：")[0].strip()
            else:
                question = question_part.split("\n")[0].strip()
        elif "问题:" in response_clean:  # 处理英文冒号的情况
            question_part = response_clean.split("问题:")[1]
            if "推理路径设计：" in question_part or "推理路径设计:" in question_part:
                sep = "推理路径设计：" if "推理路径设计：" in question_part else "推理路径设计:"
                question = question_part.split(sep)[0].strip()
            elif "答案：" in question_part or "答案:" in question_part:
                sep = "答案：" if "答案：" in question_part else "答案:"
                question = question_part.split(sep)[0].strip()
            else:
                question = question_part.split("\n")[0].strip()
        else:
            logger.warning("Failed to parse question from combined CoT response (length: %d): %s",
                         len(response_clean), response_clean[:300])
            return {}
        
        # 尝试解析推理路径
        if "Reasoning-Path Design:" in response_clean:
            reasoning_part = response_clean.split("Reasoning-Path Design:")[1]
            if "Answer:" in reasoning_part:
                reasoning_path = reasoning_part.split("Answer:")[0].strip()
            else:
                reasoning_path = reasoning_part.strip()
        elif "推理路径设计：" in response_clean:
            reasoning_part = response_clean.split("推理路径设计：")[1]
            if "答案：" in reasoning_part:
                reasoning_path = reasoning_part.split("答案：")[0].strip()
            elif "答案:" in reasoning_part:
                reasoning_path = reasoning_part.split("答案:")[0].strip()
            else:
                reasoning_path = reasoning_part.strip()
        elif "推理路径设计:" in response_clean:  # 处理英文冒号
            reasoning_part = response_clean.split("推理路径设计:")[1]
            if "答案：" in reasoning_part:
                reasoning_path = reasoning_part.split("答案：")[0].strip()
            elif "答案:" in reasoning_part:
                reasoning_path = reasoning_part.split("答案:")[0].strip()
            else:
                reasoning_path = reasoning_part.strip()
        else:
            reasoning_path = ""
        
        # 尝试解析答案
        if "Answer:" in response_clean:
            answer = response_clean.split("Answer:")[1].strip()
        elif "答案：" in response_clean:
            answer = response_clean.split("答案：")[1].strip()
        elif "答案:" in response_clean:  # 处理英文冒号
            answer = response_clean.split("答案:")[1].strip()
        else:
            # 如果没有找到答案标记，使用推理路径后的内容
            if reasoning_path:
                answer = response_clean.split(reasoning_path)[-1].strip()
            else:
                answer = response_clean.split(question)[-1].strip() if question else response_clean.strip()
        
        question = question.strip('"')
        reasoning_path = reasoning_path.strip('"')
        answer = answer.strip('"')
        
        logger.debug("CoT Combined - Question: %s", question)
        logger.debug("CoT Combined - Reasoning Path: %s", reasoning_path)
        logger.debug("CoT Combined - Answer: %s", answer)
        
        return {
            "question": question,
            "reasoning_path": reasoning_path,
            "answer": answer,
        }
    
    @staticmethod
    def build_prompt_for_cot_generation(
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]],
        question: str,
        reasoning_path: str,
    ) -> str:
        """
        Build prompts for COT Generation.
        """
        nodes, edges = batch
        entities_str = "\n".join(
            [
                f"{index + 1}. {node[0]}: {node[1]['description']}"
                for index, node in enumerate(nodes)
            ]
        )
        relationships_str = "\n".join(
            [
                f"{index + 1}. {edge[0]} -- {edge[1]}: {edge[2]['description']}"
                for index, edge in enumerate(edges)
            ]
        )
        language = detect_main_language(entities_str + relationships_str)
        prompt = COT_GENERATION_PROMPT[language]["COT_GENERATION"].format(
            entities=entities_str,
            relationships=relationships_str,
            question=question,
            reasoning_template=reasoning_path,
        )
        return prompt

    @staticmethod
    def parse_response(response: str) -> dict:
        if "Question:" in response and "Reasoning-Path Design:" in response:
            question = (
                response.split("Question:")[1]
                .split("Reasoning-Path Design:")[0]
                .strip()
            )
            reasoning_path = response.split("Reasoning-Path Design:")[1].strip()
        elif "问题：" in response and "推理路径设计：" in response:
            question = response.split("问题：")[1].split("推理路径设计：")[0].strip()
            reasoning_path = response.split("推理路径设计：")[1].strip()
        else:
            logger.warning("Failed to parse CoT template: %s", response)
            return {}

        question = question.strip('"')
        reasoning_path = reasoning_path.strip('"')
        logger.debug("CoT Question: %s", question)
        logger.debug("CoT Reasoning Path: %s", reasoning_path)
        return {
            "question": question,
            "reasoning_path": reasoning_path,
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
        from graphgen.bases.base_generator import _add_context_and_source_info
        
        result = {}
        
        if self.use_combined_mode:
            # 合并模式：一次性生成问题和答案（减少50%调用）
            prompt = self.build_combined_prompt(batch)
            response = await self.llm_client.generate_answer(prompt)
            parsed = self.parse_combined_response(response)
            
            if not parsed or "question" not in parsed or "answer" not in parsed:
                logger.warning("Failed to parse combined CoT response, falling back to two-step mode")
                # 回退到两步模式
                prompt = self.build_prompt(batch)
                response = await self.llm_client.generate_answer(prompt)
                response = self.parse_response(response)
                question, reasoning_path = response["question"], response["reasoning_path"]
                prompt = self.build_prompt_for_cot_generation(batch, question, reasoning_path)
                cot_answer = await self.llm_client.generate_answer(prompt)
                question = question
                cot_answer = cot_answer
                reasoning_path = reasoning_path
            else:
                question = parsed["question"]
                cot_answer = parsed["answer"]
                reasoning_path = parsed.get("reasoning_path", "")
        else:
            # 原始两步模式
            prompt = self.build_prompt(batch)
            response = await self.llm_client.generate_answer(prompt)
            response = self.parse_response(response)
            question, reasoning_path = response["question"], response["reasoning_path"]
            prompt = self.build_prompt_for_cot_generation(batch, question, reasoning_path)
            cot_answer = await self.llm_client.generate_answer(prompt)
        
        logger.debug("CoT Answer: %s", cot_answer)
        qa_pairs = {
            compute_content_hash(question): {
                "question": question,
                "answer": cot_answer,
                "reasoning_path": reasoning_path,
            }
        }
        
        # Add context and source information
        await _add_context_and_source_info(
            qa_pairs,
            batch,
            chunks_storage,
            full_docs_storage,
            "cot"
        )
        
        result.update(qa_pairs)
        return result
