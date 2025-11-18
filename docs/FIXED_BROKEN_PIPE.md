# 修复 Broken Pipe 错误

## 问题描述

启动任务时出现错误：`[Errno 32] Broken pipe`

## 原因分析

### 原始问题

系统使用 FastAPI 的 `BackgroundTasks` 来处理长时间运行的任务。当任务处理时间较长时，可能出现以下问题：

1. **客户端提前断开**：前端请求在任务完成后超时断开
2. **管道断裂**：`BackgroundTasks` 依赖 HTTP 请求连接，断开后导致 Broken pipe 错误
3. **任务状态丢失**：连接断开可能导致任务状态无法正确更新

### 错误场景

```
前端发送请求 → 后端接收请求 → 启动 BackgroundTask → 返回响应
                                            ↓
                                   长时间处理任务
                                            ↓
                                客户端断开连接 ← Broken Pipe
```

## 解决方案

### 使用独立线程替代 BackgroundTasks

将任务执行从 `BackgroundTasks` 迁移到独立的 `threading.Thread`：

#### 1. 修改任务服务 (`backend/services/task_service.py`)

**之前**：
```python
def start_task(self, task_id: str, config: TaskConfig, 
               background_tasks: BackgroundTasks):
    # ...
    background_tasks.add_task(self.task_processor.process_task, task_id, config)
    # ...
```

**之后**：
```python
def start_task(self, task_id: str, config: TaskConfig):
    # ...
    thread = threading.Thread(
        target=self._run_task_in_thread,
        args=(task_id, config),
        daemon=True
    )
    thread.start()
    # ...

def _run_task_in_thread(self, task_id: str, config: TaskConfig):
    """在线程中运行任务"""
    try:
        self.task_processor.process_task(task_id, config)
    except Exception as e:
        print(f"任务处理异常: {e}")
        task_manager.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error_message=str(e)
        )
```

#### 2. 更新 API 端点 (`backend/api/endpoints.py`)

移除 `BackgroundTasks` 依赖：

**之前**：
```python
from fastapi import APIRouter, ..., BackgroundTasks

@router.post("/tasks/{task_id}/start")
async def start_task(task_id: str, config: TaskConfig,
                     background_tasks: BackgroundTasks):
    result = task_service.start_task(task_id, config, background_tasks)
    return result
```

**之后**：
```python
from fastapi import APIRouter, ...

@router.post("/tasks/{task_id}/start")
async def start_task(task_id: str, config: TaskConfig):
    result = task_service.start_task(task_id, config)
    return result
```

## 优势

### 1. 解耦连接

- 任务在线程中独立运行
- 不依赖 HTTP 请求连接
- 支持任务长时间运行

### 2. 错误处理

- 在线程内部捕获异常
- 正确更新任务状态
- 避免任务静默失败

### 3. 可扩展性

- 易于添加任务队列
- 支持任务调度
- 便于监控和调试

## 测试验证

1. **启动任务**
   - 创建任务
   - 点击"启动任务"
   - 不应出现 Broken pipe 错误

2. **任务状态**
   - 任务状态正确更新
   - 处理中 → 已完成/失败

3. **长时间任务**
   - 测试耗时较长的任务
   - 验证不会因为连接超时而失败

## 相关文件

- `backend/services/task_service.py` - 任务服务
- `backend/api/endpoints.py` - API 端点
- `backend/core/task_processor.py` - 任务处理器

## 注意事项

1. **线程安全**：确保任务管理器线程安全
2. **资源清理**：daemon 线程会在主程序退出时自动终止
3. **错误处理**：捕获并记录所有异常
4. **日志记录**：记录任务执行的详细信息

---

**修复日期**: 2025-10-27  
**版本**: v2.0.0
