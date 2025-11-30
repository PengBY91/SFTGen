import asyncio
from typing import Any, Optional, Dict

from graphgen.bases import BaseLLMClient
from graphgen.models import (
    AggregatedGenerator,
    AtomicGenerator,
    AtomicQuestionGenerator,
    CoTGenerator,
    MultiHopGenerator,
)
from graphgen.models.llm.batch_llm_wrapper import BatchLLMWrapper
from graphgen.templates import ATOMIC_ANSWER_PROMPT
from graphgen.utils import compute_content_hash, detect_main_language, logger, run_concurrent


def _extract_question_from_formatted_result(result: dict[str, Any]) -> str:
    """Extract question text from different output formats."""
    if not isinstance(result, dict):
        return ""
    if "instruction" in result:
        return result.get("instruction", "")
    if "conversations" in result:
        for msg in result.get("conversations", []):
            if msg.get("from") == "human":
                return msg.get("value", "")
    if "messages" in result:
        for msg in result.get("messages", []):
            if msg.get("role") == "user":
                return msg.get("content", "")
    return result.get("question") or result.get("input", "")


def _filter_one_hop_batch(
    batch: tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]
) -> tuple[list[tuple[str, dict]], list[tuple[Any, Any, dict]]]:
    """
    Filter batch to contain only one-hop information for atomic generation.
    For atomic mode, we should only use a small amount of graph information (one hop).
    This function limits the batch to contain at most one node and its directly connected edges,
    or one edge and its two endpoint nodes.
    
    :param batch: Original batch (nodes, edges)
    :return: Filtered batch with one-hop information only
    """
    nodes, edges = batch
    
    # If batch is already small (1-2 nodes, 0-2 edges), return as is
    if len(nodes) <= 2 and len(edges) <= 2:
        return batch
    
    # Strategy 1: If there's a single edge, keep only that edge and its two endpoint nodes
    if len(edges) == 1 and len(nodes) <= 3:
        edge = edges[0]
        source, target = edge[0], edge[1]
        filtered_nodes = [n for n in nodes if n[0] == source or n[0] == target]
        return (filtered_nodes, edges)
    
    # Strategy 2: If there's a single node, keep only that node and edges directly connected to it
    if len(nodes) == 1:
        node_id = nodes[0][0]
        filtered_edges = [e for e in edges if e[0] == node_id or e[1] == node_id]
        # Also include nodes connected by these edges
        connected_node_ids = set()
        for e in filtered_edges:
            connected_node_ids.add(e[0])
            connected_node_ids.add(e[1])
        filtered_nodes = [n for n in nodes if n[0] in connected_node_ids]
        return (filtered_nodes, filtered_edges)
    
    # Strategy 3: For larger batches, select the first node and its one-hop neighbors
    if len(nodes) > 0:
        # Use the first node as anchor
        anchor_node_id = nodes[0][0]
        # Find edges connected to anchor
        connected_edges = [e for e in edges if e[0] == anchor_node_id or e[1] == anchor_node_id]
        # Find nodes connected to anchor
        connected_node_ids = {anchor_node_id}
        for e in connected_edges:
            connected_node_ids.add(e[0])
            connected_node_ids.add(e[1])
        filtered_nodes = [n for n in nodes if n[0] in connected_node_ids]
        # Limit to at most 3 nodes and 3 edges for atomic mode
        if len(filtered_nodes) > 3:
            filtered_nodes = filtered_nodes[:3]
        if len(connected_edges) > 3:
            connected_edges = connected_edges[:3]
        return (filtered_nodes, connected_edges)
    
    # Fallback: return original batch if no filtering strategy applies
    return batch


def _build_context_text(context_block: dict[str, Any]) -> str:
    """Reconstruct textual context from the stored context metadata."""
    if not isinstance(context_block, dict):
        return ""
    context_lines = []
    for node in context_block.get("nodes", []):
        context_lines.append(f"- {node.get('name', '')}: {node.get('description', '')}")
    for edge in context_block.get("edges", []):
        source = edge.get("source", "")
        target = edge.get("target", "")
        desc = edge.get("description", "")
        context_lines.append(f"- {source} - {target}: {desc}")
    return "\n".join(line for line in context_lines if line.strip())


