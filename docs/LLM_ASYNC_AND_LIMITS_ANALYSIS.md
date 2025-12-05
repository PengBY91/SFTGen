# 大模型调用异步与并发限制分析报告

## 📋 执行摘要

本报告详细分析了代码库中涉及大模型调用的所有代码，重点关注：
1. **是否为异步请求**
2. **最大请求并发数量是否有限制**

## ✅ 1. 异步请求分析

### 1.1 基础架构：完全异步实现

**所有LLM调用都是异步的**，代码库采用了全面的异步架构：

#### 基础抽象类
```39:44:graphgen/bases/base_llm_client.py
    @abc.abstractmethod
    async def generate_answer(
        self, text: str, history: Optional[List[str]] = None, **extra: Any
    ) -> str:
        """Generate answer from the model."""
        raise NotImplementedError
```

所有核心方法都定义为 `async def`，强制要求异步实现。

#### 具体实现：OpenAI客户端
```148:176:graphgen/models/llm/openai_client.py
    async def generate_answer(
        self,
        text: str,
        history: Optional[List[str]] = None,
        **extra: Any,
    ) -> str:
        kwargs = self._pre_generate(text, history)

        prompt_tokens = 0
        for message in kwargs["messages"]:
            prompt_tokens += len(self.tokenizer.encode(message["content"]))
        estimated_tokens = prompt_tokens + kwargs["max_tokens"]

        if self.request_limit:
            await self.rpm.wait(silent=True)
            await self.tpm.wait(estimated_tokens, silent=True)

        completion = await self.client.chat.completions.create(  # pylint: disable=E1125
            model=self.model_name, **kwargs
        )
        if hasattr(completion, "usage"):
            self.token_usage.append(
                {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }
            )
        return self.filter_think_tags(completion.choices[0].message.content)
```

**关键点**：
- 使用 `AsyncOpenAI` 客户端（第63行）
- 使用 `await` 关键字调用 API（第165行）
- 异步限流等待（第162-163行）

#### 异步上下文管理器支持
```67:87:graphgen/models/llm/openai_client.py
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出，确保客户端正确关闭"""
        await self.aclose()
        return False
    
    async def aclose(self):
        """关闭异步客户端"""
        try:
            if hasattr(self, 'client') and self.client is not None:
                await self.client.close()
        except RuntimeError as e:
            # 忽略"Event loop is closed"错误
            if "Event loop is closed" not in str(e):
                raise
        except Exception:
            # 静默处理其他关闭错误
            pass
```

### 1.2 异步调用链

#### 知识图谱抽取
```44:50:graphgen/operators/build_kg/build_text_kg.py
    results = await run_concurrent(
        kg_builder.extract,
        chunks,
        desc="[2/4]Extracting entities and relationships from chunks",
        unit="chunk",
        progress_bar=progress_bar,
    )
```

#### 实际提取方法
```44:76:graphgen/models/kg_builder/light_rag_kg_builder.py
    async def extract(
        self, chunk: Chunk
    ) -> Tuple[Dict[str, List[dict]], Dict[Tuple[str, str], List[dict]]]:
        """
        Extract entities and relationships from a single chunk using the LLM client.
        Supports caching to avoid re-extraction of identical chunks.
        :param chunk
        :return: (nodes_data, edges_data)
        """
        chunk_id = chunk.id
        content = chunk.content
        
        # Check cache first if enabled
        if self.enable_cache:
            chunk_hash = compute_content_hash(content, prefix="extract-")
            cached_result = await self.cache_storage.get_by_id(chunk_hash)
            if cached_result is not None:
                logger.debug("Cache hit for chunk %s", chunk_id)
                return cached_result["nodes"], cached_result["edges"]

        # step 1: language_detection
        language = detect_main_language(content)

        hint_prompt = KG_EXTRACTION_PROMPT[language]["TEMPLATE"].format(
            **KG_EXTRACTION_PROMPT["FORMAT"], input_text=content
        )

        # step 2: initial glean
        if self.batch_manager:
            final_result = await self.batch_manager.add_request(hint_prompt)
        else:
            final_result = await self.llm_client.generate_answer(hint_prompt)
```

**总结**：整个调用链都是异步的，从顶层的 `run_concurrent` 到底层的 API 调用。

---

## ⚠️ 2. 并发限制分析

### 2.1 并发限制机制存在，但**默认未启用**

#### 2.1.1 `run_concurrent` 函数的并发限制

