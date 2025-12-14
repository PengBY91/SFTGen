"""
Simple test script for evaluation dataset generation
"""

import os
import sys
import yaml
from graphgen.graphgen import GraphGen
from graphgen.utils import logger, set_logger

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_evaluation_generation():
    """Test basic evaluation dataset generation"""
    
    # Set up logging
    set_logger("test_eval.log", if_stream=True)
    logger.info("Starting evaluation generation test")
    
    # Load example configuration
    config_path = "resources/examples/evaluation_example.yaml"
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return False
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Create test working directory
    working_dir = "test_output"
    os.makedirs(working_dir, exist_ok=True)
    
    try:
        # Initialize GraphGen
        logger.info("Initializing GraphGen")
        graph_gen = GraphGen(unique_id=99999, working_dir=working_dir)
        
        # Note: This test assumes you have already built a knowledge graph
        # If not, you would need to call:
        # graph_gen.insert(read_config=config["read"], split_config=config["split"])
        
        # Generate evaluation dataset
        logger.info("Generating evaluation dataset")
        graph_gen.generate_evaluation(
            partition_config=config["partition"],
            evaluation_config=config["evaluation"],
        )
        
        # Check if output file exists
        output_file = os.path.join(working_dir, "data", "evaluation", "99999_eval.json")
        if os.path.exists(output_file):
            logger.info(f"✓ Evaluation dataset generated successfully: {output_file}")
            
            # Load and display statistics
            import json
            with open(output_file, "r") as f:
                dataset = json.load(f)
            
            logger.info(f"Dataset name: {dataset.get('name')}")
            logger.info(f"Total items: {dataset.get('statistics', {}).get('total_items')}")
            logger.info(f"Type distribution: {dataset.get('statistics', {}).get('type_distribution')}")
            logger.info(f"Difficulty distribution: {dataset.get('statistics', {}).get('difficulty_distribution')}")
            
            return True
        else:
            logger.error("✗ Evaluation dataset file not found")
            return False
    
    except Exception as e:
        logger.error(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_evaluation_generation()
    sys.exit(0 if success else 1)
