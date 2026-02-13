# Optimization Plan: Hierarchical SFT Data Generation

## Goal Description

Enhance SFTGen to better handle hierarchical domain knowledge (e.g., taxonomy, partonomy) by introducing structure-aware sampling and tree-structured context generation. This aims to solve the issue where flat triple-based generation fails to capture logic like inheritance, sibling comparison, and multi-level hierarchy.

## User Review Required

> [!IMPORTANT]
>
> - **New Dependencies**: Python packages `networkx` (already used) need to be leveraged for new graph traversals.
> - **Configuration Changes**: New parameters `partition_method="hierarchical"` and `generation_mode="tree"` will be added to the configuration.
> - **Prompt Strategy**: We are shifting from "flat context" to "structured context" (Markdown/JSON trees).

## Proposed Changes

### 1. Partition Layer: Hierarchical Sampling (`HierarchicalPartitioner`)

We need a dedicated partitioner that groups nodes based on hierarchical relationships rather than just density or random walks.

#### [NEW] `graphgen/models/partitioner/hierarchical_partitioner.py`

- Implement `HierarchicalPartitioner` class inheriting from `BasePartitioner`.
- **Logic**:
  - **Identify Hierarchy**: Filter edges by specified relations (e.g., `is_a`, `subclass_of`, `part_of`, `includes`).
  - **Sibling Grouping (Horizontal)**: For each parent node, create a community containing the parent and all its children.
  - **Chain Grouping (Vertical)**: Sample paths of length 2-3 specifically along hierarchical edges (e.g., Grandparent -> Parent -> Child).
- **Output**: Returns a list of `Community` objects optimized for hierarchical reasoning.

#### [MODIFY] `graphgen/operators/partition/partition_kg.py`

- Register the new `hierarchical` method in `partition_kg` function.
- Add logic to instantiate `HierarchicalPartitioner` when `method="hierarchical"`.

### 2. Generation Layer: Tree-Structured Context (`TreeStructureGenerator`)

A new generator that serializes the subgraph into a structured format before feeding it to the LLM.

#### [NEW] `graphgen/models/generator/tree_generator.py`

- Implement `TreeStructureGenerator` class inheriting from `BaseGenerator`.
- **Method `_build_tree_context(batch)`**:
  - Takes nodes and edges from the batch.
  - Reconstructs a mini-graph using NetworkX.
  - Identifies the root(s) of the hierarchy within the batch.
  - Serializes the graph into a **Markdown Outline** or **JSON Tree**, attaching non-hierarchical attributes to their respective nodes.
- **Method `build_prompt(batch)`**:
  - Uses the structured context.
  - Selects specific prompts for comparison ("Compare A and B") or inheritance logic ("Why does C have property P?").

#### [MODIFY] `graphgen/operators/generate/generate_qas.py`

- Add support for `mode="tree"` (or `hierarchical`).
- Instantiate `TreeStructureGenerator` when this mode is selected.
- Adjust batch filtering if necessary (though the partitioner should handle most of it).

### 3. Template Layer: Structure-Aware Prompts

#### [MODIFY] `graphgen/templates/__init__.py` (and related files)

- Add `HIERARCHICAL_GENERATION_PROMPT`.
  - **Focus**: "You are analyzing a hierarchical knowledge tree..."
  - **Tasks**:
    - Contrast siblings (Sibling Comparison).
    - Explain inheritance (Property Inheritance).
    - Summarize branch/category (Abstraction).

### 4. Configuration Updates

#### [MODIFY] `graphgen/graphgen.py` (or CLI entry points)

- Ensure new configuration options (`hierarchical_relations`, `structure_format`) can be passed down to the partitioner and generator.

## Detailed Test Plan & Test Cases

This section outlines the testing strategy to ensure the reliability and correctness of the new hierarchical generation features.

### 1. Unit Tests: Hierarchical Partitioning

**File**: `tests/test_hierarchical_partitioner.py`

#### Test Case 1.1: Sibling Grouping (Horizontal)

