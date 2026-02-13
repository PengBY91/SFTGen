"""Utilities for processing and serializing hierarchical knowledge structures."""

import json
import logging
from typing import Any, List, Tuple
import networkx as nx

logger = logging.getLogger(__name__)


class HierarchySerializer:
    """
    Serializer for hierarchical knowledge structures.
    
    Converts graph data (nodes and edges) into structured formats (Markdown, JSON, Outline)
    suitable for LLM prompts.
    """

    def __init__(
        self,
        hierarchical_relations: List[str] = None,
        structure_format: str = "markdown"
    ):
        """
        Initialize HierarchySerializer.

        :param hierarchical_relations: List of relation types indicating hierarchy (e.g., "is_a")
        :param structure_format: Default output format - "markdown", "json", or "outline"
        """
        self.hierarchical_relations = hierarchical_relations or [
            "is_a",
            "subclass_of",
            "part_of",
            "includes",
            "type_of",
        ]
        self.structure_format = structure_format

    def serialize(
        self,
        nodes: List[Tuple[str, dict]],
        edges: List[Tuple[Any, Any, dict]],
        structure_format: str = None,
        require_hierarchy: bool = False,
    ) -> str:
        """
        Serialize graph data to hierarchical structure.

        :param nodes: List of (node_id, data) tuples
        :param edges: List of (src, tgt, data) tuples
        :param structure_format: Output format override
        :param require_hierarchy: If True, returns empty string if no hierarchical edges are found.
        :return: Formatted hierarchy string
        """
        if not nodes:
            return "No hierarchical structure available."

        # Build graph and identify roots
        G, roots, node_dict = self._build_graph(nodes, edges)

        if require_hierarchy and G.number_of_edges() == 0:
            return ""

        if not roots:
             # If no roots found (e.g., all nodes in cycles), use first node if available
            roots = [nodes[0][0]] if nodes else []

        # Determine format
        fmt = structure_format or self.structure_format

        # Serialize
        if fmt == "markdown":
            return self._serialize_markdown(G, roots, node_dict)
        elif fmt == "json":
            return self._serialize_json(G, roots, node_dict)
        elif fmt == "outline":
            return self._serialize_outline(G, roots, node_dict)
        else:
            logger.warning(f"Unknown format {fmt}, using markdown")
            return self._serialize_markdown(G, roots, node_dict)

    def _build_graph(
        self,
        nodes: List[Tuple[str, dict]],
        edges: List[Tuple[Any, Any, dict]]
    ) -> Tuple[nx.DiGraph, List[str], dict]:
        """
        Build NetworkX graph from nodes and edges, identifying hierarchical relations.
        
        :return: Tuple of (Graph, root_nodes, node_data_dict)
        """
        G = nx.DiGraph()
        node_dict = {}

        # Add nodes
        for node_id, data in nodes:
            G.add_node(node_id)
            node_dict[node_id] = data

        # Classify edges and build hierarchy
        for src, tgt, data in edges:
            relation_type = data.get("relation_type", data.get("description", ""))

            if relation_type in self.hierarchical_relations:
                # src is child, tgt is parent (src is_a tgt)
                # NOTE: The direction semantic depends on the relation name.
                # Usually "is_a": child -> parent.
                # But for tree display (Root -> Child), we want Parent -> Child edges.
                # If relation is "is_a" or "subclass_of", logic is Child -> Parent.
                # If relation is "includes" or "has_part", logic is Parent -> Child.
                
                # However, existing TreeStructureGenerator implementation assumes:
                # G.add_edge(src, tgt) means src is PARENT of tgt? 
                # Let's check the original code:
                # "if relation_type in self.hierarchical_relations: ... G.add_edge(src, tgt, relation=relation_type)"
                # "roots = [node for node in G.nodes() if G.in_degree(node) == 0]"
                # This implies edges go from Root -> Leaf.
                # So if relation is "is_a" (Child -> Parent), we should probably REVERSE it for the graph if we want the root to have in-degree 0.
                
                # WAIT. In the original `tree_generator.py`:
                # hierarchy_text = self._serialize_to_format(batch)
                # ...
                # for src, tgt, data in edges:
                #    if relation_type in self.hierarchical_relations:
                #        G.add_edge(src, tgt, relation=relation_type)
                #
                # If my triples are (Dog, Mammal, is_a), then G has edge Dog -> Mammal.
                # Roots have in-degree 0. So Dog has in-degree 0 (if valid), Mammal has in-degree 1.
                # So Dog is considered a "Root".
                # _serialize_markdown writes Dog then its successors (Mammal).
                # So the output would be Dog -> Mammal.
                #
                # Typically we want Mammal -> Dog.
                # So (Dog, Mammal, is_a) should be treated as child->parent.
                # To make Mammal the root (in-degree 0), the edge in G should be Mammal -> Dog.
                #
                # Does `GraphGen` store edges as (Subject, Object, Predicate)?
                # Usually (S, O, P). So (Dog, Mammal, is_a).
                #
                # If the original code just did `G.add_edge(src, tgt)`, then it produces trees where Subject is the parent.
                # If the triples are (Parent, Child, includes), this works.
                # If the triples are (Child, Parent, is_a), this produces inverted trees.
                #
                # I will preserve the EXACT logic from `tree_generator.py` to avoid breaking existing behavior, 
                # assuming the user's data or existing logic expects this.
                # The original code:
                # G.add_edge(src, tgt, relation=relation_type)
                
                G.add_edge(src, tgt, relation=relation_type)
            else:
                # Attribute edge
                if not G.has_node(src):
                    G.add_node(src)
                if not G.has_node(tgt):
                    G.add_node(tgt)
                
                # Store as node attribute
                if src in node_dict:
                    if "attributes" not in node_dict[src]:
                        node_dict[src]["attributes"] = []
                    node_dict[src]["attributes"].append({
                        "relation": relation_type,
                        "target": tgt,
                        "description": data.get("description", "")
                    })

        # Detect and handle cycles
        try:
            cycles = list(nx.simple_cycles(G))
            if cycles:
                logger.warning(f"Detected {len(cycles)} cycles in hierarchy, will handle gracefully")
                # Remove back edges to break cycles
                for cycle in cycles:
                    if len(cycle) >= 2:
                        # Remove last edge in cycle
                        if G.has_edge(cycle[-1], cycle[0]):
                            G.remove_edge(cycle[-1], cycle[0])
        except Exception as e:
            logger.warning(f"Error checking cycles: {e}")

        # Find roots (nodes with no incoming hierarchical edges)
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]

        return G, roots, node_dict

    def _serialize_markdown(
        self,
        G: nx.DiGraph,
        roots: List[str],
        node_dict: dict,
        level: int = 0
    ) -> str:
        """Serialize to Markdown format with headers."""
        lines = []
        visited = set()

        def _serialize_node(node_id: str, depth: int):
            if node_id in visited:
                return
            visited.add(node_id)

            data = node_dict.get(node_id, {})
            header_prefix = "#" * (depth + 1)

            # Node header and description
            description = data.get("description", "No description available")
            lines.append(f"{header_prefix} {node_id}")
            lines.append(f"**Description**: {description}")

            # Attributes
            attributes = data.get("attributes", [])
            if attributes:
                lines.append("**Attributes**:")
                for attr in attributes:
                    rel = attr.get("relation", "related_to")
                    tgt = attr.get("target", "unknown")
                    desc = attr.get("description", "")
                    
                    line = f"- {rel}: {tgt}"
                    lines.append(line)
                    if desc:
                        lines.append(f"  - {desc}")

            lines.append("")

            # Children
            children = list(G.successors(node_id))
            for child in children:
                _serialize_node(child, depth + 1)

        for root in roots:
            _serialize_node(root, 0)

        return "\n".join(lines)

    def _serialize_json(
        self,
        G: nx.DiGraph,
        roots: List[str],
        node_dict: dict
    ) -> str:
        """Serialize to JSON format."""
        visited = set()

        def _build_tree(node_id: str) -> dict:
            if node_id in visited:
                return {"name": node_id, "_cyclic": True}
            visited.add(node_id)

            data = node_dict.get(node_id, {})

            node_tree = {
                "name": node_id,
                "description": data.get("description", "No description available"),
            }

            # Add attributes
            attributes = data.get("attributes", [])
            if attributes:
                node_tree["attributes"] = [
                    {
                        "relation": attr.get("relation", "related_to"),
                        "target": attr.get("target", "unknown"),
                        "description": attr.get("description", "")
                    }
                    for attr in attributes
                ]

            # Add children
            children = list(G.successors(node_id))
            if children:
                node_tree["children"] = [_build_tree(child) for child in children]

            return node_tree

        trees = [_build_tree(root) for root in roots]
        result = {"hierarchy": trees} if len(trees) > 1 else trees[0] if trees else {}

        return json.dumps(result, indent=2, ensure_ascii=False)

    def _serialize_outline(
        self,
        G: nx.DiGraph,
        roots: List[str],
        node_dict: dict,
        indent: str = "  "
    ) -> str:
        """Serialize to outline format with indentation."""
        lines = []
        visited = set()

        def _serialize_node(node_id: str, depth: int):
            if node_id in visited:
                return
            visited.add(node_id)

            data = node_dict.get(node_id, {})
            prefix = indent * depth

            # Node name
            lines.append(f"{prefix}- {node_id}")

            # Description
            description = data.get("description", "No description available")
            lines.append(f"{prefix}  Description: {description}")

            # Attributes
            attributes = data.get("attributes", [])
            for attr in attributes:
                rel = attr.get("relation", "related_to")
                tgt = attr.get("target", "unknown")
                lines.append(f"{prefix}  - {rel}: {tgt}")

            # Children
            children = list(G.successors(node_id))
            for child in children:
                _serialize_node(child, depth + 1)

        for root in roots:
            _serialize_node(root, 0)

        return "\n".join(lines)
