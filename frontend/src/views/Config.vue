<template>
  <div class="config-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>配置设置</span>
          <div class="header-actions">
            <el-button @click="handleReset">重置为默认</el-button>
            <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
          </div>
        </div>
      </template>

      <el-form :model="config" label-width="200px" label-position="left">
        <el-collapse v-model="activeNames">
          <!-- 模型配置 -->
          <el-collapse-item title="模型配置" name="model">
            <el-form-item label="Tokenizer">
              <el-input v-model="config.tokenizer" placeholder="cl100k_base" />
            </el-form-item>

            <el-form-item label="Synthesizer Base URL">
              <el-input v-model="config.synthesizer_url" placeholder="https://api.siliconflow.cn/v1" />
            </el-form-item>

            <el-form-item label="Synthesizer Model">
              <el-input v-model="config.synthesizer_model" placeholder="Qwen/Qwen2.5-7B-Instruct" />
            </el-form-item>

            <el-form-item label="Synthesizer API Key">
              <el-input
                v-model="config.api_key"
                type="password"
                show-password
                placeholder="请输入API Key"
              />
            </el-form-item>

            <el-form-item label="测试连接">
              <el-button @click="handleTestConnection" :loading="testing">测试 Synthesizer 连接</el-button>
            </el-form-item>

            <el-divider />

            <el-form-item label="使用 Trainee 模型">
              <el-switch v-model="config.if_trainee_model" />
            </el-form-item>

            <template v-if="config.if_trainee_model">
              <el-form-item label="Trainee Base URL">
                <el-input v-model="config.trainee_url" placeholder="https://api.siliconflow.cn/v1" />
              </el-form-item>

              <el-form-item label="Trainee Model">
                <el-input v-model="config.trainee_model" placeholder="Qwen/Qwen2.5-7B-Instruct" />
              </el-form-item>

              <el-form-item label="Trainee API Key">
                <el-input
                  v-model="config.trainee_api_key"
                  type="password"
                  show-password
                  placeholder="请输入API Key"
                />
              </el-form-item>

              <el-form-item label="Quiz Samples">
                <el-input-number v-model="config.quiz_samples" :min="1" :max="10" />
                <span class="form-item-tip">每个社区生成的问答样本数量</span>
              </el-form-item>
            </template>
          </el-collapse-item>

          <!-- 文本切分配置 -->
          <el-collapse-item title="文本切分配置" name="split">
            <el-form-item label="Chunk Size">
              <el-slider
                v-model="config.chunk_size"
                :min="256"
                :max="4096"
                :step="256"
                show-input
              />
              <span class="form-item-tip">文本块的大小（token数）</span>
            </el-form-item>

            <el-form-item label="Chunk Overlap">
              <el-slider
                v-model="config.chunk_overlap"
                :min="0"
                :max="500"
                :step="50"
                show-input
              />
              <span class="form-item-tip">文本块之间的重叠大小（token数）</span>
            </el-form-item>
          </el-collapse-item>

          <!-- 分区配置 -->
          <el-collapse-item title="图分区配置" name="partition">
            <el-form-item label="分区方法">
              <el-select v-model="config.partition_method">
                <el-option label="ECE (推荐)" value="ece" />
                <el-option label="DFS" value="dfs" />
                <el-option label="BFS" value="bfs" />
                <el-option label="Leiden" value="leiden" />
              </el-select>
            </el-form-item>

            <!-- ECE 参数 -->
            <template v-if="config.partition_method === 'ece'">
              <el-divider content-position="left">ECE 参数</el-divider>
              <el-form-item label="Max Units Per Community">
                <el-input-number v-model="config.ece_max_units" :min="1" :max="100" />
                <span class="form-item-tip">每个社区的最大单元数</span>
              </el-form-item>
              <el-form-item label="Min Units Per Community">
                <el-input-number v-model="config.ece_min_units" :min="1" :max="100" />
                <span class="form-item-tip">每个社区的最小单元数</span>
              </el-form-item>
              <el-form-item label="Max Tokens Per Community">
                <el-slider
                  v-model="config.ece_max_tokens"
                  :min="512"
                  :max="20480"
                  :step="512"
                  show-input
                />
                <span class="form-item-tip">每个社区的最大token数</span>
              </el-form-item>
            </template>

            <!-- DFS 参数 -->
            <template v-if="config.partition_method === 'dfs'">
              <el-divider content-position="left">DFS 参数</el-divider>
              <el-form-item label="Max Units Per Community">
                <el-input-number v-model="config.dfs_max_units" :min="1" :max="100" />
              </el-form-item>
            </template>

            <!-- BFS 参数 -->
            <template v-if="config.partition_method === 'bfs'">
              <el-divider content-position="left">BFS 参数</el-divider>
              <el-form-item label="Max Units Per Community">
                <el-input-number v-model="config.bfs_max_units" :min="1" :max="100" />
              </el-form-item>
            </template>

            <!-- Leiden 参数 -->
            <template v-if="config.partition_method === 'leiden'">
              <el-divider content-position="left">Leiden 参数</el-divider>
              <el-form-item label="Max Community Size">
                <el-input-number v-model="config.leiden_max_size" :min="1" :max="100" />
              </el-form-item>
              <el-form-item label="Use Largest Connected Component">
                <el-switch v-model="config.leiden_use_lcc" />
              </el-form-item>
              <el-form-item label="Random Seed">
                <el-input-number v-model="config.leiden_random_seed" :min="0" />
              </el-form-item>
            </template>
          </el-collapse-item>

          <!-- 生成配置 -->
          <el-collapse-item title="数据生成配置" name="generate">
            <el-form-item label="生成模式">
              <el-checkbox-group v-model="config.mode">
                <el-checkbox label="atomic">Atomic - 原子级问答</el-checkbox>
                <el-checkbox label="multi_hop">Multi-hop - 多跳问答</el-checkbox>
                <el-checkbox label="aggregated">Aggregated - 聚合问答</el-checkbox>
                <el-checkbox label="cot">CoT - 思维链问答</el-checkbox>
              </el-checkbox-group>
              <div class="form-item-tip">可选择多个生成模式，将同时生成所有选中模式的数据</div>
            </el-form-item>

            <el-form-item label="输出数据格式">
              <el-radio-group v-model="config.data_format">
                <el-radio label="Alpaca">Alpaca</el-radio>
                <el-radio label="Sharegpt">Sharegpt</el-radio>
                <el-radio label="ChatML">ChatML</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-collapse-item>

          <!-- 限流配置 -->
          <el-collapse-item title="API 限流配置" name="rate_limit">
            <el-form-item label="RPM (每分钟请求数)">
              <el-slider
                v-model="config.rpm"
                :min="10"
                :max="10000"
                :step="10"
                show-input
              />
            </el-form-item>

            <el-form-item label="TPM (每分钟Token数)">
              <el-slider
                v-model="config.tpm"
                :min="1000"
                :max="5000000"
                :step="1000"
                show-input
              />
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const configStore = useConfigStore()
// 确保 mode 是数组格式
const initialConfig = { ...configStore.config }
if (typeof initialConfig.mode === 'string') {
  initialConfig.mode = [initialConfig.mode]
} else if (!Array.isArray(initialConfig.mode)) {
  initialConfig.mode = ['aggregated']
}
const config = ref(initialConfig)
const activeNames = ref(['model', 'split', 'partition', 'generate', 'rate_limit'])
const saving = ref(false)
const testing = ref(false)

