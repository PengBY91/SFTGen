"""Tree structure generator for hierarchical knowledge."""

import json
import re
from typing import Any, List, Optional, Tuple
import networkx as nx

from graphgen.bases import BaseGenerator
from graphgen.templates import HIERARCHICAL_GENERATION_PROMPT
from graphgen.utils import compute_content_hash, detect_main_language, logger


class TreeStructureGenerator(BaseGenerator):
    """
    Generator for hierarchical knowledge structures.

    Serializes knowledge subgraphs into tree formats (Markdown, JSON, Outline)
    and generates QA pairs focused on hierarchical reasoning.
    """

    def __init__(
        self,
        llm_client,
        structure_format: str = "markdown",
        hierarchical_relations: List[str] = None,
        chinese_only: bool = False,
    ):
        """
        Initialize TreeStructureGenerator.

        :param llm_client: LLM client instance
        :param structure_format: Output format - "markdown", "json", or "outline"
        :param hierarchical_relations: List of relation types indicating hierarchy
        :param chinese_only: Whether to generate only Chinese QA pairs
        """
        super().__init__(llm_client)
        self.structure_format = structure_format
        self.hierarchical_relations = hierarchical_relations or [
            "is_a",
            "subclass_of",
            "part_of",
            "includes",
            "type_of",
        ]
        self.chinese_only = chinese_only
        self._generation_mode = "hierarchical"

    def build_prompt(
        self,
        batch: Tuple[List[Tuple[str, dict]], List[Tuple[Any, Any, dict]]]
    ) -> str:
        """
        Build prompt with hierarchical structure.

        :param batch: Tuple of (nodes, edges)
        :return: Formatted prompt string
        """
        # Build hierarchical structure
        hierarchy_text = self._serialize_to_format(batch)

        # Detect language
        language = "zh" if self.chinese_only else detect_main_language(hierarchy_text)

        # Select reasoning pattern (randomly for diversity)
        import random
        reasoning_patterns = ["sibling", "inheritance", "abstraction", "multilevel"]
        selected_pattern = random.choice(reasoning_patterns)

        # Get appropriate template
        templates = HIERARCHICAL_GENERATION_PROMPT.get(language, HIERARCHICAL_GENERATION_PROMPT["en"])
        template = templates.get(selected_pattern, templates["sibling"])

        prompt = template.format(context=hierarchy_text)
        logger.debug(
            f"Built hierarchical prompt with format={self.structure_format}, "
            f"pattern={selected_pattern}, language={language}"
        )

        return prompt

    def _serialize_to_format(
        self,
        batch: Tuple[List[Tuple[str, dict]], List[Tuple[Any, Any, dict]]]
    ) -> str:
        """
        Serialize batch to hierarchical structure.

        :param batch: Tuple of (nodes, edges)
        :return: Formatted hierarchy string
        """
        nodes, edges = batch

        if not nodes:
            return "No hierarchical structure available."

        # Build directed graph
        G = nx.DiGraph()
        node_dict = {}

        # Add nodes
        for node_id, data in nodes:
            G.add_node(node_id)
            node_dict[node_id] = data

        # Classify edges and build hierarchy
        hierarchical_edge_tuples = []

        for src, tgt, data in edges:
            relation_type = data.get("relation_type", data.get("description", ""))

            if relation_type in self.hierarchical_relations:
                # src is child, tgt is parent (src is_a tgt)
                G.add_edge(src, tgt, relation=relation_type)
                hierarchical_edge_tuples.append((src, tgt, relation_type))
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

        if not roots:
            # If no roots found (e.g., all nodes in cycles), use first node
            roots = [nodes[0][0]] if nodes else []

        # Serialize based on format
        if self.structure_format == "markdown":
            return self._serialize_markdown(G, roots, node_dict)
        elif self.structure_format == "json":
            return self._serialize_json(G, roots, node_dict)
        elif self.structure_format == "outline":
            return self._serialize_outline(G, roots, node_dict)
        else:
            logger.warning(f"Unknown format {self.structure_format}, using markdown")
            return self._serialize_markdown(G, roots, node_dict)

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
                    lines.append(f"- {rel}: {tgt}")
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

    @staticmethod
    def parse_response(response: str) -> dict:
        """
        Parse response containing hierarchical QA pair.

        Expected format:
        Question: ...
        Answer: ...
        Hierarchical Reasoning: ... (optional)

        :param response: LLM response string
        :return: Dictionary with QA pair
        """
        result = {}

        if not response or not response.strip():
            logger.warning("Empty response received")
            return result

        # Clean response
        response_clean = response.strip()

        # Pre-processing: Remove meta-descriptions
        meta_prefixes = [
            r"^根据您提供的层次结构[，,]\s*以下是.*?[：:]\s*",
            r"^根据.*?层次[，,]\s*以下是.*?[：:]\s*",
            r"^Based on the (?:hierarchical|tree) structure.*?here is.*?[：:]\s*",
            r"^Here is (?:a|the) (?:QA|question-answer) pair.*?[：:]\s*",
        ]

        for pattern in meta_prefixes:
            response_clean = re.sub(pattern, "", response_clean, flags=re.IGNORECASE)

        response_clean = response_clean.strip()

        # Try to extract Question, Answer, and Hierarchical Reasoning
        question = None
        answer = None
        reasoning = None

        # Pattern 1: Full format with all three components
        pattern_full = re.compile(
            r"(?:Question|问题)[：:]\s*(.+?)(?=(?:Answer|答案)[：:])"
            r".*?(?:Answer|答案)[：:]\s*(.+?)(?=(?:Hierarchical Reasoning|层次推理)[：:]|$)"
            r"(?:.*?(?:Hierarchical Reasoning|层次推理)[：:]\s*(.+))?$",
            re.DOTALL | re.IGNORECASE
        )

        match = pattern_full.search(response_clean)
        if match:
            question = match.group(1).strip().strip('"').strip("'")
            answer = match.group(2).strip().strip('"').strip("'")
            reasoning = match.group(3).strip().strip('"').strip("'") if match.lastindex >= 3 and match.group(3) else None
        else:
            # Pattern 2: Standard QA format (no hierarchical reasoning)
            markers = [
                ("Question:", "Answer:", "en"),
                ("问题：", "答案：", "zh"),
                ("Q:", "A:", "en"),
                ("问：", "答：", "zh"),
            ]

            for q_marker, a_marker, lang in markers:
                if q_marker in response_clean:
                    try:
                        q_pos = response_clean.find(q_marker)
                        a_pos = response_clean.find(a_marker, q_pos + len(q_marker))

                        if a_pos > q_pos:
                            question = response_clean[q_pos + len(q_marker):a_pos].strip()
                            remaining = response_clean[a_pos + len(a_marker):].strip()

                            # Check for hierarchical reasoning
                            reasoning_markers = ["Hierarchical Reasoning:", "层次推理："]
                            for r_marker in reasoning_markers:
                                if r_marker in remaining:
                                    r_pos = remaining.find(r_marker)
                                    answer = remaining[:r_pos].strip()
                                    reasoning = remaining[r_pos + len(r_marker):].strip()
                                    break
                            else:
                                answer = remaining

                            question = question.strip('"').strip("'")
                            answer = answer.strip('"').strip("'")
                            break
                    except (IndexError, ValueError) as e:
                        logger.debug(f"Error parsing with markers {q_marker}/{a_marker}: {e}")
                        continue

        if question and answer:
            q_hash = compute_content_hash(question)
            result[q_hash] = {
                "question": question,
                "answer": answer,
            }
            if reasoning:
                result[q_hash]["hierarchical_reasoning"] = reasoning

            logger.debug(
                f"Parsed hierarchical QA pair: Q={question[:50]}, "
                f"reasoning={'included' if reasoning else 'none'}"
            )
        elif question:
            logger.warning(f"Question found but no answer extracted: {question[:100]}")
        else:
            logger.warning(
                f"Failed to parse hierarchical QA pair from response: "
                f"{response_clean[:200] if len(response_clean) > 200 else response_clean}"
            )

        return result
