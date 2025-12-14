<template>
  <div class="config-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>评测配置设置</span>
          <div class="header-actions">
            <el-button @click="handleReset">重置为默认</el-button>
            <el-button type="success" @click="handleSave" :loading="saving">保存配置</el-button>
          </div>
        </div>
      </template>

      <el-form :model="config" label-width="200px" label-position="left">
        <el-collapse v-model="activeNames">
          <!-- 模型配置 -->
          <el-collapse-item title="模型配置" name="model">
            <el-form-item label="Tokenizer">
              <el-input v-model="config.tokenizer" placeholder="cl100k_base" />
              <span class="form-item-tip">用于计算token数量的分词器</span>
            </el-form-item>

            <el-form-item label="Synthesizer Base URL">
              <el-input v-model="config.synthesizer_url" placeholder="https://api.siliconflow.cn/v1" />
              <span class="form-item-tip">评测数据生成模型的API地址</span>
            </el-form-item>

            <el-form-item label="Synthesizer Model">
              <el-input v-model="config.synthesizer_model" placeholder="Qwen/Qwen2.5-7B-Instruct" />
              <span class="form-item-tip">用于生成评测数据的模型名称</span>
            </el-form-item>

            <el-form-item label="Synthesizer API Key">
              <el-input
                v-model="config.api_key"
                type="password"
                show-password
                placeholder="请输入API Key"
              />
              <span class="form-item-tip">模型API的访问密钥</span>
            </el-form-item>

            <el-form-item label="测试连接">
              <el-button @click="handleTestConnection" :loading="testing">测试 Synthesizer 连接</el-button>
            </el-form-item>

            <el-divider content-position="left">限流配置</el-divider>

            <el-form-item label="RPM (每分钟请求数)">
              <el-slider
                v-model="config.rpm"
                :min="10"
                :max="10000"
                :step="10"
                show-input
              />
              <span class="form-item-tip">控制API调用频率，避免超出限制</span>
            </el-form-item>

            <el-form-item label="TPM (每分钟Token数)">
              <el-slider
                v-model="config.tpm"
                :min="1000"
                :max="5000000"
                :step="1000"
                show-input
              />
              <span class="form-item-tip">控制Token使用量，避免超出限制</span>
            </el-form-item>
          </el-collapse-item>

          <!-- 评测集基本配置 -->
          <el-collapse-item title="评测集基本配置" name="basic">
            <el-form-item label="评测集名称">
              <el-input v-model="config.evaluation_dataset_name" placeholder="Domain Knowledge Evaluation Dataset" />
              <span class="form-item-tip">为生成的评测集指定一个描述性名称</span>
            </el-form-item>

            <el-form-item label="目标评测项数量">
              <el-input-number
                v-model="config.evaluation_target_items"
                :min="10"
                :max="1000"
                :step="10"
                controls-position="right"
              />
              <span class="form-item-tip">建议生成100-300个评测项以全面评估模型能力</span>
            </el-form-item>

            <el-form-item label="输出格式">
              <el-radio-group v-model="config.evaluation_output_format">
                <el-radio label="json">JSON</el-radio>
                <el-radio label="jsonl">JSONL</el-radio>
              </el-radio-group>
              <span class="form-item-tip">选择评测数据集的输出格式</span>
            </el-form-item>
          </el-collapse-item>

          <!-- 评测类型分布 -->
          <el-collapse-item title="评测类型分布" name="type_distribution">
            <el-alert
              title="评测类型说明"
              type="info"
              :closable="false"
              style="margin-bottom: 20px"
            >
              <template #default>
                <div style="font-size: 12px; line-height: 1.6">
                  <ul style="margin: 8px 0; padding-left: 20px">
                    <li><strong>知识覆盖</strong>：测试模型对领域知识的掌握广度</li>
                    <li><strong>推理能力</strong>：评估模型的逻辑推理和多跳推理能力</li>
                    <li><strong>事实准确</strong>：检验模型回答的准确性和可靠性</li>
                    <li><strong>综合应用</strong>：考察模型综合运用知识解决复杂问题的能力</li>
                  </ul>
                </div>
              </template>
            </el-alert>

            <el-form-item label="类型占比（%）">
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
              <span class="form-item-tip">当前占比合计：{{ evalTypeTotal }}%，建议接近 100%</span>
            </el-form-item>
          </el-collapse-item>

          <!-- 难度分布 -->
          <el-collapse-item title="难度分布" name="difficulty_distribution">
            <el-form-item label="难度占比（%）">
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
              <span class="form-item-tip">当前占比合计：{{ evalDifficultyTotal }}%，建议接近 100%</span>
            </el-form-item>

            <el-divider content-position="left">难度级别说明</el-divider>

            <el-descriptions :column="1" border>
              <el-descriptions-item label="简单">
                基础知识点测试，单跳推理，直接事实查询
              </el-descriptions-item>
              <el-descriptions-item label="中等">
                多知识点关联，2-3跳推理，需要一定理解能力
              </el-descriptions-item>
              <el-descriptions-item label="困难">
                复杂场景，多跳推理（3+），需要深度理解和综合分析
              </el-descriptions-item>
            </el-descriptions>
          </el-collapse-item>

          <!-- 质量控制 -->
          <el-collapse-item title="质量控制" name="quality_control">
            <el-form-item label="启用质量检查">
              <el-switch v-model="config.enable_quality_check" />
              <span class="form-item-tip">自动检查生成的评测项质量，过滤低质量项目</span>
            </el-form-item>

            <template v-if="config.enable_quality_check">
              <el-form-item label="最小质量分数">
                <el-slider
                  v-model="config.min_quality_score"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  show-input
                />
                <span class="form-item-tip">低于此分数的评测项将被过滤（0-1之间）</span>
              </el-form-item>
            </template>

            <el-form-item label="启用去重">
              <el-switch v-model="config.enable_deduplication" />
              <span class="form-item-tip">自动去除重复或高度相似的评测项</span>
            </el-form-item>

            <template v-if="config.enable_deduplication">
              <el-form-item label="相似度阈值">
                <el-slider
                  v-model="config.similarity_threshold"
                  :min="0.5"
                  :max="1.0"
                  :step="0.05"
                  show-input
                />
                <span class="form-item-tip">相似度超过此阈值的项目将被视为重复</span>
              </el-form-item>
            </template>
          </el-collapse-item>
        </el-collapse>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

