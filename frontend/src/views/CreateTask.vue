<template>
  <div class="create-task-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>新建任务</span>
        </div>
      </template>

      <el-steps :active="currentStep" align-center>
        <el-step title="任务信息" />
        <el-step title="上传文件" />
        <el-step title="配置参数" />
        <el-step title="确认创建" />
      </el-steps>

      <!-- 步骤 1: 任务信息 -->
      <div v-show="currentStep === 0" class="step-content">
        <el-form :model="taskInfo" label-width="120px">
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
        </el-form>
      </div>

      <!-- 步骤 2: 上传文件 -->
      <div v-show="currentStep === 1" class="step-content">
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
          accept=".txt,.json,.jsonl,.csv,.pdf"
          multiple
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 .txt, .json, .jsonl, .csv, .pdf 格式文件，最多10个文件
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
      </div>

      <!-- 步骤 3: 配置参数 -->
      <div v-show="currentStep === 2" class="step-content">
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

          <el-divider content-position="left">生成配置</el-divider>

          <el-form-item label="生成模式">
            <el-radio-group v-model="taskConfig.mode">
              <el-radio value="atomic">Atomic</el-radio>
              <el-radio value="multi_hop">Multi-hop</el-radio>
              <el-radio value="aggregated">Aggregated</el-radio>
              <el-radio value="CoT">CoT</el-radio>
              <el-radio value="all">all</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="数据格式">
            <el-radio-group v-model="taskConfig.data_format">
              <el-radio value="Alpaca">Alpaca</el-radio>
              <el-radio value="Sharegpt">Sharegpt</el-radio>
              <el-radio value="ChatML">ChatML</el-radio>
            </el-radio-group>
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

      <!-- 步骤 4: 确认创建 -->
      <div v-show="currentStep === 3" class="step-content">
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
              <p><strong>生成模式：</strong>{{ taskConfig.mode }}</p>
              <p><strong>数据格式：</strong>{{ taskConfig.data_format }}</p>
              <p><strong>分区方法：</strong>{{ taskConfig.partition_method }}</p>
            </div>
          </template>
        </el-result>
      </div>

      <!-- 操作按钮 -->
      <div class="step-actions">
        <el-button v-if="currentStep > 0" @click="prevStep">上一步</el-button>
        <el-button v-if="currentStep < 3" type="primary" @click="nextStep" :disabled="!canNext">
          下一步
        </el-button>
        <el-button
          v-if="currentStep === 3"
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
const taskConfig = ref<TaskConfig>({ ...configStore.config })

// 页面加载时从后端加载最新配置
onMounted(async () => {
  await configStore.loadConfig()
  // 重新初始化任务配置，使用最新的配置
  taskConfig.value = { ...configStore.config }
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
    return taskInfo.value.task_name.trim() !== ''
  }
  if (currentStep.value === 1) {
    return fileList.value.length > 0
  }
  if (currentStep.value === 2) {
    return taskConfig.value.api_key !== ''
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
  if (currentStep.value === 1 && fileList.value.length > 0) {
    // 上传所有文件
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
  } else if (currentStep.value < 3) {
    currentStep.value++
  }
}

// 提交任务
const submitTask = async () => {
  try {
    submitting.value = true
    
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
    
    // 启动任务
    const startResponse = await api.startTask(taskId, taskConfig.value)
    
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
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.step-content {
  margin-top: 40px;
  min-height: 400px;
}

.upload-demo {
  width: 100%;
}

.file-info {
  margin-top: 20px;
}

.confirm-info {
  text-align: left;
  max-width: 600px;
  margin: 0 auto;
}

.confirm-info p {
  margin: 10px 0;
  font-size: 14px;
}

.confirm-info ul {
  margin: 5px 0;
  padding-left: 20px;
}

.confirm-info li {
  margin: 5px 0;
}

.step-actions {
  margin-top: 40px;
  text-align: center;
}

.step-actions .el-button {
  margin: 0 10px;
}
</style>