```83:106:graphgen/utils/run_concurrent.py
async def run_concurrent(
    coro_fn: Callable[[T], Awaitable[R]],
    items: List[T],
    *,
    desc: str = "processing",
    unit: str = "item",
    progress_bar: Optional[Any] = None,
    log_interval: int = 50,  # 默认每 50 个记录一次日志
    desc_callback: Optional[Callable[[int, int, List[R]], str]] = None,  # 新增：动态描述回调 (completed_count, total, results) -> desc
    max_concurrent: Optional[int] = None,  # 新增：最大并发数，None 表示无限制
) -> List[R]:
    import time
    
    # 如果有并发限制，使用 Semaphore 包装 coro_fn
    if max_concurrent is not None and max_concurrent > 0:
        semaphore = asyncio.Semaphore(max_concurrent)
        original_coro_fn = coro_fn
        
        async def limited_coro_fn(item: T) -> R:
            async with semaphore:
                return await original_coro_fn(item)
        
        coro_fn = limited_coro_fn
        logger.debug(f"启用并发限制: max_concurrent={max_concurrent}")
```

**关键发现**：
- ✅ 支持 `max_concurrent` 参数
- ⚠️ **默认值为 `None`（无限制）**
- ✅ 如果设置，会使用 `asyncio.Semaphore` 进行限制

#### 2.1.2 实际调用情况

**所有实际调用中，都没有传入 `max_concurrent` 参数**：

```44:50:graphgen/operators/build_kg/build_text_kg.py
    results = await run_concurrent(
        kg_builder.extract,
        chunks,
        desc="[2/4]Extracting entities and relationships from chunks",
        unit="chunk",
        progress_bar=progress_bar,
    )
```

这意味着**当前所有LLM调用都没有并发数量限制**。

### 2.2 批量请求管理器的并发限制

```24:62:graphgen/utils/batch_request_manager.py
class BatchRequestManager:
    """
    批量请求管理器
    收集多个请求，批量并发处理，减少网络延迟
    """
    
    def __init__(
        self,
        llm_client,
        batch_size: int = 10,
        max_wait_time: float = 0.5,
        enable_batching: bool = True,
        max_concurrent: Optional[int] = None,  # 新增：最大并发数，None 表示无限制
    ):
        """
        初始化批量请求管理器
        
        :param llm_client: LLM客户端实例
        :param batch_size: 每批处理的请求数量
        :param max_wait_time: 最大等待时间（秒），超过此时间即使未达到batch_size也会发送
        :param enable_batching: 是否启用批量处理
        :param max_concurrent: 最大并发请求数，用于限制同时处理的请求数量（适用于 Ollama 等服务）
        """
        self.llm_client = llm_client
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.enable_batching = enable_batching
        self.max_concurrent = max_concurrent
        
        self.request_queue: List[BatchRequest] = []
        self.queue_lock = asyncio.Lock()
        self.batch_task: Optional[asyncio.Task] = None
        self.pending_futures: Dict[int, asyncio.Future] = {}
        self.request_counter = 0
        
        # 如果有并发限制，创建 Semaphore
        self.semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent and max_concurrent > 0 else None
        if self.semaphore:
            logger.debug(f"BatchRequestManager 启用并发限制: max_concurrent={max_concurrent}")
```

**关键发现**：
- ✅ 支持 `max_concurrent` 参数
- ⚠️ **默认值为 `None`（无限制）**

#### 实际创建时的调用

```34:42:graphgen/models/kg_builder/light_rag_kg_builder.py
        self.enable_batch_requests = enable_batch_requests
        self.batch_manager: Optional[BatchRequestManager] = None
        if enable_batch_requests:
            self.batch_manager = BatchRequestManager(
                llm_client=llm_client,
                batch_size=batch_size,
                max_wait_time=max_wait_time,
                enable_batching=True
            )
```

**关键发现**：创建 `BatchRequestManager` 时**没有传入 `max_concurrent` 参数**，意味着使用默认值 `None`（无限制）。

### 2.3 速率限制（RPM/TPM）

虽然并发数量没有限制，但有**速率限制机制**：

#### RPM（每分钟请求数）限制

