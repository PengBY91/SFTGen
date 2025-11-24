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
    if "Answer:" in response:
        return response.split("Answer:", 1)[1].strip().strip('"')
    if "答案：" in response:
        return response.split("答案：", 1)[1].strip().strip('"')
    logger.warning("Failed to parse answer from response: %s", response)
    return ""


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
        question_hash = compute_content_hash(question)
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
                    persistent_question_hashes.add(compute_content_hash(question_text))
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
            # 创建包装函数，传递chunks_storage和full_docs_storage
            async def generate_with_storage(batch):
                return await generator.generate(
                    batch, 
                    chunks_storage=chunks_storage,
                    full_docs_storage=full_docs_storage
                )
            
            task = asyncio.create_task(
                run_concurrent(
                    generate_with_storage,
                    batches,
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
            all_results = deduplicate_formatted_items(
                all_results,
                session_seen_hashes,
                persistent_question_hashes if persistent_deduplication else None,
            )

        if target_qa_pairs:
            original_count = len(all_results)
            all_results = limit_results(all_results, target_qa_pairs)
            logger.info(
                "[Generation] Final results after limiting: %d (target: %d, original: %d)",
                len(all_results), target_qa_pairs, original_count
            )
        else:
            logger.info("[Generation] Final results: %d (no limit)", len(all_results))

        return all_results
    else:
        if mode == "atomic":
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
                    question_hash = key or compute_content_hash(question)
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

            if target_qa_pairs:
                pending_questions = pending_questions[:target_qa_pairs]

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
            results = limit_results(results, target_qa_pairs)
            logger.info(
                "[Generation] Final results after limiting: %d (target: %d, original: %d)",
                len(results), target_qa_pairs, original_count
            )
        else:
            logger.info("[Generation] Final results: %d (no limit)", len(results))
    
    # 刷新批量包装器，确保所有请求完成
    if batch_wrapper:
        await batch_wrapper.flush()

    return results
