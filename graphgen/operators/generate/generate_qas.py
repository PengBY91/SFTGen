import asyncio
from typing import Any, Optional, Dict

from graphgen.bases import BaseLLMClient
from graphgen.models import (
    AggregatedGenerator,
    AtomicGenerator,
    CoTGenerator,
    MultiHopGenerator,
)
from graphgen.models.llm.batch_llm_wrapper import BatchLLMWrapper
from graphgen.utils import logger, run_concurrent


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
        return items[:limit]

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

    # 获取优化配置
    use_multi_template = generation_config.get("use_multi_template", True)
    template_seed = generation_config.get("template_seed", None)
    enable_batch_requests = generation_config.get("enable_batch_requests", True)
    batch_size = generation_config.get("batch_size", 10)
    max_wait_time = generation_config.get("max_wait_time", 0.5)
    target_qa_pairs = parse_target_count(generation_config.get("target_qa_pairs"))
    mode_ratios_config = generation_config.get("mode_ratios") or {}
    
    # 创建批量LLM包装器（如果启用批量请求）
    actual_llm_client = llm_client
    batch_wrapper: Optional[BatchLLMWrapper] = None
    if enable_batch_requests:
        batch_wrapper = BatchLLMWrapper(
            llm_client=llm_client,
            batch_size=batch_size,
            max_wait_time=max_wait_time,
            enable_batching=True
        )
        actual_llm_client = batch_wrapper
    
    if mode == "all":
        # 创建所有四种生成器的列表，并记录对应的 mode
        generators = [
            (AtomicGenerator(actual_llm_client, use_multi_template=use_multi_template, template_seed=template_seed), "atomic"),
            (AggregatedGenerator(actual_llm_client), "aggregated"),
            (MultiHopGenerator(actual_llm_client), "multi_hop"),
            (CoTGenerator(actual_llm_client), "cot"),
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
                result["mode"] = gen_mode
            all_results.extend(formatted_results)

        if target_qa_pairs:
            all_results = limit_results(all_results, target_qa_pairs)

        return all_results
    else:
        if mode == "atomic":
            generator = AtomicGenerator(
                actual_llm_client, 
                use_multi_template=use_multi_template, 
                template_seed=template_seed
            )
        elif mode == "aggregated":
            generator = AggregatedGenerator(actual_llm_client)
        elif mode == "multi_hop":
            generator = MultiHopGenerator(actual_llm_client)
        elif mode == "cot":
            generator = CoTGenerator(actual_llm_client)
        else:
            raise ValueError(f"Unsupported generation mode: {mode}")

        # 创建包装函数，传递chunks_storage和full_docs_storage
        async def generate_with_storage(batch):
            return await generator.generate(
                batch,
                chunks_storage=chunks_storage,
                full_docs_storage=full_docs_storage
            )
        
        results = await run_concurrent(
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
            results, output_data_format=data_format
        )

        if target_qa_pairs:
            results = limit_results(results, target_qa_pairs)
    
    # 刷新批量包装器，确保所有请求完成
    if batch_wrapper:
        await batch_wrapper.flush()

    return results
