"""
优化的KG构建模块 - 支持Prompt合并
将多个chunk的抽取任务合并成一个prompt，显著减少LLM调用次数
"""
from collections import defaultdict
from typing import List, Optional, Any
import re

from graphgen.bases.base_storage import BaseGraphStorage, BaseKVStorage
from graphgen.bases.datatypes import Chunk
from graphgen.models import LightRAGKGBuilder, OpenAIClient
from graphgen.utils import run_concurrent, logger, compute_content_hash
from graphgen.templates import KG_EXTRACTION_PROMPT
from graphgen.utils import (
    detect_main_language,
    handle_single_entity_extraction,
    handle_single_relationship_extraction,
    split_string_by_multi_markers,
)


def batch_chunks(chunks: List[Chunk], batch_size: int) -> List[List[Chunk]]:
    """将chunks分批，每批batch_size个"""
    batches = []
    for i in range(0, len(chunks), batch_size):
        batches.append(chunks[i:i + batch_size])
    return batches


async def build_text_kg_with_prompt_merging(
    llm_client: OpenAIClient,
    kg_instance: BaseGraphStorage,
    chunks: List[Chunk],
    progress_bar: Optional[Any] = None,
    cache_storage: Optional[BaseKVStorage] = None,
    enable_cache: bool = True,
    enable_batch_requests: bool = True,
    batch_size: int = 10,
    max_wait_time: float = 0.5,
    enable_prompt_merging: bool = True,
    prompt_merge_size: int = 5,
):
    """
    优化版本的KG构建，支持Prompt合并
    
    :param llm_client: LLM客户端
    :param kg_instance: 图存储实例
    :param chunks: chunk列表
    :param progress_bar: 进度条
    :param cache_storage: 缓存存储
    :param enable_cache: 是否启用缓存
    :param enable_batch_requests: 是否启用批量请求
    :param batch_size: 批量大小
    :param max_wait_time: 最大等待时间
    :param enable_prompt_merging: 是否启用Prompt合并（关键优化！）
    :param prompt_merge_size: 每次合并的chunk数量
    :return:
    """
    
    kg_builder = LightRAGKGBuilder(
        llm_client=llm_client, 
        max_loop=3,
        cache_storage=cache_storage,
        enable_cache=enable_cache,
        enable_batch_requests=enable_batch_requests,
        batch_size=batch_size,
        max_wait_time=max_wait_time
    )
    
    if enable_prompt_merging and prompt_merge_size > 1:
        logger.info(
            "[Prompt Merging] Enabled with merge_size=%d. "
            "Expected to reduce LLM calls by ~%d%%",
            prompt_merge_size,
            int((1 - 1/prompt_merge_size) * 100)
        )
        # 使用合并模式
        results = await extract_with_prompt_merging(
            kg_builder,
            chunks,
            prompt_merge_size,
            cache_storage,
            enable_cache,
            progress_bar,
        )
    else:
        # 原始模式：每个chunk单独抽取
        results = await run_concurrent(
            kg_builder.extract,
            chunks,
            desc="[2/4]Extracting entities and relationships from chunks",
            unit="chunk",
            progress_bar=progress_bar,
        )
    
    # 刷新批量管理器
    if kg_builder.batch_manager:
        await kg_builder.batch_manager.flush()

    # 合并节点和边
    nodes = defaultdict(list)
    edges = defaultdict(list)
    for n, e in results:
        for k, v in n.items():
            nodes[k].extend(v)
        for k, v in e.items():
            edges[tuple(sorted(k))].extend(v)

    await run_concurrent(
        lambda kv: kg_builder.merge_nodes(kv, kg_instance=kg_instance),
        list(nodes.items()),
        desc="Inserting entities into storage",
    )

    await run_concurrent(
        lambda kv: kg_builder.merge_edges(kv, kg_instance=kg_instance),
        list(edges.items()),
        desc="Inserting relationships into storage",
    )
    
    # 再次刷新
    if kg_builder.batch_manager:
        await kg_builder.batch_manager.flush()

    return kg_instance


