# 审核页面 UI 增强功能

## 功能概述

增强审核页面的显示功能，使内容预览支持自动换行，并在详情页面展示上下文和图谱信息。

## 改进内容

### 1. 内容预览优化

#### 改进前
- 文本被截断到 100 个字符
- 无法查看完整内容
- 没有上下文信息显示

#### 改进后
- **自动换行显示**: 文本内容自动换行，显示完整内容
- **图谱信息预览**: 显示实体数和关系数统计
- **宽度调整**: 列宽从 300px 增加到 400px

### 2. 详情对话框增强

#### 新增功能

**a. 内容显示**
- 使用描述列表（descriptions）结构化显示问题和答案
- 支持换行显示长文本内容

**b. 上下文与图谱展示**
- **实体列表**: 
  - 显示所有实体的标签
  - 鼠标悬停显示实体描述
  - 标签可以交互（hover 效果）
  
- **关系列表**:
  - 显示所有实体之间的关系
  - 格式：源实体 → 目标实体：关系描述
  - 使用箭头和标签清晰表示关系链
  
- **图谱结构**:
  - 显示完整的图谱 JSON 数据
  - 包含 entities 和 relationships

**c. 完整数据**
- 保留原有的完整 JSON 显示
- 便于开发调试

### 3. 视觉改进

#### 样式优化
- **卡片式设计**: 上下文和图谱信息使用卡片样式
- **颜色区分**: 
  - 实体标签使用蓝色系
  - 关系使用灰色边框
  - 图谱信息区域使用浅蓝色背景
- **交互效果**: 
  - 实体标签 hover 时有缩放和阴影效果
  - 提供良好的视觉反馈

## 实现细节

### 1. 列表预览

```vue
<div class="content-preview">
  <div v-if="row.content.instruction" class="preview-line">
    <strong>问题：</strong>
    <span class="text-content">{{ row.content.instruction }}</span>
  </div>
  <div v-if="row.content.output" class="preview-line">
    <strong>答案：</strong>
    <span class="text-content">{{ row.content.output }}</span>
  </div>
  <!-- 显示上下文信息 -->
  <div v-if="row.content.context" class="context-info">
    <el-tag size="small" type="info">图谱信息</el-tag>
    <span class="context-text">
      实体数: {{ row.content.context.nodes?.length || 0 }} | 
      关系数: {{ row.content.context.edges?.length || 0 }}
    </span>
  </div>
</div>
```

**关键样式**:
```css
.text-content {
  white-space: normal;
  word-wrap: break-word;
  word-break: break-all;
}
```

### 2. 实体展示

```vue
<div class="entity-list">
  <el-tag 
    v-for="(node, index) in currentItem.content.context.nodes" 
    :key="index"
    class="entity-tag"
    :title="node.description"
  >
    {{ node.name }}
  </el-tag>
</div>
```

**样式**:
```css
.entity-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}
```

### 3. 关系展示

```vue
<div class="relation-item">
  <el-tag size="small">{{ edge.source }}</el-tag>
  <span class="relation-arrow">→</span>
  <el-tag size="small">{{ edge.target }}</el-tag>
  <span class="relation-desc">: {{ edge.description }}</span>
</div>
```

## 效果展示

### 列表预览

```
问题：什么是量子计算？
这是一个重要的概念...

答案：量子计算是一种利用量子力学现象...

[图谱信息] 实体数: 3 | 关系数: 2
```

### 详情页面

#### 内容区域
```
┌────────────────────────────────────┐
│ 问题/指令                          │
│ 什么是量子计算？                    │
├────────────────────────────────────┤
│ 输出/答案                          │
│ 量子计算是一种利用量子力学现象进行   │
│ 计算的新型计算方式...               │
└────────────────────────────────────┘
```

#### 上下文与图谱

**实体** (3)
```
[量子计算] [量子比特] [量子门]
```

**关系** (2)
```
[量子计算] → [量子比特] : 使用
[量子计算] → [量子门] : 基于
```

**图谱结构**
```json
{
  "entities": ["量子计算", "量子比特", "量子门"],
  "relationships": [
    ["量子计算", "量子比特"],
    ["量子计算", "量子门"]
  ]
}
```

## 使用场景

### 1. 快速浏览
- 在列表页面快速查看内容概览
- 了解图谱复杂度（实体数和关系数）

### 2. 详细审核
- 点击"查看"按钮进入详情
- 查看完整的上下文和图谱信息
- 验证数据的来源和结构

### 3. 数据验证
- 检查实体关系是否正确
- 确认答案是否与图谱一致
- 识别可能的数据问题

## 技术实现

### 修改的文件
- `frontend/src/views/Review.vue`

### 主要改进
1. **列表预览**:
   - 移除文本截断
   - 添加自动换行
   - 增加上下文信息显示

2. **详情对话框**:
   - 添加内容结构化显示
   - 新增上下文和图谱展示区域
   - 优化 JSON 显示

3. **样式优化**:
   - 添加丰富的 CSS 样式
   - 实现交互效果
   - 改善视觉体验

## 兼容性

### 向后兼容
- 如果数据中没有 context 或 graph 字段，页面仍然正常工作
- 使用可选链操作符 `?.` 避免报错

### 数据格式要求
- 推荐使用包含 context 和 graph 的数据
- 如果没有这些字段，只显示基本内容

## 相关功能

- [FEATURE_ENHANCED_OUTPUT.md](./FEATURE_ENHANCED_OUTPUT.md) - 增强输出数据格式
- 输出数据包含 context 和 graph 信息，这些信息在审核页面得以展示

---

**添加日期**: 2025-10-27  
**版本**: v2.0.0
