# Configs for GraphGen

## 管线配置

每个 YAML 文件定义一条完整管线的配置(read / split / search / quiz_and_judge / partition / generate)。

用法:

```bash
python -m graphgen.generate --config_file graphgen/configs/aggregated_config.yaml --output_dir ./out
```

## LLM 与其他 API 配置

配置文件顶部支持可选的 `llm` 与 `apis` 段,直接在 YAML 中设置模型与 API:

```yaml
llm:
  synthesizer:
    model: deepseek-chat            # 任意 OpenAI 兼容模型
    base_url: https://api.huiyan-ai.cn/v1
    api_key: ${SYNTHESIZER_API_KEY} # ${VAR} 引用环境变量,密钥不必写进文件
    rpm: 1000
    tpm: 50000
    temperature: 0.0
    max_tokens: 4096
  trainee:
    enabled: false                  # quiz_and_judge 评估用
    model: ${TRAINEE_MODEL}
    base_url: ${TRAINEE_BASE_URL}
    api_key: ${TRAINEE_API_KEY}
  tokenizer:
    model: cl100k_base

apis:                               # 搜索等其他 API(写入对应环境变量)
  google_search:
    api_key: ${GOOGLE_SEARCH_API_KEY}
    cx: ${GOOGLE_SEARCH_CX}
```

取值优先级: **命令行参数 > YAML 配置 > 环境变量(.env) > 内置默认值**。

未配置 `llm` 段时行为与旧版一致(全部从环境变量读取),因此旧配置文件无需修改。

graphgen_cli.py 也可通过 `-c/--config` 使用同一机制:

```bash
python graphgen_cli.py -i input.txt -c graphgen/configs/aggregated_config.yaml
```

相关实现: `graphgen/configs/llm_config.py`
