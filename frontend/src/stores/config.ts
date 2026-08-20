import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TaskConfig } from '@/api/types'
import api from '@/api'
import { ElMessage } from 'element-plus'

// LLM 连接相关字段：这些字段的默认值以服务端为准（graphgen/configs/llm_config.py / .env）
export const LLM_FIELDS = [
  'synthesizer_url',
  'synthesizer_model',
  'api_key',
  'trainee_url',
  'trainee_model',
  'trainee_api_key',
  'rpm',
  'tpm',
  'tokenizer'
] as const

// 本地兜底默认（仅在服务端不可达时使用；正常情况会被 /config/llm-defaults 覆盖）
const LOCAL_LLM_FALLBACK: Partial<TaskConfig> = {
  synthesizer_url: '',
  synthesizer_model: '',
  trainee_url: '',
  trainee_model: '',
  api_key: '',
  trainee_api_key: '',
  rpm: 1000,
  tpm: 50000,
  tokenizer: 'cl100k_base'
}

// 非 LLM 字段的本地默认
const BASE_DEFAULTS: Omit<TaskConfig, keyof typeof LOCAL_LLM_FALLBACK> = {
  if_trainee_model: false,
  chunk_size: 1024,
  chunk_overlap: 100,
  quiz_samples: 2,
  partition_method: 'ece',
  dfs_max_units: 5,
  bfs_max_units: 5,
  leiden_max_size: 20,
  leiden_use_lcc: false,
  leiden_random_seed: 42,
  ece_max_units: 20,
  ece_min_units: 3,
  ece_max_tokens: 10240,
  ece_unit_sampling: 'random',
  mode: ['aggregated'],
  data_format: 'Alpaca',
  // 优化配置
  enable_extraction_cache: true,
  dynamic_chunk_size: false,
  use_multi_template: true,
  template_seed: undefined,
  // 批量请求配置（知识抽取阶段）
  enable_batch_requests: true,
  batch_size: 10,
  max_wait_time: 0.5,
  // 批量生成配置（问题生成阶段）
  use_adaptive_batching: false,
  min_batch_size: 5,
  max_batch_size: 50,
  enable_prompt_cache: true,
  cache_max_size: 10000,
  cache_ttl: undefined,
  // 生成配置
  qa_pair_limit: 200,
  qa_ratio_atomic: 20,
  qa_ratio_aggregated: 20,
  qa_ratio_multi_hop: 20,
  qa_ratio_cot: 20,
  qa_ratio_hierarchical: 20,
  // Hierarchical 配置
  hierarchical_relations: ['is_a', 'subclass_of', 'part_of', 'includes', 'type_of'],
  structure_format: 'markdown',
  max_hierarchical_depth: 3,
  max_siblings_per_community: 10,
  persistent_deduplication: true,
  question_first: true,
  chinese_only: false
} as unknown as Omit<TaskConfig, keyof typeof LOCAL_LLM_FALLBACK>

function buildDefaults(llmDefaults: Partial<TaskConfig> | null): TaskConfig {
  const llm = { ...LOCAL_LLM_FALLBACK, ...(llmDefaults || {}) }
  return { ...BASE_DEFAULTS, ...llm } as TaskConfig
}

export const useConfigStore = defineStore('config', () => {
  // 服务端 LLM 默认值缓存
  const llmDefaults = ref<Partial<TaskConfig> | null>(null)

  const config = ref<TaskConfig>(buildDefaults(null))

  // 拉取服务端 LLM 默认值，并填充当前配置中为空的 LLM 字段
  const fetchLLMDefaults = async () => {
    try {
      const response = await api.getLLMDefaults()
      if (response.success && response.data) {
        llmDefaults.value = response.data
        // 填充空字段（不覆盖用户已填的值）
        for (const field of LLM_FIELDS) {
          const current = (config.value as Record<string, unknown>)[field]
          const server = (response.data as Record<string, unknown>)[field]
          const isEmpty =
            current === undefined || current === null || current === '' ||
            (field === 'tokenizer' && current === 'cl100k_base' && server)
          if ((server !== undefined && server !== null && server !== '') && (isEmpty)) {
            ;(config.value as Record<string, unknown>)[field] = server
          }
        }
      }
    } catch (error) {
      console.log('使用本地 LLM 兜底默认值')
    }
  }

  // 加载配置
  const loadConfig = async () => {
    // 先取服务端 LLM 默认值（保证未保存过配置时也有正确的连接信息）
    await fetchLLMDefaults()
    try {
      const response = await api.loadConfig()
      if (response.success && response.data) {
        const loadedConfig = { ...config.value, ...response.data }
        // 兼容处理：如果 mode 是字符串，转换为数组
        if (typeof loadedConfig.mode === 'string') {
          loadedConfig.mode = [loadedConfig.mode]
        } else if (!Array.isArray(loadedConfig.mode)) {
          loadedConfig.mode = ['aggregated']
        }
        config.value = loadedConfig
      }
    } catch (error) {
      console.log('使用默认配置')
    }
  }

  // 保存配置
  const saveConfig = async () => {
    try {
      const response = await api.saveConfig(config.value)
      if (response.success) {
        ElMessage.success('配置保存成功')
      }
    } catch (error) {
      ElMessage.error('配置保存失败')
    }
  }

  // 更新配置
  const updateConfig = (key: keyof TaskConfig, value: any) => {
    ;(config.value as Record<string, unknown>)[key] = value
  }

  // 重置配置（LLM 字段使用服务端默认值）
  const resetConfig = () => {
    config.value = buildDefaults(llmDefaults.value)
  }

  return {
    config,
    llmDefaults,
    fetchLLMDefaults,
    loadConfig,
    saveConfig,
    updateConfig,
    resetConfig
  }
})
