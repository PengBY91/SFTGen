# CLAUDE.md

本文件为 Claude Code 在本仓库工作时的指引。

## 项目概览

KGE-Gen（仓库目录名 SFTGen）：知识图谱引导的 LLM 训练数据（SFT）合成平台。核心流程：文档 → 知识图谱构建（LLM 抽取实体/关系）→（可选）Trainee 模型理解评估 → 图分区 → 多模式 QA 生成。另含独立的 DA-ToG 管线（意图树 + 图适配器 + 评审器三层结构，控制意图覆盖度）。前后端分离：FastAPI 后端 + Vue 3 前端 + Gradio WebUI + 多个 CLI。

## 常用命令

```bash
# 环境（start.sh 期望 conda 环境名为 graphgen；也可 pip install -r requirements.txt）
conda activate graphgen

# 主 CLI（单文件 / 批量 / DA-ToG）
python graphgen_cli.py -i input.txt -k $API_KEY
python graphgen_cli.py -i input.txt -c graphgen/configs/aggregated_config.yaml

# 管线配置文件方式（read/split/quiz_and_judge/partition/generate 全在 YAML 中）
python -m graphgen.generate --config_file graphgen/configs/aggregated_config.yaml --output_dir ./out

# 评测数据生成 / DA-ToG 指标
python graphgen_eval_cli.py --config_file graphgen/configs/evaluation_config.yaml --output_dir ./eval_out

# 测试（pytest，多数 mock 了 LLM，无需真实 API）
pytest tests/ -v
pytest tests/test_e2e_mock.py -v   # 端到端冒烟

# Web 服务（后端 8000 / Gradio 7860 / 前端 3000；默认账号 admin / admin123）
./start.sh start|stop|restart|status
uvicorn backend.app:app --host 0.0.0.0 --port 8000   # 手动起后端
cd frontend && npm run dev                            # 手动起前端

# 格式化（black + isort，行宽 88，见 pyproject.toml）
black <paths> && isort <paths>
```

## 架构与关键路径

- 核心类 `GraphGen`：`graphgen/graphgen.py`。方法对应流程步骤：`insert()`（读取/分块/抽取入图）→ `search()`（可选外部搜索）→ `quiz_and_judge()`（可选 Trainee 评估）→ `generate()`（分区 + QA 生成）→ `clear()`
- 操作符：`graphgen/operators/`（read / split / build_kg / quiz.py / judge.py / partition / generate）
- 生成器：`graphgen/models/generator/`（atomic / aggregated / multi_hop / cot / tree 即 hierarchical / datog），在 `operators/generate/generate_qas.py` 按 `generate.mode` 注册分发
- 分区器：`graphgen/models/partitioner/`（ece / bfs / dfs / anchor_bfs / leiden / hierarchical），在 `operators/partition/partition_kg.py` 注册
- DA-ToG：`graphgen/datog_pipeline.py` 编排；意图树 `models/taxonomy/`、图适配 `models/graph_adapter/`、评审 `models/critic/`；配置模板 `graphgen/configs/datog_config.yaml`，领域示例 `graphgen/configs/datog/{cybersecurity,finance}/`
- 后端：`backend/app.py`（FastAPI 入口，路由前缀 `/api`）、`backend/core/task_processor.py`（Web 任务执行）、`backend/api/endpoints.py` 与 `endpoints_datog.py`
- 存储：`graphgen/models/storage/`（NetworkXStorage 图、JsonKVStorage、JsonListStorage）；Web 任务数据在 `tasks/`，运行中间产物在 `cache/`
- 提示模板：`graphgen/templates/`（kg 抽取 + 各生成模式，多为中英双语）

## 配置解析机制

LLM/API 配置优先级：**命令行参数 > 管线 YAML 的 `llm`/`apis` 段 > 环境变量（.env）> 内置默认值**。实现：`graphgen/configs/llm_config.py`（YAML 中支持 `${VAR}` / `${VAR:-default}` 引用环境变量；`load_llm_config()` / `build_llm_clients()` / `apply_apis_to_environ()`）。`graphgen_cli.py::_resolve_model_args` 会把解析结果写回 `os.environ`，`run_datog` 等按环境变量读取的路径依赖这一行为。

## 代码风格与惯例

- black（行宽 88）+ isort（black profile），配置在 `pyproject.toml`
- 代码注释、日志、文档以**中文**为主，新代码保持一致
- 异步优先：核心流程大量使用 `async/await` 与 `asyncio.gather` 并发调用 LLM
- LLM 调用一律走 `BaseLLMClient` 子类（`OpenAIClient`），带 RPM/TPM 限流与 token 统计；批量优化通过 `BatchLLMWrapper` / `batch_request_manager`

## 注意事项

- 核心类名是 `GraphGen`（`graphgen/graphgen.py`），项目名才是 KGE-Gen——别在代码里写 `KGE-Gen` 类名
- `graphgen/configs/llm_config.py` 的 `_DEFAULTS` **不含**内置 API key：无任何配置时 `build_llm_clients()` 会抛 ValueError；引导用户显式配置自己的 key（`.env` 或 YAML `llm` 段），不要往代码里写死 key
- DA-ToG CLI：`--datog-config` 必须搭配 `--datog-input`（从文档建图谱）或 `--datog-kg`（加载已有图谱）之一，校验和分派在 `graphgen_cli.py::main()`；`run_datog` 从 `os.environ` 读 LLM 配置（由 `_resolve_model_args` 写回）
- `GraphGen` 的 `insert/search/quiz_and_judge/generate` 是 `@async_to_sync_method` 包装过的，直接同步调用即可，不要 `asyncio.run`
- LLM 返回的格式化文本（自定义 `<|>` 分隔的实体/关系格式）解析在 `graphgen/operators/build_kg/` 与 `graphgen/utils/llm_response_repair.py`，改动提示模板时需同步检查解析与修复逻辑
- 默认模型 deepseek-v4-flash 是混合推理模型，默认经 `request_params` 关闭思考（`{"thinking": {"type": "disabled"}}`），否则结构化任务拿到的全是空响应；详见 `llm_config.py` `_DEFAULTS` 注释
- 新增生成模式/分区方法时，记得同时注册到 `generate_qas.py` / `partition_kg.py` 并在 `graphgen/models/__init__.py` 导出；相关回归测试放 `tests/`
- `requirements.txt` 中 gradio 默认被注释（environment.yml 里才有）；WebUI 相关测试需自行安装 gradio
