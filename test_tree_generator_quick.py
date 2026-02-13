"""Test tree structure generator."""

from graphgen.models import TreeStructureGenerator


def test_tree_generator_serialization():
    """Test tree serialization formats."""

    # Create mock batch
    nodes = [
        ("Animal", {"description": "A living organism"}),
        ("Mammal", {"description": "A warm-blooded animal"}),
        ("Bird", {"description": "A feathered animal"}),
        ("Cat", {"description": "A feline mammal"}),
    ]

    edges = [
        ("Mammal", "Animal", {"relation_type": "is_a", "description": "Mammal is a type of animal"}),
        ("Bird", "Animal", {"relation_type": "is_a", "description": "Bird is a type of animal"}),
        ("Cat", "Mammal", {"relation_type": "is_a", "description": "Cat is a type of mammal"}),
        ("Cat", " whiskers", {"relation_type": "has", "description": "Cats have whiskers"}),
    ]

    batch = (nodes, edges)

    # Test Markdown format
    print("=" * 60)
    print("Testing Markdown format:")
    print("=" * 60)
    gen_md = TreeStructureGenerator(
        llm_client=None,
        structure_format="markdown",
        hierarchical_relations=["is_a"]
    )
    md_output = gen_md._serialize_to_format(batch)
    print(md_output[:500])
    assert "# Animal" in md_output or "# Mammal" in md_output, "Markdown should contain headers"
    print("\n✓ Markdown serialization works")

    # Test JSON format
    print("\n" + "=" * 60)
    print("Testing JSON format:")
    print("=" * 60)
    gen_json = TreeStructureGenerator(
        llm_client=None,
        structure_format="json",
        hierarchical_relations=["is_a"]
    )
    json_output = gen_json._serialize_to_format(batch)
    print(json_output[:500])
    assert '"name"' in json_output, "JSON should contain 'name' field"
    assert '"children"' in json_output or '"description"' in json_output, "JSON should contain hierarchy"
    print("\n✓ JSON serialization works")

    # Test Outline format
    print("\n" + "=" * 60)
    print("Testing Outline format:")
    print("=" * 60)
    gen_outline = TreeStructureGenerator(
        llm_client=None,
        structure_format="outline",
        hierarchical_relations=["is_a"]
    )
    outline_output = gen_outline._serialize_to_format(batch)
    print(outline_output[:500])
    assert "- " in outline_output, "Outline should contain list markers"
    print("\n✓ Outline serialization works")

    # Test response parsing
    print("\n" + "=" * 60)
    print("Testing response parsing:")
    print("=" * 60)

    test_response = """Question: How do Mammals and Birds differ?
Answer: Mammals and Birds are both animals, but they have different characteristics. Mammals are warm-blooded and typically have fur or hair, while Birds have feathers. Both groups inherit the basic properties of being animals, but they evolved different adaptations.
Hierarchical Reasoning: Both Mammal and Bird are children of Animal in the hierarchy, making them siblings. The comparison explores their inherited vs unique properties."""

    parsed = TreeStructureGenerator.parse_response(test_response)
    print(f"Parsed {len(parsed)} QA pairs")
    for q_hash, qa in parsed.items():
        print(f"  Q: {qa['question'][:50]}...")
        print(f"  A: {qa['answer'][:50]}...")
        if 'hierarchical_reasoning' in qa:
            print(f"  R: {qa['hierarchical_reasoning'][:50]}...")

    assert len(parsed) == 1, "Should parse exactly one QA pair"
    assert "question" in list(parsed.values())[0], "Should have 'question' field"
    assert "answer" in list(parsed.values())[0], "Should have 'answer' field"
    print("\n✓ Response parsing works")

    print("\n✅ All TreeStructureGenerator tests passed!")


if __name__ == "__main__":
    test_tree_generator_serialization()
