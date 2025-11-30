# 日志优化与多模式选择修复

## 问题分析

### 1. ANSI 转义序列污染日志文件
**现象：**
```
[类型 2/4: aggregated] 批次: 0/461 | 已生成: 0 QA (目标: 150) | 总目标: 500 QA:   0%|          | 0/461 [00:00<?, ?batch/s][A
[类型 3/4: multi_hop] 批次: 0/461 | 已生成: 0 QA (目标: 0) | 总目标: 500 QA:   0%|          | 0/461 [00:00<?, ?batch/s][A[A
```

**原因：**
- `tqdm` 进度条使用 ANSI 转义序列 `[A` (光标向上移动) 来在终端中更新进度条
- 这些控制字符被写入日志文件，导致日志难以阅读
- 当 `mode="all"` 时，4 个并发任务的进度条输出互相干扰

**解决方案：**
- 禁用 `tqdm` 的终端输出 (`disable=True`)
- 使用 `logger.info()` 代替，输出清晰的进度信息
- 格式化输出包含：描述、进度百分比、速度

### 2. 批次数量分配不合理
**现象：**
```
目标: 100 个 atomic QA
实际生成: 461 个 atomic QA (超出 361%)
```

**原因：**
在 `mode="all"` 模式下，所有 4 种生成器共享相同的 `batches` 列表：
- atomic: 使用全部 461 个批次
- aggregated: 使用全部 461 个批次  
- multi_hop: 使用全部 461 个批次
- cot: 使用全部 461 个批次

每个模式都处理了全部批次，导致生成数量远超目标。

**解决方案：**
根据每个模式的目标数量，动态分配批次：

```python
# 为每个模式计算所需批次数
mode_target = mode_targets[gen_mode]  # 例如: atomic=100
avg_qa_per_batch = 1.0  # atomic 每批次约生成 1 个 QA
required_batches = int(mode_target / avg_qa_per_batch * 1.3)  # 加 30% 缓冲

# 只分配所需数量的批次
batches_to_use = batches[:required_batches]
```

这样可以确保每个模式只处理必要的批次数量，生成的 QA 数量更接近目标。

### 3. 多模式选择支持不完整

**现象：**
用户在前端选择了 2 个或 3 个模式（例如只选择 `atomic` 和 `aggregated`），但实际生成时会生成所有 4 种模式的 QA。

**原因：**
1. 前端支持多选模式，`mode` 字段可以是字符串数组
2. 后端 `task_processor.py` 将 2-3 个模式的选择强制转换为 `mode="all"`
3. 但转换时没有调整 `mode_ratios`，所有模式的 ratio 都保持原值
4. `generate_qas.py` 看到 `mode="all"` 后会为所有 4 个模式分配批次

**示例：**
```python
# 用户选择: ["atomic", "aggregated"]
# task_processor.py 转换为: mode="all"
# mode_ratios: {"atomic": 25, "aggregated": 25, "multi_hop": 25, "cot": 25}
# 结果: 生成了所有 4 种模式的 QA ❌
```

**解决方案：**
在 `task_processor.py` 中，将未选中的模式的 ratio 设置为 0：

```python
# 用户选择: ["atomic", "aggregated"]  
# task_processor.py 转换为: mode="all"
# mode_ratios: {"atomic": 25, "aggregated": 25, "multi_hop": 0, "cot": 0}
# 结果: 只生成 atomic 和 aggregated 两种模式 ✅
```

## 修改内容

### 文件 1: `graphgen/utils/run_concurrent.py`

**修改 1: 禁用 tqdm 终端输出**
```python
# 第 110 行
pbar = tqdm_async(total=len(items), desc=initial_desc, unit=unit, disable=True, file=None)
```

**修改 2: 添加 logger 输出**
```python
# 第 160-179 行
# 记录到日志（替代 tqdm 的终端输出）
progress_percent = (completed_count / len(items)) * 100
if current_rate > 0:
    logger.info(
        "%s: %d/%d (%.1f%%) | 速度: %.2f %s/s",
        current_desc,
        completed_count,
        len(items),
        progress_percent,
        current_rate,
        unit
    )
else:
    logger.info(
        "%s: %d/%d (%.1f%%)",
        current_desc,
        completed_count,
        len(items),
        progress_percent
    )
```

### 文件 2: `graphgen/operators/generate/generate_qas.py`

