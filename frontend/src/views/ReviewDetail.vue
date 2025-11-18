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
        <el-button type="success" @click="handleApprove" :loading="actionLoading" v-else>
          通过
        </el-button>
        <el-button type="danger" @click="handleReject" :loading="actionLoading" v-else>
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
            <el-form-item label="审核人">
              <el-input v-model="editForm.reviewer" placeholder="请输入审核人姓名" />
            </el-form-item>
          </el-form>

          <!-- 只读模式 -->
          <div v-else class="read-only-content">
            <div class="content-section">
              <div class="section-label">问题/指令</div>
              <div class="section-content">{{ currentItem.content.instruction || '-' }}</div>
            </div>
            <div class="content-section" v-if="currentItem.content.input">
              <div class="section-label">输入</div>
              <div class="section-content">{{ currentItem.content.input }}</div>
            </div>
            <div class="content-section">
              <div class="section-label">输出/答案</div>
              <div class="section-content">{{ currentItem.content.output || '-' }}</div>
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
            <el-descriptions-item label="生成模式" v-if="currentItem.content.mode">
              <el-tag type="info">{{ currentItem.content.mode }}</el-tag>
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
        <el-card class="context-card" v-if="currentItem.content.context || currentItem.content.graph">
          <template #header>
            <div class="card-header">
              <el-icon><Connection /></el-icon>
              <span>上下文与图谱</span>
            </div>
          </template>

          <!-- 实体信息 -->
          <div v-if="currentItem.content.context?.nodes && currentItem.content.context.nodes.length > 0" class="info-section">
            <div class="section-title">
              <el-icon><Collection /></el-icon>
              <span>实体 ({{ currentItem.content.context.nodes.length }})</span>
            </div>
            <div class="entity-list">
              <el-tag 
                v-for="(node, idx) in currentItem.content.context.nodes" 
                :key="`node-${idx}`"
                class="entity-tag"
                type="info"
                effect="plain"
                :title="getNodeTooltip(node)"
              >
                {{ getNodeName(node) }}
              </el-tag>
            </div>
            <el-collapse v-if="hasNodeDescriptions(currentItem.content.context.nodes)" class="detail-collapse">
              <el-collapse-item title="查看实体详情" name="entities">
                <div v-for="(node, idx) in currentItem.content.context.nodes" :key="`desc-${idx}`" class="entity-detail">
                  <strong>{{ getNodeName(node) }}:</strong>
                  <span class="entity-desc-text">{{ getNodeDescription(node) || '无描述' }}</span>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- 关系信息 -->
          <div v-if="currentItem.content.context?.edges && currentItem.content.context.edges.length > 0" class="info-section">
            <div class="section-title">
              <el-icon><Share /></el-icon>
              <span>关系 ({{ currentItem.content.context.edges.length }})</span>
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

          <!-- 图谱结构 -->
          <div v-if="currentItem.content.graph" class="info-section">
            <div class="section-title">图谱结构</div>
            <div class="graph-info">
              <div class="info-item" v-if="currentItem.content.graph.entity_count">
                <strong>实体数量:</strong> {{ currentItem.content.graph.entity_count }}
              </div>
              <div class="info-item" v-if="currentItem.content.graph.relationship_count">
                <strong>关系数量:</strong> {{ currentItem.content.graph.relationship_count }}
              </div>
            </div>
            <el-collapse class="detail-collapse">
              <el-collapse-item title="查看完整图谱结构 (JSON)" name="graph">
                <pre class="graph-content">{{ JSON.stringify(currentItem.content.graph, null, 2) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>

        <!-- 来源信息 -->
        <el-card class="source-card" v-if="currentItem.content.source_chunks || currentItem.content.source_documents">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>来源信息</span>
            </div>
          </template>

          <!-- 来源Chunks -->
          <div v-if="currentItem.content.source_chunks && currentItem.content.source_chunks.length > 0" class="info-section">
            <div class="section-title">来源文本块 ({{ currentItem.content.source_chunks.length }})</div>
            <el-collapse>
              <el-collapse-item 
                v-for="(chunk, idx) in currentItem.content.source_chunks" 
                :key="`chunk-${idx}`"
                :title="`文本块 ${idx + 1}: ${chunk.chunk_id || '未知'}`"
                :name="`chunk-${idx}`"
              >
                <div class="chunk-detail">
                  <div class="detail-row">
                    <strong>Chunk ID:</strong> {{ chunk.chunk_id }}
                  </div>
                  <div class="detail-row">
                    <strong>类型:</strong> {{ chunk.type }}
                  </div>
                  <div class="detail-row" v-if="chunk.language">
                    <strong>语言:</strong> {{ chunk.language }}
                  </div>
                  <div class="detail-row" v-if="chunk.length">
                    <strong>长度:</strong> {{ chunk.length }} tokens
                  </div>
                  <div class="detail-row" v-if="chunk.full_doc_id">
                    <strong>来源文档ID:</strong> {{ chunk.full_doc_id }}
                  </div>
                  <div class="detail-row" v-if="chunk.content">
                    <strong>内容:</strong>
                    <div class="chunk-content">{{ chunk.content }}</div>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- 来源文档 -->
          <div v-if="currentItem.content.source_documents && currentItem.content.source_documents.length > 0" class="info-section">
            <div class="section-title">来源文档 ({{ currentItem.content.source_documents.length }})</div>
            <el-collapse>
              <el-collapse-item 
                v-for="(doc, idx) in currentItem.content.source_documents" 
                :key="`doc-${idx}`"
                :title="`文档 ${idx + 1}: ${doc.doc_id || '未知'}`"
                :name="`doc-${idx}`"
              >
                <div class="doc-detail">
                  <div class="detail-row">
                    <strong>文档ID:</strong> {{ doc.doc_id }}
                  </div>
                  <div class="detail-row">
                    <strong>类型:</strong> {{ doc.type }}
                  </div>
                  <div class="detail-row" v-if="doc.content_preview">
                    <strong>内容预览:</strong>
                    <div class="doc-content">{{ doc.content_preview }}...</div>
                  </div>
                  <div class="detail-row" v-if="doc.metadata && Object.keys(doc.metadata).length > 0">
                    <strong>元数据:</strong>
                    <pre class="metadata-content">{{ JSON.stringify(doc.metadata, null, 2) }}</pre>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>

        <!-- 元数据 -->
        <el-card class="metadata-card" v-if="currentItem.content.metadata">
          <template #header>
            <div class="card-header">
              <el-icon><InfoFilled /></el-icon>
              <span>元数据</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="生成模式" v-if="currentItem.content.metadata.generation_mode">
              {{ currentItem.content.metadata.generation_mode }}
            </el-descriptions-item>
            <el-descriptions-item label="批次大小" v-if="currentItem.content.metadata.batch_size">
              {{ currentItem.content.metadata.batch_size }}
            </el-descriptions-item>
            <el-descriptions-item label="包含Chunks" v-if="currentItem.content.metadata.has_chunks !== undefined">
              {{ currentItem.content.metadata.has_chunks ? '是' : '否' }}
            </el-descriptions-item>
            <el-descriptions-item label="包含文档" v-if="currentItem.content.metadata.has_documents !== undefined">
              {{ currentItem.content.metadata.has_documents ? '是' : '否' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 完整JSON -->
        <el-card class="json-card">
          <template #header>
            <div class="card-header">
              <el-icon><DocumentCopy /></el-icon>
              <span>完整数据 (JSON)</span>
            </div>
          </template>
          <el-collapse>
            <el-collapse-item title="展开查看完整 JSON 数据" name="full-json">
              <pre class="json-content">{{ JSON.stringify(currentItem.content, null, 2) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { DataItem } from '@/api/types'
import api from '@/api'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Edit,
  Connection,
  Collection,
  Share,
  Document,
  InfoFilled,
  DocumentCopy
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
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
  comment: '',
  reviewer: ''
})

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
          instruction: item.content.instruction || '',
          input: item.content.input || '',
          output: item.content.output || '',
          comment: item.review_comment || '',
          reviewer: item.reviewer || ''
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
      instruction: currentItem.value.content.instruction || '',
      input: currentItem.value.content.input || '',
      output: currentItem.value.content.output || '',
      comment: currentItem.value.review_comment || '',
      reviewer: currentItem.value.reviewer || ''
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
      reviewer: editForm.value.reviewer || '手动审核',
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
      reviewer: '手动审核'
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
      reviewer: '手动审核'
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

.json-content {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 500px;
  overflow-y: auto;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .detail-content {
    grid-template-columns: 1fr;
  }
}
</style>


