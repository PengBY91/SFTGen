"""Generate evaluation dataset from knowledge graph batches"""

import asyncio
from typing import Dict, List, Any
from collections import defaultdict

from graphgen.bases.base_llm_client import BaseLLMClient
from graphgen.bases.eval_datatypes import EvaluationItem, EvaluationDataset
from graphgen.models.eval_generator import (
    KnowledgeCoverageGenerator,
    ReasoningEvalGenerator,
    FactualAccuracyGenerator,
    ComprehensiveEvalGenerator,
)
from graphgen.utils import logger, run_concurrent


async def generate_eval_dataset(
    llm_client: BaseLLMClient,
    batches: List[tuple],
    evaluation_config: Dict[str, Any],
    chunks_storage=None,
    full_docs_storage=None,
) -> EvaluationDataset:
    """
    Generate evaluation dataset from knowledge graph batches.
    
    :param llm_client: LLM client for generation
    :param batches: list of (nodes, edges) tuples
    :param evaluation_config: evaluation configuration
    :param chunks_storage: chunks storage instance
    :param full_docs_storage: full documents storage instance
    :return: EvaluationDataset object
    """
    logger.info("Starting evaluation dataset generation")
    
    # Debug: log the evaluation_config to see what we're receiving
    logger.info(f"Received evaluation_config: {evaluation_config}")
    
    # Extract configuration
    target_eval_items = evaluation_config.get("target_eval_items", 500)
    
    # Handle both nested (old) and flattened (new) config structures
    type_distribution = evaluation_config.get("type_distribution")
    if type_distribution is None:
        # Default distribution
        type_distribution = {
            "knowledge_coverage": 0.3,
            "reasoning_ability": 0.3,
            "factual_accuracy": 0.2,
            "comprehensive": 0.2,
        }
        logger.warning("type_distribution is None, using default distribution")
    
    difficulty_distribution = evaluation_config.get("difficulty_distribution")
    if difficulty_distribution is None:
        # Default distribution
        difficulty_distribution = {
            "easy": 0.3,
            "medium": 0.5,
            "hard": 0.2,
        }
        logger.warning("difficulty_distribution is None, using default distribution")
    
    output_format = evaluation_config.get("output_format", "benchmark")
    
    # Average number of items generated per batch (prompts typically request 2-3 items)
    items_per_batch = evaluation_config.get("items_per_batch", 2.5)
    
    # Calculate target counts for each type and difficulty
    import math
    type_targets = {
        eval_type: math.ceil(target_eval_items * ratio)
        for eval_type, ratio in type_distribution.items()
    }
    
    # Initialize generators
    generators = {
        "knowledge_coverage": KnowledgeCoverageGenerator(llm_client),
        "reasoning_ability": ReasoningEvalGenerator(llm_client),
        "factual_accuracy": FactualAccuracyGenerator(llm_client),
        "comprehensive": ComprehensiveEvalGenerator(llm_client),
    }
    
    # Generate evaluation items for each type
    all_eval_items = []
    
    for eval_type, target_count in type_targets.items():
        if target_count == 0:
            continue
        
        logger.info(f"Generating {target_count} {eval_type} evaluation items")
        generator = generators[eval_type]
        
        # Distribute difficulty levels
        difficulty_counts = {
            difficulty: math.ceil(target_count * ratio)
            for difficulty, ratio in difficulty_distribution.items()
        }
        
        # Generate items for each difficulty level
        for difficulty, count in difficulty_counts.items():
            if count == 0:
                continue
            
            # Select batches for this difficulty/type combination
            # Each batch generates ~2-3 items, so we need fewer batches than items
            import math
            num_batches_needed = max(1, math.ceil(count / items_per_batch))
            
            # Cycle through batches if we need more batches than available
            batch_indices = [i % len(batches) for i in range(num_batches_needed)]
            selected_batches = [batches[i] for i in batch_indices]
            
            logger.info(
                f"  {difficulty}: need {count} items, selecting {num_batches_needed} batches "
                f"(~{items_per_batch:.1f} items/batch)"
            )
            
            # Generate evaluation items (one per batch)
            async def generate_for_batch(batch):
                try:
                    return await generator.generate(
                        batch=batch,
                        difficulty=difficulty,
                        chunks_storage=chunks_storage,
                        full_docs_storage=full_docs_storage,
                    )
                except Exception as e:
                    logger.error(f"Error generating {eval_type} eval item: {e}")
                    return {}
            
            results = await run_concurrent(
                generate_for_batch,
                selected_batches,
                desc=f"Generating {eval_type} ({difficulty})",
            )
            
            # Collect all evaluation items from results
            batch_items = []
            for result in results:
                for item_id, item in result.items():
                    batch_items.append(item)
            
            # Limit to exact count needed (truncate if we got more than expected)
            items_to_add = batch_items[:count]
            all_eval_items.extend(items_to_add)
            
            logger.info(
                f"  Generated {len(batch_items)} items from {len(results)} batches, "
                f"using {len(items_to_add)} items"
            )
    
    # Log pre-deduplication count
    logger.info(f"Total items before deduplication: {len(all_eval_items)}")
    
    # Remove duplicates based on question similarity
    unique_items = _deduplicate_eval_items(all_eval_items)
    
    logger.info(
        f"Items after deduplication: {len(unique_items)} "
        f"(removed {len(all_eval_items) - len(unique_items)} duplicates)"
    )
    
    # Limit to target count
    if len(unique_items) > target_eval_items:
        logger.info(f"Truncating from {len(unique_items)} to {target_eval_items} items")
        unique_items = unique_items[:target_eval_items]
    
    # Create evaluation dataset
    dataset = EvaluationDataset(
        name=evaluation_config.get("dataset_name", "LLM Evaluation Dataset"),
        description=evaluation_config.get("description", "Evaluation dataset for domain model assessment"),
        items=unique_items,
        metadata={
            "target_eval_items": target_eval_items,
            "actual_eval_items": len(unique_items),
            "type_distribution": type_distribution,
            "difficulty_distribution": difficulty_distribution,
            "output_format": output_format,
        },
    )
    
    logger.info(f"Generated {len(unique_items)} evaluation items")
    logger.info(f"Statistics: {dataset.get_statistics()}")
    
    return dataset