def _parse_answer_from_response(response: str) -> str:
    """
    Parse answer text from model response.
    
    Returns empty string if parsing fails, allowing caller to handle the failure.
    """
    if not response or not response.strip():
        logger.debug("Empty response provided to _parse_answer_from_response")
        return ""
    
    response_clean = response.strip()
    
    # Strategy 1: Try various answer markers (most common case)
    answer_markers = [
        ("答案：", "zh"),  # 中文全角冒号
        ("答案:", "zh"),   # 中文半角冒号
        ("Answer:", "en"), # 英文
        ("A:", "en"),
        ("答：", "zh"),
        ("答:", "zh"),
        ("Answer", "en"),  # 无冒号
        ("答案", "zh"),    # 无冒号
    ]
    
    for marker, lang in answer_markers:
        if marker in response_clean:
            try:
                # 找到标记后的内容
                parts = response_clean.split(marker, 1)
                if len(parts) > 1:
                    answer = parts[1].strip()
                    
                    # 移除引号
                    answer = answer.strip('"').strip("'").strip()
                    
                    # 移除后续的问题标记或其他标记
                    for q_marker in ["问题：", "Question:", "Q:", "问："]:
                        if q_marker in answer:
                            answer = answer.split(q_marker, 1)[0].strip()
                    
                    # 处理多行答案：取第一段或前两段（如果第一段太短）
                    if "\n" in answer:
                        lines = [line.strip() for line in answer.split("\n") if line.strip()]
                        if lines:
                            # 如果第一行足够长，只用第一行
                            if len(lines[0]) >= 20:
                                answer = lines[0]
                            # 否则取前两行
                            elif len(lines) > 1:
                                answer = "\n".join(lines[:2])
                            else:
                                answer = lines[0]
                    
                    if answer and len(answer.strip()) > 0:
                        logger.debug(
                            "Successfully parsed answer using marker '%s': %s",
                            marker, answer[:100]
                        )
                        return answer
            except (IndexError, ValueError) as e:
                logger.debug("Error parsing with marker '%s': %s", marker, str(e))
                continue
    
    # Strategy 2: Check if response contains question marker (response might be Q&A format)
    # If so, extract the answer part
    for q_marker in ["问题：", "Question:", "Q:", "问："]:
        if q_marker in response_clean:
            # 找到问题标记后的内容
            parts = response_clean.split(q_marker, 1)
            if len(parts) > 1:
                after_question = parts[1].strip()
                # 检查是否有答案标记
                for a_marker in ["答案：", "Answer:", "A:", "答："]:
                    if a_marker in after_question:
                        answer = after_question.split(a_marker, 1)[1].strip()
                        answer = answer.strip('"').strip("'").strip()
                        if answer:
                            logger.debug(
                                "Successfully parsed answer after question marker: %s",
                                answer[:100]
                            )
                            return answer
                # 如果没有答案标记，但问题后的内容足够长，可能是答案
                if len(after_question) > 20:
                    logger.debug(
                        "Using content after question marker as answer: %s",
                        after_question[:100]
                    )
                    return after_question
    
    # Strategy 3: If no markers found, check if entire response looks like an answer
    # (not a question, not too short)
    cleaned = response_clean
    
    # 移除常见的提示词前缀
    prefixes_to_remove = [
        "根据以上文本，",
        "Based on the text above,",
        "根据文本，",
        "Based on the text,",
        "根据提供的信息，",
        "Based on the provided information,",
    ]
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    
    # 检查是否包含问题（如果包含，可能不是纯答案）
    has_question_markers = any(marker in cleaned for marker in ["问题：", "Question:", "Q:", "问：", "？", "?"])
    
    # 如果文本足够长且不包含问题标记，可能是答案
    if len(cleaned) > 10 and not has_question_markers:
        logger.debug(
            "Using entire cleaned response as answer (no markers found): %s",
            cleaned[:100]
        )
        return cleaned.strip('"').strip("'").strip()
    
    # Strategy 4: Last resort - if response is substantial, use it anyway
    if len(response_clean) > 20:
        logger.warning(
            "No answer markers found, but response is substantial. Using as answer: %s",
            response_clean[:100]
        )
        return response_clean.strip('"').strip("'").strip()
    
    # All strategies failed
    logger.warning(
        "Failed to parse answer from response. Length: %d, Content: %s",
        len(response_clean), response_clean[:200]
    )
    return ""


def _build_question_hash(question: str, mode: Optional[str] = None) -> str:
    """Build a question hash that is scoped by mode to avoid cross-mode collisions."""
    key = f"{(mode or '').strip()}::{question.strip()}"
    return compute_content_hash(key)


