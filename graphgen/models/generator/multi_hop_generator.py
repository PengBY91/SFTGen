import re
from typing import Any

from graphgen.bases import BaseGenerator
from graphgen.templates import MULTI_HOP_GENERATION_PROMPT
from graphgen.utils import compute_content_hash, detect_main_language, logger


class MultiHopGenerator(BaseGenerator):
    def __init__(self, llm_client):
        """
        初始化 Multi-hop 生成器
        
        :param llm_client: LLM客户端
        """
        super().__init__(llm_client)
        self._generation_mode = "multi_hop"
    
    @staticmethod
    def _format_batch_data(
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> tuple[str, str, str]:
        """
        格式化批次数据为实体和关系字符串，并检测语言
        
        :param batch: 包含节点和边的批次数据
        :return: (entities_str, relationships_str, language)
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
        return entities_str, relationships_str, language
    
    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        """
        Build prompts for multi-hop QA generation.
        :param batch: tuple of (nodes, edges)
        :return: formatted prompt string
        """
        entities_str, relationships_str, language = self._format_batch_data(batch)
        prompt = MULTI_HOP_GENERATION_PROMPT[language].format(
            entities=entities_str, relationships=relationships_str
        )
        return prompt

    @staticmethod
    def parse_response(response: str) -> dict:
        """
        Parse multi-hop response that should include question, answer, and reasoning path.
        Expected format:
        Question: ...
        Answer: ...
        Reasoning Path: ... (optional)
        
        Uses robust regex-based parsing to handle various format variations.
        """
        if not response or not response.strip():
            logger.warning("Empty multi-hop response received")
            return {}
        
        # 定义匹配模式（支持多种变体）
        patterns = {
            "question_en": [
                r"Question:\s*(.+?)(?=Answer:|Reasoning Path:|Reasoning:|Path:|\Z)",
                r"Question\s*:\s*(.+?)(?=Answer:|Reasoning Path:|Reasoning:|Path:|\Z)",
            ],
            "question_zh": [
                r"问题：\s*(.+?)(?=答案：|推理路径：|路径：|推理：|\Z)",
                r"问题\s*：\s*(.+?)(?=答案：|推理路径：|路径：|推理：|\Z)",
            ],
            "answer_en": [
                r"Answer:\s*(.+?)(?=Reasoning Path:|Reasoning:|Path:|\Z)",
                r"Answer\s*:\s*(.+?)(?=Reasoning Path:|Reasoning:|Path:|\Z)",
            ],
            "answer_zh": [
                r"答案：\s*(.+?)(?=推理路径：|路径：|推理：|\Z)",
                r"答案\s*：\s*(.+?)(?=推理路径：|路径：|推理：|\Z)",
            ],
            "reasoning_en": [
                r"Reasoning Path:\s*(.+?)(?=\Z)",
                r"Reasoning:\s*(.+?)(?=\Z)",
                r"Path:\s*(.+?)(?=\Z)",
            ],
            "reasoning_zh": [
                r"推理路径：\s*(.+?)(?=\Z)",
                r"路径：\s*(.+?)(?=\Z)",
                r"推理：\s*(.+?)(?=\Z)",
            ],
        }
        
        question = ""
        answer = ""
        reasoning_path = ""
        
        # 解析问题
        for pattern in patterns["question_en"] + patterns["question_zh"]:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                question = match.group(1).strip()
                break
        
        # 解析答案
        for pattern in patterns["answer_en"] + patterns["answer_zh"]:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                answer = match.group(1).strip()
                break
        
        # 解析推理路径（可选）
        for pattern in patterns["reasoning_en"] + patterns["reasoning_zh"]:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                reasoning_path = match.group(1).strip()
                break
        
        # 清理引号
        question = question.strip('"').strip("'")
        answer = answer.strip('"').strip("'")
        reasoning_path = reasoning_path.strip('"').strip("'")
        
        # 验证必需字段
        if not question or not answer:
            logger.warning(
                "Failed to parse multi-hop response - missing required fields. "
                "Question: %s, Answer: %s",
                bool(question),
                bool(answer)
            )
            return {}
        
        logger.debug(
            "Multi-hop QA: Q=%s, A=%s, Path=%s",
            question[:100] if question else "None",
            answer[:100] if answer else "None",
            reasoning_path[:100] if reasoning_path else "N/A"
        )
        
        return {
            compute_content_hash(question): {
                "question": question,
                "answer": answer,
                "reasoning_path": reasoning_path,
            }
        }
