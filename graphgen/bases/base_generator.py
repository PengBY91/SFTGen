from abc import ABC, abstractmethod
from typing import Any

from graphgen.bases.base_llm_client import BaseLLMClient


async def _add_context_and_source_info(
    qa_pairs: dict,
    batch: tuple,
    chunks_storage=None,
    full_docs_storage=None,
    generation_mode: str = "unknown"
) -> None:
    """
    辅助函数：为QA对添加上下文、图谱、chunks和文档信息
    
    :param qa_pairs: QA对字典
    :param batch: (nodes, edges) 元组
    :param chunks_storage: chunks存储实例
    :param full_docs_storage: 文档存储实例
    :param generation_mode: 生成模式
    """
    nodes, edges = batch
    
    def _normalize_ids(raw_value):
        """将 chunk/doc id 统一整理成列表"""
        if not raw_value:
            return []
        values = []
        if isinstance(raw_value, (list, tuple, set)):
            values.extend(raw_value)
        else:
            values.append(raw_value)
        normalized = []
        for value in values:
            if not value:
                continue
            if isinstance(value, str):
                parts = [v.strip() for v in value.split("<SEP>") if v.strip()]
                if parts:
                    normalized.extend(parts)
                else:
                    normalized.append(value.strip())
            else:
                normalized.append(str(value))
        return normalized

    # Collect chunk IDs and document IDs from nodes / edges
    chunk_ids = set()
    doc_ids = set()
    for node_id, node_data in nodes:
        chunk_or_source = node_data.get("chunk_id") or node_data.get("source_id")
        for chunk_id in _normalize_ids(chunk_or_source):
            chunk_ids.add(chunk_id)
    for edge in edges:
        edge_data = edge[2] if len(edge) > 2 else {}
        chunk_or_source = edge_data.get("chunk_id") or edge_data.get("source_id")
        for chunk_id in _normalize_ids(chunk_or_source):
            chunk_ids.add(chunk_id)
    
    # Get chunk information
    chunks_info = {}
    if chunks_storage and chunk_ids:
        for chunk_id in chunk_ids:
            try:
                chunk_data = await chunks_storage.get_by_id(chunk_id)
                if chunk_data:
                    chunks_info[chunk_id] = {
                        "chunk_id": chunk_id,
                        "content": chunk_data.get("content", ""),
                        "type": chunk_data.get("type", ""),
                        "full_doc_id": chunk_data.get("full_doc_id", ""),
                        "length": chunk_data.get("length", 0),
                        "language": chunk_data.get("language", ""),
                    }
                    doc_id = chunk_data.get("full_doc_id")
                    for did in _normalize_ids(doc_id):
                        doc_ids.add(did)
            except Exception:
                pass
    
    # Get document information
    docs_info = {}
    if full_docs_storage and doc_ids:
        for doc_id in doc_ids:
            try:
                doc_data = await full_docs_storage.get_by_id(doc_id)
                if doc_data:
                    docs_info[doc_id] = {
                        "doc_id": doc_id,
                        "type": doc_data.get("type", ""),
                        "content_preview": doc_data.get("content", "")[:200] if doc_data.get("content") else "",
                        "metadata": {k: v for k, v in doc_data.items() if k not in ["content"]},
                    }
            except Exception:
                pass
    
    # Add context and graph information to each QA pair
    for qa_key, qa_value in qa_pairs.items():
        if isinstance(qa_value, dict):
            qa_value["context"] = {
                "nodes": [
                    {
                        "name": node[0], 
                        "description": node[1].get('description', ''),
                        "chunk_id": node[1].get('chunk_id', ''),
                        "entity_type": node[1].get('entity_type', ''),
                    } 
                    for node in nodes
                ],
                "edges": [
                    {
                        "source": edge[0], 
                        "target": edge[1], 
                        "description": edge[2].get('description', ''),
                        "relation_type": edge[2].get('relation_type', ''),
                    } 
                    for edge in edges
                ]
            }
            qa_value["graph"] = {
                "entities": [node[0] for node in nodes],
                "relationships": [[edge[0], edge[1]] for edge in edges],
                "entity_count": len(nodes),
                "relationship_count": len(edges),
            }
            if chunks_info:
                qa_value["source_chunks"] = list(chunks_info.values())
            if docs_info:
                qa_value["source_documents"] = list(docs_info.values())
            qa_value["metadata"] = {
                "generation_mode": generation_mode,
                "batch_size": len(nodes) + len(edges),
                "has_chunks": len(chunks_info) > 0,
                "has_documents": len(docs_info) > 0,
            }


class BaseGenerator(ABC):
    """
    Generate QAs based on given prompts.
    """

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    @abstractmethod
    def build_prompt(
        self,
        batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
    ) -> str:
        """Build prompt for LLM based on the given batch"""

    @staticmethod
    @abstractmethod
    def parse_response(response: str) -> Any:
        """Parse the LLM response and return the generated QAs"""

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
        :param batch: tuple of (nodes, edges)
        :param chunks_storage: chunks storage instance
        :param full_docs_storage: full documents storage instance
        :return: QA pairs
        """
        result = {}
        prompt = self.build_prompt(batch)
        response = await self.llm_client.generate_answer(prompt)
        qa_pairs = self.parse_response(response)  # generate one or more QA pairs
        
        # Add context and graph information using helper function
        await _add_context_and_source_info(
            qa_pairs, 
            batch, 
            chunks_storage, 
            full_docs_storage,
            getattr(self, '_generation_mode', 'unknown')
        )
        
        result.update(qa_pairs)
        return result

    @staticmethod
    def format_generation_results(
        results: list[dict], output_data_format: str
    ) -> list[dict[str, Any]]:
        if output_data_format == "Alpaca":
            results = [
                {
                    "instruction": v["question"],
                    "input": "",
                    "output": v["answer"],
                    "context": v.get("context", {}),
                    "graph": v.get("graph", {}),
                    "source_chunks": v.get("source_chunks", []),
                    "source_documents": v.get("source_documents", []),
                    "metadata": v.get("metadata", {}),
                }
                for item in results
                for k, v in item.items()
            ]
        elif output_data_format == "Sharegpt":
            results = [
                {
                    "conversations": [
                        {"from": "human", "value": v["question"]},
                        {"from": "gpt", "value": v["answer"]},
                    ],
                    "context": v.get("context", {}),
                    "graph": v.get("graph", {}),
                    "source_chunks": v.get("source_chunks", []),
                    "source_documents": v.get("source_documents", []),
                    "metadata": v.get("metadata", {}),
                }
                for item in results
                for k, v in item.items()
            ]
        elif output_data_format == "ChatML":
            results = [
                {
                    "messages": [
                        {"role": "user", "content": v["question"]},
                        {"role": "assistant", "content": v["answer"]},
                    ],
                    "context": v.get("context", {}),
                    "graph": v.get("graph", {}),
                    "source_chunks": v.get("source_chunks", []),
                    "source_documents": v.get("source_documents", []),
                    "metadata": v.get("metadata", {}),
                }
                for item in results
                for k, v in item.items()
            ]
        else:
            raise ValueError(f"Unknown output data format: {output_data_format}")
        return results
