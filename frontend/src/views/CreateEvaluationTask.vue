<template>
  <div class="create-task-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>新建评测数据集任务</span>
        </div>
      </template>

      <el-steps :active="currentStep" align-center>
        <el-step title="任务信息与文件" />
        <el-step title="评测配置" />
        <el-step title="确认创建" />
      </el-steps>

      <!-- 步骤 1: 任务信息与上传文件 -->
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

      <!-- 步骤 2: 评测配置 -->
      <div v-show="currentStep === 1" class="step-content">
        <el-form :model="evalConfig" label-width="180px" label-position="left">
          <el-divider content-position="left">模型配置</el-divider>

          <el-form-item label="API Key" required>
            <el-input
              v-model="evalConfig.api_key"
              type="password"
              show-password
              placeholder="请输入 API Key"
            />
          </el-form-item>

          <el-form-item label="Synthesizer URL">
            <el-input v-model="evalConfig.synthesizer_url" />
          </el-form-item>

          <el-form-item label="Synthesizer Model">
            <el-input v-model="evalConfig.synthesizer_model" />
          </el-form-item>

          <el-divider content-position="left">限流配置</el-divider>

          <el-form-item label="RPM (每分钟请求数)">
            <el-slider
              v-model="evalConfig.rpm"
              :min="10"
              :max="10000"
              :step="10"
              show-input
            />
            <div class="form-item-tip">控制API调用频率，避免超出限制</div>
          </el-form-item>

          <el-form-item label="TPM (每分钟Token数)">
            <el-slider
              v-model="evalConfig.tpm"
              :min="1000"
              :max="5000000"
              :step="1000"
              show-input
            />
            <div class="form-item-tip">控制Token使用量，避免超出限制。如果看到TPM超限警告，请降低此值</div>
          </el-form-item>

          <el-divider content-position="left">文本分割配置</el-divider>

          <el-form-item label="Chunk Size">
            <el-slider
              v-model="evalConfig.chunk_size"
              :min="128"
              :max="4096"
              :step="128"
              show-input
            />
          </el-form-item>

          <el-form-item label="Chunk Overlap">
            <el-slider
              v-model="evalConfig.chunk_overlap"
              :min="0"
              :max="500"
              :step="100"
              show-input
            />
          </el-form-item>

          <el-divider content-position="left">评测集配置</el-divider>

          <el-form-item label="评测集名称">
            <el-input v-model="evalConfig.evaluation_dataset_name" placeholder="Domain Knowledge Evaluation Dataset" />
          </el-form-item>

          <el-form-item label="目标评测项数量">
            <el-input-number
              v-model="evalConfig.evaluation_target_items"
              :min="10"
              :max="1000"
              :step="10"
              controls-position="right"
            />
            <div class="form-item-tip">建议生成100-300个评测项以全面评估模型能力</div>
          </el-form-item>

          <el-form-item label="评测类型分布（%）">
            <div class="qa-ratio-grid">
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">知识覆盖</span>
                <el-input-number
                  v-model="evalTypeDistribution.knowledge_coverage"
                  :min="0"
                  :max="100"
                  :step="5"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">推理能力</span>
                <el-input-number
                  v-model="evalTypeDistribution.reasoning_ability"
                  :min="0"
                  :max="100"
                  :step="5"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">事实准确</span>
                <el-input-number
                  v-model="evalTypeDistribution.factual_accuracy"
                  :min="0"
                  :max="100"
                  :step="5"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">综合应用</span>
                <el-input-number
                  v-model="evalTypeDistribution.comprehensive"
                  :min="0"
                  :max="100"
                  :step="5"
                />
              </div>
            </div>
            <div class="form-item-tip">当前占比合计：{{ evalTypeTotal }}%</div>
          </el-form-item>

          <el-form-item label="难度分布（%）">
            <div class="qa-ratio-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">简单</span>
                <el-input-number
                  v-model="evalDifficultyDistribution.easy"
                  :min="0"
                  :max="100"
                  :step="5"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">中等</span>
                <el-input-number
                  v-model="evalDifficultyDistribution.medium"
                  :min="0"
                  :max="100"
                  :step="5"
                />
              </div>
              <div class="qa-ratio-item">
                <span class="qa-ratio-label">困难</span>
                <el-input-number
                  v-model="evalDifficultyDistribution.hard"
                  :min="0"
                  :max="100"
                  :step="5"
                />
              </div>
            </div>
            <div class="form-item-tip">当前占比合计：{{ evalDifficultyTotal }}%</div>
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
              <p><strong>任务类型：</strong>评测数据集</p>
              <p><strong>文件数量：</strong>{{ fileList.length }} 个</p>
              <p><strong>目标评测项：</strong>{{ evalConfig.evaluation_target_items }} 个</p>
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
import api from '@/api'
import { ElMessage } from 'element-plus'
import type { UploadInstance, UploadProps, UploadUserFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

const router = useRouter()

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

// 评测配置
const evalConfig = ref({
  api_key: '',
  synthesizer_url: 'https://api.siliconflow.cn/v1',
  synthesizer_model: 'Qwen/Qwen2.5-7B-Instruct',
  rpm: 500,
  tpm: 100000,
  chunk_size: 1024,
  chunk_overlap: 100,
  evaluation_dataset_name: 'Domain Knowledge Evaluation Dataset',
  evaluation_target_items: 200
})

// 评测类型分布
const evalTypeDistribution = ref({
  knowledge_coverage: 30,
  reasoning_ability: 30,
  factual_accuracy: 20,
  comprehensive: 20
})

// 评测难度分布
const evalDifficultyDistribution = ref({
  easy: 30,
  medium: 50,
  hard: 20
})

// 计算评测类型分布总和
const evalTypeTotal = computed(() => {
  const total = Object.values(evalTypeDistribution.value).reduce((sum, val) => sum + val, 0)
  return Math.round(total * 10) / 10
})

// 计算评测难度分布总和
const evalDifficultyTotal = computed(() => {
  const total = Object.values(evalDifficultyDistribution.value).reduce((sum, val) => sum + val, 0)
  return Math.round(total * 10) / 10
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
    return taskInfo.value.task_name.trim() !== '' && fileList.value.length > 0
  }
  if (currentStep.value === 1) {
    return evalConfig.value.api_key !== ''
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
    
    // 创建任务
    const filenames = fileList.value.map(f => f.name)
    const createResponse = await api.createTask(
      taskInfo.value.task_name,
      filenames,
      uploadedFilePaths.value,
      taskInfo.value.task_description,
      'evaluation'  // 设置任务类型为evaluation
    )
    
    if (!createResponse.success) {
      throw new Error(createResponse.error || '创建任务失败')
    }
    
    const taskId = createResponse.data?.task_id
    if (!taskId) {
      throw new Error('未获取到任务ID')
    }
    
    // 构建评测任务配置
    const configToSubmit = {
      api_key: evalConfig.value.api_key,
      synthesizer_url: evalConfig.value.synthesizer_url,
      synthesizer_model: evalConfig.value.synthesizer_model,
      rpm: evalConfig.value.rpm,
      tpm: evalConfig.value.tpm,
      chunk_size: evalConfig.value.chunk_size,
      chunk_overlap: evalConfig.value.chunk_overlap,
      partition_method: 'ece',
      evaluation: {
        enabled: true,
        dataset_name: evalConfig.value.evaluation_dataset_name,
        target_eval_items: evalConfig.value.evaluation_target_items,
        type_distribution: {
          knowledge_coverage: evalTypeDistribution.value.knowledge_coverage / 100,
          reasoning_ability: evalTypeDistribution.value.reasoning_ability / 100,
          factual_accuracy: evalTypeDistribution.value.factual_accuracy / 100,
          comprehensive: evalTypeDistribution.value.comprehensive / 100
        },
        difficulty_distribution: {
          easy: evalDifficultyDistribution.value.easy / 100,
          medium: evalDifficultyDistribution.value.medium / 100,
          hard: evalDifficultyDistribution.value.hard / 100
        },
        output_format: 'benchmark',
        min_quality_score: 0.5
      }
    }
    
    // 启动任务
    const startResponse = await api.startTask(taskId, configToSubmit)
    
    if (!startResponse.success) {
      throw new Error(startResponse.error || '启动任务失败')
    }
    
    ElMessage.success('评测任务创建并启动成功')
    router.push('/tasks')
  } catch (error: any) {
    console.error('Submit error:', error)
    const message = typeof error === 'string' ? error : (error?.message || '操作失败')
    ElMessage.error(message)
  } finally {
    submitting.value = false
  }
}
// 加载配置
onMounted(() => {
  try {
    const saved = localStorage.getItem('evaluation_config')
    if (saved) {
      const savedConfig = JSON.parse(saved)
      
      // 更新评测配置
      evalConfig.value = {
        api_key: savedConfig.api_key || '',
        synthesizer_url: savedConfig.synthesizer_url || 'https://api.siliconflow.cn/v1',
        synthesizer_model: savedConfig.synthesizer_model || 'Qwen/Qwen2.5-7B-Instruct',
        rpm: savedConfig.rpm || 500,
        tpm: savedConfig.tpm || 100000,
        chunk_size: savedConfig.chunk_size || 1024,
        chunk_overlap: savedConfig.chunk_overlap || 100,
        evaluation_dataset_name: savedConfig.evaluation_dataset_name || 'Domain Knowledge Evaluation Dataset',
        evaluation_target_items: savedConfig.evaluation_target_items || 200
      }
      
      // 更新评测类型分布
      if (savedConfig.evaluation_type_distribution) {
        evalTypeDistribution.value = {
          knowledge_coverage: Math.round(savedConfig.evaluation_type_distribution.knowledge_coverage * 100),
          reasoning_ability: Math.round(savedConfig.evaluation_type_distribution.reasoning_ability * 100),
          factual_accuracy: Math.round(savedConfig.evaluation_type_distribution.factual_accuracy * 100),
          comprehensive: Math.round(savedConfig.evaluation_type_distribution.comprehensive * 100)
        }
      }
      
      // 更新难度分布
      if (savedConfig.evaluation_difficulty_distribution) {
        evalDifficultyDistribution.value = {
          easy: Math.round(savedConfig.evaluation_difficulty_distribution.easy * 100),
          medium: Math.round(savedConfig.evaluation_difficulty_distribution.medium * 100),
          hard: Math.round(savedConfig.evaluation_difficulty_distribution.hard * 100)
        }
      }
      
      ElMessage.success('已加载默认评测配置')
    }
  } catch (error) {
    console.error('加载默认配置失败:', error)
  }
})
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
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
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
  border-color: #67c23a;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.2);
}

:deep(.el-icon--upload) {
  font-size: 80px;
  color: #67c23a;
  margin-bottom: 16px;
}

.upload-demo {
  width: 100%;
}

.file-info {
  margin-top: 24px;
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
  border-left: 3px solid #67c23a;
  border-radius: 4px;
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

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: none;
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
  border: none;
}
</style>
