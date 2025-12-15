<template>
  <div class="review-container">
    <!-- 数据列表头部（直接在页面中展示） -->
    <div class="review-header">
      <div class="header-left">
        <span class="header-title">数据列表</span>
        <div class="stats-inline">
          <span class="stat-inline-item">总数: <strong>{{ stats.total }}</strong></span>
          <span class="stat-inline-item pending">待审核: <strong>{{ stats.pending }}</strong></span>
          <span class="stat-inline-item approved">已通过: <strong>{{ stats.approved }}</strong></span>

        </div>
      </div>
      <div class="header-actions">
            <el-select v-model="modeFilter" placeholder="筛选生成模式" clearable style="width: 150px; margin-right: 10px">
              <el-option label="Atomic" value="atomic" />
              <el-option label="Multi-hop" value="multi_hop" />
              <el-option label="Aggregated" value="aggregated" />
              <el-option label="CoT" value="cot" />
            </el-select>
            <el-select v-model="statusFilter" placeholder="筛选审核状态" clearable style="width: 150px; margin-right: 10px">
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
              <el-option label="已修改" value="modified" />
              <el-option label="自动通过" value="auto_approved" />
              <el-option label="自动拒绝" value="auto_rejected" />
            </el-select>
            <el-button size="small" @click="refreshData" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button size="small" type="primary" @click="showAutoReviewDialog">
              <el-icon><MagicStick /></el-icon>
              自动审核
            </el-button>
            <el-button size="small" type="primary" @click="batchApprove" :disabled="selectedItems.length === 0">
              批量通过
            </el-button>
            <el-button size="small" type="danger" @click="batchReject" :disabled="selectedItems.length === 0">
              批量拒绝
            </el-button>
            <el-button size="small" type="success" @click="showExportDialog">
              <el-icon><Download /></el-icon>
              下载数据
            </el-button>
            <el-select v-model="pageSize" placeholder="每页数量" style="width: 120px; margin-left: 10px" @change="handlePageSizeChange">
              <el-option label="10" :value="10" />
              <el-option label="20" :value="20" />
              <el-option label="50" :value="50" />
              <el-option label="100" :value="100" />
              <el-option label="200" :value="200" />
            </el-select>
          </div>
    </div>

    <!-- 数据表格（直接在页面中展示） -->
    <div class="table-wrapper">
      <el-table
        ref="tableRef"
        :data="paginatedData"
        @selection-change="handleSelectionChange"
        row-key="item_id"
        style="width: 100%"
        stripe
        v-loading="loading"
      >
        <el-table-column type="selection" width="50" :reserve-selection="false" />
        <el-table-column prop="item_id" label="ID" width="160" show-overflow-tooltip />
        <el-table-column label="内容预览" min-width="600">
          <template #default="{ row }">
            <div class="content-preview">
              <!-- 评测任务：显示评测项字段 -->
              <template v-if="isEvaluationItem(row.content)">
                <!-- 评测类型和难度 -->
                <div v-if="row.content.type || row.content.difficulty" class="preview-line">
                  <el-tag v-if="row.content.type" size="small" type="primary">{{ row.content.type }}</el-tag>
                  <el-tag v-if="row.content.difficulty" size="small" :type="getDifficultyTagType(row.content.difficulty)" style="margin-left: 5px">
                    {{ row.content.difficulty }}
                  </el-tag>
                </div>
                
                <!-- 问题 -->
                <div v-if="row.content.question" class="preview-line">
                  <strong>问题：</strong>
                  <span class="text-content">{{ row.content.question }}</span>
                </div>
                
                <!-- 参考答案 -->
                <div v-if="row.content.reference_answer" class="preview-line">
                  <strong>参考答案：</strong>
                  <span class="text-content">{{ row.content.reference_answer }}</span>
                </div>
                
                <!-- 评估标准 -->
                <div v-if="row.content.evaluation_criteria" class="preview-line">
                  <strong>评估标准：</strong>
                  <span class="text-content">{{ row.content.evaluation_criteria.scoring_rubric || '-' }}</span>
                </div>
                
                <!-- 关键点 -->
                <div v-if="row.content.evaluation_criteria?.key_points?.length" class="preview-line">
                  <strong>关键点：</strong>
                  <span class="text-content">{{ row.content.evaluation_criteria.key_points.join(', ') }}</span>
                </div>
              </template>
              
              <!-- SFT任务：显示SFT字段 -->
              <template v-else>
                <!-- 问题 -->
                <div v-if="getQuestion(row.content)" class="preview-line">
                  <strong>问题：</strong>
                  <span class="text-content">{{ getQuestion(row.content) }}</span>
                </div>
                
                <!-- 推理路径（COT 和 Multi-hop） -->
                <div v-if="(getGenerationMode(row) === 'cot' || getGenerationMode(row) === 'multi_hop') && getReasoningPath(row.content)" class="preview-line">
                  <strong>推理路径：</strong>
                  <span class="text-content reasoning-path">{{ getReasoningPath(row.content) }}</span>
                </div>
                
                <!-- COT 特有：思考过程 -->
                <div v-if="getGenerationMode(row) === 'cot' && getThinkingProcess(row.content)" class="preview-line">
                  <strong>思考过程：</strong>
                  <span class="text-content thinking-process">{{ getThinkingProcess(row.content) }}</span>
                </div>
                
                <!-- COT 特有：最终答案 -->
                <div v-if="getGenerationMode(row) === 'cot' && getFinalAnswer(row.content)" class="preview-line">
                  <strong>最终答案：</strong>
                  <span class="text-content final-answer">{{ getFinalAnswer(row.content) }}</span>
                </div>
                
                <!-- COT 向后兼容：如果没有分离的字段，显示完整答案 -->
                <div v-if="getGenerationMode(row) === 'cot' && !getThinkingProcess(row.content) && !getFinalAnswer(row.content) && getAnswer(row.content)" class="preview-line">
                  <strong>答案：</strong>
                  <span class="text-content">{{ getAnswer(row.content) }}</span>
                </div>
                
                <!-- 非 COT：显示普通答案 -->
                <div v-if="getGenerationMode(row) !== 'cot' && getAnswer(row.content)" class="preview-line">
                  <strong>答案：</strong>
                  <span class="text-content">{{ getAnswer(row.content) }}</span>
                </div>
                
                <!-- 显示上下文信息 -->
                <div v-if="row.content.context" class="context-info">
                  <el-tag size="small" type="info">图谱信息</el-tag>
                  <span class="context-text">
                    实体数: {{ row.content.context.nodes?.length || 0 }} | 
                    关系数: {{ row.content.context.edges?.length || 0 }}
                  </span>
                </div>
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="生成模式" width="90">
          <template #default="{ row }">
            <span v-if="getGenerationMode(row)" class="text-normal">
              {{ getGenerationMode(row) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="100">
          <template #default="{ row }">
            <span class="text-normal">
              {{ STATUS_TEXT_MAP[row.review_status] || row.review_status }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="自动评分" width="85">
          <template #default="{ row }">
            <span v-if="row.auto_review_score !== null && row.auto_review_score !== undefined">
              {{ (row.auto_review_score * 100).toFixed(0) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="审核人" width="100" show-overflow-tooltip>
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
    </div>

    <!-- 分页组件 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100, 200]"
        :total="filteredData.length"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handlePageSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- "前往顶部"按钮 - 浮动在右下角 -->
    <div 
      class="go-to-top-float" 
      :class="{ 'visible': showGoToTop }"
      @click="scrollToTop"
    >
      <el-icon><ArrowUp /></el-icon>
      <span>顶部</span>
    </div>

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

    <!-- 导出数据对话框 -->
    <el-dialog
      v-model="exportDialogVisible"
      title="导出数据"
      width="500px"
    >
      <el-form label-width="120px">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportFormat">
            <el-radio label="json">JSON 格式</el-radio>
            <el-radio label="csv">CSV 格式</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="数据范围">
          <el-alert
            title="将导出所有问答对数据，包含审核状态信息"
            type="info"
            :closable="false"
          />
        </el-form-item>
        <el-form-item label="可选字段" v-if="exportFormat === 'csv'">
          <el-checkbox-group v-model="exportFields">
            <el-checkbox label="context">上下文</el-checkbox>
            <el-checkbox label="graph">图谱</el-checkbox>
            <el-checkbox label="source_chunks">来源片段</el-checkbox>
            <el-checkbox label="source_documents">来源文档</el-checkbox>
            <el-checkbox label="metadata">元数据</el-checkbox>
          </el-checkbox-group>
          <div style="margin-top: 8px; font-size: 12px; color: #909399;">
            注：这些字段可能包含复杂数据，仅在需要时勾选
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmExport" :loading="exportLoading">
          <el-icon><Download /></el-icon>
          确认导出
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
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

import type { DataItem, ReviewStats, DataContent } from '@/api/types'
import api from '@/api'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  MagicStick,
  Download,
  View,
  Check,
  Close,
  ArrowUp
} from '@element-plus/icons-vue'

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
const modeFilter = ref('')
const selectedItems = ref<DataItem[]>([])
const autoReviewDialogVisible = ref(false)
const autoReviewLoading = ref(false)
const exportDialogVisible = ref(false)
const exportLoading = ref(false)
const exportFormat = ref<'json' | 'csv'>('json')
const exportFields = ref<string[]>([])  // 可选字段列表
const tableRef = ref<any>(null)
const isTableUpdating = ref(false)  // 标志：表格数据正在更新或清除选择中

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)  // 默认每页20条

// "前往顶部"按钮显示控制
const showGoToTop = ref(false)

const autoReviewForm = ref({
  scope: 'pending',
  threshold: 70,
  autoApprove: true,
  autoReject: false
})

// 过滤后的数据
const filteredData = computed(() => {
  let result = data.value
  // 按审核状态筛选
  if (statusFilter.value) {
    result = result.filter(item => item.review_status === statusFilter.value)
  }
  // 按生成模式筛选
  if (modeFilter.value) {
    result = result.filter(item => {
      const mode = getGenerationMode(item)
      return mode === modeFilter.value
    })
  }
  return result
})

// 分页后的数据
const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredData.value.slice(start, end)
})

