import asyncio
from typing import Awaitable, Callable, List, Optional, TypeVar, Any

from tqdm.asyncio import tqdm as tqdm_async

from .log import logger

T = TypeVar("T")
R = TypeVar("R")


# async def run_concurrent(
#     coro_fn: Callable[[T], Awaitable[R]],
#     items: List[T],
#     *,
#     desc: str = "processing",
#     unit: str = "item",
#     progress_bar: Optional[gr.Progress] = None,
# ) -> List[R]:
#     tasks = [asyncio.create_task(coro_fn(it)) for it in items]
#
#     results = []
#     async for future in tqdm_async(
#         tasks, desc=desc, unit=unit
#     ):
#         try:
#             result = await future
#             results.append(result)
#         except Exception as e: # pylint: disable=broad-except
#             logger.exception("Task failed: %s", e)
#
#         if progress_bar is not None:
#             progress_bar((len(results)) / len(items), desc=desc)
#
#     if progress_bar is not None:
#         progress_bar(1.0, desc=desc)
#     return results

#     results = await tqdm_async.gather(*tasks, desc=desc, unit=unit)
#
#     ok_results = []
#     for idx, res in enumerate(results):
#         if isinstance(res, Exception):
#             logger.exception("Task failed: %s", res)
#             if progress_bar:
#                 progress_bar((idx + 1) / len(items), desc=desc)
#             continue
#         ok_results.append(res)
#         if progress_bar:
#             progress_bar((idx + 1) / len(items), desc=desc)
#
#     if progress_bar:
#         progress_bar(1.0, desc=desc)
#     return ok_results

# async def run_concurrent(
#         coro_fn: Callable[[T], Awaitable[R]],
#         items: List[T],
#         *,
#         desc: str = "processing",
#         unit: str = "item",
#         progress_bar: Optional[gr.Progress] = None,
# ) -> List[R]:
#     tasks = [asyncio.create_task(coro_fn(it)) for it in items]
#
#     results = []
#     # 使用同步方式更新进度条，避免异步冲突
#     for i, task in enumerate(asyncio.as_completed(tasks)):
#         try:
#             result = await task
#             results.append(result)
#             # 同步更新进度条
#             if progress_bar is not None:
#                 # 在同步上下文中更新进度
#                 progress_bar((i + 1) / len(items), desc=desc)
#         except Exception as e:
#             logger.exception("Task failed: %s", e)
#             results.append(e)
#
#     return results


async def run_concurrent(
    coro_fn: Callable[[T], Awaitable[R]],
    items: List[T],
    *,
    desc: str = "processing",
    unit: str = "item",
    progress_bar: Optional[Any] = None,
    log_interval: int = 50,  # 默认每 50 个记录一次日志
    desc_callback: Optional[Callable[[int, int, List[R]], str]] = None,  # 新增：动态描述回调 (completed_count, total, results) -> desc
) -> List[R]:
    import time
    
    tasks = [asyncio.create_task(coro_fn(it)) for it in items]

    completed_count = 0
    results = []
    
    # 用于计算当前批次速度的时间窗口
    batch_start_time = time.time()
    batch_completion_times = []  # 记录最近完成的批次的时间戳
    window_size = 10  # 使用最近10个完成项计算速度

    # 初始描述（如果有回调，使用回调生成）
    initial_desc = desc_callback(0, len(items), results) if desc_callback else desc
    pbar = tqdm_async(total=len(items), desc=initial_desc, unit=unit)

    if progress_bar is not None:
        progress_bar(0.0, desc=f"{desc} (0/{len(items)})")

    # 用于记录上次日志时的数量
    last_logged_count = 0

    for future in asyncio.as_completed(tasks):
        try:
            result = await future
            results.append(result)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Task failed: %s", e)
            # even if failed, record it to keep results consistent with tasks
            results.append(e)

        completed_count += 1
        
        # 记录完成时间用于计算当前批次速度
        current_time = time.time()
        batch_completion_times.append(current_time)
        
        # 只保留最近 window_size 个时间戳
        if len(batch_completion_times) > window_size:
            batch_completion_times.pop(0)
        
        # 【优化】只在达到间隔或完成时更新进度条和日志
        should_log = (
            completed_count - last_logged_count >= log_interval or  # 达到间隔
            completed_count == len(items)  # 或者全部完成
        )
        
        if should_log:
            # 计算当前批次速度（基于最近完成的项）
            if len(batch_completion_times) >= 2:
                time_span = batch_completion_times[-1] - batch_completion_times[0]
                if time_span > 0:
                    current_rate = len(batch_completion_times) / time_span
                    pbar.set_postfix({"rate": f"{current_rate:.2f} {unit}/s"})
            
            # 更新描述（如果有回调）
            if desc_callback:
                # 过滤掉异常结果用于回调
                valid_results = [r for r in results if not isinstance(r, Exception)]
                new_desc = desc_callback(completed_count, len(items), valid_results)
                pbar.set_description(new_desc)
            
            # 更新进度条（一次性更新多个）
            update_count = completed_count - last_logged_count
            pbar.update(update_count)
            last_logged_count = completed_count

            if progress_bar is not None:
                progress = completed_count / len(items)
                current_desc = desc_callback(completed_count, len(items), [r for r in results if not isinstance(r, Exception)]) if desc_callback else desc
                progress_bar(progress, desc=f"{current_desc} ({completed_count}/{len(items)})")

    pbar.close()

    if progress_bar is not None:
        progress_bar(1.0, desc=f"{desc} (completed)")

    # filter out exceptions
    results = [res for res in results if not isinstance(res, Exception)]

    return results
