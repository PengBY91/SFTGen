<template>
  <div class="review-container">
    <!-- 统计卡片 -->
    <el-card class="stats-card">
      <template #header>
        <div class="card-header">
          <span>审核统计</span>
          <div class="header-actions">
            <el-button size="small" @click="refreshData" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button size="small" type="primary" @click="showAutoReviewDialog">
              <el-icon><MagicStick /></el-icon>
              自动审核
            </el-button>
            <el-button size="small" type="success" @click="exportData">
              <el-icon><Download /></el-icon>
              导出数据
            </el-button>
          </div>
        </div>
      </template>
      <div class="stats-content">
        <div class="stat-item">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总数</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #e6a23c">{{ stats.pending }}</div>
          <div class="stat-label">待审核</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #67c23a">{{ stats.approved }}</div>
          <div class="stat-label">已通过</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #f56c6c">{{ stats.rejected }}</div>
          <div class="stat-label">已拒绝</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #409eff">{{ stats.modified }}</div>
          <div class="stat-label">已修改</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #95d475">{{ stats.auto_approved }}</div>
          <div class="stat-label">自动通过</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #f78989">{{ stats.auto_rejected }}</div>
          <div class="stat-label">自动拒绝</div>
        </div>
      </div>
    </el-card>

    <!-- 数据列表 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>数据列表</span>
          <div class="header-actions">
            <el-select v-model="statusFilter" placeholder="筛选状态" clearable style="width: 150px; margin-right: 10px">
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
              <el-option label="已修改" value="modified" />
              <el-option label="自动通过" value="auto_approved" />
              <el-option label="自动拒绝" value="auto_rejected" />
            </el-select>
            <el-button size="small" type="primary" @click="batchApprove" :disabled="selectedItems.length === 0">
              批量通过
            </el-button>
            <el-button size="small" type="danger" @click="batchReject" :disabled="selectedItems.length === 0">
              批量拒绝
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="filteredData"
        @selection-change="handleSelectionChange"
        style="width: 100%"
        stripe
        v-loading="loading"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="item_id" label="ID" width="200" />
        <el-table-column label="内容预览" min-width="400">
          <template #default="{ row }">
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
          </template>
        </el-table-column>
        <el-table-column label="生成模式" min-width="100">
          <template #default="{ row }">
            <el-tag 
              v-if="getGenerationMode(row)" 
              type="info" 
              size="small"
            >
              {{ getGenerationMode(row) }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="120">
          <template #default="{ row }">
            <el-tag :type="STATUS_TYPE_MAP[row.review_status] || 'info'">
              {{ STATUS_TEXT_MAP[row.review_status] || row.review_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="自动评分" width="100">
          <template #default="{ row }">
            <span v-if="row.auto_review_score !== null && row.auto_review_score !== undefined">
              {{ (row.auto_review_score * 100).toFixed(0) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="审核人" width="120">
          <template #default="{ row }">
            {{ row.reviewer || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="viewDetail(row)">
              <el-icon><View /></el-icon>
              详情/编辑
            </el-button>
            <el-button size="small" type="success" @click="approveItem(row)">
              <el-icon><Check /></el-icon>
              通过
            </el-button>
            <el-button size="small" type="danger" @click="rejectItem(row)">
              <el-icon><Close /></el-icon>
              拒绝
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 自动审核对话框 -->
    <el-dialog
      v-model="autoReviewDialogVisible"
      title="自动审核设置"
      width="500px"
    >
      <el-form label-width="120px">
        <el-form-item label="审核范围">
          <el-radio-group v-model="autoReviewForm.scope">
            <el-radio label="selected">已选中的数据</el-radio>
            <el-radio label="pending">所有待审核数据</el-radio>
            <el-radio label="all">全部数据</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="通过阈值">
          <el-slider v-model="autoReviewForm.threshold" :min="0" :max="100" :step="5" />
          <span>{{ autoReviewForm.threshold }}%</span>
        </el-form-item>
        <el-form-item label="自动通过">
          <el-switch v-model="autoReviewForm.autoApprove" />
          <span style="margin-left: 10px; font-size: 12px; color: #909399">
            高于阈值自动标记为通过
          </span>
        </el-form-item>
        <el-form-item label="自动拒绝">
          <el-switch v-model="autoReviewForm.autoReject" />
          <span style="margin-left: 10px; font-size: 12px; color: #909399">
            低于阈值20%自动标记为拒绝
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="autoReviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startAutoReview" :loading="autoReviewLoading">
          开始自动审核
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// 状态映射（提升到组件外避免重复创建）
const STATUS_TEXT_MAP: Record<string, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已拒绝',
  modified: '已修改',
  auto_approved: '自动通过',
  auto_rejected: '自动拒绝'
}

const STATUS_TYPE_MAP: Record<string, any> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  modified: 'primary',
  auto_approved: '',
  auto_rejected: 'info'
}
import type { DataItem, ReviewStats } from '@/api/types'
import api from '@/api'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  MagicStick,
  Download,
  View,
  Check,
  Close
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const loading = ref(false)
const data = ref<DataItem[]>([])
const stats = ref<ReviewStats>({
  total: 0,
  pending: 0,
  approved: 0,
  rejected: 0,
  modified: 0,
  auto_approved: 0,
  auto_rejected: 0
})

const statusFilter = ref('')
const selectedItems = ref<DataItem[]>([])
const autoReviewDialogVisible = ref(false)
const autoReviewLoading = ref(false)

const autoReviewForm = ref({
  scope: 'pending',
  threshold: 70,
  autoApprove: true,
  autoReject: false
})

// 过滤后的数据
const filteredData = computed(() => {
  if (!statusFilter.value) {
    return data.value
  }
  return data.value.filter(item => item.review_status === statusFilter.value)
})

// 刷新数据
const refreshData = async () => {
  loading.value = true
  try {
    const [dataRes, statsRes] = await Promise.all([
      api.getReviewData(taskId),
      api.getReviewStats(taskId)
    ])

    if (dataRes.success && dataRes.data) {
      data.value = dataRes.data
    }

    if (statsRes.success && statsRes.data) {
      stats.value = statsRes.data
    }
  } catch (error) {
    console.error('刷新数据失败', error)
  } finally {
    loading.value = false
  }
}

// 获取生成模式（从多个可能的位置）
const getGenerationMode = (row: DataItem): string => {
  // 优先从 content.mode 获取
  if (row.content?.mode) {
    return row.content.mode
  }
  // 其次从 content.metadata.generation_mode 获取
  if (row.content?.metadata?.generation_mode) {
    return row.content.metadata.generation_mode
  }
  // 最后从顶层 mode 获取（如果存在）
  if ((row as any).mode) {
    return (row as any).mode
  }
  return ''
}

// 截断文本
const truncate = (text: string, length: number) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}



// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

// 选择变化
const handleSelectionChange = (selection: DataItem[]) => {
  selectedItems.value = selection
}

// 查看详情（跳转到详情页面）
const viewDetail = (item: DataItem) => {
  router.push(`/review/${taskId}/detail/${item.item_id}`)
}

// 通过单个
const approveItem = async (item: DataItem) => {
  try {
    const response = await api.reviewItem({
      task_id: taskId,  // 添加 task_id
      item_id: item.item_id,
      review_status: 'approved',
      reviewer: '手动审核'
    })

    if (response.success) {
      ElMessage.success('审核通过')
      await refreshData()
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 拒绝单个
const rejectItem = async (item: DataItem) => {
  try {
    const response = await api.reviewItem({
      task_id: taskId,  // 添加 task_id
      item_id: item.item_id,
      review_status: 'rejected',
      reviewer: '手动审核'
    })

    if (response.success) {
      ElMessage.success('已拒绝')
      await refreshData()
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
}


// 批量通过
const batchApprove = async () => {
  if (selectedItems.value.length === 0) return

  try {
    const response = await api.batchReview({
      task_id: taskId,  // 添加 task_id
      item_ids: selectedItems.value.map(item => item.item_id),
      review_status: 'approved',
      reviewer: '批量审核'
    })

    if (response.success) {
      ElMessage.success(`批量通过成功，共 ${selectedItems.value.length} 条`)
      await refreshData()
    }
  } catch (error) {
    ElMessage.error('批量操作失败')
  }
}

// 批量拒绝
const batchReject = async () => {
  if (selectedItems.value.length === 0) return

  try {
    const response = await api.batchReview({
      task_id: taskId,  // 添加 task_id
      item_ids: selectedItems.value.map(item => item.item_id),
      review_status: 'rejected',
      reviewer: '批量审核'
    })

    if (response.success) {
      ElMessage.success(`批量拒绝成功，共 ${selectedItems.value.length} 条`)
      await refreshData()
    }
  } catch (error) {
    ElMessage.error('批量操作失败')
  }
}

// 显示自动审核对话框
const showAutoReviewDialog = () => {
  autoReviewDialogVisible.value = true
}

// 开始自动审核
const startAutoReview = async () => {
  let itemIds: string[] = []

  if (autoReviewForm.value.scope === 'selected') {
    if (selectedItems.value.length === 0) {
      ElMessage.warning('请先选择要审核的数据')
      return
    }
    itemIds = selectedItems.value.map(item => item.item_id)
  } else if (autoReviewForm.value.scope === 'pending') {
    itemIds = data.value
      .filter(item => item.review_status === 'pending')
      .map(item => item.item_id)
  } else {
    itemIds = data.value.map(item => item.item_id)
  }

  if (itemIds.length === 0) {
    ElMessage.warning('没有需要审核的数据')
    return
  }

  autoReviewLoading.value = true
  try {
    const response = await api.autoReview({
      item_ids: itemIds,
      threshold: autoReviewForm.value.threshold / 100,
      auto_approve: autoReviewForm.value.autoApprove,
      auto_reject: autoReviewForm.value.autoReject
    })

    if (response.success) {
      ElMessage.success(`自动审核完成，共审核 ${itemIds.length} 条数据`)
      autoReviewDialogVisible.value = false
      await refreshData()
    }
  } catch (error) {
    ElMessage.error('自动审核失败')
  } finally {
    autoReviewLoading.value = false
  }
}

// 导出数据
const exportData = async () => {
  try {
    // 先导出
    const exportRes = await api.exportReviewedData(taskId, 'approved,modified,auto_approved')
    
    if (exportRes.success) {
      // 然后下载
      const blob = await api.downloadReviewedData(taskId)
      const url = window.URL.createObjectURL(blob as Blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${taskId}_reviewed.json`
      link.click()
      window.URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    }
  } catch (error) {
    ElMessage.error('导出失败')
  }
}


// 初始化
onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.review-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-card {
  width: 100%;
}

.stats-content {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.content-preview {
  font-size: 14px;
  line-height: 1.6;
}

.preview-line {
  margin-bottom: 8px;
}

.preview-line strong {
  color: #303133;
  margin-right: 8px;
}

.text-content {
  white-space: normal;
  word-wrap: break-word;
  word-break: break-all;
}

.context-info {
  margin-top: 8px;
  padding: 6px 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.context-text {
  font-size: 12px;
  color: #606266;
}
</style>