// 默认配置
const defaultConfig = {
  // 模型配置
  tokenizer: 'cl100k_base',
  synthesizer_url: 'https://api.siliconflow.cn/v1',
  synthesizer_model: 'Qwen/Qwen2.5-7B-Instruct',
  api_key: '',
  rpm: 500,
  tpm: 100000,
  // 评测集配置
  evaluation_dataset_name: 'Domain Knowledge Evaluation Dataset',
  evaluation_target_items: 200,
  evaluation_output_format: 'json',
  enable_quality_check: true,
  min_quality_score: 0.6,
  enable_deduplication: true,
  similarity_threshold: 0.85
}

const config = ref({ ...defaultConfig })
const activeNames = ref(['model', 'basic', 'type_distribution', 'difficulty_distribution', 'quality_control'])
const saving = ref(false)
const testing = ref(false)

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

// 测试连接
const handleTestConnection = async () => {
  if (!config.value.api_key) {
    ElMessage.error('请先填写 API Key')
    return
  }

  if (!config.value.synthesizer_url) {
    ElMessage.error('请先填写 Synthesizer Base URL')
    return
  }

  if (!config.value.synthesizer_model) {
    ElMessage.error('请先填写 Synthesizer Model')
    return
  }

  testing.value = true
  try {
    const response = await api.testConnection({
      base_url: config.value.synthesizer_url || '',
      api_key: config.value.api_key,
      model_name: config.value.synthesizer_model || ''
    })
    if (response.success) {
      ElMessage.success(response.message || '连接测试成功')
    } else {
      ElMessage.error(response.error || '连接测试失败')
    }
  } catch (error: any) {
    const errorMessage = error?.response?.data?.detail || 
                        error?.response?.data?.error || 
                        error?.message || 
                        '连接测试失败，请检查配置和网络连接'
    ElMessage.error(errorMessage)
    console.error('连接测试失败:', error)
  } finally {
    testing.value = false
  }
}

