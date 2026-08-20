"""LLM / API 统一配置加载。

支持在管线 YAML 配置文件中直接设置 LLM 与其他 API：

.. code-block:: yaml

    llm:
      synthesizer:
        model: deepseek-chat
        base_url: https://api.huiyan-ai.cn/v1
        api_key: ${SYNTHESIZER_API_KEY}   # ${ENV_VAR} 引用，密钥不必写进配置文件
        rpm: 1000
        tpm: 50000
        temperature: 0.0
        max_tokens: 4096
      trainee:
        enabled: false                     # 不启用时不创建 client
        model: ${TRAINEE_MODEL}
        base_url: ${TRAINEE_BASE_URL}
        api_key: ${TRAINEE_API_KEY}
      tokenizer:
        model: cl100k_base
    apis:                                  # 其他 API（写入 os.environ，供搜索等模块使用）
      google_search:
        api_key: ${GOOGLE_SEARCH_API_KEY}
        cx: ${GOOGLE_SEARCH_CX}

取值优先级：YAML 配置 > 环境变量（.env）> 内置默认值。
未配置 llm 段时，行为与旧版本完全一致（全部从环境变量读取）。
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from dotenv import load_dotenv

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

# 各字段的默认值（api_key 无内置默认值，必须通过 YAML / 环境变量 / 命令行提供）
# 注意：deepseek-v4-flash 是混合推理模型。若不关闭思考，它会在抽取/生成类
# 结构化任务上长时间推理（实测 8192 token 上限内都不产出 content，管线拿到的
# 全是空响应）。故默认通过 request_params 关闭思考（经 extra_body 透传）。
# 如需开启推理，在 YAML 的 llm.synthesizer.request_params 配置
# {"thinking": {"type": "enabled"}} 或 {"reasoning_effort": "low"}。
_DEFAULTS = {
    "synthesizer": {
        "model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com",
        "api_key": "",
        "rpm": 1000,
        "tpm": 50000,
        "temperature": 0.0,
        "max_tokens": 4096,
        "top_p": 0.95,
        "request_params": {"thinking": {"type": "disabled"}},
    },
    "trainee": {
        "model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com",
        "api_key": "",
        "rpm": 1000,
        "tpm": 50000,
        "temperature": 0.0,
        "max_tokens": 4096,
        "top_p": 0.95,
        "request_params": {"thinking": {"type": "disabled"}},
    },
    "tokenizer": {"model": "cl100k_base"},
}

# YAML 字段 -> 环境变量 的映射（YAML 未配置时从环境变量取）
_ENV_FALLBACK = {
    "synthesizer": {
        "model": "SYNTHESIZER_MODEL",
        "base_url": "SYNTHESIZER_BASE_URL",
        "api_key": "SYNTHESIZER_API_KEY",
        "rpm": "RPM",
        "tpm": "TPM",
    },
    "trainee": {
        "model": "TRAINEE_MODEL",
        "base_url": "TRAINEE_BASE_URL",
        "api_key": "TRAINEE_API_KEY",
        "rpm": "RPM",
        "tpm": "TPM",
    },
    "tokenizer": {"model": "TOKENIZER_MODEL"},
}

# apis 段的 YAML 键 -> os.environ 键 的映射
_APIS_ENV_KEYS = {
    "google_search": {
        "api_key": "GOOGLE_SEARCH_API_KEY",
        "cx": "GOOGLE_SEARCH_CX",
    },
    "bing_search": {"api_key": "BING_SEARCH_API_KEY"},
    "wikipedia": {"api_key": "WIKIPEDIA_API_KEY"},
    "uniprot": {"api_key": "UNIPROT_API_KEY"},
}


def default_request_params() -> Dict[str, Any]:
    """服务端默认的附加请求参数（默认关闭混合推理模型的思考）。

    供直接构造 OpenAIClient 的入口（GraphGen 兜底、webui 等）使用，
    保证"默认关闭思考"在所有路径生效。
    """
    return dict(_DEFAULTS["synthesizer"].get("request_params") or {})


def expand_env_vars(value: Any) -> Any:
    """递归展开字符串中的 ${VAR} / ${VAR:-default} 引用。

    未定义且无默认值的环境变量展开为空字符串。
    """
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            var, default = match.group(1), match.group(2)
            env_value = os.environ.get(var)
            if env_value is not None and env_value != "":
                return env_value
            return default if default is not None else ""

        return _ENV_VAR_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env_vars(v) for v in value]
    return value


@dataclass
class LLMClientConfig:
    """单个 LLM 客户端的连接与采样配置。"""

    model: str = ""
    base_url: str = ""
    api_key: str = ""
    rpm: int = 1000
    tpm: int = 50000
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 0.95
    enabled: bool = True
    # 附加到每次请求的提供商特有参数（如 DeepSeek 的 reasoning_effort）
    request_params: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self) -> bool:
        return bool(self.model and self.base_url and self.api_key)

    def redacted(self) -> Dict[str, Any]:
        """返回脱敏形式（api_key 只保留首尾各 4 字符），用于日志/展示。"""
        key = self.api_key or ""
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ("***" if key else "")
        return {
            "model": self.model,
            "base_url": self.base_url,
            "api_key": masked,
            "rpm": self.rpm,
            "tpm": self.tpm,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "enabled": self.enabled,
        }


@dataclass
class LLMConfig:
    """管线 YAML 中 llm 段解析后的完整配置。"""

    synthesizer: LLMClientConfig = field(default_factory=LLMClientConfig)
    trainee: LLMClientConfig = field(default_factory=LLMClientConfig)
    tokenizer_model: str = "cl100k_base"
    apis: Dict[str, Dict[str, str]] = field(default_factory=dict)


def _coerce_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _resolve_client_section(
    section: str,
    yaml_section: Optional[dict],
) -> LLMClientConfig:
    """按 YAML > 环境变量 > 默认值 的优先级解析一个客户端配置段。"""
    yaml_section = yaml_section or {}
    defaults = _DEFAULTS[section]
    env_map = _ENV_FALLBACK[section]

    def _get(key: str, cast=str, default=None):
        # 1) YAML 显式配置
        if key in yaml_section and yaml_section[key] is not None:
            raw = expand_env_vars(yaml_section[key])
            if raw == "" and key == "api_key":
                pass  # 空引用视为未配置，继续回退
            else:
                return raw
        # 2) 环境变量
        env_key = env_map.get(key)
        if env_key and os.environ.get(env_key):
            return os.environ[env_key]
        # 3) 默认值
        return default if default is not None else defaults.get(key)

    enabled = yaml_section.get("enabled", True)
    request_params = expand_env_vars(yaml_section.get("request_params"))
    if not isinstance(request_params, dict) or not request_params:
        # YAML 未配置时使用默认值（如关闭混合推理模型的思考）
        request_params = dict(defaults.get("request_params") or {})
    return LLMClientConfig(
        model=str(_get("model") or ""),
        base_url=str(_get("base_url") or ""),
        api_key=str(_get("api_key") or ""),
        rpm=_coerce_int(_get("rpm"), defaults["rpm"]),
        tpm=_coerce_int(_get("tpm"), defaults["tpm"]),
        temperature=_coerce_float(_get("temperature"), defaults["temperature"]),
        max_tokens=_coerce_int(_get("max_tokens"), defaults["max_tokens"]),
        top_p=_coerce_float(_get("top_p"), defaults["top_p"]),
        enabled=bool(enabled),
        request_params=request_params,
    )


def load_llm_config(config: Optional[dict] = None, load_env_file: bool = True) -> LLMConfig:
    """从管线配置字典解析 LLM/API 配置。

    :param config: 完整管线 YAML 解析后的 dict（取其中的 llm / apis 段），可为 None
    :param load_env_file: 是否先加载 .env（默认加载）
    """
    if load_env_file:
        load_dotenv(override=False)

    config = config or {}
    llm_section = config.get("llm") or {}
    apis_section = expand_env_vars(config.get("apis") or {})

    cfg = LLMConfig(
        synthesizer=_resolve_client_section("synthesizer", llm_section.get("synthesizer")),
        trainee=_resolve_client_section("trainee", llm_section.get("trainee")),
        tokenizer_model=str(
            expand_env_vars((llm_section.get("tokenizer") or {}).get("model"))
            or os.environ.get("TOKENIZER_MODEL")
            or _DEFAULTS["tokenizer"]["model"]
        ),
        apis=apis_section,
    )
    return cfg


def apply_apis_to_environ(apis: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """把 YAML apis 段的值写入 os.environ（不覆盖已有值），供搜索等按环境变量读取的模块使用。

    :return: 实际写入的 {环境变量名: 值}
    """
    applied: Dict[str, str] = {}
    for api_name, fields in apis.items():
        env_map = _APIS_ENV_KEYS.get(api_name)
        if not env_map:
            continue
        for field_name, env_key in env_map.items():
            value = (fields or {}).get(field_name)
            if value and not os.environ.get(env_key):
                os.environ[env_key] = value
                applied[env_key] = value
    return applied


def build_llm_clients(llm_config: LLMConfig):
    """根据 LLMConfig 构建 (tokenizer_instance, synthesizer_client, trainee_client)。

    trainee 未启用（enabled=false）或未配置完整时返回 None。
    """
    from graphgen.models import OpenAIClient, Tokenizer
    from graphgen.models.llm.limitter import RPM, TPM

    synth = llm_config.synthesizer
    if not synth.is_ready():
        raise ValueError(
            "Synthesizer LLM 配置不完整（model / base_url / api_key 存在空值）。"
            "请在管线 YAML 的 llm.synthesizer 段、.env 环境变量（SYNTHESIZER_*）"
            "或命令行参数中配置。"
        )

    tokenizer_instance = Tokenizer(llm_config.tokenizer_model)
    synthesizer_client = OpenAIClient(
        model_name=synth.model,
        base_url=synth.base_url,
        api_key=synth.api_key,
        temperature=synth.temperature,
        max_tokens=synth.max_tokens,
        top_p=synth.top_p,
        request_limit=True,
        rpm=RPM(synth.rpm),
        tpm=TPM(synth.tpm),
        tokenizer=tokenizer_instance,
        extra_request_params=synth.request_params,
    )

    trainee_client = None
    if llm_config.trainee.enabled and llm_config.trainee.is_ready():
        tr = llm_config.trainee
        trainee_client = OpenAIClient(
            model_name=tr.model,
            base_url=tr.base_url,
            api_key=tr.api_key,
            temperature=tr.temperature,
            max_tokens=tr.max_tokens,
            top_p=tr.top_p,
            request_limit=True,
            rpm=RPM(tr.rpm),
            tpm=TPM(tr.tpm),
            tokenizer=tokenizer_instance,
            extra_request_params=tr.request_params,
        )

    return tokenizer_instance, synthesizer_client, trainee_client