// 刷新数据
const refreshData = async () => {
  // 防止重复调用导致的卡死
  if (loading.value) {
    console.warn('[refreshData] 刷新正在进行中，跳过重复调用')
    return
  }
  
  console.log('[refreshData] 开始刷新数据')
  loading.value = true
  isTableUpdating.value = true // 标记开始更新，阻止 selection-change 副作用
  
  // 先清空选中项并清除表格选择
  selectedItems.value = []
  if (tableRef.value) {
    try {
      tableRef.value.clearSelection()
      console.log('[refreshData] 表格选择已提前清除')
    } catch (e) {
      console.warn('[refreshData] 清除表格选择失败:', e)
    }
  }
  
  try {
    console.log('[refreshData] 发送API请求')
    const [dataRes, statsRes] = await Promise.all([
      api.getReviewData(taskId),
      api.getReviewStats(taskId)
    ]) as [any, any]  // 因为拦截器已解包

    console.log('[refreshData] API请求完成')
    
    // 响应拦截器已经返回 response.data，所以直接访问
    if (dataRes?.success && dataRes.data) {
      data.value = dataRes.data
      console.log('[refreshData] 数据已更新，条数:', dataRes.data.length)
    } else {
      data.value = []
      console.log('[refreshData] 数据为空或失败')
    }

    if (statsRes?.success && statsRes.data) {
      stats.value = statsRes.data
    }
    
    console.log('[refreshData] 刷新完成')
  } catch (error) {
    console.error('[refreshData] 刷新数据失败', error)
    selectedItems.value = []
  } finally {
    loading.value = false
    // 缩短延迟时间，因为后端已经优化
    setTimeout(() => {
      isTableUpdating.value = false
      console.log('[refreshData] isTableUpdating重置')
    }, 100)
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

// 获取问题/指令内容（兼容不同数据格式）
const getQuestion = (content: DataContent): string => {
  // Alpaca 格式
  if ('instruction' in content && content.instruction) {
    return content.instruction
  }
  // Sharegpt 格式
  if ('conversations' in content && Array.isArray(content.conversations)) {
    const humanMsg = content.conversations.find(msg => msg.from === 'human')
    if (humanMsg?.value) {
      return humanMsg.value
    }
  }
  // ChatML 格式
  if ('messages' in content && Array.isArray(content.messages)) {
    const userMsg = content.messages.find(msg => msg.role === 'user')
    if (userMsg?.content) {
      return userMsg.content
    }
  }
  return ''
}

// 获取答案/输出内容（兼容不同数据格式）
const getAnswer = (content: DataContent): string => {
  // Alpaca 格式
  if ('output' in content && content.output) {
    return content.output
  }
  // Sharegpt 格式
  if ('conversations' in content && Array.isArray(content.conversations)) {
    const gptMsg = content.conversations.find(msg => msg.from === 'gpt')
    if (gptMsg?.value) {
      return gptMsg.value
    }
  }
  // ChatML 格式
  if ('messages' in content && Array.isArray(content.messages)) {
    const assistantMsg = content.messages.find(msg => msg.role === 'assistant')
    if (assistantMsg?.content) {
      return assistantMsg.content
    }
  }
  return ''
}

// 获取推理路径（COT 格式）
const getReasoningPath = (content: DataContent): string => {
  if ('reasoning_path' in content && content.reasoning_path) {
    return content.reasoning_path
  }
  return ''
}

// 获取思考过程（COT 特有）
const getThinkingProcess = (content: DataContent): string => {
  if ('thinking_process' in content && content.thinking_process) {
    return content.thinking_process
  }
  return ''
}

// 获取最终答案（COT 特有）
const getFinalAnswer = (content: DataContent): string => {
  if ('final_answer' in content && content.final_answer) {
    return content.final_answer
  }
  return ''
}

// 判断是否是评测任务项
const isEvaluationItem = (content: any): boolean => {
  // 评测项包含 reference_answer 或 evaluation_criteria 字段
  return content && (
    ('reference_answer' in content) ||
    ('evaluation_criteria' in content) ||
    (content.id && typeof content.id === 'string' && content.id.startsWith('eval_'))
  )
}

// 获取难度标签类型
const getDifficultyTagType = (difficulty: string): string => {
  const typeMap: Record<string, string> = {
    'easy': 'success',
    'medium': 'warning',
    'hard': 'danger'
  }
  return typeMap[difficulty] || 'info'
}


// 分页变化处理
const handlePageChange = (page: number) => {
  currentPage.value = page
  // 分页变化时清空选择
  selectedItems.value = []
  
  // 滚动到表格顶部
  nextTick(() => {
    const tableEl = document.querySelector('.el-table__body-wrapper')
    if (tableEl) {
      tableEl.scrollTop = 0
    }
  })
}

// 每页数量变化处理
const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1  // 重置到第一页
  // 分页变化时清空选择
  selectedItems.value = []
  
  // 保存到 localStorage
  localStorage.setItem('review_page_size', String(size))
  
  // 滚动到表格顶部
  nextTick(() => {
    const tableEl = document.querySelector('.el-table__body-wrapper')
    if (tableEl) {
      tableEl.scrollTop = 0
    }
  })
}

// 选择变化
const handleSelectionChange = (selection: DataItem[]) => {
  console.log('[handleSelectionChange] 触发，isTableUpdating:', isTableUpdating.value, '选中数:', selection.length)
  
  // 如果表格正在更新或清除选择，忽略此次更新
  if (isTableUpdating.value) {
    console.log('[handleSelectionChange] isTableUpdating=true，忽略')
    return
  }
  
  // 过滤掉不在当前分页数据中的选中项，避免状态不一致
  const currentItemIds = new Set(paginatedData.value.map(item => item.item_id))
  selectedItems.value = selection.filter(item => currentItemIds.has(item.item_id))
  console.log('[handleSelectionChange] 更新selectedItems，条数:', selectedItems.value.length)
}

// 查看详情（跳转到详情页面）
const viewDetail = (item: DataItem) => {
  router.push(`/review/${taskId}/detail/${item.item_id}`)
}

// 通过单个
const approveItem = async (item: DataItem) => {
  try {
    await api.reviewItem({
      task_id: taskId,
      item_id: item.item_id,
      review_status: 'approved',
      reviewer: '手动审核'
    })

    ElMessage.success('审核通过')
    await refreshData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 拒绝单个
const rejectItem = async (item: DataItem) => {
  try {
    await api.reviewItem({
      task_id: taskId,
      item_id: item.item_id,
      review_status: 'rejected',
      reviewer: '手动审核'
    })

    ElMessage.success('已拒绝')
    await refreshData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}


// 批量通过
const batchApprove = async () => {
  if (selectedItems.value.length === 0) return
  if (loading.value) {
    console.warn('[batchApprove] 正在刷新中，跳过')
    return
  }

  console.log('[batchApprove] 开始批量通过')
  const itemCount = selectedItems.value.length
  const itemIds = selectedItems.value.map(item => item.item_id)

  try {
    console.log('[batchApprove] 发送批量审核请求')
    await api.batchReview({
      task_id: taskId,
      item_ids: itemIds,
      review_status: 'approved',
      reviewer: '批量审核'
    })

    console.log('[batchApprove] 批量审核完成')
    ElMessage.success(`批量通过成功，共 ${itemCount} 条`)
    
    // 调用refreshData（会自动处理选择清除）
    console.log('[batchApprove] 调用refreshData')
    await refreshData()
    console.log('[batchApprove] refreshData完成')
  } catch (error) {
    console.error('[batchApprove] 批量操作失败', error)
    ElMessage.error('批量操作失败')
  }
}

// 批量拒绝
const batchReject = async () => {
  if (selectedItems.value.length === 0) return
  if (loading.value) {
    console.warn('[batchReject] 正在刷新中，跳过')
    return
  }

  console.log('[batchReject] 开始批量拒绝')
  const itemCount = selectedItems.value.length
  const itemIds = selectedItems.value.map(item => item.item_id)

  try {
    console.log('[batchReject] 发送批量审核请求')
    await api.batchReview({
      task_id: taskId,
      item_ids: itemIds,
      review_status: 'rejected',
      reviewer: '批量审核'
    })

    console.log('[batchReject] 批量拒绝完成')
    ElMessage.success(`批量拒绝成功，共 ${itemCount} 条`)
    
    console.log('[batchReject] 调用refreshData')
    await refreshData()
    console.log('[batchReject] refreshData完成')
  } catch (error) {
    console.error('[batchReject] 批量操作失败', error)
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

  console.log('[startAutoReview] 开始自动审核', itemIds.length, '条数据')
  autoReviewLoading.value = true
  try {
    await api.autoReview({
      item_ids: itemIds,
      threshold: autoReviewForm.value.threshold / 100,
      auto_approve: autoReviewForm.value.autoApprove,
      auto_reject: autoReviewForm.value.autoReject
    })

    console.log('[startAutoReview] 自动审核完成')
    ElMessage.success(`自动审核完成，共审核 ${itemIds.length} 条数据`)
    autoReviewDialogVisible.value = false
    
    console.log('[startAutoReview] 调用refreshData')
    await refreshData()
    console.log('[startAutoReview] refreshData完成')
  } catch (error) {
    console.error('[startAutoReview] 自动审核失败', error)
    ElMessage.error('自动审核失败')
  } finally {
    autoReviewLoading.value = false
  }
}

// 显示导出对话框
const showExportDialog = () => {
  exportDialogVisible.value = true
}

// 确认导出
const confirmExport = async () => {
  exportLoading.value = true
  try {
    // 导出所有数据（不过滤状态），后端只生成 JSON
    await api.exportReviewedData(taskId, 'all')
    
    // 下载文件（根据选择的格式，后端会即时转换）
    const blob = await api.downloadReviewedData(taskId, exportFormat.value, exportFields.value) as unknown as Blob
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // 根据格式设置文件名
    const fileExt = exportFormat.value === 'csv' ? 'csv' : 'json'
    link.download = `${taskId}_all_data.${fileExt}`
    
    link.click()
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
    exportDialogVisible.value = false
  } catch (error) {
    console.error('导出失败', error)
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
}


// 监听筛选状态变化，重置到第一页
watch([statusFilter, modeFilter], () => {
  currentPage.value = 1
})

// 滚动到顶部
const scrollToTop = () => {
  const mainEl = document.querySelector('.layout-main')
  if (mainEl) {
    mainEl.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// 监听滚动，控制"前往顶部"按钮显示
let mainElement: Element | null = null
const handleScroll = () => {
  if (mainElement) {
    // 滚动超过 200px 时显示按钮
    showGoToTop.value = mainElement.scrollTop > 200
  }
}

// 初始化
onMounted(() => {
  // 从 localStorage 恢复每页数量设置
  const savedPageSize = localStorage.getItem('review_page_size')
  if (savedPageSize) {
    const size = parseInt(savedPageSize, 10)
    if ([10, 20, 50, 100, 200].includes(size)) {
      pageSize.value = size
    }
  }
  
  // 添加滚动监听
  setTimeout(() => {
    mainElement = document.querySelector('.layout-main')
    if (mainElement) {
      mainElement.addEventListener('scroll', handleScroll)
    }
  }, 100)
  
  refreshData()
})

// 清理
onUnmounted(() => {
  if (mainElement) {
    mainElement.removeEventListener('scroll', handleScroll)
  }
})
</script>

<style scoped>
.review-container {
  display: flex;
  flex-direction: column;
  gap: 0;
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 数据列表头部（直接在页面中展示） */
.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
  margin-bottom: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
  flex: 1;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
  color: white;
}

.stats-inline {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.stat-inline-item {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
}

.stat-inline-item strong {
  font-size: 16px;
  font-weight: 700;
  margin-left: 4px;
}

.stat-inline-item.pending strong {
  color: #ffd666;
}

.stat-inline-item.approved strong {
  color: #95de64;
}

.stat-inline-item.rejected strong {
  color: #ff7875;
}

.stat-inline-item.modified strong {
  color: #69c0ff;
}

.stat-inline-item.auto-approved strong {
  color: #b7eb8f;
}

.stat-inline-item.auto-rejected strong {
  color: #ffa39e;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

:deep(.review-header .el-button) {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  color: white;
  font-weight: 500;
  border-radius: 8px;
}

:deep(.review-header .el-button:hover) {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.3);
}

:deep(.review-header .el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: none;
}

:deep(.review-header .el-select .el-input__inner) {
  color: white;
}

:deep(.review-header .el-select .el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.7);
}

.table-wrapper {
  background: white;
  border-radius: 0 0 12px 12px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

:deep(.el-table) {
  border-radius: 0;
  font-size: 14px;
}

:deep(.el-table th) {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  font-weight: 600;
  color: #475569;
}

:deep(.el-table__row) {
  transition: all 0.2s;
}

:deep(.el-table__row:hover) {
  background: #f0f9ff !important;
}

.content-preview {
  font-size: 14px;
  line-height: 1.8;
  padding: 8px;
}

.preview-line {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #fafbfc;
  border-radius: 6px;
  border-left: 3px solid #409eff;
}

.preview-line:last-child {
  margin-bottom: 0;
}

.preview-line strong {
  color: #303133;
  margin-right: 8px;
  font-weight: 600;
  font-size: 13px;
}

.text-content {
  color: #475569;
  white-space: normal;
  word-wrap: break-word;
  word-break: break-word;
  line-height: 1.6;
}

.reasoning-path {
  color: #1e40af;
  font-style: italic;
  background: linear-gradient(135deg, #dbeafe 0%, #e0f2fe 100%);
  padding: 8px 12px;
  border-radius: 6px;
  display: inline-block;
  margin-top: 6px;
  border-left: 3px solid #3b82f6;
  font-weight: 500;
}

.thinking-process {
  color: #0f766e;
  background: linear-gradient(135deg, #ccfbf1 0%, #d1fae5 100%);
  padding: 10px 14px;
  border-radius: 6px;
  display: block;
  margin-top: 6px;
  border-left: 3px solid #14b8a6;
  font-weight: 400;
  line-height: 1.7;
}

.final-answer {
  color: #064e3b;
  background: linear-gradient(135deg, #d1fae5 0%, #dcfce7 100%);
  padding: 10px 14px;
  border-radius: 6px;
  display: block;
  margin-top: 6px;
  border-left: 3px solid #10b981;
  font-weight: 500;
  line-height: 1.7;
}

.text-normal {
  color: #303133;
  font-size: 14px;
  font-weight: 400;
}

.context-info {
  margin-top: 12px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #f0fdf4 0%, #f7fee7 100%);
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-left: 3px solid #10b981;
}

.context-text {
  font-size: 12px;
  color: #065f46;
  font-weight: 500;
}

:deep(.el-button) {
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.3s;
}

:deep(.el-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

:deep(.el-tag) {
  border-radius: 4px;
  font-weight: 500;
  padding: 4px 10px;
  border: none;
}

:deep(.el-tag--success) {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

:deep(.el-tag--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #f5a742 100%);
}

:deep(.el-tag--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%);
}

:deep(.el-tag--primary) {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

:deep(.el-tag--info) {
  background: linear-gradient(135deg, #909399 0%, #a6a9ad 100%);
}

:deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  margin: 0;
}

:deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
}

:deep(.el-dialog__close) {
  color: white;
}

:deep(.el-table) {
  --el-table-border-color: #e5e7eb;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: #fafbfc;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%);
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
  border: none;
}

:deep(.el-button--success:hover) {
  background: linear-gradient(135deg, #059669 0%, #10b981 100%);
}

:deep(.el-button--danger) {
  background: linear-gradient(135deg, #ef4444 0%, #f87171 100%);
  border: none;
}

:deep(.el-button--danger:hover) {
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
  border-top: 1px solid #e5e7eb;
}

:deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: #606266;
  --el-pagination-border-radius: 6px;
}

:deep(.el-pagination .el-pager li) {
  border-radius: 4px;
  margin: 0 2px;
  transition: all 0.2s;
}

:deep(.el-pagination .el-pager li:hover) {
  background-color: #f0f9ff;
  color: #409eff;
}

:deep(.el-pagination .el-pager li.is-active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
}

:deep(.el-pagination .btn-prev),
:deep(.el-pagination .btn-next) {
  border-radius: 4px;
  transition: all 0.2s;
}

:deep(.el-pagination .btn-prev:hover),
:deep(.el-pagination .btn-next:hover) {
  background-color: #f0f9ff;
  color: #409eff;
}

:deep(.el-pagination .el-select .el-input__wrapper) {
  border-radius: 4px;
}

/* "前往顶部"浮动按钮样式 */
.go-to-top-float {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 56px;
  height: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  cursor: pointer;
  color: white;
  font-weight: 500;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
  z-index: 999;
  opacity: 0;
  transform: translateY(20px) scale(0.8);
  pointer-events: none;
}

.go-to-top-float.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

.go-to-top-float:hover {
  transform: translateY(-4px) scale(1.1);
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.5);
}

.go-to-top-float .el-icon {
  font-size: 20px;
}

.go-to-top-float span {
  font-size: 10px;
  margin-top: -2px;
}
</style>


