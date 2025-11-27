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
    """Parse answer text from model response."""
    if not response or not response.strip():
        return ""
    
    # Try various answer markers
    answer_markers = [
        ("Answer:", "en"),
        ("答案：", "zh"),
        ("A:", "en"),
        ("答：", "zh"),
        ("Answer", "en"),
        ("答案", "zh"),
    ]
    
    for marker, lang in answer_markers:
        if marker in response:
            try:
                answer = response.split(marker, 1)[1].strip()
                # Remove quotes if present
                answer = answer.strip('"').strip("'").strip()
                # Remove any trailing markers or extra content
                # Stop at next major marker or end of line if it's a single line answer
                if "\n" in answer:
                    # Take first paragraph or until next major marker
                    lines = answer.split("\n")
                    answer = lines[0].strip()
                    # If first line is very short, try to get more
                    if len(answer) < 20 and len(lines) > 1:
                        answer = "\n".join(lines[:2]).strip()
                
                if answer:
                    return answer
            except (IndexError, ValueError):
                continue
    
    # If no marker found, try to extract answer from plain text
    # Remove common prefixes and clean up
    cleaned = response.strip()
    # Remove question if present
    for q_marker in ["Question:", "问题：", "Q:", "问："]:
        if q_marker in cleaned:
            cleaned = cleaned.split(q_marker, 1)[1].strip()
            if "Answer:" in cleaned or "答案：" in cleaned:
                continue  # Let the marker-based parsing handle it
    
    # If cleaned text is substantial, use it as answer
    if len(cleaned) > 10:
        logger.debug("Using cleaned response as answer (no marker found): %s", cleaned[:100])
        return cleaned.strip('"').strip("'").strip()
    
    logger.warning("Failed to parse answer from response: %s", response[:200] if len(response) > 200 else response)
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
            (AtomicGenerator(actual_llm_client, use_multi_template=use_multi_template, template_seed=template_seed), "atomic"),
            (AggregatedGenerator(actual_llm_client, use_combined_mode=use_combined_mode), "aggregated"),
            (MultiHopGenerator(actual_llm_client), "multi_hop"),
            (CoTGenerator(actual_llm_client, use_combined_mode=use_combined_mode), "cot"),
        ]

        all_results = []
        data_format = generation_config["data_format"]

        tasks = []
        for generator, gen_mode in generators:
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

            task = asyncio.create_task(
                run_concurrent(
                    generate_with_storage,
                    batches_to_use,
                    desc=f"[4/4]Generating QAs for {gen_mode}",
                    unit="batch",
                    progress_bar=progress_bar,
                )
            )
            tasks.append(task)

        per_mode_limits: Dict[str, Optional[int]] = {}
        generator_modes = [gen_mode for _, gen_mode in generators]
        if target_qa_pairs:
            ratio_map = normalize_mode_ratios(mode_ratios_config, generator_modes)
            remaining = target_qa_pairs
            for idx, gen_mode in enumerate(generator_modes):
                if idx == len(generator_modes) - 1:
                    limit = max(0, remaining)
                else:
                    ratio_value = ratio_map.get(gen_mode, 0)
                    limit = max(0, int(round(target_qa_pairs * ratio_value)))
                    limit = min(limit, remaining)
                    remaining -= limit
                per_mode_limits[gen_mode] = limit
            logger.info(
                "[Generation] Per-mode limits: %s (total target: %d)",
                per_mode_limits, target_qa_pairs
            )
        else:
            per_mode_limits = {gen_mode: None for gen_mode in generator_modes}

        # 并发执行所有任务
        results_list = await asyncio.gather(*tasks)

        # 处理结果
        all_results = []
        for results, (generator, gen_mode) in zip(results_list, generators):
            formatted_results = generator.format_generation_results(
                results,
                output_data_format=data_format
            )
            per_mode_limit = per_mode_limits.get(gen_mode)
            formatted_results = limit_results(formatted_results, per_mode_limit)
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

        # 应用总限制（如果去重后仍然超过目标）
        if target_qa_pairs:
            original_count = len(all_results)
            if original_count > target_qa_pairs:
                # 如果去重后仍然超过目标，需要按原始配置的比例重新分配
                # 计算当前各模式的实际数量
                mode_counts: Dict[str, int] = {}
                mode_items: Dict[str, list] = {}
                for result in all_results:
                    mode = result.get("mode", "unknown")
                    mode_counts[mode] = mode_counts.get(mode, 0) + 1
                    if mode not in mode_items:
                        mode_items[mode] = []
                    mode_items[mode].append(result)
                
                # 使用原始配置的比例（而不是去重后的实际比例）
                ratio_map = normalize_mode_ratios(mode_ratios_config, list(mode_items.keys()))
                limited_results = []
                remaining = target_qa_pairs
                
                # 按原始配置的比例分配
                sorted_modes = sorted(mode_items.keys())  # 确保顺序一致
                for idx, mode in enumerate(sorted_modes):
                    items = mode_items[mode]
                    if idx == len(sorted_modes) - 1:
                        # 最后一个模式，使用剩余的所有配额
                        limit = max(0, min(remaining, len(items)))
                    else:
                        ratio_value = ratio_map.get(mode, 0)
                        limit = max(0, int(round(target_qa_pairs * ratio_value)))
                        limit = min(limit, remaining, len(items))
                        remaining -= limit
                    limited_results.extend(items[:limit])
                
                all_results = limited_results
                logger.info(
                    "[Generation] Final results after limiting: %d (target: %d, original: %d, per-mode before: %s)",
                    len(all_results), target_qa_pairs, original_count, mode_counts
                )
            else:
                logger.info(
                    "[Generation] Final results: %d (target: %d, no limiting needed)",
                    len(all_results), target_qa_pairs
                )
        else:
            logger.info("[Generation] Final results: %d (no limit)", len(all_results))

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

            # 在问题阶段应用一个宽松的限制（target * 1.2），以应对答案生成失败
            # 最终结果会在后面应用精确限制
            if target_qa_pairs:
                # 允许生成比目标多20%的问题，以应对答案生成失败
                question_limit = int(target_qa_pairs * 1.2)
                if len(pending_questions) > question_limit:
                    pending_questions = pending_questions[:question_limit]
                    logger.info(
                        "[Generation] Limited pending questions to %d (target: %d, actual: %d)",
                        question_limit, target_qa_pairs, len(pending_questions)
                    )

            if not pending_questions:
                logger.warning(
                    "No new atomic questions available after deduplication. Skipping answer stage."
                )
                return []

            async def answer_question(entry: dict[str, Any]) -> dict[str, Any]:
                context_text = _build_context_text(entry.get("context", {}))
                if not context_text:
                    context_text = entry["question"]
                language = detect_main_language(context_text or entry["question"])
                template = ATOMIC_ANSWER_PROMPT.get(
                    language, ATOMIC_ANSWER_PROMPT["en"]
                )
                prompt = template.format(
                    context=context_text,
                    question=entry["question"],
                )
                response = await actual_llm_client.generate_answer(prompt)
                answer = _parse_answer_from_response(response)
                if not answer:
                    # 如果解析失败，尝试使用原始响应作为答案
                    if response and response.strip():
                        answer = response.strip()
                        logger.warning("Failed to parse answer, using raw response: %s", answer[:100])
                    else:
                        logger.warning("Empty answer response for question: %s", entry["question"][:100])
                        return {}
                metadata = dict(entry.get("metadata") or {})
                metadata["generation_mode"] = "atomic"
                qa_payload = {
                    "question": entry["question"],
                    "answer": answer,
                    "context": entry.get("context", {}),
                    "graph": entry.get("graph", {}),
                    "source_chunks": entry.get("source_chunks", []),
                    "source_documents": entry.get("source_documents", []),
                    "metadata": metadata,
                    "mode": "atomic",
                    "reasoning_path": entry.get("reasoning_path", ""),
                }
                return {entry["hash"]: qa_payload}

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

        if target_qa_pairs:
            original_count = len(results)
            if original_count > target_qa_pairs:
                results = limit_results(results, target_qa_pairs)
                logger.info(
                    "[Generation] Final results after limiting: %d (target: %d, original: %d)",
                    len(results), target_qa_pairs, original_count
                )
            else:
                logger.info(
                    "[Generation] Final results: %d (target: %d, no limiting needed)",
                    len(results), target_qa_pairs
                )
        else:
            logger.info("[Generation] Final results: %d (no limit)", len(results))
    
    # 刷新批量包装器，确保所有请求完成
    if batch_wrapper:
        await batch_wrapper.flush()

    return results