```8:44:graphgen/models/llm/limitter.py
class RPM:
    def __init__(self, rpm: int = 1000):
        self.rpm = rpm
        self.record = {"rpm_slot": self.get_minute_slot(), "counter": 0}

    @staticmethod
    def get_minute_slot():
        current_time = time.time()
        dt_object = datetime.fromtimestamp(current_time)
        total_minutes_since_midnight = dt_object.hour * 60 + dt_object.minute
        return total_minutes_since_midnight

    async def wait(self, silent=False):
        current = time.time()
        dt_object = datetime.fromtimestamp(current)
        minute_slot = self.get_minute_slot()

        if self.record["rpm_slot"] == minute_slot:
            # check RPM exceed
            if self.record["counter"] >= self.rpm:
                # wait until next minute
                next_minute = dt_object.replace(second=0, microsecond=0) + timedelta(
                    minutes=1
                )
                _next = next_minute.timestamp()
                sleep_time = abs(_next - current)
                if not silent:
                    logger.info("RPM sleep %s", sleep_time)
                await asyncio.sleep(sleep_time)

                self.record = {"rpm_slot": self.get_minute_slot(), "counter": 0}
        else:
            self.record = {"rpm_slot": self.get_minute_slot(), "counter": 0}
        self.record["counter"] += 1

        if not silent:
            logger.debug(self.record)
```

#### TPM（每分钟Token数）限制

```47:86:graphgen/models/llm/limitter.py
class TPM:
    def __init__(self, tpm: int = 20000):
        self.tpm = tpm
        self.record = {"tpm_slot": self.get_minute_slot(), "counter": 0}

    @staticmethod
    def get_minute_slot():
        current_time = time.time()
        dt_object = datetime.fromtimestamp(current_time)
        total_minutes_since_midnight = dt_object.hour * 60 + dt_object.minute
        return total_minutes_since_midnight

    async def wait(self, token_count, silent=False):
        current = time.time()
        dt_object = datetime.fromtimestamp(current)
        minute_slot = self.get_minute_slot()

        # get next slot, skip
        if self.record["tpm_slot"] != minute_slot:
            self.record = {"tpm_slot": minute_slot, "counter": token_count}
            return

        # check RPM exceed
        old_counter = self.record["counter"]
        self.record["counter"] += token_count
        if self.record["counter"] > self.tpm:
            logger.info("Current TPM: %s, limit: %s", old_counter, self.tpm)
            # wait until next minute
            next_minute = dt_object.replace(second=0, microsecond=0) + timedelta(
                minutes=1
            )
            _next = next_minute.timestamp()
            sleep_time = abs(_next - current)
            logger.warning("TPM limit exceeded, wait %s seconds", sleep_time)
            await asyncio.sleep(sleep_time)

            self.record = {"tpm_slot": self.get_minute_slot(), "counter": token_count}

        if not silent:
            logger.debug(self.record)
```

#### 速率限制的使用

```161:163:graphgen/models/llm/openai_client.py
        if self.request_limit:
            await self.rpm.wait(silent=True)
            await self.tpm.wait(estimated_tokens, silent=True)
```

**关键发现**：
- ✅ 有RPM（每分钟请求数）和TPM（每分钟Token数）限制
- ⚠️ **只有当 `request_limit=True` 时才会启用**
- ⚠️ 默认值：RPM=1000，TPM=50000

#### 实际配置

在任务处理器中可以看到：

```68:76:webui/task_processor.py
            synthesizer_llm_client = OpenAIClient(
                model_name=env.get("SYNTHESIZER_MODEL", ""),
                base_url=env.get("SYNTHESIZER_BASE_URL", ""),
                api_key=env.get("SYNTHESIZER_API_KEY", ""),
                request_limit=True,
                rpm=RPM(env.get("RPM", 1000)),
                tpm=TPM(env.get("TPM", 50000)),
                tokenizer=tokenizer_instance,
            )
```

**关键发现**：在某些场景下会设置 `request_limit=True` 并配置RPM/TPM，但这**不是并发数量限制**，而是**速率限制**。

---

## 📊 3. 总结与风险评估

### 3.1 异步请求：✅ 完全异步

**结论**：所有大模型调用都是异步的，包括：
- 基础抽象类使用 `async def`
- 具体实现使用 `AsyncOpenAI` 客户端
- 所有调用使用 `await` 关键字
- 完整的异步调用链

### 3.2 并发限制：⚠️ 默认无限制

#### 当前状态

