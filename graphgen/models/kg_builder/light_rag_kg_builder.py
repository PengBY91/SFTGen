import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from graphgen.bases import BaseGraphStorage, BaseKGBuilder, BaseKVStorage, BaseLLMClient, Chunk
from graphgen.templates import KG_EXTRACTION_PROMPT, KG_SUMMARIZATION_PROMPT
from graphgen.utils import (
    compute_content_hash,
    detect_main_language,
    handle_single_entity_extraction,
    handle_single_relationship_extraction,
    logger,
    pack_history_conversations,
    split_string_by_multi_markers,
)
from graphgen.utils.batch_request_manager import BatchRequestManager


class LightRAGKGBuilder(BaseKGBuilder):
    def __init__(
        self, 
        llm_client: BaseLLMClient, 
        max_loop: int = 3,
        cache_storage: Optional[BaseKVStorage] = None,
        enable_cache: bool = True,
        enable_batch_requests: bool = True,
        batch_size: int = 10,
        max_wait_time: float = 0.5
    ):
        super().__init__(llm_client)
        self.max_loop = max_loop
        self.cache_storage = cache_storage
        self.enable_cache = enable_cache and cache_storage is not None
        self.enable_batch_requests = enable_batch_requests
        self.batch_manager: Optional[BatchRequestManager] = None
        if enable_batch_requests:
            self.batch_manager = BatchRequestManager(
                llm_client=llm_client,
                batch_size=batch_size,
                max_wait_time=max_wait_time,
                enable_batching=True
            )

    async def extract(
        self, chunk: Chunk
    ) -> Tuple[Dict[str, List[dict]], Dict[Tuple[str, str], List[dict]]]:
        """
        Extract entities and relationships from a single chunk using the LLM client.
        Supports caching to avoid re-extraction of identical chunks.
        :param chunk
        :return: (nodes_data, edges_data)
        """
        chunk_id = chunk.id
        content = chunk.content
        
        # Check cache first if enabled
        if self.enable_cache:
            chunk_hash = compute_content_hash(content, prefix="extract-")
            cached_result = await self.cache_storage.get_by_id(chunk_hash)
            if cached_result is not None:
                logger.debug("Cache hit for chunk %s", chunk_id)
                return cached_result["nodes"], cached_result["edges"]

        # step 1: language_detection
        language = detect_main_language(content)

        hint_prompt = KG_EXTRACTION_PROMPT[language]["TEMPLATE"].format(
            **KG_EXTRACTION_PROMPT["FORMAT"], input_text=content
        )

        # step 2: initial glean
        if self.batch_manager:
            final_result = await self.batch_manager.add_request(hint_prompt)
        else:
            final_result = await self.llm_client.generate_answer(hint_prompt)
        logger.debug("First extraction result: %s", final_result)

        # step3: iterative refinement
        # history = pack_history_conversations(hint_prompt, final_result)
        # for loop_idx in range(self.max_loop):
        #     if_loop_result = await self.llm_client.generate_answer(
        #         text=KG_EXTRACTION_PROMPT[language]["IF_LOOP"], history=history
        #     )
        #     if_loop_result = if_loop_result.strip().strip('"').strip("'").lower()
        #     if if_loop_result != "yes":
        #         break

        #     glean_result = await self.llm_client.generate_answer(
        #         text=KG_EXTRACTION_PROMPT[language]["CONTINUE"], history=history
        #     )
        #     logger.debug("Loop %s glean: %s", loop_idx + 1, glean_result)

        #     history += pack_history_conversations(
        #         KG_EXTRACTION_PROMPT[language]["CONTINUE"], glean_result
        #     )
        #     final_result += glean_result

        # step 4: parse the final result
        records = split_string_by_multi_markers(
            final_result,
            [
                KG_EXTRACTION_PROMPT["FORMAT"]["record_delimiter"],
                KG_EXTRACTION_PROMPT["FORMAT"]["completion_delimiter"],
            ],
        )

        nodes = defaultdict(list)
        edges = defaultdict(list)

        for record in records:
            match = re.search(r"\((.*)\)", record)
            if not match:
                continue
            inner = match.group(1)

            attributes = split_string_by_multi_markers(
                inner, [KG_EXTRACTION_PROMPT["FORMAT"]["tuple_delimiter"]]
            )

            entity = await handle_single_entity_extraction(attributes, chunk_id)
            if entity is not None:
                nodes[entity["entity_name"]].append(entity)
                continue

            relation = await handle_single_relationship_extraction(attributes, chunk_id)
            if relation is not None:
                key = (relation["src_id"], relation["tgt_id"])
                edges[key].append(relation)

        result = (dict(nodes), dict(edges))
        
        # Cache the result if enabled
        if self.enable_cache:
            chunk_hash = compute_content_hash(content, prefix="extract-")
            await self.cache_storage.upsert({
                chunk_hash: {
                    "nodes": result[0],
                    "edges": result[1],
                    "chunk_id": chunk_id
                }
            })
            logger.debug("Cached extraction result for chunk %s", chunk_id)
        
        return result

    async def merge_nodes(
        self,
        node_data: tuple[str, List[dict]],
        kg_instance: BaseGraphStorage,
    ) -> None:
        entity_name, node_data = node_data
        entity_types = []
        source_ids = []
        descriptions = []

        node = await kg_instance.get_node(entity_name)
        if node is not None:
            entity_types.append(node["entity_type"])
            source_ids.extend(
                split_string_by_multi_markers(node["source_id"], ["<SEP>"])
            )
            descriptions.append(node["description"])

        # take the most frequent entity_type
        entity_type = sorted(
            Counter([dp["entity_type"] for dp in node_data] + entity_types).items(),
            key=lambda x: x[1],
            reverse=True,
        )[0][0]

        description = "<SEP>".join(
            sorted(set([dp["description"] for dp in node_data] + descriptions))
        )
        description = await self._handle_kg_summary(entity_name, description)

        source_id = "<SEP>".join(
            set([dp["source_id"] for dp in node_data] + source_ids)
        )

        node_data = {
            "entity_type": entity_type,
            "description": description,
            "source_id": source_id,
        }
        await kg_instance.upsert_node(entity_name, node_data=node_data)

    async def merge_edges(
        self,
        edges_data: tuple[Tuple[str, str], List[dict]],
        kg_instance: BaseGraphStorage,
    ) -> None:
        (src_id, tgt_id), edge_data = edges_data

        source_ids = []
        descriptions = []

        edge = await kg_instance.get_edge(src_id, tgt_id)
        if edge is not None:
            source_ids.extend(
                split_string_by_multi_markers(edge["source_id"], ["<SEP>"])
            )
            descriptions.append(edge["description"])

        description = "<SEP>".join(
            sorted(set([dp["description"] for dp in edge_data] + descriptions))
        )
        source_id = "<SEP>".join(
            set([dp["source_id"] for dp in edge_data] + source_ids)
        )

        for insert_id in [src_id, tgt_id]:
            if not await kg_instance.has_node(insert_id):
                await kg_instance.upsert_node(
                    insert_id,
                    node_data={
                        "source_id": source_id,
                        "description": description,
                        "entity_type": "UNKNOWN",
                    },
                )

        description = await self._handle_kg_summary(
            f"({src_id}, {tgt_id})", description
        )

        await kg_instance.upsert_edge(
            src_id,
            tgt_id,
            edge_data={"source_id": source_id, "description": description},
        )

    async def _handle_kg_summary(
        self,
        entity_or_relation_name: str,
        description: str,
        max_summary_tokens: int = 200,
    ) -> str:
        """
        Handle knowledge graph summary

        :param entity_or_relation_name
        :param description
        :param max_summary_tokens
        :return summary
        """

        tokenizer_instance = self.llm_client.tokenizer
        language = detect_main_language(description)

        tokens = tokenizer_instance.encode(description)
        if len(tokens) < max_summary_tokens:
            return description

        use_description = tokenizer_instance.decode(tokens[:max_summary_tokens])
        prompt = KG_SUMMARIZATION_PROMPT[language]["TEMPLATE"].format(
            entity_name=entity_or_relation_name,
            description_list=use_description.split("<SEP>"),
            **KG_SUMMARIZATION_PROMPT["FORMAT"],
        )
        if self.batch_manager:
            new_description = await self.batch_manager.add_request(prompt)
        else:
            new_description = await self.llm_client.generate_answer(prompt)
        logger.info(
            "Entity or relation %s summary: %s",
            entity_or_relation_name,
            new_description,
        )
        return new_description