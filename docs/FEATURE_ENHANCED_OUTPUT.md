# 增强输出数据功能

## 功能概述

为生成的数据增加上下文和图谱信息，并在任务处理过程中实时显示已生成的问答对数量。

## 实现内容

### 1. 数据格式增强

生成的每个问答对现在包含以下信息：

#### Alpaca 格式示例

```json
{
  "instruction": "问题内容",
  "input": "",
  "output": "答案内容",
  "context": {
    "nodes": [
      {"name": "实体1", "description": "实体1描述"},
      {"name": "实体2", "description": "实体2描述"}
    ],
    "edges": [
      {"source": "实体1", "target": "实体2", "description": "关系描述"}
    ]
  },
  "graph": {
    "entities": ["实体1", "实体2"],
    "relationships": [["实体1", "实体2"]]
  }
}
```

#### Sharegpt 格式示例

```json
{
  "conversations": [
    {"from": "human", "value": "问题内容"},
    {"from": "gpt", "value": "答案内容"}
  ],
  "context": {
    "nodes": [...],
    "edges": [...]
  },
  "graph": {
    "entities": [...],
    "relationships": [...]
  }
}
```

#### ChatML 格式示例

```json
{
  "messages": [
    {"role": "user", "content": "问题内容"},
    {"role": "assistant", "content": "答案内容"}
  ],
  "context": {
    "nodes": [...],
    "edges": [...]
  },
  "graph": {
    "entities": [...],
    "relationships": [...]
  }
}
```

### 2. 字段说明

#### `context` - 上下文信息

- **nodes**: 生成该问答对所涉及的实体列表
  - `name`: 实体名称
  - `description`: 实体描述
  
- **edges**: 实体之间的关系列表
  - `source`: 源实体
  - `target`: 目标实体
  - `description`: 关系描述

#### `graph` - 图谱表示

- **entities**: 实体名称列表
- **relationships**: 关系对列表 `[源实体, 目标实体]`

### 3. 实时统计功能

#### 前端显示

- 处理中的任务现在可以显示当前已生成的问答对数量
- 实时更新，无需等待任务完成

#### 技术实现

在任务处理过程中：
1. 定期保存临时输出文件
2. 读取临时文件统计已生成的问答对数量
3. 更新任务状态（不改变任务状态，仅更新 `qa_count`）
4. 前端自动刷新显示最新数量

## 应用场景

### 1. 数据可追溯性

- **溯源**: 可以追踪每个问答对来自哪个知识图谱子图
- **验证**: 可以验证生成答案的准确性
- **调试**: 可以分析生成过程中的问题

### 2. 数据增强

- **上下文感知**: 模型训练时可以知道答案的上下文
- **图谱推理**: 可以基于图谱结构进行推理
- **关系理解**: 可以理解实体之间的关系

### 3. 质量监控

- **实时进度**: 查看任务处理进度
- **性能分析**: 分析每个批次的处理效率
- **错误定位**: 快速定位问题所在的知识图谱片段

## 技术实现

### 1. 修改生成器基类

**文件**: `graphgen/bases/base_generator.py`

在 `generate` 方法中添加上下文和图谱信息：

```python
async def generate(self, batch, ...):
    # ... 生成 QA 对 ...
    
    # 添加 context 和 graph 信息
    nodes, edges = batch
    for qa_key, qa_value in qa_pairs.items():
        if isinstance(qa_value, dict):
            # 添加上下文
            qa_value["context"] = {
                "nodes": [...],
                "edges": [...]
            }
            # 添加图谱
            qa_value["graph"] = {
                "entities": [...],
                "relationships": [...]
            }
```

### 2. 修改格式输出

在所有数据格式中都添加了 `context` 和 `graph` 字段：

- Alpaca 格式
- Sharegpt 格式
- ChatML 格式

### 3. 实时统计

在任务处理过程中定期更新统计信息，但不影响任务执行。

## 数据示例

### 完整输出示例

```json
[
  {
    "instruction": "什么是量子计算？",
    "input": "",
    "output": "量子计算是一种利用量子力学现象进行计算的新型计算方式...",
    "context": {
      "nodes": [
        {"name": "量子计算", "description": "一种新型计算方法"},
        {"name": "量子比特", "description": "量子计算的基本单位"}
      ],
      "edges": [
        {"source": "量子计算", "target": "量子比特", "description": "使用"}
      ]
    },
    "graph": {
      "entities": ["量子计算", "量子比特"],
      "relationships": [["量子计算", "量子比特"]]
    }
  }
]
```

## 兼容性

### 向后兼容

- 已有的数据处理代码不受影响
- `context` 和 `graph` 字段为可选字段
- 如果没有这些字段，系统会自动添加空值

### 现有字段保留

- `instruction` / `question` - 问题
- `output` / `answer` - 答案
- 所有原有字段保持不变

## 使用建议

### 1. 训练模型

在训练时可以：
- 忽略新字段（保持原有行为）
- 使用 context 增强训练数据
- 基于图谱结构进行推理

### 2. 数据验证

- 检查每个问答对的来源
- 验证答案与图谱的一致性
- 分析实体关系

### 3. 性能优化

- 根据需要选择是否使用 context
- 大型数据集可以考虑压缩存储
- 实时统计不影响主流程性能

## 相关文件

- `graphgen/bases/base_generator.py` - 生成器基类
- `graphgen/models/generator/atomic_generator.py` - 原子生成器
- `backend/core/task_processor.py` - 任务处理器
- `frontend/src/views/Tasks.vue` - 任务列表

---

**添加日期**: 2025-10-27  
**版本**: v2.0.0