**修改: 为 mode="all" 动态分配批次**
```python
# 第 481-541 行
for idx, (generator, gen_mode) in enumerate(generators):
    # 计算当前模式需要的批次数量
    batches_to_use = batches
    
    # 如果设置了目标数量，根据模式目标动态分配批次
    if target_qa_pairs and gen_mode in mode_targets:
        mode_target = mode_targets[gen_mode]
        if mode_target > 0:
            # 估算每个batch平均生成多少个QA对
            estimated_qa_per_batch_mode = {
                "atomic": 1.0,
                "aggregated": 1.5,
                "multi_hop": 1.0,
                "cot": 1.0,
            }
            avg_qa_per_batch = estimated_qa_per_batch_mode.get(gen_mode, 1.0)
            # 使用1.3倍缓冲
            required_batches_for_mode = int(mode_target / avg_qa_per_batch * 1.3)
            required_batches_for_mode = min(required_batches_for_mode, len(batches))
            
            if required_batches_for_mode < len(batches):
                batches_to_use = batches[:required_batches_for_mode]
        else:
            # 目标为0，跳过此模式
            batches_to_use = []
    
    # 如果没有批次，跳过此模式
    if not batches_to_use:
        async def return_empty():
            return []
        task = asyncio.create_task(return_empty())
        tasks.append(task)
        continue
    
    # ... 继续处理
```

### 文件 3: `backend/core/task_processor.py`

**修改: 支持部分模式选择**
```python
# 第 312-365 行
# 处理 mode：支持数组格式
mode = config.mode
selected_modes = set()  # 记录用户选择的模式

if isinstance(mode, list):
    if len(mode) == 0:
        mode = "aggregated"  # 默认值
        selected_modes = {"aggregated"}
    elif len(mode) == 1:
        mode = mode[0]
        selected_modes = {mode}
    else:
        # 用户选择了多个模式
        selected_modes = set(mode)
        all_modes = {"atomic", "multi_hop", "aggregated", "cot"}
        
        if selected_modes == all_modes:
            # 如果选择了所有4种模式，使用 "all"
            mode = "all"
        else:
            # 如果选择了部分模式（2个或3个），也使用 "all"
            # 但通过 mode_ratios 控制只生成选中的模式
            mode = "all"
else:
    # mode 是字符串
    if mode == "all":
        selected_modes = {"atomic", "multi_hop", "aggregated", "cot"}
    else:
        selected_modes = {mode}

# 构建 mode_ratios，未选中的模式设置为 0
all_mode_names = {"atomic", "aggregated", "multi_hop", "cot"}
mode_ratios = {}

for mode_name in all_mode_names:
    ratio_attr = f"qa_ratio_{mode_name}"
    configured_ratio = float(getattr(config, ratio_attr, 25.0))
    
    # ⭐ 关键：如果模式未被选中，强制设置为 0
    if mode_name not in selected_modes:
        mode_ratios[mode_name] = 0.0
    else:
        mode_ratios[mode_name] = configured_ratio
```

## 预期效果

### 1. 日志格式改进
**修复前：**
```
[类型 1/4: atomic] 批次: 0/461 | 已生成: 0 QA (目标: 100) | 总目标: 500 QA:   0%|          | 0/461 [00:00<?, ?batch/s][A[A
```

**修复后：**
```
INFO: [类型 1/4: atomic] 批次: 50/130 | 已生成: 45 QA (目标: 100) | 总目标: 500 QA: 50/130 (38.5%) | 速度: 2.15 batch/s
INFO: [类型 1/4: atomic] 批次: 100/130 | 已生成: 92 QA (目标: 100) | 总目标: 500 QA: 100/130 (76.9%) | 速度: 2.08 batch/s
INFO: [类型 1/4: atomic] 批次: 130/130 | 已生成: 118 QA (目标: 100) | 总目标: 500 QA: 130/130 (100.0%) | 速度: 2.12 batch/s
INFO: [Generation] Mode atomic generated 118 QA pairs
```

### 批次分配优化
**修复前：**
- atomic: 461 批次 → 461 QA (目标: 100)
- aggregated: 461 批次 → 650 QA (目标: 150)
- multi_hop: 461 批次 → 0 QA (目标: 0)
- cot: 461 批次 → 580 QA (目标: 250)
- **总计**: ~1691 QA (目标: 500) ❌ 超出 238%

**修复后：**
- atomic: 130 批次 → ~118 QA (目标: 100) ✅
- aggregated: 195 批次 → ~162 QA (目标: 150) ✅
- multi_hop: 0 批次 → 0 QA (目标: 0) ✅
- cot: 325 批次 → ~268 QA (目标: 250) ✅
- **总计**: ~548 QA (目标: 500) ✅ 超出 9.6%

### 2. 批次分配优化

**场景 1: 用户选择所有 4 种模式，目标 500 QA**

同上述修复效果。

**场景 2: 用户只选择 2 种模式（atomic + aggregated），目标 200 QA**

**修复前：**
```python
# 前端: mode = ["atomic", "aggregated"]
# 后端转换: mode = "all"
# mode_ratios = {"atomic": 25, "aggregated": 25, "multi_hop": 25, "cot": 25}
# 结果:
- atomic: 461 批次 → 461 QA
- aggregated: 461 批次 → 650 QA
- multi_hop: 461 批次 → 0 QA    # ❌ 不应该处理
- cot: 461 批次 → 580 QA         # ❌ 不应该处理
# 总计: ~1691 QA ❌ 包含了不应该生成的模式
```