def deduplicate_formatted_items(
    items: list[dict[str, Any]],
    seen_hashes: set[str],
    persist_seen: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    deduplicated = []
    for result in items:
        question = _extract_question_from_formatted_result(result)
        if not question:
            deduplicated.append(result)
            continue
        question_hash = _build_question_hash(question, result.get("mode"))
        if question_hash in seen_hashes:
            continue
        seen_hashes.add(question_hash)
        if persist_seen is not None:
            persist_seen.add(question_hash)
        deduplicated.append(result)
    removed = len(items) - len(deduplicated)
    if removed > 0:
        logger.info("Deduplication removed %d duplicated results", removed)
    return deduplicated


async def generate_qas(
    llm_client: BaseLLMClient,
    batches: list[
        tuple[
            list[tuple[str, dict]], list[tuple[Any, Any, dict] | tuple[Any, Any, Any]]
        ]
    ],
    generation_config: dict,
    progress_bar=None,
    chunks_storage=None,
    full_docs_storage=None,
    qa_storage=None,
) -> list[dict[str, Any]]:
    """
    Generate question-answer pairs based on nodes and edges.
    :param llm_client: LLM client
    :param batches
    :param generation_config
    :param progress_bar
    :param chunks_storage: chunks storage instance
    :param full_docs_storage: full documents storage instance
    :return: QA pairs
    """
    mode = generation_config["mode"]
    logger.debug("[Generation] mode: %s, batches: %d", mode, len(batches))
    
    def limit_results(items: list[dict[str, Any]], limit: Optional[int]) -> list[dict[str, Any]]:
        if limit is None or limit <= 0:
            return items if limit is None else []
        original_count = len(items)
        limited = items[:limit]
        if original_count > limit:
            logger.info(
                "Limited results: %d -> %d (target: %d)",
                original_count, len(limited), limit
            )
        return limited

    def normalize_mode_ratios(ratios: Dict[str, Any], modes: list[str]) -> Dict[str, float]:
        normalized = {}
        for mode_name in modes:
            value = ratios.get(mode_name, 0)
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = 0.0
            normalized[mode_name] = max(0.0, value)
        total = sum(normalized.values())
        if total <= 0:
            equal_ratio = 1.0 / len(modes) if modes else 0
            return {mode_name: equal_ratio for mode_name in modes}
        return {mode_name: normalized[mode_name] / total for mode_name in modes}

    def parse_target_count(raw_value: Any) -> Optional[int]:
        if raw_value in (None, "", False):
            return None
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    question_first_enabled = generation_config.get("question_first", mode == "atomic")
    persistent_deduplication = generation_config.get("persistent_deduplication", True)
    persistent_question_hashes: set[str] = set()
    if persistent_deduplication and qa_storage:
        try:
            existing_items = await qa_storage.all_items()
            for item in existing_items or []:
                question_text = _extract_question_from_formatted_result(item)
                if question_text:
                    persistent_question_hashes.add(
                        _build_question_hash(question_text, item.get("mode"))
                    )
            logger.info(
                "[Generation] Loaded %d persisted questions for deduplication",
                len(persistent_question_hashes),
            )
        except Exception as exc:
            logger.warning("Failed to load persisted QA for deduplication: %s", exc)
    session_seen_hashes: set[str] = set(persistent_question_hashes)
    
    # 获取优化配置
    use_multi_template = generation_config.get("use_multi_template", True)
    template_seed = generation_config.get("template_seed", None)
    chinese_only = generation_config.get("chinese_only", False)
    enable_batch_requests = generation_config.get("enable_batch_requests", True)
    batch_size = generation_config.get("batch_size", 10)
    max_wait_time = generation_config.get("max_wait_time", 0.5)
    enable_cache = generation_config.get("enable_prompt_cache", True)
    cache_max_size = generation_config.get("cache_max_size", 10000)
    cache_ttl = generation_config.get("cache_ttl", None)
    use_combined_mode = generation_config.get("use_combined_mode", False)
    use_adaptive_batching = generation_config.get("use_adaptive_batching", False)
    min_batch_size = generation_config.get("min_batch_size", 5)
    max_batch_size = generation_config.get("max_batch_size", 50)
    target_qa_pairs = parse_target_count(generation_config.get("target_qa_pairs"))
    mode_ratios_config = generation_config.get("mode_ratios") or {}
    
    # 记录目标数量配置
    if target_qa_pairs:
        logger.info(
            "[Generation] Target QA pairs: %d, Mode: %s, Mode ratios: %s",
            target_qa_pairs, mode, mode_ratios_config
        )
    else:
        logger.info("[Generation] No target QA pairs limit (unlimited generation)")
    
    # 动态调整batches数量（如果设置了目标数量）
    # 估算每个batch平均生成多少个QA对，然后调整batches数量
    if target_qa_pairs and batches:
        # 不同模式的估算值（可以根据实际情况调整）
        estimated_qa_per_batch = {
            "atomic": 1.5,      # atomic模式每个batch约1-2个QA对
            "aggregated": 2.0,  # aggregated模式每个batch约2个QA对
            "multi_hop": 1.5,   # multi_hop模式每个batch约1-2个QA对
            "cot": 1.5,         # cot模式每个batch约1-2个QA对
        }
        
        if mode == "all":
            # 对于all模式，需要为每个子模式分别计算
            # 使用平均估算值
            avg_qa_per_batch = sum(estimated_qa_per_batch.values()) / len(estimated_qa_per_batch)
            # 考虑去重和失败率，使用1.5倍缓冲
            required_batches = int(target_qa_pairs / avg_qa_per_batch * 1.5)
        else:
            # 单个模式
            avg_qa_per_batch = estimated_qa_per_batch.get(mode, 1.5)
            # 考虑去重和失败率，使用1.5倍缓冲
            required_batches = int(target_qa_pairs / avg_qa_per_batch * 1.5)
        
        # 如果需要的batches数量超过实际batches，考虑重复使用或拆分
        if required_batches > len(batches):
            original_batch_count = len(batches)
            # 如果batches数量不足，重复使用batches直到达到目标
            # 使用循环方式重复batches，确保覆盖所有原始batches
            repeat_times = (required_batches + len(batches) - 1) // len(batches)  # 向上取整
            extended_batches = []
            for i in range(repeat_times):
                extended_batches.extend(batches)
            batches = extended_batches[:required_batches]
            logger.warning(
                "[Generation] Batches数量不足: 实际 %d 个, 需要 %d 个. "
                "已重复使用batches %d 次, 扩展到 %d 个 (target: %d QA pairs, estimated %.1f QA per batch). "
                "建议减小分区参数 max_units_per_community 以生成更多batches.",
                original_batch_count, required_batches, repeat_times, len(batches), 
                target_qa_pairs, avg_qa_per_batch
            )
        elif required_batches < len(batches):
            original_batch_count = len(batches)
            batches = batches[:required_batches]
            logger.info(
                "[Generation] Dynamically adjusted batches: %d -> %d (target: %d QA pairs, estimated %.1f QA per batch)",
                original_batch_count, len(batches), target_qa_pairs, avg_qa_per_batch
            )
        else:
            logger.info(
                "[Generation] Using all %d batches (target: %d QA pairs, estimated %.1f QA per batch, required: %d batches)",
                len(batches), target_qa_pairs, avg_qa_per_batch, required_batches
            )
    
    # 创建批量LLM包装器（如果启用批量请求或缓存）
    actual_llm_client = llm_client
    batch_wrapper: Optional[BatchLLMWrapper] = None
    if enable_batch_requests or enable_cache:
        batch_wrapper = BatchLLMWrapper(
            llm_client=llm_client,
            batch_size=batch_size,
            max_wait_time=max_wait_time,
            enable_batching=enable_batch_requests,
            enable_cache=enable_cache,
            cache_max_size=cache_max_size,
            cache_ttl=cache_ttl,
            use_adaptive_batching=use_adaptive_batching,
            min_batch_size=min_batch_size,
            max_batch_size=max_batch_size,
        )
        actual_llm_client = batch_wrapper
    
    # 获取合并模式配置
    use_combined_mode = generation_config.get("use_combined_mode", False)
    
    if mode == "all":
        # 创建所有四种生成器的列表，并记录对应的 mode
        generators = [
            (AtomicGenerator(actual_llm_client, use_multi_template=use_multi_template, template_seed=template_seed, chinese_only=chinese_only), "atomic"),
            (AggregatedGenerator(actual_llm_client, use_combined_mode=use_combined_mode), "aggregated"),
            (MultiHopGenerator(actual_llm_client), "multi_hop"),
            (CoTGenerator(actual_llm_client, use_combined_mode=use_combined_mode), "cot"),
        ]

        all_results = []
        data_format = generation_config["data_format"]
        
        # 计算每个模式的目标QA数量
        mode_names = [gen_mode for _, gen_mode in generators]
        mode_ratios = normalize_mode_ratios(mode_ratios_config, mode_names)
        mode_targets = {}
        if target_qa_pairs:
            for mode_name in mode_names:
                mode_targets[mode_name] = int(target_qa_pairs * mode_ratios[mode_name])
            logger.info(
                "[Generation] Mode targets: %s (total: %d)",
                mode_targets, target_qa_pairs
            )

        tasks = []
        for idx, (generator, gen_mode) in enumerate(generators):
            # 对于atomic模式，过滤批次为一跳信息
            batches_to_use = batches
            if gen_mode == "atomic":
                batches_to_use = [
                    _filter_one_hop_batch(batch) for batch in batches
                ]
                logger.info(
                    "[Generation] Filtered batches for atomic mode to one-hop information. "
                    "Original batch count: %d, Filtered batch count: %d",
                    len(batches), len(batches_to_use)
                )
            
            # 创建包装函数，传递chunks_storage和full_docs_storage
            async def generate_with_storage(
                batch,
                current_generator=generator,
            ):
                return await current_generator.generate(
                    batch,
                    chunks_storage=chunks_storage,
                    full_docs_storage=full_docs_storage,
                )
            
            # 创建动态描述回调函数
            def create_desc_callback(mode_name, mode_idx, total_modes):
                def desc_callback(completed_batches, total_batches, results):
                    # 计算当前已生成的QA数量
                    # results 是 generator.generate() 返回的 dict 列表
                    # 每个 dict 的键数量 = QA 对数量
                    current_qa_count = sum(len(r) if isinstance(r, dict) else 0 for r in results)
                    
                    # 构建描述字符串
                    desc_parts = [f"[类型 {mode_idx + 1}/{total_modes}: {mode_name}]"]
                    desc_parts.append(f"批次: {completed_batches}/{total_batches}")
                    
                    if target_qa_pairs and mode_name in mode_targets:
                        mode_target = mode_targets[mode_name]
                        desc_parts.append(f"| 已生成: {current_qa_count} QA (目标: {mode_target})")
                        desc_parts.append(f"| 总目标: {target_qa_pairs} QA")
                    else:
                        desc_parts.append(f"| 已生成: {current_qa_count} QA")
                    
                    return " ".join(desc_parts)
                return desc_callback

            task = asyncio.create_task(
                run_concurrent(
                    generate_with_storage,
                    batches_to_use,
                    desc=f"[类型 {idx + 1}/{len(generators)}: {gen_mode}]",
                    unit="batch",
                    progress_bar=progress_bar,
                    desc_callback=create_desc_callback(gen_mode, idx, len(generators)),
                )
            )
            tasks.append(task)

        # 并发执行所有任务
        results_list = await asyncio.gather(*tasks)

        # 处理结果（不应用每个模式的限制，允许超过目标）
        all_results = []
        for results, (generator, gen_mode) in zip(results_list, generators):
            formatted_results = generator.format_generation_results(
                results,
                output_data_format=data_format
            )
            for result in formatted_results:
                # 强制设置 mode 为当前生成模式，确保正确性
                old_mode = result.get("mode")
                result["mode"] = gen_mode
                if old_mode and old_mode != gen_mode:
                    logger.warning(
                        "[Generation] Mode mismatch: expected %s, found %s in result, corrected to %s",
                        gen_mode, old_mode, gen_mode
                    )
            all_results.extend(formatted_results)
            logger.info(
                "[Generation] Mode %s generated %d QA pairs",
                gen_mode, len(formatted_results)
            )
        
        # 结果去重（基于内容hash）
        enable_deduplication = generation_config.get("enable_deduplication", True)
        if enable_deduplication:
            original_before_dedup = len(all_results)
            all_results = deduplicate_formatted_items(
                all_results,
                session_seen_hashes,
                persistent_question_hashes if persistent_deduplication else None,
            )
            if original_before_dedup != len(all_results):
                logger.info(
                    "[Generation] After deduplication: %d -> %d results",
                    original_before_dedup, len(all_results)
                )

        # 统计各模式的数量（不应用限制，允许超过目标）
        if target_qa_pairs:
            mode_counts: Dict[str, int] = {}
            for result in all_results:
                mode = result.get("mode", "unknown")
                mode_counts[mode] = mode_counts.get(mode, 0) + 1
            logger.info(
                "[Generation] Final results: %d (target: %d, per-mode counts: %s)",
                len(all_results), target_qa_pairs, mode_counts
            )
        else:
            mode_counts: Dict[str, int] = {}
            for result in all_results:
                mode = result.get("mode", "unknown")
                mode_counts[mode] = mode_counts.get(mode, 0) + 1
            logger.info(
                "[Generation] Final results: %d (no limit, per-mode counts: %s)",
                len(all_results), mode_counts
            )

        return all_results
    else:
        if mode == "atomic":
            # Filter batches to contain only one-hop information for atomic mode
            filtered_batches = [
                _filter_one_hop_batch(batch) for batch in batches
            ]
            batches = filtered_batches
            logger.info(
                "[Generation] Filtered batches for atomic mode to one-hop information. "
                "Original batch count: %d, Filtered batch count: %d",
                len(batches), len(filtered_batches)
            )
            generator = AtomicGenerator(
                actual_llm_client,
                use_multi_template=use_multi_template,
                template_seed=template_seed,
                chinese_only=chinese_only,
            )
        elif mode == "aggregated":
            generator = AggregatedGenerator(
                actual_llm_client, use_combined_mode=use_combined_mode
            )
        elif mode == "multi_hop":
            generator = MultiHopGenerator(actual_llm_client)
        elif mode == "cot":
            generator = CoTGenerator(
                actual_llm_client, use_combined_mode=use_combined_mode
            )
        else:
            raise ValueError(f"Unsupported generation mode: {mode}")

        # 创建包装函数，传递chunks_storage和full_docs_storage
        async def generate_with_storage(batch):
            return await generator.generate(
                batch,
                chunks_storage=chunks_storage,
                full_docs_storage=full_docs_storage,
            )

        async def run_atomic_two_stage() -> list[dict[str, Any]]:
            question_generator = AtomicQuestionGenerator(
                actual_llm_client,
                use_multi_template=use_multi_template,
                template_seed=template_seed,
                chinese_only=chinese_only,
            )

            async def generate_questions_with_storage(batch):
                return await question_generator.generate(
                    batch,
                    chunks_storage=chunks_storage,
                    full_docs_storage=full_docs_storage,
                )

            question_results = await run_concurrent(
                generate_questions_with_storage,
                batches,
                desc="[4/4]Generating atomic questions",
                unit="batch",
                progress_bar=progress_bar,
            )

            pending_questions: list[dict[str, Any]] = []
            for batch_result in question_results:
                for key, payload in batch_result.items():
                    question = payload.get("question")
                    if not question:
                        continue
                    question_hash = key or _build_question_hash(question, "atomic")
                    if question_hash in session_seen_hashes:
                        continue
                    session_seen_hashes.add(question_hash)
                    pending_questions.append(
                        {
                            "hash": question_hash,
                            "question": question,
                            "context": payload.get("context", {}),
                            "graph": payload.get("graph", {}),
                            "source_chunks": payload.get("source_chunks", []),
                            "source_documents": payload.get("source_documents", []),
                            "metadata": dict(payload.get("metadata") or {}),
                            "reasoning_path": payload.get("reasoning_path", ""),
                        }
                    )

            # 记录问题数量（不应用限制，允许超过目标）
            if target_qa_pairs:
                logger.info(
                    "[Generation] Generated %d questions (target: %d QA pairs)",
                    len(pending_questions), target_qa_pairs
                )

            if not pending_questions:
                logger.warning(
                    "No new atomic questions available after deduplication. Skipping answer stage."
                )
                return []

            async def answer_question(entry: dict[str, Any]) -> dict[str, Any]:
                try:
                    # 1. 构建上下文 - 分析为什么可能为空
                    context_text = _build_context_text(entry.get("context", {}))
                    if not context_text:
                        # 如果上下文为空，尝试从 graph 中重建
                        graph = entry.get("graph", {})
                        if graph:
                            nodes = graph.get("entities", [])
                            edges = graph.get("relationships", [])
                            context_parts = []
                            # 从 graph 的 nodes 和 edges 重建上下文
                            for node in nodes[:3]:
                                if isinstance(node, str):
                                    context_parts.append(f"- {node}")
                                elif isinstance(node, dict):
                                    name = node.get("name", "")
                                    desc = node.get("description", "")
                                    if name or desc:
                                        context_parts.append(f"- {name}: {desc}")
                            for edge in edges[:3]:
                                if isinstance(edge, list) and len(edge) >= 2:
                                    context_parts.append(f"- {edge[0]} -> {edge[1]}")
                            context_text = "\n".join(context_parts) if context_parts else entry["question"]
                        else:
                            context_text = entry["question"]
                            logger.warning(
                                "No context available for question, using question as context: %s",
                                entry["question"][:100]
                            )
                    
                    # 2. 检测语言并选择模板
                    language = detect_main_language(context_text or entry["question"])
                    
                    # 3. 选择模板（考虑chinese_only配置）
                    if chinese_only:
                        from graphgen.templates import ATOMIC_ANSWER_PROMPT_CHINESE_ONLY
                        template = ATOMIC_ANSWER_PROMPT_CHINESE_ONLY.get("zh", ATOMIC_ANSWER_PROMPT["zh"])
                    else:
                        template = ATOMIC_ANSWER_PROMPT.get(
                            language, ATOMIC_ANSWER_PROMPT["en"]
                        )
                    
                    # 3. 构建 prompt
                    prompt = template.format(
                        context=context_text,
                        question=entry["question"],
                    )
                    
                    # 4. 调用 LLM 生成答案
                    response = await actual_llm_client.generate_answer(prompt)
                    
                    # 5. 分析响应 - 为什么可能为空或解析失败
                    if not response:
                        logger.error(
                            "LLM returned None for question: %s, context length: %d",
                            entry["question"][:100], len(context_text)
                        )
                        # 返回空字典会导致问题丢失，改为返回带错误标记的 QA 对
                        return {
                            entry["hash"]: {
                                "question": entry["question"],
                                "answer": "",
                                "context": entry.get("context", {}),
                                "graph": entry.get("graph", {}),
                                "source_chunks": entry.get("source_chunks", []),
                                "source_documents": entry.get("source_documents", []),
                                "metadata": {
                                    "generation_mode": "atomic",
                                    "answer_generation_failed": True,
                                    "failure_reason": "LLM returned None"
                                },
                                "mode": "atomic",
                                "reasoning_path": entry.get("reasoning_path", ""),
                            }
                        }
                    
                    response_clean = response.strip()
                    if not response_clean:
                        logger.error(
                            "LLM returned empty string for question: %s, raw response length: %d",
                            entry["question"][:100], len(response)
                        )
                        return {
                            entry["hash"]: {
                                "question": entry["question"],
                                "answer": "",
                                "context": entry.get("context", {}),
                                "graph": entry.get("graph", {}),
                                "source_chunks": entry.get("source_chunks", []),
                                "source_documents": entry.get("source_documents", []),
                                "metadata": {
                                    "generation_mode": "atomic",
                                    "answer_generation_failed": True,
                                    "failure_reason": "LLM returned empty string"
                                },
                                "mode": "atomic",
                                "reasoning_path": entry.get("reasoning_path", ""),
                            }
                        }
                    
                    # 6. 解析答案 - 分析为什么可能失败
                    answer = _parse_answer_from_response(response_clean)
                    
                    if not answer:
                        # 分析解析失败的原因
                        logger.warning(
                            "Failed to parse answer from response. Question: %s, Response length: %d, Response preview: %s",
                            entry["question"][:100], len(response_clean), response_clean[:200]
                        )
                        
                        # 尝试更宽松的解析策略
                        # 策略1: 检查是否响应本身就是答案（没有标记）
                        if len(response_clean) > 10:
                            # 移除可能的提示词残留
                            cleaned = response_clean
                            # 移除开头的常见提示词
                            prefixes_to_remove = [
                                "根据以上文本，",
                                "Based on the text above,",
                                "根据文本，",
                                "Based on the text,",
                            ]
                            for prefix in prefixes_to_remove:
                                if cleaned.startswith(prefix):
                                    cleaned = cleaned[len(prefix):].strip()
                            
                            # 如果清理后的文本足够长，使用它作为答案
                            if len(cleaned) > 10:
                                answer = cleaned
                                logger.info(
                                    "Using cleaned response as answer (no marker found): %s",
                                    answer[:100]
                                )
                        
                        # 策略2: 如果还是没有答案，尝试提取第一段
                        if not answer:
                            # 按段落分割
                            paragraphs = [p.strip() for p in response_clean.split("\n\n") if p.strip()]
                            if paragraphs:
                                # 使用第一段，但排除明显是问题或提示的部分
                                first_para = paragraphs[0]
                                # 检查是否包含问题标记
                                if not any(marker in first_para for marker in ["问题：", "Question:", "Q:", "问："]):
                                    if len(first_para) > 10:
                                        answer = first_para
                                        logger.info(
                                            "Using first paragraph as answer: %s",
                                            answer[:100]
                                        )
                        
                        # 策略3: 如果仍然失败，记录详细信息用于分析
                        if not answer:
                            logger.error(
                                "All parsing strategies failed. Response details:\n"
                                "  Question: %s\n"
                                "  Response length: %d\n"
                                "  Response content: %s\n"
                                "  Context length: %d\n"
                                "  Has answer markers: %s",
                                entry["question"][:100],
                                len(response_clean),
                                response_clean[:500],
                                len(context_text),
                                any(marker in response_clean for marker in ["答案：", "Answer:", "A:", "答："])
                            )
                            # 即使解析失败，也返回响应内容，避免丢失问题
                            answer = response_clean[:500]  # 限制长度
                    
                    # 7. 验证并返回结果
                    if answer and len(answer.strip()) > 0:
                        metadata = dict(entry.get("metadata") or {})
                        metadata["generation_mode"] = "atomic"
                        qa_payload = {
                            "question": entry["question"],
                            "answer": answer.strip(),
                            "context": entry.get("context", {}),
                            "graph": entry.get("graph", {}),
                            "source_chunks": entry.get("source_chunks", []),
                            "source_documents": entry.get("source_documents", []),
                            "metadata": metadata,
                            "mode": "atomic",
                            "reasoning_path": entry.get("reasoning_path", ""),
                        }
                        return {entry["hash"]: qa_payload}
                    else:
                        logger.error(
                            "Answer is empty after all parsing attempts. Question: %s",
                            entry["question"][:100]
                        )
                        # 返回空答案但保留问题，避免丢失
                        return {
                            entry["hash"]: {
                                "question": entry["question"],
                                "answer": "",
                                "context": entry.get("context", {}),
                                "graph": entry.get("graph", {}),
                                "source_chunks": entry.get("source_chunks", []),
                                "source_documents": entry.get("source_documents", []),
                                "metadata": {
                                    "generation_mode": "atomic",
                                    "answer_generation_failed": True,
                                    "failure_reason": "Answer parsing failed",
                                    "raw_response": response_clean[:500]
                                },
                                "mode": "atomic",
                                "reasoning_path": entry.get("reasoning_path", ""),
                            }
                        }
                
                except Exception as e:
                    logger.exception(
                        "Exception in answer_question for question: %s - %s",
                        entry["question"][:100], str(e)
                    )
                    # 返回带错误信息的 QA 对，避免丢失问题
                    return {
                        entry["hash"]: {
                            "question": entry["question"],
                            "answer": "",
                            "context": entry.get("context", {}),
                            "graph": entry.get("graph", {}),
                            "source_chunks": entry.get("source_chunks", []),
                            "source_documents": entry.get("source_documents", []),
                            "metadata": {
                                "generation_mode": "atomic",
                                "answer_generation_failed": True,
                                "failure_reason": f"Exception: {str(e)}"
                            },
                            "mode": "atomic",
                            "reasoning_path": entry.get("reasoning_path", ""),
                        }
                    }

            answer_results = await run_concurrent(
                answer_question,
                pending_questions,
                desc="[4/4]Answering atomic questions",
                unit="question",
                progress_bar=progress_bar,
            )
            filtered = [res for res in answer_results if res]
            logger.info(
                "[Generation] Two-stage atomic pipeline produced %d answered questions",
                len(filtered),
            )
            return filtered

        if mode == "atomic" and question_first_enabled:
            raw_generation_results = await run_atomic_two_stage()
        else:
            raw_generation_results = await run_concurrent(
                generate_with_storage,
                batches,
                desc="[4/4]Generating QAs",
                unit="batch",
                progress_bar=progress_bar,
            )

        # format
        data_format = generation_config["data_format"]
        logger.debug("Output data format: %s", data_format)

        results = generator.format_generation_results(
            raw_generation_results, output_data_format=data_format
        )
        
        # 为单个模式添加 mode 字段（如果还没有或与预期不符）
        if mode != "all":
            for result in results:
                old_mode = result.get("mode")
                # 如果 mode 不存在或与预期不符，强制设置为当前模式
                if not old_mode or old_mode != mode:
                    result["mode"] = mode
                    if old_mode and old_mode != mode:
                        logger.warning(
                            "[Generation] Mode mismatch in single mode: expected %s, found %s in result, corrected to %s",
                            mode, old_mode, mode
                        )
        
        # 结果去重（基于内容hash）
        enable_deduplication = generation_config.get("enable_deduplication", True)
        if enable_deduplication:
            results = deduplicate_formatted_items(
                results,
                session_seen_hashes,
                persistent_question_hashes if persistent_deduplication else None,
            )

        # 记录最终结果（不应用限制，允许超过目标）
        if target_qa_pairs:
            logger.info(
                "[Generation] Final results: %d (target: %d, mode: %s)",
                len(results), target_qa_pairs, mode
            )
        else:
            logger.info("[Generation] Final results: %d (no limit, mode: %s)", len(results), mode)
    
    # 刷新批量包装器，确保所有请求完成
    if batch_wrapper:
        await batch_wrapper.flush()

    return results
