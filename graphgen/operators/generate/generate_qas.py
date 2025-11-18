import asyncio
from typing import Any

from graphgen.bases import BaseLLMClient
from graphgen.models import (
    AggregatedGenerator,
    AtomicGenerator,
    CoTGenerator,
    MultiHopGenerator,
)
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
    :return: QA pairs
    """
    mode = generation_config["mode"]
    logger.debug("[Generation] mode: %s, batches: %d", mode, len(batches))
    if mode == "all":
        # 创建所有四种生成器的列表，并记录对应的 mode
        generators = [
            (AtomicGenerator(llm_client), "atomic"),
            (AggregatedGenerator(llm_client), "aggregated"),
            (MultiHopGenerator(llm_client), "multi_hop"),
            (CoTGenerator(llm_client), "cot"),
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
            generator = AtomicGenerator(llm_client)
        elif mode == "aggregated":
            generator = AggregatedGenerator(llm_client)
        elif mode == "multi_hop":
            generator = MultiHopGenerator(llm_client)
        elif mode == "cot":
            generator = CoTGenerator(llm_client)
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

    return results