| 限制类型 | 是否存在 | 是否默认启用 | 默认值 | 实际使用情况 |
|---------|---------|-------------|--------|-------------|
| **并发数量限制** | ✅ 是 | ❌ 否 | `None` (无限制) | 所有调用都未设置 |
| **速率限制 (RPM)** | ✅ 是 | ⚠️ 条件启用 | 1000/分钟 | 需要 `request_limit=True` |
| **速率限制 (TPM)** | ✅ 是 | ⚠️ 条件启用 | 50000/分钟 | 需要 `request_limit=True` |

#### 风险分析

1. **高并发风险**：
   - 如果处理大量 chunks（例如1000+），会同时发起1000+个并发请求
   - 可能导致API服务器过载
   - 可能触发API提供商的限流机制
   - 可能导致本地资源耗尽（内存、连接数）

2. **API限流风险**：
   - 大多数API提供商都有并发限制（例如OpenAI：10-50个并发）
   - 无限制并发可能导致请求被拒绝或返回429错误

3. **资源耗尽风险**：
   - 大量并发连接可能导致：
     - 内存占用过高
     - 文件描述符耗尽
     - 网络连接数耗尽

---

## 🔧 4. 建议与改进方案

### 4.1 立即建议：添加默认并发限制

#### 建议1：为 `run_concurrent` 添加默认并发限制

```python
# 当前代码（无限制）
results = await run_concurrent(
    kg_builder.extract,
    chunks,
    desc="[2/4]Extracting entities",
)

# 建议修改（添加并发限制）
results = await run_concurrent(
    kg_builder.extract,
    chunks,
    desc="[2/4]Extracting entities",
    max_concurrent=50,  # 根据API提供商设置合适的值
)
```

#### 建议2：为 `BatchRequestManager` 添加默认并发限制

```python
# 当前代码（无限制）
self.batch_manager = BatchRequestManager(
    llm_client=llm_client,
    batch_size=batch_size,
    max_wait_time=max_wait_time,
    enable_batching=True
)

# 建议修改（添加并发限制）
self.batch_manager = BatchRequestManager(
    llm_client=llm_client,
    batch_size=batch_size,
    max_wait_time=max_wait_time,
    enable_batching=True,
    max_concurrent=50,  # 根据实际情况设置
)
```

### 4.2 配置化并发限制

建议在配置文件中添加并发限制配置：

```yaml
# 建议配置项
llm_config:
  max_concurrent_requests: 50  # 最大并发请求数
  rpm: 1000  # 每分钟请求数
  tpm: 50000  # 每分钟Token数
```

### 4.3 根据API提供商自动设置

不同API提供商的并发限制不同：

| API提供商 | 典型并发限制 | 建议配置 |
|----------|------------|---------|
| OpenAI (付费账户) | 50-200 | 50 |
| OpenAI (免费账户) | 5-10 | 5 |
| 本地部署 (Ollama) | 1-4 | 2-4 |
| 其他云服务 | 10-50 | 30 |

---

## 📝 5. 代码示例：如何启用并发限制

### 示例1：在知识图谱抽取时启用并发限制

```python
# 在 graphgen/operators/build_kg/build_text_kg.py 中
results = await run_concurrent(
    kg_builder.extract,
    chunks,
    desc="[2/4]Extracting entities and relationships from chunks",
    unit="chunk",
    progress_bar=progress_bar,
    max_concurrent=50,  # 添加此参数
)
```

### 示例2：在批量请求管理器中启用并发限制

```python
# 在 graphgen/models/kg_builder/light_rag_kg_builder.py 中
if enable_batch_requests:
    self.batch_manager = BatchRequestManager(
        llm_client=llm_client,
        batch_size=batch_size,
        max_wait_time=max_wait_time,
        enable_batching=True,
        max_concurrent=50,  # 添加此参数
    )
```

---

## ✅ 6. 结论

### 异步请求
- ✅ **所有LLM调用都是异步的**
- ✅ 使用了完整的异步架构
- ✅ 性能良好

### 并发限制
- ⚠️ **当前默认无并发数量限制**
- ⚠️ **存在高并发风险**
- ✅ 有速率限制机制（RPM/TPM），但需要手动启用
- ✅ 代码已支持并发限制，但未在实际使用中启用

### 建议行动
1. **立即**：在所有 `run_concurrent` 调用中添加 `max_concurrent` 参数
2. **短期**：在配置文件中添加并发限制配置项
3. **中期**：根据API提供商自动设置合适的并发限制
4. **长期**：添加动态并发调整机制，根据API响应时间自动优化

---

**报告生成时间**：2025-01-27
**分析范围**：整个代码库中涉及LLM调用的所有代码