def _deduplicate_eval_items(items: List[EvaluationItem]) -> List[EvaluationItem]:
    """
    Remove duplicate evaluation items based on question similarity.
    
    :param items: list of evaluation items
    :return: deduplicated list
    """
    seen_questions = set()
    unique_items = []
    
    for item in items:
        # Simple deduplication based on question text
        question_lower = item.question.lower().strip()
        if question_lower not in seen_questions:
            seen_questions.add(question_lower)
            unique_items.append(item)
    
    return unique_items


async def save_eval_dataset(
    dataset: EvaluationDataset,
    output_path: str,
    output_format: str = "benchmark",
) -> None:
    """
    Save evaluation dataset to file.
    
    :param dataset: EvaluationDataset object
    :param output_path: path to save the dataset
    :param output_format: output format (benchmark, qa_pair, multiple_choice)
    """
    import json
    
    # Format the dataset
    if output_format == "benchmark":
        output_data = dataset.to_dict()
    elif output_format == "qa_pair":
        from graphgen.bases.base_eval_generator import BaseEvaluationGenerator
        formatted_items = BaseEvaluationGenerator.format_evaluation_results(
            dataset.items, "qa_pair"
        )
        output_data = {
            "name": dataset.name,
            "description": dataset.description,
            "items": formatted_items,
            "statistics": dataset.get_statistics(),
        }
    elif output_format == "multiple_choice":
        from graphgen.bases.base_eval_generator import BaseEvaluationGenerator
        formatted_items = BaseEvaluationGenerator.format_evaluation_results(
            dataset.items, "multiple_choice"
        )
        output_data = {
            "name": dataset.name,
            "description": dataset.description,
            "items": formatted_items,
            "statistics": dataset.get_statistics(),
        }
    else:
        raise ValueError(f"Unknown output format: {output_format}")
    
    # Save to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved evaluation dataset to {output_path}")
