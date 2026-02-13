<template>
  <div class="create-task-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>新建任务</span>
        </div>
      </template>

      <el-steps :active="currentStep" align-center>
<el-step title="任务信息与文件" />
        <el-step title="配置参数" />
        <el-step title="确认创建" />
      </el-steps>

      <!-- 步骤 1: 任务信息与上传文件（合并） -->
      <div v-show="currentStep === 0" class="step-content">
        <el-form :model="taskInfo" label-width="120px">
          <el-divider content-position="left">任务信息</el-divider>
          
          <el-form-item label="任务名称" required>
            <el-input
              v-model="taskInfo.task_name"
              placeholder="请输入任务名称"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="任务简介">
            <el-input
              v-model="taskInfo.task_description"
              type="textarea"
              :rows="4"
              placeholder="请输入任务简介（可选）"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>

          <el-divider content-position="left">上传文件</el-divider>

          <el-form-item label="">
            <el-upload
              ref="uploadRef"
              class="upload-demo"
              drag
              :auto-upload="false"
              :limit="10"
              :file-list="fileList"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :on-exceed="handleExceed"
              accept=".txt,.json,.jsonl,.csv,.pdf,.docx,.md,.markdown"
              multiple
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽文件到此处或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 .txt, .json, .jsonl, .csv, .pdf, .docx, .md, .markdown 格式文件，最多10个文件
                </div>
              </template>
            </el-upload>

            <div v-if="fileList.length > 0" class="file-info">
              <el-alert
                :title="`已选择 ${fileList.length} 个文件`"
                type="success"
                :closable="false"
              />
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤 2: 配置参数 -->
      <div v-show="currentStep === 1" class="step-content">
        <el-form :model="taskConfig" label-width="180px" label-position="left">
          <el-divider content-position="left">模型配置</el-divider>

          <el-form-item label="API Key" required>
            <el-input
              v-model="taskConfig.api_key"
              type="password"
              show-password
              placeholder="请输入 API Key"
            />
          </el-form-item>

          <el-form-item label="Synthesizer URL">
            <el-input v-model="taskConfig.synthesizer_url" />
          </el-form-item>

          <el-form-item label="Synthesizer Model">
            <el-input v-model="taskConfig.synthesizer_model" />
          </el-form-item>

          <el-form-item label="使用 Trainee 模型">
            <el-switch v-model="taskConfig.if_trainee_model" />
          </el-form-item>

          <template v-if="taskConfig.if_trainee_model">
            <el-form-item label="Trainee API Key">
              <el-input
                v-model="taskConfig.trainee_api_key"
                type="password"
                show-password
                placeholder="留空则使用相同的 API Key"
              />
            </el-form-item>

            <el-form-item label="Trainee URL">
              <el-input v-model="taskConfig.trainee_url" />
            </el-form-item>

            <el-form-item label="Trainee Model">
              <el-input v-model="taskConfig.trainee_model" />
            </el-form-item>

            <el-form-item label="Quiz Samples">
              <el-input-number v-model="taskConfig.quiz_samples" :min="1" :max="10" />
            </el-form-item>
          </template>

          <el-divider content-position="left">文本分割配置</el-divider>

          <el-form-item label="Tokenizer">
            <el-select v-model="taskConfig.tokenizer">
              <el-option label="cl100k_base (GPT-4)" value="cl100k_base" />
              <el-option label="p50k_base (GPT-3)" value="p50k_base" />
              <el-option label="r50k_base (Codex)" value="r50k_base" />
            </el-select>
          </el-form-item>

          <el-form-item label="Chunk Size">
            <el-slider
              v-model="taskConfig.chunk_size"
              :min="128"
              :max="4096"
              :step="128"
              show-input
            />
          </el-form-item>

          <el-form-item label="Chunk Overlap">
            <el-slider
              v-model="taskConfig.chunk_overlap"
              :min="0"
              :max="500"
              :step="100"
              show-input
            />
          </el-form-item>

          <el-divider content-position="left">分区配置</el-divider>

          <el-form-item label="分区方法">
            <el-select v-model="taskConfig.partition_method">
              <el-option label="ECE" value="ece" />
              <el-option label="DFS" value="dfs" />
              <el-option label="BFS" value="bfs" />
              <el-option label="Leiden" value="leiden" />
              <el-option label="Hierarchical" value="hierarchical" />
            </el-select>
          </el-form-item>

          <!-- ECE 参数 -->
          <template v-if="taskConfig.partition_method === 'ece'">
            <el-form-item label="Max Units">
              <el-input-number v-model="taskConfig.ece_max_units" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="Min Units">
              <el-input-number v-model="taskConfig.ece_min_units" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="Max Tokens">
              <el-slider
                v-model="taskConfig.ece_max_tokens"
                :min="512"
                :max="20480"
                :step="512"
                show-input
              />
            </el-form-item>
          </template>

          <!-- DFS 参数 -->
          <template v-if="taskConfig.partition_method === 'dfs'">
            <el-form-item label="Max Units">
              <el-input-number v-model="taskConfig.dfs_max_units" :min="1" :max="100" />
            </el-form-item>
          </template>

          <!-- BFS 参数 -->
          <template v-if="taskConfig.partition_method === 'bfs'">
            <el-form-item label="Max Units">
              <el-input-number v-model="taskConfig.bfs_max_units" :min="1" :max="100" />
            </el-form-item>
          </template>

          <!-- Leiden 参数 -->
          <template v-if="taskConfig.partition_method === 'leiden'">
            <el-form-item label="Max Size">
              <el-input-number v-model="taskConfig.leiden_max_size" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="Use LCC">
              <el-switch v-model="taskConfig.leiden_use_lcc" />
            </el-form-item>
            <el-form-item label="Random Seed">
              <el-input-number v-model="taskConfig.leiden_random_seed" />
            </el-form-item>
          </template>

          <!-- Hierarchical 参数 -->
          <template v-if="taskConfig.partition_method === 'hierarchical'">
            <el-form-item label="层次关系类型">
              <el-select
                v-model="taskConfig.hierarchical_relations"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="选择或输入关系类型"
              >
                <el-option label="is_a" value="is_a" />
                <el-option label="subclass_of" value="subclass_of" />
                <el-option label="part_of" value="part_of" />
                <el-option label="includes" value="includes" />
                <el-option label="type_of" value="type_of" />
              </el-select>
            </el-form-item>
            <el-form-item label="最大层次深度">
              <el-slider
                v-model="taskConfig.max_hierarchical_depth"
                :min="1"
                :max="10"
                :step="1"
                show-input
              />
            </el-form-item>
            <el-form-item label="最大兄弟节点数">
              <el-slider
                v-model="taskConfig.max_siblings_per_community"
                :min="2"
                :max="20"
                :step="1"
                show-input
              />
            </el-form-item>
          </template>

          <el-divider content-position="left">生成配置</el-divider>

          <el-form-item label="生成模式">
            <el-checkbox-group v-model="taskConfig.mode">
              <el-checkbox label="atomic">Atomic - 原子级问答</el-checkbox>
              <el-checkbox label="multi_hop">Multi-hop - 多跳问答</el-checkbox>
              <el-checkbox label="aggregated">Aggregated - 聚合问答</el-checkbox>
              <el-checkbox label="cot">CoT - 思维链问答</el-checkbox>
              <el-checkbox label="hierarchical">Hierarchical - 层次化问答</el-checkbox>
            </el-checkbox-group>
            <div class="form-item-tip">可选择多个生成模式，将同时生成所有选中模式的数据</div>
          </el-form-item>

          <el-form-item label="数据格式">
            <el-radio-group v-model="taskConfig.data_format">
              <el-radio value="Alpaca">Alpaca</el-radio>
              <el-radio value="Sharegpt">Sharegpt</el-radio>
              <el-radio value="ChatML">ChatML</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="只生成中文">
            <el-switch v-model="taskConfig.chinese_only" />
            <div class="form-item-tip">强制生成纯中文问答对，问题和答案都不包含英文（推荐用于中文训练数据）</div>
          </el-form-item>

          <el-form-item label="树结构格式" v-if="taskConfig.mode.includes('hierarchical')">
            <el-radio-group v-model="taskConfig.structure_format">
              <el-radio value="markdown">Markdown (推荐)</el-radio>
              <el-radio value="json">JSON</el-radio>
              <el-radio value="outline">Outline</el-radio>
            </el-radio-group>
            <div class="form-item-tip">层次化问答的树结构序列化格式</div>
          </el-form-item>

          <el-divider content-position="left">数量与类型控制</el-divider>

          <el-form-item label="目标问答数量">
            <el-input-number
              v-model="taskConfig.qa_pair_limit"
              :min="0"
              :max="20000"
              :step="50"
              controls-position="right"
            />
            <div class="form-item-tip">0 或留空表示不限制数量，建议根据训练需求设定目标值</div>
          </el-form-item>

          <el-form-item label="类型占比（%）">
            <div class="qa-ratio-grid">
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">Atomic</span>
                <el-input-number
                  v-model="taskConfig.qa_ratio_atomic"
                  :min="0"
                  :max="100"
                  :step="1"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">Aggregated</span>
                <el-input-number
                  v-model="taskConfig.qa_ratio_aggregated"
                  :min="0"
                  :max="100"
                  :step="1"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">Multi-hop</span>
                <el-input-number
                  v-model="taskConfig.qa_ratio_multi_hop"
                  :min="0"
                  :max="100"
                  :step="1"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">CoT</span>
                <el-input-number
                  v-model="taskConfig.qa_ratio_cot"
                  :min="0"
                  :max="100"
                  :step="1"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">Hierarchical</span>
                <el-input-number
                  v-model="taskConfig.qa_ratio_hierarchical"
                  :min="0"
                  :max="100"
                  :step="1"
                />
              </div>
            </div>
            <div class="form-item-tip">当前占比合计：{{ ratioTotal }}%，建议接近 100%</div>
          </el-form-item>

          <el-divider content-position="left">限流配置</el-divider>

          <el-form-item label="RPM">
            <el-slider
              v-model="taskConfig.rpm"
              :min="10"
              :max="10000"
              :step="100"
              show-input
            />
          </el-form-item>

          <el-form-item label="TPM">
            <el-slider
              v-model="taskConfig.tpm"
              :min="5000"
              :max="5000000"
              :step="1000"
              show-input
            />
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤 3: 确认创建 -->
      <div v-show="currentStep === 2" class="step-content">
        <el-result icon="success" title="准备就绪" sub-title="请确认任务信息">
          <template #extra>
            <div class="confirm-info">
              <p><strong>任务名称：</strong>{{ taskInfo.task_name }}</p>
              <p v-if="taskInfo.task_description"><strong>任务简介：</strong>{{ taskInfo.task_description }}</p>
              <p><strong>文件数量：</strong>{{ fileList.length }} 个</p>
              <p><strong>文件列表：</strong></p>
              <ul>
                <li v-for="file in fileList" :key="file.uid">{{ file.name }}</li>
              </ul>
              <p><strong>生成模式：</strong>{{ Array.isArray(taskConfig.mode) ? taskConfig.mode.join(', ') : taskConfig.mode }}</p>
              <p><strong>数据格式：</strong>{{ taskConfig.data_format }}</p>
              <p><strong>分区方法：</strong>{{ taskConfig.partition_method }}</p>
            </div>
          </template>
        </el-result>
      </div>

      <!-- 操作按钮 -->
      <div class="step-actions">
        <el-button v-if="currentStep > 0" @click="prevStep">上一步</el-button>
        <el-button v-if="currentStep < 2" type="primary" @click="nextStep" :disabled="!canNext">
          下一步
        </el-button>
        <el-button
          v-if="currentStep === 2"
          type="success"
          @click="submitTask"
          :loading="submitting"
        >
          创建并启动任务
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfigStore } from '@/stores/config'
import type { TaskConfig } from '@/api/types'
import api from '@/api'
import { ElMessage, genFileId } from 'element-plus'
import type { UploadInstance, UploadProps, UploadRawFile, UploadUserFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

const router = useRouter()
const configStore = useConfigStore()

const uploadRef = ref<UploadInstance>()
const fileList = ref<UploadUserFile[]>([])
const uploadedFilePaths = ref<string[]>([])
const currentStep = ref(0)
const submitting = ref(false)

// 任务信息
const taskInfo = ref({
  task_name: '',
  task_description: ''
})

// 任务配置（从 store 初始化）
const initialConfig = { ...configStore.config }
// 确保 mode 是数组格式
if (typeof initialConfig.mode === 'string') {
  initialConfig.mode = [initialConfig.mode]
} else if (!Array.isArray(initialConfig.mode)) {
  initialConfig.mode = ['aggregated']
}
const taskConfig = ref<TaskConfig>(initialConfig)

const ratioTotal = computed(() => {
  const ratios = [
    Number(taskConfig.value.qa_ratio_atomic ?? 0),
    Number(taskConfig.value.qa_ratio_aggregated ?? 0),
    Number(taskConfig.value.qa_ratio_multi_hop ?? 0),
    Number(taskConfig.value.qa_ratio_cot ?? 0),
    Number(taskConfig.value.qa_ratio_hierarchical ?? 0)
  ]
  const total = ratios.reduce((sum, value) => {
    const normalized = Number.isFinite(value) ? value : 0
    return sum + normalized
  }, 0)
  return Math.round(total * 10) / 10
})

// 页面加载时从后端加载最新配置
onMounted(async () => {
  await configStore.loadConfig()
  // 重新初始化任务配置，使用最新的配置
  const loadedConfig = { ...configStore.config }
  // 确保 mode 是数组格式
  if (typeof loadedConfig.mode === 'string') {
    loadedConfig.mode = [loadedConfig.mode]
  } else if (!Array.isArray(loadedConfig.mode)) {
    loadedConfig.mode = ['aggregated']
  }
  taskConfig.value = loadedConfig
})

// 文件变化处理
const handleFileChange: UploadProps['onChange'] = (uploadFile, uploadFiles) => {
  fileList.value = uploadFiles
}

// 文件移除处理
const handleFileRemove: UploadProps['onRemove'] = (uploadFile, uploadFiles) => {
  fileList.value = uploadFiles
}

// 文件超出限制处理
const handleExceed: UploadProps['onExceed'] = (files) => {
  ElMessage.warning('最多只能上传10个文件')
}

// 判断是否可以进入下一步
const canNext = computed(() => {
  if (currentStep.value === 0) {
    // 第1步：任务信息和文件都需要填写
    return taskInfo.value.task_name.trim() !== '' && fileList.value.length > 0
  }
  if (currentStep.value === 1) {
    // 第2步：配置参数验证
    if (!taskConfig.value.api_key) {
      return false
    }
    // 验证至少选择一个生成模式
    const mode = taskConfig.value.mode
    if (!mode || (Array.isArray(mode) && mode.length === 0)) {
      return false
    }
    return true
  }
  return true
})

// 上一步
const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

// 下一步
const nextStep = async () => {
  if (currentStep.value === 0 && fileList.value.length > 0) {
    // 第1步完成后上传所有文件
    try {
      ElMessage.info('正在上传文件...')
      uploadedFilePaths.value = []
      
      for (const file of fileList.value) {
        if (file.raw) {
          const response = await api.uploadFile(file.raw)
          if (response.success && response.data) {
            uploadedFilePaths.value.push(response.data.filepath)
          } else {
            throw new Error(`上传文件 ${file.name} 失败`)
          }
        }
      }
      
      ElMessage.success('文件上传成功')
      currentStep.value++
    } catch (error: any) {
      const message = typeof error === 'string' ? error : (error?.message || '文件上传失败')
      ElMessage.error(message)
    }
  } else if (currentStep.value < 2) {
    currentStep.value++
  }
}

// 提交任务
const submitTask = async () => {
  try {
    submitting.value = true
    
    // 验证生成模式
    const mode = taskConfig.value.mode
    if (!mode || (Array.isArray(mode) && mode.length === 0)) {
      ElMessage.error('请至少选择一个生成模式')
      submitting.value = false
      return
    }
    
    // 确保 mode 是数组格式
    const configToSubmit = { ...taskConfig.value }
    if (typeof configToSubmit.mode === 'string') {
      configToSubmit.mode = [configToSubmit.mode]
    } else if (!Array.isArray(configToSubmit.mode)) {
      configToSubmit.mode = ['aggregated']
    }
    
    // 创建任务
    const filenames = fileList.value.map(f => f.name)
    const createResponse = await api.createTask(
      taskInfo.value.task_name,
      filenames,
      uploadedFilePaths.value,
      taskInfo.value.task_description
    )
    
    if (!createResponse.success) {
      throw new Error(createResponse.error || '创建任务失败')
    }
    
    const taskId = createResponse.data?.task_id
    if (!taskId) {
      throw new Error('未获取到任务ID')
    }
    
    // 启动任务（使用处理后的配置）
    const startResponse = await api.startTask(taskId, configToSubmit)
    
    if (!startResponse.success) {
      throw new Error(startResponse.error || '启动任务失败')
    }
    
    ElMessage.success('任务创建并启动成功')
    router.push('/tasks')
  } catch (error: any) {
    console.error('Submit error:', error)
    const message = typeof error === 'string' ? error : (error?.message || '操作失败')
    ElMessage.error(message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.create-task-container {
  max-width: 1000px;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom: none;
  padding: 20px 24px;
}

.card-header {
  font-size: 20px;
  font-weight: 600;
  color: white;
  text-align: center;
}

:deep(.el-card__body) {
  padding: 32px;
}

:deep(.el-steps) {
  margin: 24px 0 40px;
}

:deep(.el-step__title) {
  font-weight: 600;
}

:deep(.el-step__title.is-finish) {
  color: #667eea;
}

:deep(.el-step__head.is-finish .el-step__line) {
  background-color: #667eea;
}

:deep(.el-step__head.is-finish .el-step__icon) {
  background-color: #667eea;
  border-color: #667eea;
}

:deep(.el-step__head.is-process .el-step__icon) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #667eea;
}

.step-content {
  margin-top: 40px;
  min-height: 400px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

:deep(.el-upload-dragger) {
  border-radius: 12px;
  border: 2px dashed #d1d5db;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  transition: all 0.3s;
  padding: 48px 20px;
}

:deep(.el-upload-dragger:hover) {
  border-color: #667eea;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

:deep(.el-icon--upload) {
  font-size: 80px;
  color: #667eea;
  margin-bottom: 16px;
}

.upload-demo {
  width: 100%;
}

.file-info {
  margin-top: 24px;
}

:deep(.el-alert) {
  border-radius: 8px;
  border: none;
}

.confirm-info {
  text-align: left;
  max-width: 700px;
  margin: 0 auto;
  padding: 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}

.confirm-info p {
  margin: 12px 0;
  font-size: 15px;
  line-height: 1.8;
  color: #475569;
}

.confirm-info strong {
  color: #1e293b;
  font-weight: 600;
}

.confirm-info ul {
  margin: 8px 0;
  padding-left: 24px;
}

.confirm-info li {
  margin: 8px 0;
  color: #64748b;
  padding-left: 4px;
}

.step-actions {
  margin-top: 48px;
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.step-actions .el-button {
  margin: 0 12px;
  padding: 12px 32px;
  font-size: 15px;
  border-radius: 8px;
}

.form-item-tip {
  display: block;
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  padding: 8px 12px;
  background: #f8fafc;
  border-left: 3px solid #409eff;
  border-radius: 4px;
}

:deep(.el-checkbox) {
  display: block;
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: 6px;
  transition: all 0.2s;
}

:deep(.el-checkbox:hover) {
  background: #f0f9ff;
}

.qa-ratio-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.qa-ratio-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.qa-ratio-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.qa-ratio-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  min-width: 90px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #475569;
}

:deep(.el-input__wrapper) {
  border-radius: 6px;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
  border: none;
}

:deep(.el-button--success:hover) {
  background: linear-gradient(135deg, #059669 0%, #10b981 100%);
}

:deep(.el-result) {
  padding: 32px 0;
}

:deep(.el-result__icon svg) {
  width: 80px;
  height: 80px;
}

</style>
