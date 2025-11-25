"""
知识覆盖指标计算脚本
用于计算长尾知识覆盖率、复杂关系覆盖率和平均跳数等指标
"""

import json
import os
import sys
import argparse
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import networkx as nx

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graphgen.models import NetworkXStorage, JsonListStorage
from graphgen.utils import logger


def load_qa_pairs(qa_folder: str) -> List[Dict]:
    """
    加载QA对数据
    
    :param qa_folder: QA数据文件夹路径
    :return: QA对列表
    """
    qa_pairs = []
    if os.path.isdir(qa_folder):
        for filename in os.listdir(qa_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(qa_folder, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # 兼容不同格式
                        for key, value in data.items():
                            if isinstance(value, dict):
                                qa_pairs.append(value)
                    elif isinstance(data, list):
                        qa_pairs.extend(data)
    return qa_pairs


def get_entities_and_relations_from_kg(kg_storage: NetworkXStorage) -> Tuple[Dict[str, int], Dict[Tuple[str, str], int]]:
    """
    从知识图谱中提取所有实体和关系，并统计出现次数
    
    :param kg_storage: 知识图谱存储实例
    :return: (实体出现次数字典, 关系出现次数字典)
    """
    nodes = kg_storage.graph.nodes(data=True)
    edges = kg_storage.graph.edges(data=True)
    
    entity_counts = {}
    relation_counts = {}
    
    # 统计实体出现次数（基于source_id）
    for node_id, node_data in nodes:
        source_ids = node_data.get('source_id', '').split('<SEP>')
        for source_id in source_ids:
            if source_id:
                entity_counts[node_id] = entity_counts.get(node_id, 0) + 1
    
    # 统计关系出现次数（基于source_id）
    for src_id, tgt_id, edge_data in edges:
        source_ids = edge_data.get('source_id', '').split('<SEP>')
        for source_id in source_ids:
            if source_id:
                relation_key = (src_id, tgt_id)
                relation_counts[relation_key] = relation_counts.get(relation_key, 0) + 1
    
    return entity_counts, relation_counts


def calculate_long_tail_coverage(
    kg_storage: NetworkXStorage,
    qa_pairs: List[Dict],
    threshold: int = 5
) -> float:
    """
    计算长尾知识覆盖率
    
    :param kg_storage: 知识图谱存储实例
    :param qa_pairs: QA对列表
    :param threshold: 长尾知识阈值（出现次数 <= threshold）
    :return: 覆盖率（0-1之间）
    """
    entity_counts, relation_counts = get_entities_and_relations_from_kg(kg_storage)
    
    # 筛选长尾实体和关系
    long_tail_entities = {
        entity_id for entity_id, count in entity_counts.items() 
        if count <= threshold
    }
    long_tail_relations = {
        rel_key for rel_key, count in relation_counts.items() 
        if count <= threshold
    }
    
    total_long_tail = len(long_tail_entities) + len(long_tail_relations)
    if total_long_tail == 0:
        return 0.0
    
    # 从QA对中提取涉及的实体和关系
    covered_entities = set()
    covered_relations = set()
    
    for qa_pair in qa_pairs:
        # 从source_id或metadata中提取实体和关系信息
        source_ids = qa_pair.get('source_ids', [])
        if isinstance(source_ids, str):
            source_ids = source_ids.split('<SEP>')
        
        # 通过source_id回溯到知识图谱中的实体和关系
        # 这里需要根据实际QA对的存储格式进行调整
        metadata = qa_pair.get('metadata', {})
        node_ids = metadata.get('node_ids', [])
        edge_ids = metadata.get('edge_ids', [])
        
        for node_id in node_ids:
            if node_id in long_tail_entities:
                covered_entities.add(node_id)
        
        for edge_id in edge_ids:
            if isinstance(edge_id, (list, tuple)) and len(edge_id) == 2:
                edge_key = tuple(edge_id)
                if edge_key in long_tail_relations:
                    covered_relations.add(edge_key)
    
    covered_count = len(covered_entities) + len(covered_relations)
    coverage = covered_count / total_long_tail
    
    logger.info(
        "Long-tail coverage: %d/%d = %.2f%% (entities: %d/%d, relations: %d/%d)",
        covered_count, total_long_tail, coverage * 100,
        len(covered_entities), len(long_tail_entities),
        len(covered_relations), len(long_tail_relations)
    )
    
    return coverage


def calculate_complex_relation_coverage(
    kg_storage: NetworkXStorage,
    qa_pairs: List[Dict],
    min_path_length: int = 2
) -> float:
    """
    计算复杂关系覆盖率
    
    :param kg_storage: 知识图谱存储实例
    :param qa_pairs: QA对列表
    :param min_path_length: 最小路径长度（>= min_path_length的关系被认为是复杂关系）
    :return: 覆盖率（0-1之间）
    """
    graph = kg_storage.graph
    
    # 找出所有路径长度 >= min_path_length的关系对
    complex_relations = set()
    
    # 使用NetworkX计算所有节点对之间的最短路径
    for node1 in graph.nodes():
        for node2 in graph.nodes():
            if node1 != node2:
                try:
                    path_length = nx.shortest_path_length(graph, node1, node2)
                    if path_length >= min_path_length:
                        # 记录路径上的所有边
                        path = nx.shortest_path(graph, node1, node2)
                        for i in range(len(path) - 1):
                            edge = (path[i], path[i+1])
                            complex_relations.add(edge)
                except nx.NetworkXNoPath:
                    continue
    
    total_complex_relations = len(complex_relations)
    if total_complex_relations == 0:
        return 0.0
    
    # 从QA对中提取涉及的关系
    covered_relations = set()
    
    for qa_pair in qa_pairs:
        metadata = qa_pair.get('metadata', {})
        edge_ids = metadata.get('edge_ids', [])
        
        for edge_id in edge_ids:
            if isinstance(edge_id, (list, tuple)) and len(edge_id) == 2:
                edge_key = tuple(edge_id)
                if edge_key in complex_relations:
                    covered_relations.add(edge_key)
    
    coverage = len(covered_relations) / total_complex_relations
    
    logger.info(
        "Complex relation coverage: %d/%d = %.2f%%",
        len(covered_relations), total_complex_relations, coverage * 100
    )
    
    return coverage


def calculate_average_hops(
    kg_storage: NetworkXStorage,
    qa_pairs: List[Dict]
) -> float:
    """
    计算平均跳数
    
    :param kg_storage: 知识图谱存储实例
    :param qa_pairs: QA对列表
    :return: 平均跳数
    """
    graph = kg_storage.graph
    all_hops = []
    
    for qa_pair in qa_pairs:
        metadata = qa_pair.get('metadata', {})
        node_ids = metadata.get('node_ids', [])
        
        if len(node_ids) < 2:
            continue
        
        # 计算该QA对对应子图中所有节点对之间的最短路径长度
        subgraph_hops = []
        for i, node1 in enumerate(node_ids):
            for node2 in node_ids[i+1:]:
                if node1 in graph and node2 in graph:
                    try:
                        path_length = nx.shortest_path_length(graph, node1, node2)
                        subgraph_hops.append(path_length)
                    except nx.NetworkXNoPath:
                        continue
        
        if subgraph_hops:
            avg_hops = sum(subgraph_hops) / len(subgraph_hops)
            all_hops.append(avg_hops)
    
    if not all_hops:
        return 0.0
    
    overall_avg_hops = sum(all_hops) / len(all_hops)
    
    logger.info(
        "Average hops: %.2f (calculated from %d QA pairs)",
        overall_avg_hops, len(all_hops)
    )
    
    return overall_avg_hops


def main():
    parser = argparse.ArgumentParser(description='计算知识覆盖指标')
    parser.add_argument(
        '--kg_dir',
        type=str,
        required=True,
        help='知识图谱存储目录路径'
    )
    parser.add_argument(
        '--qa_folder',
        type=str,
        required=True,
        help='QA数据文件夹路径'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='coverage_metrics.json',
        help='输出文件路径'
    )
    parser.add_argument(
        '--long_tail_threshold',
        type=int,
        default=5,
        help='长尾知识阈值（出现次数 <= threshold）'
    )
    parser.add_argument(
        '--min_path_length',
        type=int,
        default=2,
        help='复杂关系最小路径长度'
    )
    
    args = parser.parse_args()
    
    # 加载知识图谱
    logger.info("Loading knowledge graph from %s", args.kg_dir)
    kg_storage = NetworkXStorage(args.kg_dir, namespace="graph")
    
    # 加载QA对
    logger.info("Loading QA pairs from %s", args.qa_folder)
    qa_pairs = load_qa_pairs(args.qa_folder)
    logger.info("Loaded %d QA pairs", len(qa_pairs))
    
    # 计算各项指标
    results = {
        'method': os.path.basename(args.qa_folder),
        'total_qa_pairs': len(qa_pairs),
        'long_tail_coverage': calculate_long_tail_coverage(
            kg_storage, qa_pairs, args.long_tail_threshold
        ),
        'complex_relation_coverage': calculate_complex_relation_coverage(
            kg_storage, qa_pairs, args.min_path_length
        ),
        'average_hops': calculate_average_hops(kg_storage, qa_pairs),
    }
    
    # 保存结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info("Results saved to %s", args.output)
    logger.info("Long-tail coverage: %.2f%%", results['long_tail_coverage'] * 100)
    logger.info("Complex relation coverage: %.2f%%", results['complex_relation_coverage'] * 100)
    logger.info("Average hops: %.2f", results['average_hops'])


if __name__ == '__main__':
    main()