// 保存配置
const handleSave = async () => {
  saving.value = true
  try {
    // 将分布数据保存到配置中
    const configToSave = {
      ...config.value,
      evaluation_type_distribution: {
        knowledge_coverage: evalTypeDistribution.value.knowledge_coverage / 100,
        reasoning_ability: evalTypeDistribution.value.reasoning_ability / 100,
        factual_accuracy: evalTypeDistribution.value.factual_accuracy / 100,
        comprehensive: evalTypeDistribution.value.comprehensive / 100
      },
      evaluation_difficulty_distribution: {
        easy: evalDifficultyDistribution.value.easy / 100,
        medium: evalDifficultyDistribution.value.medium / 100,
        hard: evalDifficultyDistribution.value.hard / 100
      }
    }
    
    // 保存到 localStorage
    localStorage.setItem('evaluation_config', JSON.stringify(configToSave))
    ElMessage.success('评测配置已保存')
  } catch (error) {
    ElMessage.error('保存配置失败')
    console.error('保存配置失败:', error)
  } finally {
    saving.value = false
  }
}

// 重置配置
const handleReset = async () => {
  try {
    await ElMessageBox.confirm('确定要重置为默认配置吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    config.value = { ...defaultConfig }
    evalTypeDistribution.value = {
      knowledge_coverage: 30,
      reasoning_ability: 30,
      factual_accuracy: 20,
      comprehensive: 20
    }
    evalDifficultyDistribution.value = {
      easy: 30,
      medium: 50,
      hard: 20
    }
    
    ElMessage.success('配置已重置')
  } catch {
    // 用户取消操作
  }
}

// 加载配置
onMounted(() => {
  try {
    const saved = localStorage.getItem('evaluation_config')
    if (saved) {
      const savedConfig = JSON.parse(saved)
      config.value = { ...defaultConfig, ...savedConfig }
      
      // 加载分布数据
      if (savedConfig.evaluation_type_distribution) {
        evalTypeDistribution.value = {
          knowledge_coverage: Math.round(savedConfig.evaluation_type_distribution.knowledge_coverage * 100),
          reasoning_ability: Math.round(savedConfig.evaluation_type_distribution.reasoning_ability * 100),
          factual_accuracy: Math.round(savedConfig.evaluation_type_distribution.factual_accuracy * 100),
          comprehensive: Math.round(savedConfig.evaluation_type_distribution.comprehensive * 100)
        }
      }
      
      if (savedConfig.evaluation_difficulty_distribution) {
        evalDifficultyDistribution.value = {
          easy: Math.round(savedConfig.evaluation_difficulty_distribution.easy * 100),
          medium: Math.round(savedConfig.evaluation_difficulty_distribution.medium * 100),
          hard: Math.round(savedConfig.evaluation_difficulty_distribution.hard * 100)
        }
      }
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
})
</script>

<style scoped>
/* 复用 Config.vue 的样式 */
.config-container {
  max-width: 1200px;
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
  transition: all 0.3s;
}

:deep(.el-card:hover) {
  box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.12);
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

.header-actions {
  display: flex;
  gap: 12px;
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

:deep(.el-card__body) {
  padding: 32px;
}

.form-item-tip {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  padding: 8px 12px;
  background: #f8fafc;
  border-left: 3px solid #10b981;
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

:deep(.el-collapse) {
  border: none;
}

:deep(.el-collapse-item) {
  margin-bottom: 16px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  background: white;
}

:deep(.el-collapse-item__header) {
  font-size: 16px;
  font-weight: 600;
  background: #fafbfc;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  color: #303133;
  transition: all 0.3s;
}

:deep(.el-collapse-item__header:hover) {
  background: #f0f2f5;
  color: #10b981;
}

:deep(.el-collapse-item__wrap) {
  border: none;
  background: white;
}

:deep(.el-collapse-item__content) {
  padding: 24px 20px;
}

:deep(.el-form-item) {
  margin-bottom: 28px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #475569;
}

:deep(.el-divider) {
  margin: 32px 0;
}

:deep(.el-divider__text) {
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  background: white;
  padding: 0 16px;
}
</style>
