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
        
        # 尝试解析答案（现在分为思考过程和最终答案）
        thinking_process = ""
        final_answer = ""
        
        # 英文格式
        if "Thinking Process:" in response_clean and "Final Answer:" in response_clean:
            thinking_part = response_clean.split("Thinking Process:")[1]
            thinking_process = thinking_part.split("Final Answer:")[0].strip()
            final_answer = response_clean.split("Final Answer:")[1].strip()
        # 中文格式（中文冒号）
        elif "思考过程：" in response_clean and "最终答案：" in response_clean:
            thinking_part = response_clean.split("思考过程：")[1]
            thinking_process = thinking_part.split("最终答案：")[0].strip()
            final_answer = response_clean.split("最终答案：")[1].strip()
        # 中文格式（英文冒号）
        elif "思考过程:" in response_clean and "最终答案:" in response_clean:
            thinking_part = response_clean.split("思考过程:")[1]
            thinking_process = thinking_part.split("最终答案:")[0].strip()
            final_answer = response_clean.split("最终答案:")[1].strip()
        # 向后兼容：如果只有Answer/答案标记
        elif "Answer:" in response_clean:
            answer_text = response_clean.split("Answer:")[1].strip()
            # 尝试将答案拆分为思考过程和最终答案（简单启发式：最后一段作为最终答案）
            paragraphs = [p.strip() for p in answer_text.split('\n\n') if p.strip()]
            if len(paragraphs) > 1:
                thinking_process = '\n\n'.join(paragraphs[:-1])
                final_answer = paragraphs[-1]
            else:
                thinking_process = answer_text
                final_answer = answer_text
        elif "答案：" in response_clean:
            answer_text = response_clean.split("答案：")[1].strip()
            paragraphs = [p.strip() for p in answer_text.split('\n\n') if p.strip()]
            if len(paragraphs) > 1:
                thinking_process = '\n\n'.join(paragraphs[:-1])
                final_answer = paragraphs[-1]
            else:
                thinking_process = answer_text
                final_answer = answer_text
        elif "答案:" in response_clean:
            answer_text = response_clean.split("答案:")[1].strip()
            paragraphs = [p.strip() for p in answer_text.split('\n\n') if p.strip()]
            if len(paragraphs) > 1:
                thinking_process = '\n\n'.join(paragraphs[:-1])
                final_answer = paragraphs[-1]
            else:
                thinking_process = answer_text
                final_answer = answer_text
        else:
            # 如果没有找到任何答案标记，使用推理路径后的内容
            if reasoning_path:
                remaining = response_clean.split(reasoning_path)[-1].strip()
            else:
                remaining = response_clean.split(question)[-1].strip() if question else response_clean.strip()
            
            paragraphs = [p.strip() for p in remaining.split('\n\n') if p.strip()]
            if len(paragraphs) > 1:
                thinking_process = '\n\n'.join(paragraphs[:-1])
                final_answer = paragraphs[-1]
            else:
                thinking_process = remaining
                final_answer = remaining
        
        question = question.strip('"')
        reasoning_path = reasoning_path.strip('"')
        thinking_process = thinking_process.strip('"')
        final_answer = final_answer.strip('"')
        
        # 不再合并到answer字段，保持分离
        # answer 字段仅用于向后兼容，在有思考过程和最终答案时保持为空或仅包含最终答案
        if thinking_process and final_answer:
            # 如果两者都存在，answer 使用最终答案（不包含思考过程）
            answer = final_answer
        elif thinking_process:
            # 如果只有思考过程（向后兼容场景）
            answer = thinking_process
        else:
            # 如果只有最终答案
            answer = final_answer
        
        logger.info("CoT Combined Parsing Result:")
        logger.info("  - Question: %s", question[:80] + "..." if len(question) > 80 else question)
        logger.info("  - Reasoning Path length: %d", len(reasoning_path))
        logger.info("  - Thinking Process length: %d%s", len(thinking_process), 
                   "" if thinking_process else " (EMPTY - will not display in frontend)")
        logger.info("  - Final Answer length: %d%s", len(final_answer),
                   "" if final_answer else " (EMPTY - will not display in frontend)")
        logger.info("  - Answer field length (compatibility): %d", len(answer))
        
        if not thinking_process or not final_answer:
            logger.warning("CoT response missing new format markers. Response preview: %s",
                         response_clean[:300])
        
        return {
            "question": question,
            "reasoning_path": reasoning_path,
            "answer": answer,
            "thinking_process": thinking_process,
            "final_answer": final_answer,
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

    @staticmethod
    def parse_cot_answer_response(response: str) -> dict:
        """
        解析两步模式中答案生成阶段的响应，提取思考过程和最终答案。
        
        预期格式：
        - 思考过程：...
        - 最终答案：...
        或
        - Thinking Process: ...
        - Final Answer: ...
        
        :param response: LLM 响应
        :return: 包含 thinking_process 和 final_answer 的字典
        """
        if not response or not response.strip():
            logger.warning("Empty response in parse_cot_answer_response")
            return {"thinking_process": "", "final_answer": "", "answer": ""}
        
        response_clean = response.strip()
        thinking_process = ""
        final_answer = ""
        
        # 策略1: 尝试解析中文格式（中文冒号）
        if "思考过程：" in response_clean and "最终答案：" in response_clean:
            thinking_part = response_clean.split("思考过程：")[1]
            thinking_process = thinking_part.split("最终答案：")[0].strip()
            final_answer = response_clean.split("最终答案：")[1].strip()
            logger.info("CoT Answer Parsing (CN full-width): thinking=%d chars, final=%d chars", 
                       len(thinking_process), len(final_answer))
        # 策略2: 尝试解析中文格式（英文冒号）
        elif "思考过程:" in response_clean and "最终答案:" in response_clean:
            thinking_part = response_clean.split("思考过程:")[1]
            thinking_process = thinking_part.split("最终答案:")[0].strip()
            final_answer = response_clean.split("最终答案:")[1].strip()
            logger.info("CoT Answer Parsing (CN half-width): thinking=%d chars, final=%d chars", 
                       len(thinking_process), len(final_answer))
        # 策略3: 尝试解析英文格式
        elif "Thinking Process:" in response_clean and "Final Answer:" in response_clean:
            thinking_part = response_clean.split("Thinking Process:")[1]
            thinking_process = thinking_part.split("Final Answer:")[0].strip()
            final_answer = response_clean.split("Final Answer:")[1].strip()
            logger.info("CoT Answer Parsing (EN): thinking=%d chars, final=%d chars", 
                       len(thinking_process), len(final_answer))
        # 策略4: 如果没有找到标记，尝试按段落分割（最后一段作为最终答案，其余作为思考过程）
        else:
            logger.warning("CoT answer response missing format markers. Response length: %d, preview: %s",
                         len(response_clean), response_clean[:200])
            
            # 按段落分割
            paragraphs = [p.strip() for p in response_clean.split('\n\n') if p.strip()]
            if len(paragraphs) > 1:
                # 最后一段作为最终答案，其余作为思考过程
                thinking_process = '\n\n'.join(paragraphs[:-1])
                final_answer = paragraphs[-1]
                logger.info("CoT Answer Parsing (fallback by paragraphs): thinking=%d chars, final=%d chars", 
                           len(thinking_process), len(final_answer))
            elif len(paragraphs) == 1:
                # 只有一段，尝试按句子分割
                sentences = [s.strip() for s in response_clean.split('。') if s.strip()]
                if len(sentences) > 1:
                    # 最后一句作为最终答案，其余作为思考过程
                    thinking_process = '。'.join(sentences[:-1]) + '。'
                    final_answer = sentences[-1]
                    if not final_answer.endswith('。'):
                        final_answer += '。'
                    logger.info("CoT Answer Parsing (fallback by sentences): thinking=%d chars, final=%d chars", 
                               len(thinking_process), len(final_answer))
                else:
                    # 只有一句话，全部作为最终答案
                    final_answer = response_clean
                    logger.warning("CoT answer is single sentence, using as final_answer only")
            else:
                # 完全无法解析，使用完整响应作为最终答案
                final_answer = response_clean
                logger.warning("CoT answer parsing failed, using entire response as final_answer")
        
        # 清理引号
        thinking_process = thinking_process.strip('"').strip("'").strip()
        final_answer = final_answer.strip('"').strip("'").strip()
        
        # 为了向后兼容，构建 answer 字段
        # 如果两者都存在，answer 只包含 final_answer
        if thinking_process and final_answer:
            answer = final_answer
        elif thinking_process:
            answer = thinking_process
        else:
            answer = final_answer
        
        logger.info("CoT Answer Parsed Result:")
        logger.info("  - Thinking Process length: %d%s", len(thinking_process),
                   "" if thinking_process else " (EMPTY - will not display in frontend)")
        logger.info("  - Final Answer length: %d%s", len(final_answer),
                   "" if final_answer else " (EMPTY - will not display in frontend)")
        logger.info("  - Answer field (compatibility): %d chars", len(answer))
        
        return {
            "thinking_process": thinking_process,
            "final_answer": final_answer,
            "answer": answer,
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
                
                # 生成答案（包含思考过程和最终答案）
                prompt = self.build_prompt_for_cot_generation(batch, question, reasoning_path)
                cot_answer_response = await self.llm_client.generate_answer(prompt)
                
                # 解析答案响应
                parsed_answer = self.parse_cot_answer_response(cot_answer_response)
                thinking_process = parsed_answer.get("thinking_process", "")
                final_answer = parsed_answer.get("final_answer", "")
                cot_answer = parsed_answer.get("answer", cot_answer_response)
            else:
                question = parsed["question"]
                cot_answer = parsed["answer"]
                reasoning_path = parsed.get("reasoning_path", "")
                thinking_process = parsed.get("thinking_process", "")
                final_answer = parsed.get("final_answer", "")
        else:
            # 原始两步模式：分别生成问题和答案
            # 第一步：生成问题和推理路径
            prompt = self.build_prompt(batch)
            response = await self.llm_client.generate_answer(prompt)
            response = self.parse_response(response)
            question, reasoning_path = response["question"], response["reasoning_path"]
            
            # 第二步：根据问题和推理路径生成答案（包含思考过程和最终答案）
            prompt = self.build_prompt_for_cot_generation(batch, question, reasoning_path)
            cot_answer_response = await self.llm_client.generate_answer(prompt)
            
            # 解析答案响应，提取思考过程和最终答案
            parsed_answer = self.parse_cot_answer_response(cot_answer_response)
            thinking_process = parsed_answer.get("thinking_process", "")
            final_answer = parsed_answer.get("final_answer", "")
            cot_answer = parsed_answer.get("answer", cot_answer_response)  # 向后兼容
        
        logger.debug("CoT Answer: %s", cot_answer[:200] + "..." if len(cot_answer) > 200 else cot_answer)
        
        qa_pairs = {
            compute_content_hash(question): {
                "question": question,
                "answer": cot_answer,
                "reasoning_path": reasoning_path,
                "thinking_process": thinking_process if 'thinking_process' in locals() else "",
                "final_answer": final_answer if 'final_answer' in locals() else "",
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
