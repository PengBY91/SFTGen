"""CLI tool for generating evaluation datasets"""

import argparse
import os
import sys
import time
from importlib.resources import files

import yaml
from dotenv import load_dotenv

from graphgen.graphgen import GraphGen
from graphgen.utils import logger, set_logger

# DA-ToG imports
from graphgen.models.taxonomy.taxonomy_tree import TaxonomyTree
from graphgen.utils.datog_metrics import DAToGMetrics
import json

sys_path = os.path.abspath(os.path.dirname(__file__))

load_dotenv()


def set_working_dir(folder):
    """Create working directory if it doesn't exist"""
    os.makedirs(folder, exist_ok=True)


def save_config(config_path, global_config):
    """Save configuration to file"""
    if not os.path.exists(os.path.dirname(config_path)):
        os.makedirs(os.path.dirname(config_path))
    with open(config_path, "w", encoding="utf-8") as config_file:
        yaml.dump(
            global_config, config_file, default_flow_style=False, allow_unicode=True
        )


def run_datog_metrics(args) -> bool:
    """Compute DA-ToG coverage/distribution metrics from a results file."""
    if not args.datog_taxonomy or not args.datog_results:
        logger.error(
            "--datog-taxonomy and --datog-results are required for DA-ToG metrics"
        )
        return False
    try:
        tree = TaxonomyTree.load(args.datog_taxonomy)
    except Exception as e:
        logger.error("Failed to load taxonomy tree: %s", e)
        return False

    metrics = DAToGMetrics(tree)
    try:
        report = metrics.generate_report(args.datog_results)
    except Exception as e:
        logger.error("Failed to compute DA-ToG metrics: %s", e)
        return False

    output_path = (
        args.datog_output
        or args.datog_results.rsplit(".json", 1)[0] + "_metrics.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("DA-ToG metrics saved to %s", output_path)
    logger.info(
        "Overall intent coverage: %.1f%%", report["coverage"]["overall_ratio"] * 100
    )
    return True


def main():
    """Main function for evaluation dataset generation CLI"""
    parser = argparse.ArgumentParser(
        description="Generate LLM evaluation datasets from domain documents"
    )
    parser.add_argument(
        "--config_file",
        help="Config parameters for evaluation generation.",
        default=files("graphgen").joinpath("configs", "evaluation_config.yaml"),
        type=str,
    )
    parser.add_argument(
        "--output_dir",
        help="Output directory for evaluation dataset.",
        default=sys_path,
        required=True,
        type=str,
    )
    parser.add_argument(
        "--skip_kg_build",
        help="Skip knowledge graph building (use existing KG)",
        action="store_true",
    )
    # DA-ToG 指标参数
    datog_group = parser.add_argument_group("DA-ToG 指标计算")
    datog_group.add_argument("--datog-taxonomy", help="DA-ToG 意图树文件路径", required=False)
    datog_group.add_argument("--datog-results", help="DA-ToG 结果文件路径", required=False)
    datog_group.add_argument("--datog-output", help="DA-ToG 指标输出文件路径", required=False)

    args = parser.parse_args()

    working_dir = args.output_dir

    # Load configuration
    with open(args.config_file, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    unique_id = int(time.time())

    output_path = os.path.join(working_dir, "data", "evaluation", f"{unique_id}")
    set_working_dir(output_path)

    # Set up logging
    set_logger(
        os.path.join(output_path, f"{unique_id}_eval.log"),
        if_stream=True,
    )
    logger.info(
        "Evaluation dataset generation with unique ID %s logging to %s",
        unique_id,
        os.path.join(output_path, f"{unique_id}_eval.log"),
    )

    # LLM/API 配置：优先使用 YAML 中的 llm/apis 段，未配置时回退环境变量
    from graphgen.configs.llm_config import (
        apply_apis_to_environ,
        build_llm_clients,
        load_llm_config,
    )

    llm_config = load_llm_config(config)
    apply_apis_to_environ(llm_config.apis)
    tokenizer_instance, synthesizer_client, trainee_client = build_llm_clients(llm_config)

    # Initialize GraphGen
    graph_gen = GraphGen(
        unique_id=unique_id,
        working_dir=working_dir,
        tokenizer_instance=tokenizer_instance,
        synthesizer_llm_client=synthesizer_client,
        trainee_llm_client=trainee_client,
    )

    # Step 1: Build knowledge graph (unless skipped)
    if not args.skip_kg_build:
        logger.info("Step 1: Building knowledge graph from documents")
        graph_gen.insert(read_config=config["read"], split_config=config["split"])
        
        # Optional: search for external information
        if config.get("search", {}).get("enabled"):
            graph_gen.search(search_config=config["search"])
        
        # Optional: quiz and judge
        if config.get("quiz_and_judge", {}).get("enabled"):
            graph_gen.quiz_and_judge(quiz_and_judge_config=config["quiz_and_judge"])
    else:
        logger.info("Skipping knowledge graph building (using existing KG)")

    # Step 2: Generate evaluation dataset
    logger.info("Step 2: Generating evaluation dataset")
    graph_gen.generate_evaluation(
        partition_config=config["partition"],
        evaluation_config=config["evaluation"],
    )

    # DA-ToG 指标计算模式（仅在显式传入 --datog-taxonomy 时启用）
    if args.datog_taxonomy:
        success = run_datog_metrics(args)
        sys.exit(0 if success else 1)

    # Save configuration
    save_config(os.path.join(output_path, "config.yaml"), config)

    logger.info("Evaluation dataset generation completed successfully.")
    logger.info("Output saved to %s", output_path)

if __name__ == "__main__":
    main()
