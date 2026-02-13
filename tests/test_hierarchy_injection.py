
import unittest
from unittest.mock import MagicMock, patch
import networkx as nx
import sys
import os

# Add project root to sys.path to ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graphgen.utils.hierarchy_utils import HierarchySerializer
from graphgen.models.generator.atomic_generator import AtomicGenerator
from graphgen.models.generator.aggregated_generator import AggregatedGenerator
from graphgen.models.generator.cot_generator import CoTGenerator

class TestHierarchyInjection(unittest.TestCase):
    def setUp(self):
        self.mock_llm_client = MagicMock()
        self.hierarchical_relations = ["is_a", "part_of"]
        
        # Sample batch with hierarchy
        # A is_a B, B is_a C
        self.nodes_hierarchy = [
            ("A", {"description": "Entity A"}),
            ("B", {"description": "Entity B"}),
            ("C", {"description": "Entity C"}),
        ]
        self.edges_hierarchy = [
            ("A", "B", {"description": "is_a"}),
            ("B", "C", {"description": "is_a"}),
            ("A", "D", {"description": "related_to"}), # Non-hierarchical
        ]
        self.batch_hierarchy = (self.nodes_hierarchy, self.edges_hierarchy)
        
        # Sample batch without hierarchy
        self.nodes_flat = [
            ("X", {"description": "Entity X"}),
            ("Y", {"description": "Entity Y"}),
        ]
        self.edges_flat = [
            ("X", "Y", {"description": "related_to"}),
        ]
        self.batch_flat = (self.nodes_flat, self.edges_flat)

    def test_serializer_basic(self):
        serializer = HierarchySerializer(self.hierarchical_relations)
        result = serializer.serialize(self.nodes_hierarchy, self.edges_hierarchy, structure_format="markdown")
        
        # Check if B and C appear as parents/ancestors
        self.assertIn("# C", result)
        self.assertIn("# B", result)
        self.assertIn("# A", result)
        
    def test_serializer_cycles(self):
        # A is_a B, B is_a A (Cycle)
        nodes = [("A", {}), ("B", {})]
        edges = [
            ("A", "B", {"description": "is_a"}),
            ("B", "A", {"description": "is_a"}),
        ]
        serializer = HierarchySerializer(self.hierarchical_relations)
        result = serializer.serialize(nodes, edges, structure_format="markdown")
        
        # Should not crash and should produce some output
        self.assertIn("# A", result)
        self.assertIn("# B", result)

    def test_atomic_generator_injection(self):
        # Initialize with hierarchy support
        generator = AtomicGenerator(
            self.mock_llm_client, 
            hierarchical_relations=self.hierarchical_relations
        )
        
        # Test with hierarchy batch
        prompt = generator.build_prompt(self.batch_hierarchy)
        # Check for placeholder replacement or presence of context
        # The prompt should contain the serialized hierarchy
        # Since we mock LLM, we check the returned prompt string
        self.assertIn("# C", prompt)
        self.assertIn("# B", prompt)
        
        # Test with flat batch
        prompt_flat = generator.build_prompt(self.batch_flat)
        
        # Since we use require_hierarchy=True, the hierarchical_context should be empty string
        # So we should NOT see the markdown headers for flat nodes
        self.assertNotIn("# X", prompt_flat)
        self.assertNotIn("# Y", prompt_flat)
        
        # And correct template parts should still be there
        self.assertIn("Question:", prompt_flat)

    def test_aggregated_generator_injection(self):
        generator = AggregatedGenerator(
            self.mock_llm_client,
            hierarchical_relations=self.hierarchical_relations
        )
        
        # Test build_prompt (Rephrasing)
        prompt = generator.build_prompt(self.batch_hierarchy)
        self.assertIn("# C", prompt)
        
        # Test build_combined_prompt
        prompt_combined = generator.build_combined_prompt(self.batch_hierarchy)
        self.assertIn("# C", prompt_combined)

    def test_cot_generator_injection(self):
        generator = CoTGenerator(
            self.mock_llm_client,
            hierarchical_relations=self.hierarchical_relations
        )
        
        # Test build_prompt (Template Design)
        prompt = generator.build_prompt(self.batch_hierarchy)
        self.assertIn("# C", prompt)
        
        # Test build_combined_prompt
        prompt_combined = generator.build_combined_prompt(self.batch_hierarchy)
        self.assertIn("# C", prompt_combined)
        
        # Test build_prompt_for_cot_generation
        prompt_gen = generator.build_prompt_for_cot_generation(
            self.batch_hierarchy, 
            question="Q?", 
            reasoning_path="Path"
        )
        # This might fail if build_prompt_for_cot_generation doesn't use the hierarchy logic?
        # Let's check my implementation.
        # In step 136 (summary), CoTGenerator build_prompt_for_cot_generation was updated.
        self.assertIn("# C", prompt_gen)

if __name__ == "__main__":
    unittest.main()
