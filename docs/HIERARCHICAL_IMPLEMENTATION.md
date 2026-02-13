# Hierarchical SFT Data Generation

This document describes the hierarchical SFT data generation system implemented for capturing domain knowledge hierarchies.

## Overview

The hierarchical generation system creates QA pairs that focus on hierarchical relationships in domain knowledge, including:
- **Sibling comparison**: Comparing concepts at the same level (e.g., Mammal vs Bird)
- **Inheritance reasoning**: Explaining how properties propagate from parent to child
- **Abstraction**: Identifying parent categories from children
- **Multi-level drill-down**: Tracing properties through multiple hierarchy levels

## Components

### 1. HierarchicalPartitioner

**File**: `graphgen/models/partitioner/hierarchical_partitioner.py`

Partitions knowledge graphs into hierarchical communities using two strategies:

#### Sibling Grouping (Horizontal)
- Groups parent + all children into one community
- Example: Animal → [Mammal, Bird, Fish] creates community {Animal, Mammal, Bird, Fish}
- Limit: `max_siblings` per community (default: 10)

#### Chain Sampling (Vertical)
- Samples ancestor→descendant paths
- Example: LivingThing → Animal → Mammal → Cat
- Limit: `max_depth` levels (default: 3)

#### Configuration Parameters

```python
partition_config = {
    "method": "hierarchical",
    "method_params": {
        "hierarchical_relations": ["is_a", "subclass_of", "part_of", "includes", "type_of"],
        "max_hierarchical_depth": 3,
        "max_siblings_per_community": 10,
        "include_attributes": True
    }
}
```

### 2. TreeStructureGenerator

**File**: `graphgen/models/generator/tree_generator.py`

Generates QA pairs from hierarchical subgraphs by:

1. Building tree structure from batch
2. Detecting roots (nodes with no hierarchical parents)
3. Serializing to chosen format (Markdown/JSON/Outline)
4. Generating hierarchical reasoning prompts
5. Parsing LLM responses

#### Serialization Formats

**Markdown**:
```markdown
# Animal
**Description**: A living organism

## Mammal
**Description**: A warm-blooded animal
**Attributes**:
- has: fur

### Cat
**Description**: A feline mammal
```

**JSON**:
```json
{
  "name": "Animal",
  "description": "A living organism",
  "children": [
    {
      "name": "Mammal",
      "description": "A warm-blooded animal",
      "attributes": [{"relation": "has", "target": "fur"}]
    }
  ]
}
```

**Outline**:
```
- Animal
  Description: A living organism
  - Mammal
    Description: A warm-blooded animal
    - has: fur
```

#### Configuration Parameters

```python
generation_config = {
    "mode": "hierarchical",
    "structure_format": "markdown",  # or "json" or "outline"
    "hierarchical_relations": ["is_a", "subclass_of", "part_of", "includes", "type_of"]
}
```

### 3. Templates

**File**: `graphgen/templates/generation/hierarchical_generation.py`

Four reasoning patterns in English and Chinese:

- **Sibling**: Compare sibling concepts, focus on inherited vs unique attributes
- **Inheritance**: Explain why child has property based on parent
- **Abstraction**: Identify parent category from children
- **Multi-level**: Trace property through hierarchy levels

## Usage

### Basic Usage

```python
from graphgen.models import HierarchicalPartitioner, TreeStructureGenerator

# Partition graph
partitioner = HierarchicalPartitioner(
    hierarchical_relations=["is_a", "part_of"],
    max_depth=3,
    max_siblings=10
)
communities = await partitioner.partition(graph_storage)

# Generate QA pairs
generator = TreeStructureGenerator(
    llm_client=client,
    structure_format="markdown"
)
qa_pairs = await generator.generate(batch)
```

### Full Pipeline

```python
# In backend configuration
config = TaskConfig(
    partition_method="hierarchical",
    mode="hierarchical",
    hierarchical_relations=["is_a", "subclass_of", "part_of"],
    structure_format="markdown",
    max_hierarchical_depth=3,
    max_siblings_per_community=10
)
```