// 保存配置
const handleSave = async () => {
  saving.value = true
  try {
    // 更新 store
    configStore.config = { ...config.value }
    await configStore.saveConfig()
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
    configStore.resetConfig()
    // 确保 mode 是数组格式
    const resetConfig = { ...configStore.config }
    if (typeof resetConfig.mode === 'string') {
      resetConfig.mode = [resetConfig.mode]
    } else if (!Array.isArray(resetConfig.mode)) {
      resetConfig.mode = ['aggregated']
    }
    config.value = resetConfig
    ElMessage.success('配置已重置')
  } catch {
    // 用户取消操作
  }
}

// 测试连接
const handleTestConnection = async () => {
  if (!config.value.api_key) {
    ElMessage.error('请先填写 API Key')
    return
  }

  testing.value = true
  try {
    await api.testConnection({
      base_url: config.value.synthesizer_url || '',
      api_key: config.value.api_key,
      model_name: config.value.synthesizer_model || ''
    })
    ElMessage.success('连接测试成功')
  } catch (error) {
    ElMessage.error('连接测试失败')
  } finally {
    testing.value = false
  }
}

onMounted(async () => {
  await configStore.loadConfig()
  // 确保 mode 是数组格式
  const loadedConfig = { ...configStore.config }
  if (typeof loadedConfig.mode === 'string') {
    loadedConfig.mode = [loadedConfig.mode]
  } else if (!Array.isArray(loadedConfig.mode)) {
    loadedConfig.mode = ['aggregated']
  }
  config.value = loadedConfig
})
</script>

<style scoped>
.config-container {
  max-width: 1000px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.form-item-tip {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

:deep(.el-collapse-item__header) {
  font-size: 16px;
  font-weight: 600;
}

:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-radio) {
  display: block;
  margin: 10px 0;
}

:deep(.el-checkbox) {
  display: block;
  margin: 10px 0;
}
</style>

