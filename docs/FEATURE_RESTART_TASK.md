# 重新开始任务功能

## 功能说明

为失败的任务添加"重新开始"操作按钮，方便用户快速重新执行失败的任务。

## 实现内容

### 1. 任务列表增强

在任务列表中，失败的任务现在显示特殊的"重新开始"按钮：

#### 按钮显示逻辑

- **失败的任务**：显示红色的"重新开始"按钮（⚠️ 危险类型）
- **其他可恢复的任务**：显示橙色的"继续"按钮（警告类型）
- **不可恢复的任务**：不显示按钮

### 2. 按钮样式

```vue
<!-- 失败任务 -->
<el-button type="danger" size="small">
  <el-icon><RefreshLeft /></el-icon>
  重新开始
</el-button>

<!-- 其他可恢复任务 -->
<el-button type="warning" size="small">
  <el-icon><RefreshRight /></el-icon>
  继续
</el-button>
```

### 3. 功能行为

点击"重新开始"按钮后：

1. 调用 `handleResumeTask` 函数
2. 使用任务保存的配置或当前默认配置重新启动任务
3. 任务状态从 `failed` 恢复为 `pending`
4. 显示成功消息："任务已恢复并重新启动"
5. 刷新任务列表

## 使用场景

### 场景 1：API Key 错误

**问题**：任务因 API Key 无效而失败

**解决**：
1. 修复配置中的 API Key
2. 点击失败任务的"重新开始"按钮
3. 任务使用新的 API Key 重新执行

### 场景 2：网络超时

**问题**：任务因网络超时而失败

**解决**：
1. 检查网络连接
2. 点击"重新开始"按钮
3. 任务将重新尝试执行

### 场景 3：配置错误

**问题**：任务因配置错误而失败

**解决**：
1. 修改配置设置
2. 点击"重新开始"按钮
3. 任务使用新配置重新执行

## 权限控制

- **管理员**：可以查看和使用"重新开始"按钮
- **审核员**：只能查看任务状态，无法重新开始任务

## 技术实现

### 前端修改

**文件**：`frontend/src/views/Tasks.vue`

#### 1. 添加图标导入

```typescript
import {
  Refresh,
  Search,
  VideoPlay,
  Download,
  View,
  Delete,
  Edit,
  RefreshRight,
  RefreshLeft  // 新增
} from '@element-plus/icons-vue'
```

#### 2. 修改按钮逻辑

```vue
<!-- 失败任务显示红色"重新开始"按钮 -->
<el-button
  v-if="row.status === 'failed'"
  size="small"
  type="danger"
  @click.stop="handleResumeTask(row)"
>
  <el-icon><RefreshLeft /></el-icon>
  重新开始
</el-button>

<!-- 其他可恢复任务显示橙色"继续"按钮 -->
<el-button
  v-else-if="canResumeTask(row)"
  size="small"
  type="warning"
  @click.stop="handleResumeTask(row)"
>
  <el-icon><RefreshRight /></el-icon>
  继续
</el-button>
```

#### 3. 调整列宽

将操作列宽度从 `360px` 增加到 `400px`，为"重新开始"按钮预留空间。

### 后端支持

任务恢复功能由后端 `resume_task` API 提供支持：

**端点**：`POST /api/tasks/{task_id}/resume`

**功能**：
- 检查任务状态
- 恢复任务状态为 `pending`
- 使用新配置重新启动任务
- 清除之前的错误信息

## 用户体验优化

### 1. 视觉区分

- 失败任务使用红色按钮，突出危险性
- 继续任务使用橙色按钮，表示警告
- 图标使用 `RefreshLeft`（左向刷新）表示重新开始
- 图标使用 `RefreshRight`（右向刷新）表示继续

### 2. 操作反馈

- 点击后立即显示加载状态
- 成功后显示明确的成功消息
- 失败时显示详细错误信息
- 自动刷新任务列表

### 3. 状态展示

任务列表清晰展示：
- 任务状态（失败、处理中、已完成）
- 失败原因（错误消息）
- 可执行操作（重新开始、查看详情）

## 测试验证

1. **创建测试任务**
   - 使用无效的 API Key 创建任务
   - 任务将失败

2. **验证重新开始功能**
   - 修复 API Key 配置
   - 点击失败任务的"重新开始"按钮
   - 验证任务状态变更为"处理中"
   - 验证任务能够正常完成

3. **验证按钮显示**
   - 失败任务显示红色"重新开始"按钮
   - 其他可恢复任务显示橙色"继续"按钮
   - 不可恢复任务不显示按钮

## 相关文件

- `frontend/src/views/Tasks.vue` - 任务列表页面
- `backend/services/task_service.py` - 任务服务
- `backend/api/endpoints.py` - API 端点
- `frontend/src/api/index.ts` - API 客户端

---

**添加日期**: 2025-10-27  
**版本**: v2.0.0
