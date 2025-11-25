from typing import Any

from graphgen.bases import BaseGenerator
from graphgen.templates import MULTI_HOP_GENERATION_PROMPT
from graphgen.utils import compute_content_hash, detect_main_language, logger


class MultiHopGenerator(BaseGenerator):
    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
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
        prompt = MULTI_HOP_GENERATION_PROMPT[language].format(
            entities=entities_str, relationships=relationships_str
        )
        return prompt

    @staticmethod
    def parse_response(response: str) -> dict:
        """
        Parse multi-hop response that should include reasoning path.
        Expected format:
        Question: ...
        Answer: ...
        Reasoning Path: ... (optional)
        """
        if not response or not response.strip():
            logger.warning("Empty multi-hop response received")
            return {}
        
        reasoning_path = ""
        question = ""
        answer = ""
        
        # Try English format first
        if "Question:" in response:
            parts = response.split("Question:", 1)
            if len(parts) > 1:
                question_part = parts[1]
                if "Answer:" in question_part:
                    question = question_part.split("Answer:")[0].strip()
                    answer_part = question_part.split("Answer:")[1]
                    if "Reasoning Path:" in answer_part or "Reasoning:" in answer_part:
                        # Extract reasoning path
                        reasoning_markers = ["Reasoning Path:", "Reasoning:", "Path:"]
                        for marker in reasoning_markers:
                            if marker in answer_part:
                                answer = answer_part.split(marker)[0].strip()
                                reasoning_path = answer_part.split(marker)[1].strip()
                                break
                        if not reasoning_path:
                            answer = answer_part.strip()
                    else:
                        answer = answer_part.strip()
        # Try Chinese format
        elif "问题：" in response:
            parts = response.split("问题：", 1)
            if len(parts) > 1:
                question_part = parts[1]
                if "答案：" in question_part:
                    question = question_part.split("答案：")[0].strip()
                    answer_part = question_part.split("答案：")[1]
                    if "推理路径：" in answer_part or "路径：" in answer_part:
                        # Extract reasoning path
                        reasoning_markers = ["推理路径：", "路径：", "推理："]
                        for marker in reasoning_markers:
                            if marker in answer_part:
                                answer = answer_part.split(marker)[0].strip()
                                reasoning_path = answer_part.split(marker)[1].strip()
                                break
                        if not reasoning_path:
                            answer = answer_part.strip()
                    else:
                        answer = answer_part.strip()
        else:
            # No standard markers found
            response_preview = response.strip()[:200] if response.strip() else "(empty)"
            logger.warning(
                "Failed to parse multi-hop response (no Question/问题 marker found): %s",
                response_preview
            )
            return {}
        
        question = question.strip('"').strip()
        answer = answer.strip('"').strip()
        reasoning_path = reasoning_path.strip()
        
        if not question or not answer:
            logger.warning("Incomplete multi-hop response: Q=%s, A=%s", question, answer)
            return {}
        
        logger.debug("Multi-hop QA: Q=%s, A=%s, Path=%s", question[:50], answer[:50], reasoning_path[:50] if reasoning_path else "N/A")
        
        return {
            compute_content_hash(question): {
                "question": question,
                "answer": answer,
                "reasoning_path": reasoning_path,
            }
        }
