import asyncio
from typing import Any, Optional

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
    
    # 获取优化配置
    use_multi_template = generation_config.get("use_multi_template", True)
    template_seed = generation_config.get("template_seed", None)
    enable_batch_requests = generation_config.get("enable_batch_requests", True)
    batch_size = generation_config.get("batch_size", 10)
    max_wait_time = generation_config.get("max_wait_time", 0.5)
    
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

        # 并发执行所有任务
        results_list = await asyncio.gather(*tasks)

        # 处理结果
        all_results = []
        for results, (generator, gen_mode) in zip(results_list, generators):
            formatted_results = generator.format_generation_results(
                results,
                output_data_format=data_format
            )
            for result in formatted_results:
                result["mode"] = gen_mode
            all_results.extend(formatted_results)

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
    
    # 刷新批量包装器，确保所有请求完成
    if batch_wrapper:
        await batch_wrapper.flush()

    return results
