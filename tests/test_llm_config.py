"""LLM/API 配置加载测试。"""

import os

from graphgen.configs.llm_config import (
    LLMClientConfig,
    apply_apis_to_environ,
    expand_env_vars,
    load_llm_config,
)


class TestExpandEnvVars:
    def test_basic_expansion(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_X", "abc")
        assert expand_env_vars("${TEST_KEY_X}") == "abc"
        assert expand_env_vars("prefix-${TEST_KEY_X}-suffix") == "prefix-abc-suffix"

    def test_default_value(self, monkeypatch):
        monkeypatch.delenv("TEST_MISSING_VAR", raising=False)
        assert expand_env_vars("${TEST_MISSING_VAR:-fallback}") == "fallback"
        assert expand_env_vars("${TEST_MISSING_VAR}") == ""

    def test_recursive(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_Y", "v")
        assert expand_env_vars({"a": "${TEST_KEY_Y}", "b": ["${TEST_KEY_Y}", 1]}) == {
            "a": "v",
            "b": ["v", 1],
        }


class TestLoadLLMConfig:
    def test_yaml_overrides_env(self, monkeypatch):
        monkeypatch.setenv("SYNTHESIZER_MODEL", "env-model")
        cfg = load_llm_config(
            {"llm": {"synthesizer": {"model": "yaml-model", "api_key": "k"}}},
            load_env_file=False,
        )
        assert cfg.synthesizer.model == "yaml-model"

    def test_env_fallback_when_yaml_missing(self, monkeypatch):
        monkeypatch.setenv("SYNTHESIZER_MODEL", "env-model")
        monkeypatch.setenv("SYNTHESIZER_BASE_URL", "https://env.example/v1")
        monkeypatch.setenv("SYNTHESIZER_API_KEY", "env-key")
        cfg = load_llm_config({"llm": {"synthesizer": {}}}, load_env_file=False)
        assert cfg.synthesizer.model == "env-model"
        assert cfg.synthesizer.base_url == "https://env.example/v1"
        assert cfg.synthesizer.api_key == "env-key"

    def test_no_llm_section_full_env_fallback(self, monkeypatch):
        monkeypatch.setenv("SYNTHESIZER_MODEL", "m")
        monkeypatch.setenv("SYNTHESIZER_BASE_URL", "u")
        monkeypatch.setenv("SYNTHESIZER_API_KEY", "k")
        cfg = load_llm_config({}, load_env_file=False)
        assert cfg.synthesizer.model == "m"

    def test_env_var_reference_in_yaml(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET_KEY", "sk-test")
        cfg = load_llm_config(
            {"llm": {"synthesizer": {"api_key": "${MY_SECRET_KEY}"}}},
            load_env_file=False,
        )
        assert cfg.synthesizer.api_key == "sk-test"

    def test_trainee_disabled(self):
        cfg = load_llm_config(
            {"llm": {"trainee": {"enabled": False}}}, load_env_file=False
        )
        assert cfg.trainee.enabled is False

    def test_int_fields_coerced(self):
        cfg = load_llm_config(
            {"llm": {"synthesizer": {"rpm": "2000", "tpm": "99999", "temperature": "0.7"}}},
            load_env_file=False,
        )
        assert cfg.synthesizer.rpm == 2000
        assert cfg.synthesizer.tpm == 99999
        assert cfg.synthesizer.temperature == 0.7

    def test_redacted_hides_key(self):
        c = LLMClientConfig(api_key="sk-1234567890abcd")
        r = c.redacted()
        assert "1234567890" not in r["api_key"]
        assert r["api_key"].startswith("sk-1")


class TestApplyApis:
    def test_writes_env(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
        applied = apply_apis_to_environ(
            {"google_search": {"api_key": "g-key", "cx": "g-cx"}}
        )
        assert os.environ.get("GOOGLE_SEARCH_API_KEY") == "g-key"
        assert os.environ.get("GOOGLE_SEARCH_CX") == "g-cx"
        assert "GOOGLE_SEARCH_API_KEY" in applied

    def test_does_not_overwrite_existing(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "existing")
        apply_apis_to_environ({"google_search": {"api_key": "new"}})
        assert os.environ["GOOGLE_SEARCH_API_KEY"] == "existing"


class TestThinkingDisabledByDefault:
    """默认关闭混合推理模型的思考——所有客户端构造路径必须生效。"""

    def test_defaults_contain_thinking_disabled(self):
        from graphgen.configs.llm_config import default_request_params

        assert default_request_params() == {"thinking": {"type": "disabled"}}

    def test_resolution_without_yaml_uses_default(self, monkeypatch):
        monkeypatch.setenv("SYNTHESIZER_MODEL", "m")
        monkeypatch.setenv("SYNTHESIZER_BASE_URL", "u")
        monkeypatch.setenv("SYNTHESIZER_API_KEY", "k")
        cfg = load_llm_config({}, load_env_file=False)
        assert cfg.synthesizer.request_params == {"thinking": {"type": "disabled"}}
        assert cfg.trainee.request_params == {"thinking": {"type": "disabled"}}

    def test_yaml_can_reenable(self):
        cfg = load_llm_config(
            {"llm": {"synthesizer": {"request_params": {"thinking": {"type": "enabled"}}}}},
            load_env_file=False,
        )
        assert cfg.synthesizer.request_params == {"thinking": {"type": "enabled"}}

    def test_openai_client_carries_params_in_extra_body(self):
        from graphgen.models.llm.openai_client import OpenAIClient

        client = OpenAIClient(
            model_name="m",
            api_key="k",
            extra_request_params={"thinking": {"type": "disabled"}},
        )
        kwargs = client._pre_generate("hello", None)
        assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}

    def test_graphgen_fallback_clients_carry_params(self):
        import asyncio
        import tempfile

        from graphgen.graphgen import GraphGen

        with tempfile.TemporaryDirectory() as tmp:
            gg = GraphGen(working_dir=tmp)
            try:
                assert gg.synthesizer_llm_client.extra_request_params == {
                    "thinking": {"type": "disabled"}
                }
                assert gg.trainee_llm_client.extra_request_params == {
                    "thinking": {"type": "disabled"}
                }
            finally:
                asyncio.run(gg.clear.__wrapped__(gg))