### With "all" Mode

The hierarchical generator is automatically included when using `mode="all"`:

```python
config = TaskConfig(
    mode="all",  # Runs atomic, aggregated, multi_hop, cot, and hierarchical
    qa_ratio_hierarchical=20.0  # 20% of QA pairs will be hierarchical
)
```

## Output Format

Generated QA pairs follow this structure:

```json
{
  "instruction": "How do Mammals and Birds differ?",
  "input": "",
  "output": "Mammals and Birds are both animals, but they have different characteristics..."
}
```

With hierarchical reasoning (optional):

```json
{
  "instruction": "Why do Cats have fur?",
  "input": "",
  "output": "Cats have fur because they are mammals, and all mammals have fur as a characteristic feature...",
  "hierarchical_reasoning": "Cat → Mammal → fur property inheritance"
}
```

## Testing

Run the test suite:

```bash
# Test HierarchicalPartitioner
conda run -n graphgen python test_hierarchical_quick.py

# Test TreeStructureGenerator
conda run -n graphgen python test_tree_generator_quick.py
```

## Implementation Details

### Cycle Handling

Both partitioner and generator detect and break cycles:

1. **Detection**: Use NetworkX `simple_cycles()` to find cycles
2. **Breaking**: Remove first edge in each cycle
3. **Fallback**: If cycle detection fails, continue with graceful degradation

### Edge Classification

Edges are classified into:
- **Hierarchical**: `is_a`, `subclass_of`, `part_of`, `includes`, `type_of`
- **Attribute**: All other relations

Attribute edges are included in communities but don't drive the hierarchical structure.

### Metadata

Communities include metadata:

```python
Community(
    id=0,
    nodes=["Animal", "Mammal", "Bird"],
    edges=[("Mammal", "Animal"), ("Bird", "Animal")],
    metadata={
        "type": "sibling_group",  # or "vertical_chain" or "isolated"
        "parent": "Animal"
    }
)
```

## File Structure

```
graphgen/
├── models/
│   ├── partitioner/
│   │   └── hierarchical_partitioner.py      # NEW
│   └── generator/
│       └── tree_generator.py                # NEW
├── templates/
│   └── generation/
│       └── hierarchical_generation.py       # NEW
└── operators/
    ├── partition/
    │   └── partition_kg.py                  # MODIFIED
    └── generate/
        └── generate_qas.py                  # MODIFIED

backend/
└── schemas.py                                # MODIFIED
```

## Performance Considerations

- **Cycle detection**: O(V + E) using NetworkX
- **Serialization**: Linear in tree size
- **Memory**: Proportional to hierarchy depth
- **LLM calls**: 1 call per community (similar to other generators)

## Future Enhancements

Potential improvements:
1. **Adaptive depth**: Adjust max_depth based on graph characteristics
2. **Weighted edges**: Prioritize certain hierarchical relations
3. **Cross-hierarchy**: Compare concepts across different branches
4. **Reasoning templates**: More sophisticated prompt engineering
5. **Multi-tree**: Handle multiple disconnected hierarchies

## Troubleshooting

### No communities generated

If partitioning returns empty:
- Check `hierarchical_relations` match your graph's edge types
- Verify edges have `relation_type` or `description` field
- Enable `include_attributes=True` to capture non-hierarchical edges

### Cycles detected

Cycles are automatically handled, but if you see warnings:
- Check your knowledge graph for circular dependencies
- Consider cleaning up data before partitioning

### Poor QA quality

If generated QA pairs lack hierarchical reasoning:
- Try different `structure_format` (markdown usually works best)
- Check LLM model quality
- Review prompts in `hierarchical_generation.py`

## References

- NetworkX documentation: https://networkx.org/
- Knowledge graph hierarchies: Studies in ontology learning
- QA generation: Literature on question generation from knowledge bases
