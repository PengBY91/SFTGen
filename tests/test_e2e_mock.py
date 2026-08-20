"""端到端集成冒烟测试（mock LLM，零 API 成本）。

覆盖完整链路：GraphGen.insert（合并抽取、实体/关系合并入图）
→ partition（ECE）→ generate_qas（单模式 aggregated）
→ 去重/质量过滤 → qa_storage。
历史回归（单模式 NameError、合并解析 fallback、模板 KeyError）都会在此暴露。
"""

import asyncio
import os
import tempfile

import pytest

from graphgen.graphgen import GraphGen
from graphgen.models.tokenizer import Tokenizer

SAMPLE_TEXT = (
    "云南省农业科学院粮食作物研究所于2005年育成早熟品种云粳26号，"
    "该品种外观特点为: 颖尖无色、无芒，谷壳黄色，米粒大，有香味，食味品质好，"
    "高抗稻瘟病，适宜在云南中海拔1500～1800米稻区种植。\n\n"
    "隆两优1212于2017年引入福建省龙岩市试种，表现出生育期适中、抗倒伏能力强、"
    "米质优等特点。该品种由湖南隆平高科选育，适宜在华南稻区推广种植。"
)

KG_RESPONSE_TEMPLATE = """[文本1]
("entity"<|>"云粳26号"<|>"concept"<|>"云南省农科院育成的早熟水稻品种，米粒大有香味，高抗稻瘟病。")##
("entity"<|>"隆两优1212"<|>"concept"<|>"湖南隆平高科选育的水稻品种，抗倒伏能力强，米质优。")##
("entity"<|>"云南省农业科学院"<|>"organization"<|>"育成云粳26号的科研机构。")##
("relationship"<|>"云粳26号"<|>"云南省农业科学院"<|>"云粳26号由云南省农业科学院育成。")##
("relationship"<|>"隆两优1212"<|>"湖南隆平高科"<|>"隆两优1212由湖南隆平高科选育。")##
<|COMPLETE|>"""

QA_RESPONSE = (
    "问题：云粳26号具有哪些品种特点？\n\n"
    "答案：云粳26号是云南省农业科学院粮食作物研究所2005年育成的早熟品种，"
    "具有颖尖无色、无芒、谷壳黄色、米粒大、有香味、食味品质好、高抗稻瘟病等特点，"
    "适宜在云南中海拔1500～1800米稻区种植。"
)


class ScriptedLLMClient:
    """按 prompt 类型返回脚本化响应的 mock 客户端。"""

    def __init__(self):
        self.system_prompt = ""
        self.temperature = 0.0
        self.max_tokens = 4096
        self.repetition_penalty = 1.0
        self.top_p = 0.95
        self.top_k = 50
        self.tokenizer = None
        self.token_usage = []
        self.calls = 0

    async def generate_answer(self, prompt, history=None, **extra):
        self.calls += 1
        # 合并抽取 prompt：包含 [文本N] 指令 → 返回带标记的抽取结果
        if "个文本片段" in prompt or "text fragments" in prompt:
            return KG_RESPONSE_TEMPLATE
        # 单 chunk 抽取 prompt（含抽取格式说明）
        if '("entity"' in prompt or "content_keywords" in prompt or "<|COMPLETE|>" in prompt:
            return KG_RESPONSE_TEMPLATE.replace("[文本1]\n", "")
        # 生成类 prompt
        return QA_RESPONSE


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer("cl100k_base")


def _make_graph_gen(tmpdir, tokenizer):
    client = ScriptedLLMClient()
    # KG 合并阶段的 _handle_kg_summary 会用到 llm_client.tokenizer
    client.tokenizer = tokenizer
    return GraphGen(
        working_dir=os.path.join(tmpdir, "work"),
        tokenizer_instance=tokenizer,
        synthesizer_llm_client=client,
        trainee_llm_client=client,
    )


