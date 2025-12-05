# LLM 并发请求优化分析

## 问题描述

当使用本地 LLM 服务（如 Ollama）或并发能力有限的 API 服务时，并发请求可能没有按预期工作。

## 问题分析

### 2. run_concurrent 的并发控制

**文件**: `graphgen/utils/run_concurrent.py`

**当前实现**:
```python
async def run_concurrent(...):
    tasks = [asyncio.create_task(coro_fn(it)) for it in items]  # 创建所有任务
    
    for future in asyncio.as_completed(tasks):  # 等待所有任务完成
        result = await future
        results.append(result)
```

**问题**:
- ✅ 代码会创建所有任务并同时执行（这是正确的）
- ❌ **没有并发限制**：如果有 1000 个任务，会同时创建 1000 个并发请求
- ❌ 对于 Ollama 服务，这可能超过其并发处理能力

**本地 LLM 服务的并发限制**:
- 本地服务（如 Ollama）默认可能只支持少量并发请求（通常 1-4 个，取决于配置）
- 如果同时发送大量请求，服务可能会：
  - 拒绝请求
  - 排队处理（但看起来像串行）
  - 返回错误

### 3. BatchRequestManager 的并发处理

**文件**: `graphgen/utils/batch_request_manager.py`

**当前实现**:
```python
async def _process_batch(self):
    # 取出当前批次
    batch = self.request_queue[:self.batch_size]
    
    # 并发处理批次中的请求
    tasks = []
    for request in batch:
        task = self._process_single_request(request)  # 每个请求独立调用
        tasks.append(task)
    
    # 等待所有请求完成
    await asyncio.gather(*tasks, return_exceptions=True)
```

**问题**:
- ✅ 批次内的请求是并发执行的（这是正确的）
- ❌ **没有全局并发限制**：如果有多个批次，它们会同时执行
- ❌ 每个请求仍然调用 `llm_client.generate_answer()`，如果客户端未实现，请求不会真正执行

## 根本原因

### 问题 1: 缺少并发限制
`run_concurrent` 和 `BatchRequestManager` 之前没有并发限制，可能导致：
- LLM 服务过载
- 请求被拒绝或排队
- 看起来像串行执行（实际上是服务在排队）

### 问题 2: 服务的并发能力限制
不同的 LLM 服务有不同的并发处理能力：
- 本地服务（如 Ollama）通常只支持少量并发请求（1-4 个）
- 云服务（如 OpenAI）支持更高的并发，但仍有限制
- 需要根据服务能力调整并发参数

## 解决方案

### 方案 1: 添加并发限制（已实现）

已为 `run_concurrent` 和 `BatchRequestManager` 添加了 `max_concurrent` 参数，可以限制并发请求数量。

### 方案 2: 使用并发限制参数

修改 `run_concurrent` 以支持并发限制：

```python
async def run_concurrent(
    coro_fn: Callable[[T], Awaitable[R]],
    items: List[T],
    *,
    desc: str = "processing",
    unit: str = "item",
    progress_bar: Optional[Any] = None,
    log_interval: int = 50,
    desc_callback: Optional[Callable[[int, int, List[R]], str]] = None,
    max_concurrent: Optional[int] = None,  # 新增：最大并发数
) -> List[R]:
    import time
    
    # 如果有并发限制，使用 Semaphore
    if max_concurrent is not None and max_concurrent > 0:
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_coro(item):
            async with semaphore:
                return await coro_fn(item)
        
        coro_fn = limited_coro
    
    tasks = [asyncio.create_task(coro_fn(it)) for it in items]
    # ... 其余代码保持不变
```

### 方案 3: 配置 BatchRequestManager 的并发限制

修改 `BatchRequestManager` 以支持全局并发限制：