- **Objective**: Verify that siblings under the same parent are grouped together.
- **Input Graph**:
  - Nodes: `Animal`, `Mammal`, `Bird`
  - Edges: `(Mammal, is_a, Animal)`, `(Bird, is_a, Animal)`
- **Expected Output**: A single community containing `{Animal, Mammal, Bird}`.
- **Assertion**: Check if the resulting community list contains a set with these 3 nodes.

#### Test Case 1.2: Chain Grouping (Vertical)

- **Objective**: Verify that ancestor-descendant chains are preserved.
- **Input Graph**:
  - Nodes: `LivingThing`, `Animal`, `Cat`
  - Edges: `(Animal, is_a, LivingThing)`, `(Cat, is_a, Animal)`
- **Expected Output**: A community containing `{LivingThing, Animal, Cat}`.
- **Assertion**: Verify the presence of the full chain in one community.

#### Test Case 1.3: Mixed Relations

- **Objective**: Verify that non-hierarchical edges do not break the grouping but are included if relevant.
- **Input Graph**:
  - Nodes: `Cat`, `Dog`, `Fur`
  - Edges: `(Cat, is_a, Animal)`, `(Dog, is_a, Animal)`, `(Cat, has, Fur)`
- **Expected Output**: Community `{Animal, Cat, Dog}` (Hierarchy focus). `Fur` might be included depending on depth setting, but the core hierarchy must be present.

### 2. Unit Tests: Tree Structure Generation

**File**: `tests/test_tree_generator.py`

#### Test Case 2.1: Graph to Markdown Serialization

- **Objective**: Verify that a graph subgraph is correctly converted to a Markdown tree.
- **Input Subgraph**:
  - Root: `Machine Learning`
  - Child: `Deep Learning` (relation: `type_of`)
  - Attribute: `Deep Learning` -> `requires` -> `Big Data`
- **Expected Output (String)**:
  ```markdown
  # Machine Learning

  ## Deep Learning

  - requires: Big Data
  ```
- **Assertion**: String containment checks for structure markers (`#`, `##`, `-`).

#### Test Case 2.2: Cycle Handling

- **Objective**: Ensure the serializer does not enter an infinite loop if the graph has cycles.
- **Input Subgraph**: `A -> B -> C -> A` (circular hierarchy).
- **Expected Output**: A tree structure where the cycle is broken (e.g., `A -> B -> C`, with `A` casually referenced or omitted at the leaf).
- **Assertion**: Function returns within a timeout; output length is finite.

### 3. Integration Tests: Full Pipeline

**File**: `tests/test_hierarchical_pipeline.py`

#### Test Case 3.1: End-to-End Generation

- **Objective**: Run the full pipeline with `partition_method="hierarchical"` and `mode="tree"`.
- **Input**: A small knowledge graph file (`tests/data/taxonomy_graph.json`).
- **Procedure**:
  1.  Initialize `GraphGen`.
  2.  Run `partition_kg`.
  3.  Run `generate_qas`.
- **Expected Output**:
  - `partition_kg` returns non-empty batches.
  - `generate_qas` returns a list of QA pairs.
  - Generated questions contain keywords like "compare", "classify", "distinguish".
- **Assertion**: `len(results) > 0`; Check for specific keyword presence in questions.

### 4. Manual Verification & Quality Review

#### 4.1 Dry Run with Domain Data

- **Data**: Use a snippet of the user's specific domain data (e.g., specific evaluation consulting taxonomy).
- **Action**: Generate 20 QA pairs.
- **Checklist**:
  - [ ] Does the context look like a tree?
  - [ ] Do questions ask about the _relationship_ between siblings?
  - [ ] Are there "hallucinated" attributes (attributes from sibling A assigned to sibling B)?

#### 4.2 Output Format Validation

- Check if the generated JSON follows the standard SFT format:
  ```json
  {
    "instruction": "...",
    "input": "...",
    "output": "..."
  }
  ```