async def extract_with_prompt_merging(
    kg_builder: LightRAGKGBuilder,
    chunks: List[Chunk],
    merge_size: int,
    cache_storage: Optional[BaseKVStorage],
    enable_cache: bool,
    progress_bar: Optional[Any] = None,
) -> List:
    """
    使用Prompt合并的抽取方法
    
    将多个chunks合并成一个prompt进行抽取，显著减少LLM调用次数
    
    :param kg_builder: KG构建器
    :param chunks: chunk列表
    :param merge_size: 每次合并的chunk数量
    :param cache_storage: 缓存存储
    :param enable_cache: 是否启用缓存
    :param progress_bar: 进度条
    :return: 抽取结果列表
    """
    # 将chunks分批
    chunk_batches = batch_chunks(chunks, merge_size)
    
    logger.info(
        "[Prompt Merging] Split %d chunks into %d batches (merge_size=%d)",
        len(chunks), len(chunk_batches), merge_size
    )
    
    async def extract_merged_batch(chunk_batch: List[Chunk]):
        """抽取一个合并批次"""
        if len(chunk_batch) == 1:
            # 只有一个chunk，直接使用原始方法
            logger.debug("Single chunk in batch, using original extraction method")
            return [await kg_builder.extract(chunk_batch[0])]
        
        # 检查缓存
        if enable_cache and cache_storage:
            # 为整个batch生成缓存key
            batch_content = "\n\n".join([c.content for c in chunk_batch])
            batch_hash = compute_content_hash(batch_content, prefix="merged-extract-")
            cached_result = await cache_storage.get_by_id(batch_hash)
            if cached_result is not None:
                # 缓存命中时只记录info级别
                logger.info("Cache hit for merged batch of %d chunks", len(chunk_batch))
                return cached_result["results"]
        
        # 构建合并prompt
        merged_prompt = build_merged_extraction_prompt(chunk_batch)
        # 移除过于频繁的debug日志
        # logger.debug(
        #     "Built merged prompt for %d chunks, prompt length: %d",
        #     len(chunk_batch), len(merged_prompt)
        # )
        
        # 调用LLM（一次调用处理多个chunks）
        if kg_builder.batch_manager:
            response = await kg_builder.batch_manager.add_request(merged_prompt)
        else:
            response = await kg_builder.llm_client.generate_answer(merged_prompt)
        
        # 只在有响应时记录摘要信息
        if response:
            logger.debug(
                "Received LLM response for merged batch of %d chunks: length=%d",
                len(chunk_batch), len(response)
            )
        
        # 解析响应，分配给各个chunk（使用await）
        results = await parse_merged_extraction_response(
            response, chunk_batch, kg_builder
        )
        
        # 统计结果
        total_nodes = sum(len(nodes) for nodes, _ in results)
        total_edges = sum(len(edges) for _, edges in results)
        logger.info(
            "Merged batch extraction complete: %d chunks → %d nodes, %d edges",
            len(chunk_batch), total_nodes, total_edges
        )
        
        # 缓存结果
        if enable_cache and cache_storage:
            await cache_storage.upsert({
                batch_hash: {
                    "results": results,
                    "chunk_ids": [c.id for c in chunk_batch]
                }
            })
            # 移除过于频繁的debug日志
            # logger.debug("Cached merged extraction result for %d chunks", len(chunk_batch))
        
        return results
    
    # 并发处理所有批次
    all_results = await run_concurrent(
        extract_merged_batch,
        chunk_batches,
        desc=f"[2/4]Extracting entities (merged, batch_size={merge_size})",
        unit="batch",
        progress_bar=progress_bar,
    )
    
    # 展平结果
    results = []
    for batch_results in all_results:
        results.extend(batch_results)
    
    return results


def build_merged_extraction_prompt(chunk_batch: List[Chunk]) -> str:
    """
    构建合并的抽取prompt
    
    将多个chunks的内容合并到一个prompt中
    """
    # 检测语言（使用第一个chunk的语言）
    first_content = chunk_batch[0].content
    language = detect_main_language(first_content)
    
    # 构建合并的文本内容
    merged_text_parts = []
    for idx, chunk in enumerate(chunk_batch, 1):
        merged_text_parts.append(f"[文本{idx}]" if language == "zh" else f"[Text {idx}]")
        merged_text_parts.append(chunk.content)
        merged_text_parts.append("")  # 空行分隔
    
    merged_text = "\n".join(merged_text_parts)
    
    # 构建prompt
    base_template = KG_EXTRACTION_PROMPT[language]["TEMPLATE"]
    
    # 修改提示词，说明需要处理多个文本
    if language == "zh":
        instruction = f"""你将看到{len(chunk_batch)}个文本片段。请为每个文本片段分别抽取实体和关系。
在输出中，请在每个实体或关系前标注它来自哪个文本（例如：[文本1]、[文本2]等）。
"""
    else:
        instruction = f"""You will see {len(chunk_batch)} text fragments. Please extract entities and relationships for each text fragment separately.
In your output, please label each entity or relationship with the text number it comes from (e.g., [Text 1], [Text 2], etc.).
"""
    
    prompt = base_template.format(
        **KG_EXTRACTION_PROMPT["FORMAT"],
        input_text=instruction + "\n\n" + merged_text
    )
    
    return prompt


