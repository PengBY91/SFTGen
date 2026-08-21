<template>
  <div class="datog-taxonomies-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>意图树管理</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            新建意图树
          </el-button>
        </div>
      </template>

      <el-table :data="taxonomies" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="200">
          <template #default="{ row }">
            <div class="taxonomy-name">
              <el-icon><Grid /></el-icon>
              <span>{{ row.name }}</span>
              <el-tag v-if="row.builtin" size="small" type="warning">内置示例</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="domain" label="领域" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.domain" size="small">{{ row.domain }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="300" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span v-if="row.created_at">{{ formatDate(row.created_at) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="handleView(row)">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button size="small" type="primary" :disabled="row.builtin" @click="handleEdit(row)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button size="small" type="danger" :disabled="row.builtin" @click="handleDelete(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && taxonomies.length === 0" description="暂无意图树，点击右上角新建">
        <el-button type="primary" @click="showCreateDialog = true">新建意图树</el-button>
      </el-empty>
    </el-card>

    <!-- 创建/编辑意图树对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="isEditMode ? '编辑意图树' : '新建意图树'"
      width="600px"
    >
      <el-form :model="formData" label-width="120px">
        <el-form-item label="领域名称" required>
          <el-input v-model="formData.domain" placeholder="如：finance, medical, education" />
        </el-form-item>

        <el-form-item label="意图树路径" required>
          <el-input v-model="formData.taxonomy_path" placeholder="请输入意图树文件路径" />
        </el-form-item>

        <el-divider>DA-ToG 配置</el-divider>

        <el-form-item label="采样策略">
          <el-select v-model="formData.sampling_strategy">
            <el-option label="Coverage (覆盖率优先)" value="coverage" />
            <el-option label="Uniform Branch (均分支)" value="uniform_branch" />
            <el-option label="Depth Weighted (深度加权)" value="depth_weighted" />
          </el-select>
        </el-form-item>

        <el-form-item label="最大跳数">
          <el-input-number v-model="formData.graph_max_hops" :min="1" :max="5" />
        </el-form-item>

        <el-form-item label="最大节点数">
          <el-input-number v-model="formData.graph_max_nodes" :min="5" :max="100" />
        </el-form-item>

        <el-form-item label="序列化格式">
          <el-radio-group v-model="formData.serialization_format">
            <el-radio label="natural_language">自然语言</el-radio>
            <el-radio label="markdown">Markdown</el-radio>
            <el-radio label="json">JSON</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="评审器类型">
          <el-radio-group v-model="formData.critic_type">
            <el-radio label="llm">LLM评审器</el-radio>
            <el-radio label="rule">规则评审器</el-radio>
            <el-radio label="none">不使用评审</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="最低评分" v-if="formData.critic_type !== 'none'">
          <el-slider
            v-model="formData.critic_min_score"
            :min="0"
            :max="1"
            :step="0.1"
            show-input
          />
        </el-form-item>

        <el-form-item label="目标QA数量">
          <el-input-number
            v-model="formData.generation_target_qa_pairs"
            :min="10"
            :max="10000"
          />
        </el-form-item>

        <el-form-item label="批处理大小">
          <el-input-number v-model="formData.batch_size" :min="1" :max="50" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 查看意图树对话框 -->
    <el-dialog
      v-model="showViewDialog"
      title="意图树详情"
      width="900px"
      top="5vh"
    >
      <div v-if="selectedTaxonomy" class="taxonomy-view">
        <!-- 统计信息 -->
        <div class="stats-section">
          <h4>统计信息</h4>
          <el-row :gutter="16">
            <el-col :span="6">
              <el-statistic title="节点总数" :value="taxonomyStatistics?.total_nodes || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="最大深度" :value="taxonomyStatistics?.max_depth || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="根节点" :value="taxonomyStatistics?.root_count || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="叶节点" :value="taxonomyStatistics?.leaf_count || 0" />
            </el-col>
          </el-row>

          <div class="dimension-tags" v-if="taxonomyStatistics?.dimension_distribution">
            <span class="label">认知维度：</span>
            <el-tag
              v-for="(count, dim) in taxonomyStatistics.dimension_distribution"
              :key="dim"
              size="small"
              class="dimension-tag"
            >
              {{ dim }}: {{ count }}
            </el-tag>
          </div>
        </div>

        <el-divider>树形结构</el-divider>

        <!-- 树形结构 -->
        <div class="tree-section">
          <el-tree
            :data="taxonomyTreeData"
            :props="treeProps"
            node-key="id"
            default-expand-all
            :expand-on-click-node="false"
            highlight-current
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <span class="node-name">{{ data.name }}</span>
                <el-tag
                  v-if="data.cognitive_dimension"
                  size="small"
                  type="info"
                  class="node-tag"
                >
                  {{ data.cognitive_dimension }}
                </el-tag>
                <span class="node-desc" v-if="data.description">{{ data.description }}</span>
              </div>
            </template>
          </el-tree>

          <el-empty v-if="!taxonomyTreeData.length" description="暂无节点数据" />
        </div>
      </div>

      <template #footer>
        <el-button @click="showViewDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDAToGStore } from '@/stores/datog'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Grid, View, Edit, Delete } from '@element-plus/icons-vue'
