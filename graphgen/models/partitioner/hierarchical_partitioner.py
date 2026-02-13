"""Hierarchical partitioner for domain knowledge graphs."""

import networkx as nx
from collections import defaultdict
from typing import Any, List, Set, Tuple

from graphgen.bases import BaseGraphStorage, BasePartitioner
from graphgen.bases.datatypes import Community
from graphgen.utils import logger


class HierarchicalPartitioner(BasePartitioner):
    """
    Hierarchical partitioner that groups nodes based on hierarchical relationships.

    Two strategies:
    1. Sibling grouping (horizontal): Group parent + all children into one community
    2. Chain sampling (vertical): Sample ancestor→descendant paths

    Hierarchical relations: is_a, subclass_of, part_of, includes, type_of
    Attribute relations: all other relations (included but don't dominate)
    """

    def __init__(
        self,
        hierarchical_relations: List[str] = None,
        max_depth: int = 3,
        max_siblings: int = 10,
        include_attributes: bool = True,
    ):
        """
        Initialize HierarchicalPartitioner.

        :param hierarchical_relations: List of relation types that indicate hierarchy
        :param max_depth: Maximum depth for vertical chain sampling
        :param max_siblings: Maximum siblings per community in horizontal grouping
        :param include_attributes: Whether to include non-hierarchical edges
        """
        self.hierarchical_relations = hierarchical_relations or [
            "is_a",
            "subclass_of",
            "part_of",
            "includes",
            "type_of",
        ]
        self.max_depth = max_depth
        self.max_siblings = max_siblings
        self.include_attributes = include_attributes

    async def partition(
        self,
        g: BaseGraphStorage,
        **kwargs: Any,
    ) -> List[Community]:
        """
        Partition graph into hierarchical communities.

        :param g: Graph storage
        :return: List of communities
        """
        nodes = await g.get_all_nodes()
        edges = await g.get_all_edges()

        if not nodes:
            logger.warning("No nodes found in graph")
            return []

        # Build edge classification
        hierarchical_edges, attribute_edges = self._classify_edges(edges)

        # Build parent→children and child→parents maps
        parent_to_children = defaultdict(set)
        child_to_parents = defaultdict(set)

        for src, tgt, data in hierarchical_edges:
            # src is child, tgt is parent (src is_a tgt)
            parent_to_children[tgt].add(src)
            child_to_parents[src].add(tgt)

        # Detect and handle cycles
        cycles = self._detect_cycles(nodes, parent_to_children)
        if cycles:
            logger.warning(f"Detected {len(cycles)} cycles in hierarchy, breaking them")
            parent_to_children, child_to_parents = self._break_cycles(
                cycles, parent_to_children, child_to_parents
            )

        communities: List[Community] = []
        used_nodes: Set[str] = set()

        # Strategy 1: Sibling grouping (horizontal)
        sibling_communities = self._sibling_grouping(
            nodes, parent_to_children, child_to_parents, hierarchical_edges,
            attribute_edges, used_nodes
        )
        communities.extend(sibling_communities)
        logger.info(f"Created {len(sibling_communities)} sibling group communities")

        # Strategy 2: Chain sampling (vertical)
        chain_communities = self._chain_sampling(
            nodes, parent_to_children, child_to_parents, hierarchical_edges,
            attribute_edges, used_nodes
        )
        communities.extend(chain_communities)
        logger.info(f"Created {len(chain_communities)} vertical chain communities")

        # Handle isolated nodes (no hierarchical edges)
        isolated_communities = self._handle_isolated_nodes(
            nodes, edges, used_nodes
        )
        communities.extend(isolated_communities)
        logger.info(f"Created {len(isolated_communities)} isolated node communities")

        logger.info(
            f"Total communities created: {len(communities)} "
            f"(sibling={len(sibling_communities)}, chain={len(chain_communities)}, "
            f"isolated={len(isolated_communities)})"
        )

        return communities

    def _classify_edges(
        self, edges: List[Tuple[str, str, dict]]
    ) -> Tuple[List[Tuple[str, str, dict]], List[Tuple[str, str, dict]]]:
        """Classify edges into hierarchical and attribute edges."""
        hierarchical = []
        attribute = []

        for src, tgt, data in edges:
            relation_type = data.get("relation_type", data.get("description", ""))
            if relation_type in self.hierarchical_relations:
                hierarchical.append((src, tgt, data))
            else:
                attribute.append((src, tgt, data))

        logger.debug(
            f"Classified {len(hierarchical)} hierarchical edges, "
            f"{len(attribute)} attribute edges"
        )
        return hierarchical, attribute

    def _detect_cycles(
        self,
        nodes: List[Tuple[str, dict]],
        parent_to_children: dict,
    ) -> List[List[str]]:
        """Detect cycles in hierarchical structure using NetworkX."""
        # Build directed graph
        G = nx.DiGraph()
        for node_id, _ in nodes:
            G.add_node(node_id)

        for parent, children in parent_to_children.items():
            for child in children:
                G.add_edge(child, parent)  # child → parent direction

        try:
            cycles = list(nx.simple_cycles(G))
            return cycles
        except Exception as e:
            logger.warning(f"Error detecting cycles: {e}")
            return []

    def _break_cycles(
        self,
        cycles: List[List[str]],
        parent_to_children: dict,
        child_to_parents: dict,
    ) -> Tuple[dict, dict]:
        """Break cycles by removing first edge in each cycle."""
        for cycle in cycles:
            if len(cycle) >= 2:
                # Remove edge from first to second node in cycle
                node1, node2 = cycle[0], cycle[1]
                if node2 in parent_to_children.get(node1, set()):
                    parent_to_children[node1].discard(node2)
                    child_to_parents[node2].discard(node1)
                    logger.debug(f"Broke cycle by removing edge {node1}→{node2}")

        return parent_to_children, child_to_parents

    def _sibling_grouping(
        self,
        nodes: List[Tuple[str, dict]],
        parent_to_children: dict,
        child_to_parents: dict,
        hierarchical_edges: List[Tuple[str, str, dict]],
        attribute_edges: List[Tuple[str, str, dict]],
        used_nodes: Set[str],
    ) -> List[Community]:
        """
        Strategy 1: Group parent + children into sibling communities.
        For each parent with ≥2 children, create community [parent] + children[:max_siblings]
        """
        communities = []
        node_dict = {nid: data for nid, data in nodes}

        # Find parents with multiple children
        for parent, children in parent_to_children.items():
            if parent in used_nodes:
                continue

            if len(children) >= 2:
                # Limit to max_siblings
                selected_children = [
                    c for c in list(children)[:self.max_siblings]
                    if c not in used_nodes
                ]

                if len(selected_children) < 2:
                    continue

                # Create community with parent + children
                community_nodes = [parent] + selected_children
                community_edges = []

                # Include hierarchical edges between parent and children
                for child in selected_children:
                    for src, tgt, data in hierarchical_edges:
                        if (src == child and tgt == parent) or (src == parent and tgt == child):
                            community_edges.append((src, tgt))

                # Include attribute edges within community
                if self.include_attributes:
                    community_set = set(community_nodes)
                    for src, tgt, data in attribute_edges:
                        if src in community_set and tgt in community_set:
                            community_edges.append((src, tgt))

                community = Community(
                    id=len(communities),
                    nodes=community_nodes,
                    edges=community_edges,
                    metadata={"type": "sibling_group", "parent": parent}
                )
                communities.append(community)

                # Mark nodes as used
                used_nodes.add(parent)
                used_nodes.update(selected_children)

        return communities

    def _chain_sampling(
        self,
        nodes: List[Tuple[str, dict]],
        parent_to_children: dict,
        child_to_parents: dict,
        hierarchical_edges: List[Tuple[str, str, dict]],
        attribute_edges: List[Tuple[str, str, dict]],
        used_nodes: Set[str],
    ) -> List[Community]:
        """
        Strategy 2: Sample vertical chains from roots to descendants.
        For each root (no parents), BFS/DFS down hierarchy up to max_depth.
        """
        communities = []

        # Find roots (nodes with no hierarchical parents)
        roots = [
            node_id for node_id, _ in nodes
            if node_id not in child_to_parents and node_id not in used_nodes
        ]

        for root in roots:
            # BFS down hierarchy
            chain = [root]
            visited = {root}
            queue = [root]
            depth = 0

            while queue and depth < self.max_depth:
                current = queue.pop(0)
                children = parent_to_children.get(current, set())

                for child in children:
                    if child not in visited and child not in used_nodes:
                        chain.append(child)
                        visited.add(child)
                        queue.append(child)

                depth += 1

            if len(chain) >= 2:
                # Create community with chain nodes
                community_edges = []

                # Include hierarchical edges along chain
                for i in range(len(chain) - 1):
                    for src, tgt, data in hierarchical_edges:
                        if (src == chain[i] and tgt == chain[i + 1]) or \
                           (src == chain[i + 1] and tgt == chain[i]):
                            community_edges.append((src, tgt))

                # Include attribute edges within chain
                if self.include_attributes:
                    chain_set = set(chain)
                    for src, tgt, data in attribute_edges:
                        if src in chain_set and tgt in chain_set:
                            community_edges.append((src, tgt))

                community = Community(
                    id=len(communities),
                    nodes=chain,
                    edges=community_edges,
                    metadata={"type": "vertical_chain", "root": root}
                )
                communities.append(community)

                # Mark nodes as used
                used_nodes.update(chain)

        return communities

    def _handle_isolated_nodes(
        self,
        nodes: List[Tuple[str, dict]],
        edges: List[Tuple[str, str, dict]],
        used_nodes: Set[str],
    ) -> List[Community]:
        """Handle nodes with no hierarchical edges as single-node communities."""
        communities = []

        # Find nodes with no hierarchical edges
        for node_id, data in nodes:
            if node_id not in used_nodes:
                # Check if node has any edges at all
                has_edges = any(
                    src == node_id or tgt == node_id
                    for src, tgt, _ in edges
                )

                # Create single-node community
                community = Community(
                    id=len(communities),
                    nodes=[node_id],
                    edges=[],
                    metadata={"type": "isolated", "has_edges": has_edges}
                )
                communities.append(community)
                used_nodes.add(node_id)

        return communities
