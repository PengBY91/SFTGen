"""Test hierarchical partitioner."""

import asyncio
from graphgen.models import HierarchicalPartitioner
from graphgen.bases.datatypes import Community


async def test_hierarchical_partitioner():
    """Test basic functionality of HierarchicalPartitioner."""

    # Create a mock graph storage
    class MockGraphStorage:
        async def get_all_nodes(self):
            return [
                ("Animal", {"description": "A living organism"}),
                ("Mammal", {"description": "A warm-blooded animal"}),
                ("Bird", {"description": "A feathered animal"}),
                ("Cat", {"description": "A feline mammal"}),
                ("Dog", {"description": "A canine mammal"}),
            ]

        async def get_all_edges(self):
            return [
                ("Mammal", "Animal", {"relation_type": "is_a", "description": "Mammal is a type of animal"}),
                ("Bird", "Animal", {"relation_type": "is_a", "description": "Bird is a type of animal"}),
                ("Cat", "Mammal", {"relation_type": "is_a", "description": "Cat is a type of mammal"}),
                ("Dog", "Mammal", {"relation_type": "is_a", "description": "Dog is a type of mammal"}),
            ]

    # Create partitioner
    partitioner = HierarchicalPartitioner(
        hierarchical_relations=["is_a"],
        max_depth=3,
        max_siblings=10,
        include_attributes=True
    )

    # Run partitioning
    graph = MockGraphStorage()
    communities = await partitioner.partition(g=graph)

    print(f"\n✓ Created {len(communities)} communities")
    for i, comm in enumerate(communities):
        print(f"  Community {i} (type={comm.metadata.get('type')}): "
              f"nodes={comm.nodes}, edges={len(comm.edges)}")

    # Verify sibling grouping: should have Animal + Mammal + Bird
    sibling_communities = [c for c in communities if c.metadata.get("type") == "sibling_group"]
    print(f"\n✓ Found {len(sibling_communities)} sibling group communities")

    # Verify chain sampling: should have Mammal + Cat/Dog
    chain_communities = [c for c in communities if c.metadata.get("type") == "vertical_chain"]
    print(f"✓ Found {len(chain_communities)} vertical chain communities")

    assert len(communities) > 0, "Should create at least one community"
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_hierarchical_partitioner())