async def parse_merged_extraction_response(
    response: str,
    chunk_batch: List[Chunk],
    kg_builder: LightRAGKGBuilder
) -> List:
    """
    解析合并抽取的响应
    
    将响应分配给对应的chunks
    
    :param response: LLM响应
    :param chunk_batch: chunk批次
    :param kg_builder: KG构建器
    :return: 每个chunk的抽取结果列表
    """
    logger.debug(
        "Parsing merged response for %d chunks, response length: %d",
        len(chunk_batch), len(response)
    )
    # 移除response preview，太占日志空间
    # logger.debug("Response preview: %s", response[:500])
    
    # 分割响应，按文本编号分组
    text_markers_zh = [f"[文本{i}]" for i in range(1, len(chunk_batch) + 1)]
    text_markers_en = [f"[Text {i}]" for i in range(1, len(chunk_batch) + 1)]
    
    # 改进的分割逻辑：按文本标记分组，未标记的行归入当前section
    text_sections = {}  # {chunk_idx: [lines]}
    current_idx = None  # 当前正在处理的文本索引
    
    lines = response.split("\n")
    for line in lines:
        if not line.strip():
            continue
        
        # 检查这一行是否包含新的文本标记
        found_marker_idx = None
        for idx, (marker_zh, marker_en) in enumerate(zip(text_markers_zh, text_markers_en)):
            if marker_zh in line or marker_en in line:
                found_marker_idx = idx
                current_idx = idx  # 更新当前索引
                break
        
        # 如果找到新标记，或者有当前索引，将这行加入对应的section
        if found_marker_idx is not None or current_idx is not None:
            target_idx = found_marker_idx if found_marker_idx is not None else current_idx
            if target_idx not in text_sections:
                text_sections[target_idx] = []
            # 移除行首的标记（如果有）
            clean_line = line
            for marker in text_markers_zh + text_markers_en:
                if marker in clean_line:
                    clean_line = clean_line.replace(marker, "", 1).strip()
                    break
            if clean_line:  # 只添加非空行
                text_sections[target_idx].append(clean_line)
    
    # 转换为列表格式
    text_sections_list = [(idx, "\n".join(lines)) for idx, lines in sorted(text_sections.items())]
    
    logger.debug(
        "Split response into %d sections for %d chunks: %s",
        len(text_sections_list), len(chunk_batch),
        [f"Section{idx}: {len(lines)} lines" for idx, lines in text_sections.items()]
    )
    
    # 如果没有找到标记，将整个响应分配给所有chunks（fallback）
    if not text_sections_list:
        logger.warning(
            "Failed to split merged response by text markers, "
            "falling back to duplicate extraction for all %d chunks. "
            "This might indicate that the LLM did not follow the format correctly.",
            len(chunk_batch)
        )
        logger.debug("Response markers expected: %s", text_markers_zh[:3])
        
        # Fallback策略：将整个响应作为单个文本处理
        # 然后将结果复制给所有chunks
        nodes, edges = await parse_single_extraction(response, chunk_batch[0].id)
        
        logger.info(
            "Fallback extraction result: %d nodes, %d edges (will be assigned to all %d chunks)",
            len(nodes), len(edges), len(chunk_batch)
        )
        
        # 为每个chunk创建相同的结果副本，但使用各自的chunk_id
        results = []
        for chunk in chunk_batch:
            # 创建副本并更新source_id
            chunk_nodes = {}
            for node_name, node_list in nodes.items():
                chunk_nodes[node_name] = [
                    {**node, "source_id": chunk.id} for node in node_list
                ]
            
            chunk_edges = {}
            for edge_key, edge_list in edges.items():
                chunk_edges[edge_key] = [
                    {**edge, "source_id": chunk.id} for edge in edge_list
                ]
            
            results.append((chunk_nodes, chunk_edges))
        
        return results
    
    # 为每个chunk解析其对应的section（使用await）
    results = []
    parsed_count = 0
    fallback_count = 0
    
    for idx, chunk in enumerate(chunk_batch):
        # 找到对应的section
        section_text = None
        for text_idx, section in text_sections_list:
            if text_idx == idx:
                section_text = section
                break
        
        if section_text:
            nodes, edges = await parse_single_extraction(section_text, chunk.id)
            parsed_count += 1
            # 只在前几个或每10个时记录详细信息
            if parsed_count <= 3 or parsed_count % 10 == 0:
                logger.debug(
                    "Chunk %d (%s): parsed section with %d nodes, %d edges",
                    idx, chunk.id, len(nodes), len(edges)
                )
        else:
            # 如果没有找到对应section，记录警告但不返回空结果
            fallback_count += 1
            if fallback_count <= 3:  # 只记录前3个警告
                logger.warning(
                    "No section found for chunk %d (%s), using full response as fallback",
                    idx, chunk.id
                )
            nodes, edges = await parse_single_extraction(response, chunk.id)
        
        results.append((nodes, edges))
    
    # 汇总信息
    if fallback_count > 3:
        logger.warning(
            "Total %d chunks used fallback parsing (only first 3 logged)",
            fallback_count
        )
    
    return results