def test_end_to_end_insert_and_generate(tokenizer):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.txt")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(SAMPLE_TEXT)

        graph_gen = _make_graph_gen(tmpdir, tokenizer)
        asyncio.run(graph_gen.clear.__wrapped__(graph_gen))

        # Step 1: 知识构建（含合并抽取与实体/关系合并）
        asyncio.run(
            graph_gen.insert.__wrapped__(
                graph_gen,
                read_config={"input_file": input_path},
                split_config={
                    "chunk_size": 512,
                    "chunk_overlap": 50,
                    "enable_prompt_merging": True,
                    "prompt_merge_size": 2,
                    "enable_batch_requests": False,
                },
            )
        )

        nodes = asyncio.run(graph_gen.graph_storage.get_all_nodes())
        edges = asyncio.run(graph_gen.graph_storage.get_all_edges())
        assert len(nodes) >= 3, f"expected >=3 nodes, got {len(nodes)}"
        assert len(edges) >= 2, f"expected >=2 edges, got {len(edges)}"

        # Step 2: 分区 + 生成（单模式 aggregated，修复前此路径 NameError）
        asyncio.run(
            graph_gen.generate.__wrapped__(
                graph_gen,
                partition_config={
                    "method": "ece",
                    "method_params": {
                        "max_units_per_community": 10,
                        "min_units_per_community": 1,
                        "max_tokens_per_community": 10240,
                        "unit_sampling": "random",
                    },
                },
                generate_config={
                    "mode": "aggregated",
                    "data_format": "Alpaca",
                    "enable_batch_requests": False,
                    "enable_prompt_cache": False,
                    "target_qa_pairs": 10,
                },
            )
        )

        qa_data = graph_gen.qa_storage.data
        assert isinstance(qa_data, list) and len(qa_data) >= 1, (
            f"expected QA output, got {qa_data!r}"
        )
        first = qa_data[0]
        assert first.get("instruction"), "Alpaca 格式缺少 instruction"
        assert first.get("output"), "Alpaca 格式缺少 output（答案为空）"
        assert len(first["output"]) > 20, "答案异常简短，可能被截断"


def test_end_to_end_all_mode_reuses_kg(tokenizer):
    """同一条管线再跑 all 模式：验证修复后的 6 生成器列表在完整流程中可用。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.txt")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(SAMPLE_TEXT)

        graph_gen = _make_graph_gen(tmpdir, tokenizer)
        asyncio.run(graph_gen.clear.__wrapped__(graph_gen))
        asyncio.run(
            graph_gen.insert.__wrapped__(
                graph_gen,
                read_config={"input_file": input_path},
                split_config={
                    "chunk_size": 512,
                    "chunk_overlap": 50,
                    "enable_prompt_merging": True,
                    "prompt_merge_size": 2,
                    "enable_batch_requests": False,
                },
            )
        )

        asyncio.run(
            graph_gen.generate.__wrapped__(
                graph_gen,
                partition_config={
                    "method": "ece",
                    "method_params": {
                        "max_units_per_community": 10,
                        "min_units_per_community": 1,
                        "max_tokens_per_community": 10240,
                        "unit_sampling": "random",
                    },
                },
                generate_config={
                    "mode": "all",
                    "data_format": "Alpaca",
                    "enable_batch_requests": False,
                    "enable_prompt_cache": False,
                    "mode_ratios": {
                        "atomic": 25.0,
                        "aggregated": 25.0,
                        "multi_hop": 25.0,
                        "cot": 25.0,
                    },
                },
            )
        )

        qa_data = graph_gen.qa_storage.data
        assert isinstance(qa_data, list) and len(qa_data) >= 1
        for item in qa_data:
            assert item.get("mode") in {
                "atomic", "aggregated", "multi_hop", "cot", "hierarchical", "datog",
            }, f"unexpected mode: {item.get('mode')}"
            assert item.get("instruction"), f"empty instruction in {item.get('mode')}"
            assert item.get("output"), f"empty output in {item.get('mode')}"
