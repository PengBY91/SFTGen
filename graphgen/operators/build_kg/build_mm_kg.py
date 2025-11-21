from collections import defaultdict
from typing import List, Optional, Any

from graphgen.bases.base_storage import BaseGraphStorage, BaseKVStorage
from graphgen.bases.datatypes import Chunk
from graphgen.models import MMKGBuilder, OpenAIClient
from graphgen.utils import run_concurrent


async def build_mm_kg(
    llm_client: OpenAIClient,
    kg_instance: BaseGraphStorage,
    chunks: List[Chunk],
    progress_bar: Optional[Any] = None,
    cache_storage: Optional[BaseKVStorage] = None,
    enable_cache: bool = True,
    enable_batch_requests: bool = True,
    batch_size: int = 10,
    max_wait_time: float = 0.5,
):
    """
    Build multi-modal KG and merge into kg_instance
    :param llm_client: Synthesizer LLM model to extract entities and relationships
    :param kg_instance
    :param chunks
    :param progress_bar: Progress bar to show the progress of the extraction (optional)
    :param cache_storage: Optional cache storage for extraction results
    :param enable_cache: Whether to enable caching (default: True)
    :param enable_batch_requests: Whether to enable batch requests (default: True)
    :param batch_size: Batch size for requests
    :param max_wait_time: Max wait time for batching
    :return:
    """
    mm_builder = MMKGBuilder(
        llm_client=llm_client,
        cache_storage=cache_storage,
        enable_cache=enable_cache,
        enable_batch_requests=enable_batch_requests,
        batch_size=batch_size,
        max_wait_time=max_wait_time
    )

    results = await run_concurrent(
        mm_builder.extract,
        chunks,
        desc="[2/4] Extracting entities and relationships from multi-modal chunks",
        unit="chunk",
        progress_bar=progress_bar,
    )
    
    # 刷新批量管理器，确保所有请求完成
    if mm_builder.batch_manager:
        await mm_builder.batch_manager.flush()

    nodes = defaultdict(list)
    edges = defaultdict(list)
    for n, e in results:
        for k, v in n.items():
            nodes[k].extend(v)
        for k, v in e.items():
            edges[tuple(sorted(k))].extend(v)

    await run_concurrent(
        lambda kv: mm_builder.merge_nodes(kv, kg_instance=kg_instance),
        list(nodes.items()),
        desc="Inserting entities into storage",
    )

    await run_concurrent(
        lambda kv: mm_builder.merge_edges(kv, kg_instance=kg_instance),
        list(edges.items()),
        desc="Inserting relationships into storage",
    )
    
    # 再次刷新批量管理器，确保所有合并操作中的请求也完成
    if mm_builder.batch_manager:
        await mm_builder.batch_manager.flush()

    return kg_instance