async def parse_single_extraction(text: str, chunk_id: str):
    """
    解析单个文本的抽取结果
    
    复用LightRAGKGBuilder的解析逻辑
    """
    from graphgen.utils import logger as parse_logger
    
    records = split_string_by_multi_markers(
        text,
        [
            KG_EXTRACTION_PROMPT["FORMAT"]["record_delimiter"],
            KG_EXTRACTION_PROMPT["FORMAT"]["completion_delimiter"],
        ],
    )
    
    # 只在有records时记录总体信息
    if records:
        parse_logger.debug(
            "Parsing extraction for chunk %s: found %d records",
            chunk_id, len(records)
        )
    
    nodes = defaultdict(list)
    edges = defaultdict(list)
    
    # 统计信息（减少日志频率）
    no_match_count = 0
    entity_count = 0
    relation_count = 0
    neither_count = 0
    
    for record_idx, record in enumerate(records):
        match = re.search(r"\((.*)\)", record)
        if not match:
            no_match_count += 1
            # 只记录前几个失败的，或者每100个记录一次
            if no_match_count <= 3 or record_idx % 100 == 0:
                parse_logger.debug("Record %d: no match for pattern", record_idx)
            continue
        inner = match.group(1)
        
        attributes = split_string_by_multi_markers(
            inner, [KG_EXTRACTION_PROMPT["FORMAT"]["tuple_delimiter"]]
        )
        
        # 只在前几个或每100个时记录详细信息
        if record_idx < 3 or record_idx % 100 == 0:
            parse_logger.debug(
                "Record %d: parsed %d attributes, first attr: %s",
                record_idx, len(attributes), attributes[0] if attributes else "N/A"
            )
        
        # 使用 await 而不是 asyncio.run()
        entity = await handle_single_entity_extraction(attributes, chunk_id)
        if entity is not None:
            nodes[entity["entity_name"]].append(entity)
            entity_count += 1
            # 只在前几个或每100个时记录
            if entity_count <= 3 or entity_count % 100 == 0:
                parse_logger.debug("Record %d: extracted entity '%s'", record_idx, entity["entity_name"])
            continue
        
        relation = await handle_single_relationship_extraction(attributes, chunk_id)
        if relation is not None:
            key = (relation["src_id"], relation["tgt_id"])
            edges[key].append(relation)
            relation_count += 1
            # 只在前几个或每100个时记录
            if relation_count <= 3 or relation_count % 100 == 0:
                parse_logger.debug(
                    "Record %d: extracted relationship '%s' -> '%s'",
                    record_idx, relation["src_id"], relation["tgt_id"]
                )
            continue
        
        neither_count += 1
        # 只记录前几个失败的
        if neither_count <= 3:
            parse_logger.warning(
                "Record %d: neither entity nor relationship. Attributes: %s",
                record_idx, attributes[:5] if len(attributes) > 5 else attributes
            )
    
    # 汇总统计信息
    parse_logger.info(
        "Chunk %s extraction complete: %d nodes, %d edges (from %d records, %d failed)",
        chunk_id, len(nodes), len(edges), len(records), no_match_count + neither_count
    )
    
    return dict(nodes), dict(edges)

