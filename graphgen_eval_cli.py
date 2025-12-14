"""CLI tool for generating evaluation datasets"""

import argparse
import os
import time
from importlib.resources import files

import yaml
from dotenv import load_dotenv

from graphgen.graphgen import GraphGen
from graphgen.utils import logger, set_logger

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

    # Initialize GraphGen
    graph_gen = GraphGen(unique_id=unique_id, working_dir=working_dir)

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

    # Save configuration
    save_config(os.path.join(output_path, "config.yaml"), config)
    
    logger.info("Evaluation dataset generation completed successfully.")
    logger.info("Output saved to %s", output_path)


if __name__ == "__main__":
    main()