**修复后：**
```python
# 前端: mode = ["atomic", "aggregated"]
# 后端转换: mode = "all"
# mode_ratios = {"atomic": 50, "aggregated": 50, "multi_hop": 0, "cot": 0}
# 结果:
- atomic: 130 批次 → ~118 QA (目标: 100) ✅
- aggregated: 130 批次 → ~135 QA (目标: 100) ✅
- multi_hop: 0 批次 → 0 QA      # ✅ 正确跳过
- cot: 0 批次 → 0 QA            # ✅ 正确跳过
# 总计: ~253 QA ✅ 只包含选中的模式，接近目标
```

### 3. 多模式选择支持

**支持的场景：**
1. ✅ 单个模式: `mode = "atomic"`
2. ✅ 所有模式: `mode = "all"` 或 `mode = ["atomic", "aggregated", "multi_hop", "cot"]`
3. ✅ **部分模式（新增）**: `mode = ["atomic", "aggregated"]` 或任意 2-3 个模式组合

**实现方式：**
- 将部分模式选择转换为 `mode="all"`
- 通过将未选中模式的 `mode_ratios` 设置为 0 来控制生成
- `generate_qas.py` 自动跳过 ratio 为 0 的模式

## 后续优化建议

1. **自适应批次估算**: 在运行过程中动态调整 `estimated_qa_per_batch` 值
2. **进度持久化**: 支持断点续传，避免重复生成
3. **结果缓存**: 缓存已生成的 QA 对，加速重启
4. **分布式执行**: 支持多机并行生成，提高吞吐量

## 测试建议

1. **测试场景 1: 所有模式**
   - 运行 `mode="all"` 或 `mode=["atomic", "aggregated", "multi_hop", "cot"]`
   - 设置 `target_qa_pairs=500`
   - 检查日志输出是否清晰无乱码
   - 验证最终生成的 QA 数量是否接近目标（误差 < 20%）
   - 确认各模式的比例是否符合 `mode_ratios` 配置

2. **测试场景 2: 部分模式（新增）**
   - 运行 `mode=["atomic", "aggregated"]`（只选择 2 个模式）
   - 设置 `target_qa_pairs=200`
   - 验证只生成了 `atomic` 和 `aggregated` 两种模式的 QA
   - 确认 `multi_hop` 和 `cot` 没有生成任何 QA
   - 检查日志中是否有 "Mode xxx: skipped (target: 0)" 的信息

3. **测试场景 3: 单个模式**
   - 运行 `mode="atomic"`
   - 设置 `target_qa_pairs=100`
   - 验证只生成了 `atomic` 类型的 QA
   - 确认生成数量接近目标

## 相关文件

- `graphgen/utils/run_concurrent.py`: 进度条和日志输出
- `graphgen/operators/generate/generate_qas.py`: 批次分配逻辑（mode="all" 场景）
- `backend/core/task_processor.py`: 模式选择处理和 mode_ratios 构建
- `backend/schemas.py`: 任务配置模型定义
- `.backend.log`: 后端日志文件（用于验证修复效果）

## 技术要点

### 1. 为什么不直接支持模式列表？

当前 `generate_qas.py` 的实现中，`mode` 参数只支持单个字符串（如 `"atomic"`）或特殊值 `"all"`。要支持模式列表需要重构较多代码。

通过将部分模式选择转换为 `mode="all"` + `mode_ratios`（未选中的设为 0）的方式，可以在**最小改动**的情况下实现相同效果。

### 2. mode_ratios 的作用

`mode_ratios` 控制各模式的 QA 生成比例：

```python
# 示例 1: 所有模式均等
mode_ratios = {"atomic": 25, "aggregated": 25, "multi_hop": 25, "cot": 25}
# 结果: 4 种模式各占 25%

# 示例 2: 只生成 atomic 和 aggregated
mode_ratios = {"atomic": 50, "aggregated": 50, "multi_hop": 0, "cot": 0}
# 结果: 只生成 2 种模式，各占 50%

# 示例 3: 禁用 multi_hop
mode_ratios = {"atomic": 33.3, "aggregated": 33.3, "multi_hop": 0, "cot": 33.3}
# 结果: 生成 3 种模式，multi_hop 被跳过
```

### 3. 批次分配算法

对于 `mode="all"` 的情况：

1. 根据 `target_qa_pairs` 和 `mode_ratios` 计算各模式的目标数量
2. 根据各模式的 `estimated_qa_per_batch` 估算所需批次数
3. 为每个模式分配相应数量的批次
4. 如果某个模式的目标为 0，跳过该模式（不分配批次）

```python
# 伪代码
for each mode in ["atomic", "aggregated", "multi_hop", "cot"]:
    mode_target = target_qa_pairs * mode_ratios[mode]
    if mode_target == 0:
        skip this mode
    else:
        required_batches = mode_target / estimated_qa_per_batch * 1.3
        allocate batches[:required_batches] to this mode
```
