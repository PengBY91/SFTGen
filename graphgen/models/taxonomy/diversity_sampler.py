"""
Diversity Sampler for Taxonomy Trees.

Provides multiple sampling strategies to ensure broad coverage of the
taxonomy tree during data generation.
"""

import logging
import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from graphgen.models.taxonomy.taxonomy_tree import TaxonomyNode, TaxonomyTree

logger = logging.getLogger(__name__)


class DiversitySampler:
    """
    Samples nodes from a TaxonomyTree with diversity-aware strategies.

    Supports:
    - uniform_branch: Evenly sample across branches
    - depth_weighted: Prefer deeper (more specific) nodes
    - coverage: Track history and avoid repeating covered areas
    """

    def __init__(self, tree: TaxonomyTree, seed: Optional[int] = None):
        self.tree = tree
        self.rng = random.Random(seed)
        self._coverage_history: Set[str] = set()

    # ─── Sampling Strategies ────────────────────────────────────────

    def sample(
        self,
        k: int,
        strategy: str = "coverage",
        **kwargs,
    ) -> List[TaxonomyNode]:
        """
        Sample k nodes from the tree using the given strategy.

        :param k: Number of nodes to sample
        :param strategy: "uniform_branch", "depth_weighted", or "coverage"
        :return: List of sampled TaxonomyNode instances
        """
        if self.tree.size == 0:
            return []

        k = min(k, self.tree.size)

        if strategy == "uniform_branch":
            result = self.uniform_branch_sampling(k)
        elif strategy == "depth_weighted":
            weight_factor = kwargs.get("weight_factor", 2.0)
            result = self.depth_weighted_sampling(k, weight_factor=weight_factor)
        elif strategy == "coverage":
            result = self.coverage_tracking_sampling(k)
        else:
            logger.warning("Unknown strategy '%s', falling back to coverage", strategy)
            result = self.coverage_tracking_sampling(k)

        # 统一记录采样历史：原实现仅 coverage 策略记录，
        # 其他策略下 coverage_ratio 恒为 0.0，与实际采样情况不符
        for node in result:
            self._coverage_history.add(node.id)
        return result

    def uniform_branch_sampling(self, k: int) -> List[TaxonomyNode]:
        """
        Sample evenly across branches.

        Distributes samples proportionally across root-anchored branches,
        then randomly picks within each branch.
        """
        roots = self.tree.roots
        if not roots:
            return []

        # Group leaves by their root ancestor
        branch_leaves: Dict[str, List[TaxonomyNode]] = defaultdict(list)
        for leaf in self.tree.leaves:
            branch = self.tree.get_branch(leaf.id)
            root_id = branch[0].id if branch else leaf.id
            branch_leaves[root_id].append(leaf)

        # If no leaves (single-node trees), use all nodes
        if not branch_leaves:
            all_nodes = self.tree.get_all_nodes()
            return self.rng.sample(all_nodes, min(k, len(all_nodes)))

        # Distribute k across branches proportionally
        branch_ids = list(branch_leaves.keys())
        samples_per_branch = self._distribute_k(k, len(branch_ids))

        result = []
        for branch_id, count in zip(branch_ids, samples_per_branch):
            candidates = branch_leaves[branch_id]
            if count <= len(candidates):
                result.extend(self.rng.sample(candidates, count))
            else:
                # Not enough leaves in this branch, take all + sample
                # internal nodes
                result.extend(candidates)
                remaining = count - len(candidates)
                subtree = self.tree.get_subtree(branch_id)
                internal = [n for n in subtree if not n.is_leaf and n not in result]
                if internal:
                    result.extend(self.rng.sample(internal, min(remaining, len(internal))))

        return result[:k]

    def depth_weighted_sampling(
        self,
        k: int,
        weight_factor: float = 2.0,
    ) -> List[TaxonomyNode]:
        """
        Sample with higher probability for deeper nodes.

        :param k: Number of nodes to sample
        :param weight_factor: How much to prefer deeper nodes (>1 = more)
        """
        all_nodes = self.tree.get_all_nodes()
        if not all_nodes:
            return []

        max_depth = self.tree.max_depth or 1
        weights = []
        for node in all_nodes:
            # Deeper nodes get higher weight
            normalized_depth = (node.depth + 1) / (max_depth + 1)
            weight = normalized_depth ** weight_factor
            weights.append(weight)

        # Weighted sampling without replacement
        result = []
        available = list(range(len(all_nodes)))
        available_weights = list(weights)

        for _ in range(min(k, len(all_nodes))):
            if not available:
                break
            total_w = sum(available_weights)
            if total_w <= 0:
                # Fallback to uniform
                idx = self.rng.choice(available)
            else:
                r = self.rng.random() * total_w
                cumulative = 0
                idx = available[0]
                for i, w in zip(available, available_weights):
                    cumulative += w
                    if cumulative >= r:
                        idx = i
                        break

            result.append(all_nodes[idx])
            pos = available.index(idx)
            available.pop(pos)
            available_weights.pop(pos)

        return result

    def coverage_tracking_sampling(self, k: int) -> List[TaxonomyNode]:
        """
        Sample nodes while tracking coverage to avoid repetition.

        Prioritizes uncovered nodes, then least-recently-covered branches.
        """
        all_nodes = self.tree.get_all_nodes()
        if not all_nodes:
            return []

        # Separate uncovered and covered nodes
        uncovered = [n for n in all_nodes if n.id not in self._coverage_history]
        covered = [n for n in all_nodes if n.id in self._coverage_history]

        result = []

        # First, sample from uncovered nodes
        if uncovered:
            sample_from_uncovered = min(k, len(uncovered))
            # Prefer leaves among uncovered
            uncovered_leaves = [n for n in uncovered if n.is_leaf]
            uncovered_internal = [n for n in uncovered if not n.is_leaf]

            if uncovered_leaves:
                take_leaves = min(sample_from_uncovered, len(uncovered_leaves))
                result.extend(self.rng.sample(uncovered_leaves, take_leaves))
                sample_from_uncovered -= take_leaves

            if sample_from_uncovered > 0 and uncovered_internal:
                take_internal = min(sample_from_uncovered, len(uncovered_internal))
                result.extend(self.rng.sample(uncovered_internal, take_internal))

        # If still need more, sample from covered nodes
        remaining = k - len(result)
        if remaining > 0 and covered:
            result.extend(self.rng.sample(covered, min(remaining, len(covered))))

        # Update coverage history
        for node in result:
            self._coverage_history.add(node.id)

        return result[:k]

    # ─── Coverage API ───────────────────────────────────────────────

    @property
    def coverage_ratio(self) -> float:
        """Fraction of tree nodes that have been covered by sampling."""
        if self.tree.size == 0:
            return 0.0
        return len(self._coverage_history) / self.tree.size

    @property
    def uncovered_count(self) -> int:
        """Number of uncovered nodes."""
        return self.tree.size - len(self._coverage_history)

    def get_coverage_by_dimension(self) -> Dict[str, float]:
        """Get coverage ratio per cognitive dimension."""
        from graphgen.models.taxonomy.taxonomy_tree import COGNITIVE_DIMENSIONS
        result = {}
        for dim in COGNITIVE_DIMENSIONS:
            nodes = self.tree.get_nodes_by_dimension(dim)
            if not nodes:
                continue
            covered = sum(1 for n in nodes if n.id in self._coverage_history)
            result[dim] = covered / len(nodes)
        return result

    def get_coverage_by_depth(self) -> Dict[int, float]:
        """Get coverage ratio per depth level."""
        result = {}
        for depth in range(self.tree.max_depth + 1):
            nodes = self.tree.get_nodes_at_depth(depth)
            if not nodes:
                continue
            covered = sum(1 for n in nodes if n.id in self._coverage_history)
            result[depth] = covered / len(nodes)
        return result

    def reset_coverage(self) -> None:
        """Reset coverage history."""
        self._coverage_history.clear()

    # ─── Helpers ────────────────────────────────────────────────────

    def _distribute_k(self, k: int, n_groups: int) -> List[int]:
        """Distribute k samples across n_groups as evenly as possible."""
        if n_groups == 0:
            return []
        base = k // n_groups
        remainder = k % n_groups
        distribution = [base] * n_groups
        # Distribute remainder randomly
        for i in self.rng.sample(range(n_groups), remainder):
            distribution[i] += 1
        return distribution
