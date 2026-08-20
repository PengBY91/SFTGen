"""生成路径冒烟测试。

覆盖历史上出过回归的关键点：
1. generate_qas 的单模式与 "all" 模式分支（曾因未定义变量/错误 kwarg 崩溃）
2. 两阶段 atomic 的模板占位符（曾因 {hierarchical_context} KeyError 导致答案全空）
3. 各 generator 构造签名与 generate_qas 实际传参的一致性
"""

import asyncio

import pytest

from graphgen.models import (
    AggregatedGenerator,
    AtomicGenerator,
    AtomicQuestionGenerator,
    CoTGenerator,
    DAToGGenerator,
    MultiHopGenerator,
    TreeStructureGenerator,
)
from graphgen.operators.generate.generate_qas import generate_qas
from graphgen.templates import ATOMIC_ANSWER_PROMPT, ATOMIC_QUESTION_PROMPT


class MockLLMClient:
    """最小 LLM mock：返回可被各 generator 解析的 QA 响应。"""

    def __init__(self):
        self.calls = 0
        # BatchLLMWrapper 会复制这些实例属性
        self.system_prompt = ""
        self.temperature = 0.0
        self.max_tokens = 4096
        self.repetition_penalty = 1.0
        self.top_p = 0.95
        self.top_k = 50
        self.tokenizer = None
        self.token_usage = []

    async def generate_answer(self, prompt: str, history=None, **extra):
        self.calls += 1
        return "Question: What is X?\n\nAnswer: X is a concept described in the context."


BATCHES = [
    (
        [("X", {"description": "X is a concept", "entity_type": "concept"})],
        [("X", "Y", {"description": "X relates to Y", "relation_type": "related_to"})],
    )
]


def _base_config(mode):
    return {
        "mode": mode,
        "data_format": "Alpaca",
        "hierarchical_relations": ["is_a", "subclass_of", "part_of"],
    }


class TestGeneratorConstructors:
    """generate_qas 两个分支对各 generator 的构造方式必须与签名一致。"""

    def test_construct_all_generators_as_in_all_mode(self):
        client = MockLLMClient()
        hr = ["is_a"]
        generators = [
            AtomicGenerator(
                client,
                use_multi_template=True,
                template_seed=None,
                chinese_only=False,
                hierarchical_relations=hr,
            ),
            AggregatedGenerator(
                client, use_combined_mode=True, chinese_only=False, hierarchical_relations=hr
            ),
            MultiHopGenerator(client, chinese_only=False),
            CoTGenerator(
                client, use_combined_mode=True, chinese_only=False, hierarchical_relations=hr
            ),
            TreeStructureGenerator(
                client, structure_format="markdown", hierarchical_relations=hr, chinese_only=False
            ),
            DAToGGenerator(client, data_format="Alpaca", default_dimension="concept_explanation"),
        ]
        assert len(generators) == 6

    def test_atomic_question_generator_build_prompt(self):
        """两阶段 atomic 问题阶段：模板占位符必须能被 build_prompt 填满。"""
        gen = AtomicQuestionGenerator(MockLLMClient(), hierarchical_relations=["is_a"])
        prompt = gen.build_prompt(BATCHES[0])
        assert "X is a concept" in prompt
        assert "{" not in prompt.replace("{{", ""), "unfilled placeholder remains"


class TestAtomicTemplates:
    """两阶段 atomic 的模板占位符与调用方传参必须一致。"""

    @pytest.mark.parametrize("lang", ["en", "zh"])
    def test_question_templates_fillable(self, lang):
        template = ATOMIC_QUESTION_PROMPT[lang]
        prompt = template.format(context="ctx", hierarchical_context="")
        assert "{" not in prompt

    @pytest.mark.parametrize("lang", ["en", "zh"])
    def test_answer_templates_fillable(self, lang):
        template = ATOMIC_ANSWER_PROMPT[lang]
        prompt = template.format(context="ctx", question="q", hierarchical_context="")
        assert "{" not in prompt


class TestQuestionCleanup:
    """问题元前导语清洗（真实运行中观察到 LLM 输出泄漏前导语）。"""

    def test_clean_question_preamble(self):
        from graphgen.operators.generate.generate_qas import _clean_question_text

        cases = [
            (
                "根据答案内容，可以生成如下问题：\n\n**问题：**\n圣丰家庭农场位于哪个村庄？",
                "圣丰家庭农场位于哪个村庄？",
            ),
            ("问题：云粳26号是什么品种？", "云粳26号是什么品种？"),
            ("Question: What is X?", "What is X?"),
            ("以下是生成的问题：水稻的种植范围？", "水稻的种植范围？"),
            ("直接的问题不应该被修改", "直接的问题不应该被修改"),
        ]
        for raw, expected in cases:
            assert _clean_question_text(raw) == expected, f"raw={raw!r}"

    def test_clean_formatted_items(self):
        from graphgen.operators.generate.generate_qas import _clean_formatted_questions

        items = [
            {"instruction": "根据答案内容，可以生成如下问题：\n\n**问题：**\n实际的问题？", "output": "答案"},
            {"conversations": [{"from": "human", "value": "问题：多跳问题？"}, {"from": "gpt", "value": "答"}]},
        ]
        cleaned = _clean_formatted_questions(items)
        assert cleaned[0]["instruction"] == "实际的问题？"
        assert cleaned[1]["conversations"][0]["value"] == "多跳问题？"


class TestGenerateQasModes:
    """generate_qas 端到端（mock LLM）：修复前 single/all 模式会崩溃。"""

    def test_single_mode_aggregated(self):
        client = MockLLMClient()
        results = asyncio.run(
            generate_qas(client, BATCHES, _base_config("aggregated"))
        )
        assert isinstance(results, list)

    def test_single_mode_atomic_question_first(self):
        """backend 默认 question_first=True 的 atomic 两阶段路径。"""
        client = MockLLMClient()
        config = _base_config("atomic")
        config["question_first"] = True
        results = asyncio.run(generate_qas(client, BATCHES, config))
        assert isinstance(results, list)

    def test_single_mode_hierarchical(self):
        client = MockLLMClient()
        results = asyncio.run(
            generate_qas(client, BATCHES, _base_config("hierarchical"))
        )
        assert isinstance(results, list)

    def test_all_mode(self):
        client = MockLLMClient()
        config = _base_config("all")
        config["enable_batch_requests"] = False
        config["enable_prompt_cache"] = False
        results = asyncio.run(generate_qas(client, BATCHES, config))
        assert isinstance(results, list)