```python
class BatchRequestManager:
    def __init__(
        self,
        llm_client,
        batch_size: int = 10,
        max_wait_time: float = 0.5,
        enable_batching: bool = True,
        max_concurrent: Optional[int] = None,  # 新增：最大并发数
    ):
        # ... 现有代码 ...
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent else None
    
    async def _process_single_request(self, request: BatchRequest):
        """处理单个请求"""
        try:
            # 如果有并发限制，使用 Semaphore
            if self.semaphore:
                async with self.semaphore:
                    if request.extra_params:
                        result = await self.llm_client.generate_answer(
                            request.prompt,
                            request.history,
                            **request.extra_params
                        )
                    else:
                        result = await self.llm_client.generate_answer(
                            request.prompt,
                            request.history
                        )
            else:
                # 原有逻辑
                if request.extra_params:
                    result = await self.llm_client.generate_answer(
                        request.prompt,
                        request.history,
                        **request.extra_params
                    )
                else:
                    result = await self.llm_client.generate_answer(
                        request.prompt,
                        request.history
                    )
            
            if request.callback:
                request.callback(result)
        except Exception as e:
            # ... 错误处理 ...
```

### 方案 4: 配置本地 LLM 服务

对于本地 LLM 服务（如 Ollama），需要检查并配置服务的并发能力：

1. **设置环境变量**（以 Ollama 为例）:
```bash
export OLLAMA_NUM_PARALLEL=4  # 允许 4 个并发请求
```

2. **检查服务配置**:
查看服务文档，了解支持的并发数量。

3. **监控服务日志**:
查看服务的日志，确认是否收到并发请求。

## 诊断步骤

### 1. 确认 LLM 服务类型

检查代码中使用的 LLM 客户端类型：

```bash
grep -r "OpenAIClient\|BaseLLMClient" --include="*.py"
```

### 2. 检查并发请求数量

在 `run_concurrent` 和 `BatchRequestManager` 中添加日志：

```python
logger.info(f"创建 {len(tasks)} 个并发任务")
logger.info(f"当前活跃任务数: {len([t for t in tasks if not t.done()])}")
```

### 3. 测试 LLM 服务的并发能力

创建测试脚本测试服务的并发处理能力：

```python
import asyncio
import aiohttp
import time

async def test_llm_concurrent(base_url: str, model_name: str, num_requests: int = 10):
    """测试 LLM 服务的并发处理能力"""
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(base_url=base_url, api_key="test")
    
    async def single_request(i):
        start = time.time()
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": f"Say hello {i}"}],
        )
        elapsed = time.time() - start
        print(f"Request {i}: {elapsed:.2f}s")
        return response
    
    # 并发发送请求
    start_time = time.time()
    tasks = [single_request(i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    print(f"\n总时间: {total_time:.2f}s")
    print(f"平均时间: {total_time/num_requests:.2f}s")
    print(f"并发效率: {num_requests/total_time:.2f} req/s")
    
    await client.close()

# 运行测试
asyncio.run(test_llm_concurrent("http://localhost:11434/v1", "llama2", 10))
```

### 4. 检查服务日志

查看 LLM 服务的输出，确认：
- 是否收到并发请求
- 请求是否被排队
- 是否有错误信息

## 配置建议

### 对于本地 LLM 服务（如 Ollama）

建议设置较小的并发限制：

```python
# 在调用 run_concurrent 时
results = await run_concurrent(
    kg_builder.extract,
    chunks,
    desc="Extracting entities",
    max_concurrent=4,  # 本地服务通常支持 1-4 个并发
)

# 在创建 BatchRequestManager 时
batch_manager = BatchRequestManager(
    llm_client=llm_client,
    batch_size=4,  # 较小的批次大小
    max_wait_time=1.0,
    max_concurrent=4,  # 全局并发限制
)
```

### 对于云服务（如 OpenAI API）

可以设置更大的并发限制或保持 `None`（无限制）：

```python
results = await run_concurrent(
    kg_builder.extract,
    chunks,
    max_concurrent=50,  # 云服务支持更高并发
)
```

