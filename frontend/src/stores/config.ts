import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TaskConfig } from '@/api/types'
import api from '@/api'
import { ElMessage } from 'element-plus'

export const useConfigStore = defineStore('config', () => {
  // 默认配置
  const config = ref<TaskConfig>({
    if_trainee_model: false,
    tokenizer: 'cl100k_base',
    synthesizer_url: 'https://api.siliconflow.cn/v1',
    synthesizer_model: 'Qwen/Qwen2.5-7B-Instruct',
    trainee_url: 'https://api.siliconflow.cn/v1',
    trainee_model: 'Qwen/Qwen2.5-7B-Instruct',
    api_key: '',
    trainee_api_key: '',
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
    mode: ['aggregated'],  // 改为数组格式，默认选择 aggregated
    data_format: 'Alpaca',
    rpm: 1000,
    tpm: 50000,
    // 优化配置
    enable_extraction_cache: true,  // 默认启用提取缓存
    dynamic_chunk_size: false,  // 默认关闭动态chunk大小
    use_multi_template: true,  // 默认启用多模板采样
    template_seed: undefined,  // 可选，用于可复现性
    // 批量请求配置
    enable_batch_requests: true,  // 默认启用批量请求
    batch_size: 10,  // 默认批量大小
    max_wait_time: 0.5,  // 默认最大等待时间（秒）
    // 生成配置
    qa_pair_limit: 200,  // 默认目标QA数量
    qa_ratio_atomic: 25,
    qa_ratio_aggregated: 25,
    qa_ratio_multi_hop: 25,
    qa_ratio_cot: 25,
    persistent_deduplication: true,
    question_first: true
  })

  // 加载配置
  const loadConfig = async () => {
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
    config.value[key] = value as never
  }

  // 重置配置
  const resetConfig = () => {
    config.value = {
      if_trainee_model: false,
      tokenizer: 'cl100k_base',
      synthesizer_url: 'https://api.siliconflow.cn/v1',
      synthesizer_model: 'Qwen/Qwen2.5-7B-Instruct',
      trainee_url: 'https://api.siliconflow.cn/v1',
      trainee_model: 'Qwen/Qwen2.5-7B-Instruct',
      api_key: '',
      trainee_api_key: '',
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
      mode: ['aggregated'],  // 改为数组格式，默认选择 aggregated
      data_format: 'Alpaca',
      rpm: 1000,
      tpm: 50000,
      // 优化配置
      enable_extraction_cache: true,
      dynamic_chunk_size: false,
      use_multi_template: true,
      template_seed: undefined,
      // 批量请求配置
      enable_batch_requests: true,
      batch_size: 10,
      max_wait_time: 0.5,
      // 生成配置
      qa_pair_limit: 200,
      qa_ratio_atomic: 25,
      qa_ratio_aggregated: 25,
      qa_ratio_multi_hop: 25,
      qa_ratio_cot: 25,
      persistent_deduplication: true,
      question_first: true
    }
  }

  return {
    config,
    loadConfig,
    saveConfig,
    updateConfig,
    resetConfig
  }
})

