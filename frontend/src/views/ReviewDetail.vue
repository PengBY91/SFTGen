<template>
  <div class="review-detail-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button @click="goBack" circle>
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h2>数据详情与编辑</h2>
      </div>
      <div class="header-actions">
        <el-button @click="handleCancel" v-if="isEditing">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saveLoading" v-if="isEditing">
          保存并通过
        </el-button>
        <el-button type="success" @click="handleApprove" :loading="actionLoading" v-if="!isEditing">
          通过
        </el-button>
        <el-button type="danger" @click="handleReject" :loading="actionLoading" v-if="!isEditing">
          拒绝
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="currentItem" class="detail-content">
      <!-- 左侧：可编辑内容 -->
      <div class="left-panel">
        <el-card class="content-card">
          <template #header>
            <div class="card-header">
              <span>问答内容</span>
              <el-button size="small" @click="startEdit" v-if="!isEditing">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
            </div>
          </template>

          <!-- 编辑模式 -->
          <el-form v-if="isEditing" label-width="100px" :model="editForm">
            <el-form-item label="问题/指令">
              <el-input
                v-model="editForm.instruction"
                type="textarea"
                :rows="4"
                placeholder="请输入问题或指令"
              />
            </el-form-item>
            <!-- 显示 COT 推理路径（只读） -->
            <el-form-item 
              v-if="getGenerationMode(currentItem) === 'cot' && currentItem.content.reasoning_path" 
              label="推理路径"
            >
              <el-input
                :model-value="currentItem.content.reasoning_path"
                type="textarea"
                :rows="3"
                readonly
                disabled
                placeholder="推理路径（只读）"
              />
            </el-form-item>
            <el-form-item label="输入" v-if="currentItem.content.input">
              <el-input
                v-model="editForm.input"
                type="textarea"
                :rows="2"
                placeholder="请输入输入内容（可选）"
              />
            </el-form-item>
            <el-form-item label="输出/答案">
              <el-input
                v-model="editForm.output"
                type="textarea"
                :rows="8"
                placeholder="请输入输出或答案"
              />
            </el-form-item>
            <el-form-item label="审核备注">
              <el-input
                v-model="editForm.comment"
                type="textarea"
                :rows="2"
                placeholder="请输入审核备注（可选）"
              />
            </el-form-item>
          </el-form>

          <!-- 只读模式 -->
          <div v-else class="read-only-content">
            <div class="content-section">
              <div class="section-label">问题/指令</div>
              <div class="section-content">{{ getQuestion(currentItem.content) || '-' }}</div>
            </div>
            <!-- 显示 COT 推理路径 -->
            <div class="content-section" v-if="getGenerationMode(currentItem) === 'cot' && getReasoningPath(currentItem.content)">
              <div class="section-label">推理路径</div>
              <div class="section-content reasoning-path-content">{{ getReasoningPath(currentItem.content) }}</div>
            </div>
            <div class="content-section" v-if="'input' in currentItem.content && currentItem.content.input">
              <div class="section-label">输入</div>
              <div class="section-content">{{ currentItem.content.input }}</div>
            </div>
            <div class="content-section">
              <div class="section-label">输出/答案</div>
              <div class="section-content">{{ getAnswer(currentItem.content) || '-' }}</div>
            </div>
          </div>
        </el-card>

        <!-- 基本信息 -->
        <el-card class="info-card">
          <template #header>基本信息</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ currentItem.item_id }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="STATUS_TYPE_MAP[currentItem.review_status] || 'info'">
                {{ STATUS_TEXT_MAP[currentItem.review_status] || currentItem.review_status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="生成模式" v-if="getGenerationMode(currentItem)">
              <el-tag type="info">{{ getGenerationMode(currentItem) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="自动评分" v-if="currentItem.auto_review_score">
              {{ (currentItem.auto_review_score * 100).toFixed(0) }}%
            </el-descriptions-item>
            <el-descriptions-item label="审核人" v-if="currentItem.reviewer">
              {{ currentItem.reviewer }}
            </el-descriptions-item>
            <el-descriptions-item label="审核时间" v-if="currentItem.review_time">
              {{ formatDate(currentItem.review_time) }}
            </el-descriptions-item>
            <el-descriptions-item label="审核备注" v-if="currentItem.review_comment" :span="2">
              {{ currentItem.review_comment }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>

      <!-- 右侧：只读信息 -->
      <div class="right-panel">
        <!-- 上下文与图谱 -->
        <el-card class="context-card" v-if="currentItem.content.context?.edges && currentItem.content.context.edges.length > 0">
          <template #header>
            <div class="card-header">
              <el-icon><Connection /></el-icon>
              <span>上下文与图谱</span>
            </div>
          </template>

          <!-- 关系图谱 -->
          <div v-if="currentItem.content.context?.edges && currentItem.content.context.edges.length > 0" class="info-section">
            <div class="section-title">
              <el-icon><Share /></el-icon>
              <span>关系图谱 ({{ currentItem.content.context.edges.length }})</span>
            </div>
            <div class="relation-list">
              <div 
                v-for="(edge, idx) in currentItem.content.context.edges" 
                :key="`edge-${idx}`"
                class="relation-item"
              >
                <el-tag size="small" type="primary" effect="plain">{{ getEdgeSource(edge) }}</el-tag>
                <span class="relation-arrow">→</span>
                <el-tag size="small" type="success" effect="plain">{{ getEdgeTarget(edge) }}</el-tag>
                <span v-if="getEdgeDescription(edge)" class="relation-desc">: {{ getEdgeDescription(edge) }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 来源信息 -->
        <el-card class="source-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>来源信息</span>
            </div>
          </template>

          <!-- 展示chunks原文内容 -->
          <div v-if="currentItem.content.source_chunks && currentItem.content.source_chunks.length > 0" class="chunks-content">
            <div 
              v-for="(chunk, idx) in currentItem.content.source_chunks" 
              :key="`chunk-${idx}`"
              class="chunk-item"
            >
              <div class="chunk-header">
                <div class="chunk-title">
                  <el-icon><Document /></el-icon>
                  <span>文本块 {{ idx + 1 }}</span>
                  <el-tag size="small" type="info" v-if="chunk.chunk_id" style="margin-left: 8px;">
                    {{ chunk.chunk_id }}
                  </el-tag>
                </div>
                <div class="chunk-meta" v-if="chunk.type || chunk.language || chunk.length">
                  <span v-if="chunk.type" class="meta-item">类型: {{ chunk.type }}</span>
                  <span v-if="chunk.language" class="meta-item">语言: {{ chunk.language }}</span>
                  <span v-if="chunk.length" class="meta-item">长度: {{ chunk.length }} tokens</span>
                </div>
              </div>
              <div class="chunk-text" v-if="chunk.content">
                {{ chunk.content }}
              </div>
              <div class="chunk-text empty" v-else>
                暂无内容
              </div>
            </div>
          </div>
          <div v-else class="empty-chunks">
            <el-empty description="暂无来源信息" :image-size="80" />
          </div>
        </el-card>
      </div>
    </div>

    <!-- 文档内容弹窗 -->
    <el-dialog
      v-model="documentDialogVisible"
      title="原文档内容"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="currentDocument" class="document-content">
        <div class="doc-header">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="文档ID">{{ currentDocument.doc_id || currentDocument.chunk_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ currentDocument.type || '-' }}</el-descriptions-item>
            <el-descriptions-item label="语言" v-if="currentDocument.language">{{ currentDocument.language }}</el-descriptions-item>
            <el-descriptions-item label="长度" v-if="currentDocument.length">{{ currentDocument.length }} tokens</el-descriptions-item>
            <el-descriptions-item label="来源文档ID" v-if="currentDocument.full_doc_id" :span="2">{{ currentDocument.full_doc_id }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="doc-body">
          <div class="content-label">文档内容：</div>
          <div class="content-text">{{ getDocumentFullContent(currentDocument) }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { DataItem, DataContent } from '@/api/types'
import api from '@/api'
import { ElMessage, ElDialog } from 'element-plus'
import {
  ArrowLeft,
  Edit,
  Connection,
  Collection,
  Share,
  Document
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const taskId = route.params.id as string
const itemId = route.params.itemId as string

// 状态映射
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

const loading = ref(false)
const saveLoading = ref(false)
const actionLoading = ref(false)
const currentItem = ref<DataItem | null>(null)
const isEditing = ref(false)

const editForm = ref({
  instruction: '',
  input: '',
  output: '',
  comment: ''
})

// 文档内容弹窗
const documentDialogVisible = ref(false)
const currentDocument = ref<any>(null)

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const response = await api.getReviewData(taskId)
    if (response.success && response.data) {
      const item = response.data.find((item: DataItem) => item.item_id === itemId)
      if (item) {
        currentItem.value = item
        editForm.value = {
          instruction: getQuestion(item.content) || '',
          input: ('input' in item.content ? item.content.input : '') || '',
          output: getAnswer(item.content) || '',
          comment: item.review_comment || ''
        }
      } else {
        ElMessage.error('数据项不存在')
        goBack()
      }
    }
  } catch (error) {
    ElMessage.error('加载数据失败')
    goBack()
  } finally {
    loading.value = false
  }
}

// 开始编辑
const startEdit = () => {
  isEditing.value = true
}

// 取消编辑
const handleCancel = () => {
  if (currentItem.value) {
    editForm.value = {
      instruction: getQuestion(currentItem.value.content) || '',
      input: ('input' in currentItem.value.content ? currentItem.value.content.input : '') || '',
      output: getAnswer(currentItem.value.content) || '',
      comment: currentItem.value.review_comment || ''
    }
  }
  isEditing.value = false
}

// 保存编辑
const handleSave = async () => {
  if (!currentItem.value) return

  saveLoading.value = true
  try {
    const modifiedContent = {
      instruction: editForm.value.instruction,
      input: editForm.value.input,
      output: editForm.value.output
    }

    const response = await api.reviewItem({
      task_id: taskId,
      item_id: currentItem.value.item_id,
      review_status: 'modified',
      review_comment: editForm.value.comment,
      reviewer: authStore.user?.username || '未知用户',
      modified_content: modifiedContent
    })

    if (response.success) {
      ElMessage.success('保存成功')
      isEditing.value = false
      await loadData()
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saveLoading.value = false
  }
}

// 通过
const handleApprove = async () => {
  if (!currentItem.value) return

  actionLoading.value = true
  try {
    const response = await api.reviewItem({
      task_id: taskId,
      item_id: currentItem.value.item_id,
      review_status: 'approved',
      reviewer: authStore.user?.username || '未知用户'
    })

    if (response.success) {
      ElMessage.success('审核通过')
      await loadData()
    }
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    actionLoading.value = false
  }
}

// 拒绝
const handleReject = async () => {
  if (!currentItem.value) return

  actionLoading.value = true
  try {
    const response = await api.reviewItem({
      task_id: taskId,
      item_id: currentItem.value.item_id,
      review_status: 'rejected',
      reviewer: authStore.user?.username || '未知用户'
    })

    if (response.success) {
      ElMessage.success('已拒绝')
      await loadData()
    }
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    actionLoading.value = false
  }
}

// 返回
const goBack = () => {
  router.push(`/review/${taskId}`)
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

// 获取生成模式（从多个可能的位置）
const getGenerationMode = (item: DataItem | null): string => {
  if (!item) return ''
  // 优先从 content.mode 获取
  if (item.content?.mode) {
    return item.content.mode
  }
  // 其次从 content.metadata.generation_mode 获取
  if (item.content?.metadata?.generation_mode) {
    return item.content.metadata.generation_mode
  }
  // 最后从顶层 mode 获取（如果存在）
  if ((item as any).mode) {
    return (item as any).mode
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

// 辅助函数
const getNodeName = (node: any): string => {
  if (typeof node === 'string') return node
  return node?.name || node?.id || '未知实体'
}

const getNodeDescription = (node: any): string => {
  if (typeof node === 'string') return ''
  return node?.description || node?.desc || ''
}

const getNodeTooltip = (node: any): string => {
  const name = getNodeName(node)
  const desc = getNodeDescription(node)
  return desc ? `${name}: ${desc}` : name
}

const hasNodeDescriptions = (nodes: any[]): boolean => {
  if (!nodes || nodes.length === 0) return false
  return nodes.some(node => {
    if (typeof node === 'string') return false
    return node?.description || node?.desc
  })
}

const getEdgeSource = (edge: any): string => {
  if (typeof edge === 'object' && edge.source) return edge.source
  if (Array.isArray(edge) && edge.length > 0) return edge[0]
  return '未知'
}

const getEdgeTarget = (edge: any): string => {
  if (typeof edge === 'object' && edge.target) return edge.target
  if (Array.isArray(edge) && edge.length > 1) return edge[1]
  return '未知'
}

const getEdgeDescription = (edge: any): string => {
  if (typeof edge === 'object' && edge.description) return edge.description
  if (typeof edge === 'object' && edge.relation) return edge.relation
  return ''
}

// 显示文档内容
const showDocumentContent = (doc: any) => {
  currentDocument.value = doc
  documentDialogVisible.value = true
}

// 显示chunk内容
const showChunkContent = (chunk: any) => {
  // 将chunk转换为类似文档的格式显示
  currentDocument.value = {
    doc_id: chunk.chunk_id || '未知',
    type: chunk.type || '文本块',
    content: chunk.content || '',
    full_doc_id: chunk.full_doc_id || '',
    chunk_id: chunk.chunk_id,
    language: chunk.language,
    length: chunk.length
  }
  documentDialogVisible.value = true
}

// 获取文档完整内容
const getDocumentFullContent = (doc: any): string => {
  // 如果有完整内容，直接返回
  if (doc.content && doc.content.length > 200) return doc.content
  // 如果有预览内容，返回预览
  if (doc.content_preview) {
    // 如果预览内容以...结尾，说明是截断的，尝试获取完整内容
    if (doc.content_preview.endsWith('...')) {
      return doc.content_preview + '\n\n（注：此为预览内容，完整内容可能需要从存储中获取）'
    }
    return doc.content_preview
  }
  // 如果是chunk，显示chunk内容
  if (doc.chunk_id && doc.content) {
    return doc.content
  }
  return '暂无内容'
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.review-detail-container {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.loading-container {
  padding: 40px;
}

.detail-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.content-card,
.info-card,
.context-card,
.source-card,
.metadata-card,
.json-card {
  width: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.read-only-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.content-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.section-content {
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.8;
  color: #606266;
}

.reasoning-path-content {
  background-color: #ecf5ff;
  border-left: 3px solid #409eff;
  color: #409eff;
  font-style: italic;
}

.info-section {
  margin-bottom: 20px;
}

.info-section:last-child {
  margin-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.entity-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.entity-tag {
  margin: 0;
  cursor: pointer;
}

.entity-detail {
  margin-bottom: 8px;
  padding: 8px;
  background-color: #ffffff;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.entity-detail strong {
  color: #303133;
  margin-right: 8px;
}

.entity-desc-text {
  color: #606266;
  line-height: 1.6;
}

.relation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.relation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background-color: #ffffff;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
}

.relation-arrow {
  color: #909399;
  font-size: 16px;
}

.relation-desc {
  color: #606266;
  font-size: 13px;
  margin-left: 4px;
}

.graph-info {
  margin-bottom: 12px;
  padding: 12px;
  background-color: #f0f9ff;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.info-item {
  margin-bottom: 6px;
  font-size: 14px;
  color: #606266;
}

.info-item strong {
  color: #303133;
  margin-right: 8px;
}

.detail-collapse {
  margin-top: 12px;
}

.graph-content {
  background-color: #ffffff;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
}

.chunk-detail,
.doc-detail {
  padding: 12px;
  background-color: #ffffff;
  border-radius: 4px;
}

.detail-row {
  margin-bottom: 10px;
  font-size: 14px;
  line-height: 1.6;
}

.detail-row strong {
  color: #303133;
  margin-right: 8px;
}

.chunk-content,
.doc-content {
  margin-top: 8px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
}

.metadata-content {
  margin-top: 8px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  max-height: 200px;
  overflow-y: auto;
}

.entity-relation-section {
  margin-bottom: 20px;
}

.entity-relation-section:last-child {
  margin-bottom: 0;
}

.subsection-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}

.document-links,
.chunk-links {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.doc-link,
.chunk-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.doc-link:hover,
.chunk-link:hover {
  background-color: #e4e7ed;
  color: #409eff;
}

.document-content {
  padding: 20px 0;
}

.doc-header {
  margin-bottom: 20px;
}

.doc-body {
  margin-top: 20px;
}

.content-label {
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}

.content-text {
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.8;
  max-height: 500px;
  overflow-y: auto;
  color: #606266;
}

.chunks-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chunk-item {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  background-color: #ffffff;
}

.chunk-header {
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.chunk-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.chunk-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.meta-item {
  display: flex;
  align-items: center;
}

.chunk-text {
  padding: 16px;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.8;
  color: #606266;
  background-color: #ffffff;
}

.chunk-text.empty {
  color: #909399;
  font-style: italic;
}

.empty-chunks {
  padding: 40px 0;
  text-align: center;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .detail-content {
    grid-template-columns: 1fr;
  }
}
</style>