import type { DAToGConfig, DAToGTaxonomy, TaxonomyNode, TaxonomyStatistics } from '@/api/types'

const datogStore = useDAToGStore()
const taxonomies = ref<DAToGTaxonomy[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const showViewDialog = ref(false)
const isEditMode = ref(false)
const editingTaxonomyId = ref('')
const selectedTaxonomy = ref<DAToGConfig | null>(null)
const taxonomyNodes = ref<TaxonomyNode[]>([])
const taxonomyStatistics = ref<TaxonomyStatistics | null>(null)

const treeProps = {
  children: 'children',
  label: 'name'
}

const taxonomyTreeData = computed(() => taxonomyNodes.value)

const formData = ref<DAToGConfig>({
  taxonomy_path: '',
  domain: '',
  sampling_strategy: 'coverage',
  graph_max_hops: 2,
  graph_max_nodes: 20,
  serialization_format: 'natural_language',
  critic_type: 'rule',
  critic_min_score: 0.6,
  generation_target_qa_pairs: 100,
  batch_size: 10
})

// 加载意图树列表
const loadTaxonomies = async () => {
  loading.value = true
  try {
    await datogStore.loadTaxonomies()
    taxonomies.value = datogStore.taxonomies
  } finally {
    loading.value = false
  }
}

// 查看意图树
const handleView = async (taxonomy: DAToGTaxonomy) => {
  const data = await datogStore.getTaxonomy(taxonomy.id)
  if (data) {
    selectedTaxonomy.value = data.taxonomy
    taxonomyNodes.value = data.nodes || []
    taxonomyStatistics.value = data.statistics
    showViewDialog.value = true
  }
}

// 编辑意图树
const handleEdit = async (taxonomy: DAToGTaxonomy) => {
  const data = await datogStore.getTaxonomy(taxonomy.id)
  if (data) {
    formData.value = { ...data.taxonomy }
    editingTaxonomyId.value = taxonomy.id
    isEditMode.value = true
    showCreateDialog.value = true
  }
}

// 删除意图树
const handleDelete = async (taxonomy: DAToGTaxonomy) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除意图树 "${taxonomy.name}" 吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await datogStore.deleteTaxonomy(taxonomy.id)
  } catch (error) {
    // 用户取消
  }
}

// 保存意图树
const handleSave = async () => {
  if (!formData.value.domain) {
    ElMessage.warning('请输入领域名称')
    return
  }
  if (!formData.value.taxonomy_path) {
    ElMessage.warning('请输入意图树路径')
    return
  }

  saving.value = true
  try {
    if (isEditMode.value) {
      await datogStore.updateTaxonomy(editingTaxonomyId.value, formData.value)
    } else {
      await datogStore.saveTaxonomy(formData.value)
    }
    showCreateDialog.value = false
    resetForm()
    await loadTaxonomies()
  } finally {
    saving.value = false
  }
}

// 重置表单
const resetForm = () => {
  formData.value = {
    taxonomy_path: '',
    domain: '',
    sampling_strategy: 'coverage',
    graph_max_hops: 2,
    graph_max_nodes: 20,
    serialization_format: 'natural_language',
    critic_type: 'rule',
    critic_min_score: 0.6,
    generation_target_qa_pairs: 100,
    batch_size: 10
  }
  isEditMode.value = false
  editingTaxonomyId.value = ''
}

// 格式化日期
const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadTaxonomies()
})
</script>

<style scoped>
.datog-taxonomies-container {
  max-width: 1400px;
  margin: 0 auto;
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

:deep(.el-card) {
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.08);
}

:deep(.el-card__header) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border-bottom: none;
  padding: 20px 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: white;
}

:deep(.el-card__header .el-button) {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  color: white;
  font-weight: 500;
  border-radius: 8px;
}

:deep(.el-card__header .el-button:hover) {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.3);
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table thead) {
  background: #f8fafc;
}

:deep(.el-table th) {
  background: #f8fafc !important;
  font-weight: 600;
  color: #475569;
}

.taxonomy-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.text-muted {
  color: #909399;
}

:deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
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

:deep(.el-descriptions) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-descriptions__label) {
  background: #f8fafc;
  font-weight: 600;
  color: #475569;
}

:deep(.el-descriptions__body) {
  color: #303133;
}

:deep(.el-divider) {
  margin: 20px 0;
}

:deep(.el-divider__text) {
  font-weight: 600;
  color: #64748b;
}

/* 查看对话框样式 */
.taxonomy-view {
  max-height: 70vh;
  overflow-y: auto;
}

.stats-section {
  margin-bottom: 16px;
}

.stats-section h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.dimension-tags {
  margin-top: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.dimension-tags .label {
  color: #606266;
  font-size: 13px;
}

.dimension-tag {
  margin: 0;
}

.tree-section {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.node-name {
  font-weight: 500;
  color: #303133;
}

.node-tag {
  font-size: 11px;
}

.node-desc {
  color: #909399;
  font-size: 12px;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.el-tree-node__content) {
  height: auto;
  padding: 4px 0;
}

:deep(.el-statistic__head) {
  font-size: 12px;
  color: #909399;
}

:deep(.el-statistic__number) {
  font-size: 24px;
  color: #10b981;
  font-weight: 600;
}
</style>
