export interface TaskConfig {
  if_trainee_model?: boolean
  tokenizer?: string
  synthesizer_url?: string
  synthesizer_model?: string
  trainee_url?: string
  trainee_model?: string
  api_key: string
  trainee_api_key?: string
  chunk_size?: number
  chunk_overlap?: number
  quiz_samples?: number
  partition_method?: string
  dfs_max_units?: number
  bfs_max_units?: number
  leiden_max_size?: number
  leiden_use_lcc?: boolean
  leiden_random_seed?: number
  ece_max_units?: number
  ece_min_units?: number
  ece_max_tokens?: number
  ece_unit_sampling?: string
  mode?: string | string[]  // 支持单个模式或多个模式
  data_format?: string
  rpm?: number
  tpm?: number
  // 优化配置
  enable_extraction_cache?: boolean  // 启用提取缓存
  dynamic_chunk_size?: boolean  // 动态chunk大小调整
  use_multi_template?: boolean  // 多模板采样
  template_seed?: number  // 模板随机种子（可选）
  // 批量请求配置（知识抽取阶段）
  enable_batch_requests?: boolean  // 启用批量请求
  batch_size?: number  // 批量大小
  max_wait_time?: number  // 最大等待时间（秒）
  // 批量生成配置（问题生成阶段）
  use_adaptive_batching?: boolean  // 启用自适应批量大小
  min_batch_size?: number  // 最小批量大小（用于自适应批量）
  max_batch_size?: number  // 最大批量大小（用于自适应批量）
  enable_prompt_cache?: boolean  // 启用提示缓存
  cache_max_size?: number  // 缓存最大大小
  cache_ttl?: number  // 缓存TTL（秒，undefined表示不过期）
  // 生成数量与比例配置
  qa_pair_limit?: number  // 目标QA数量
  qa_ratio_atomic?: number  // Atomic占比（百分比）
  qa_ratio_aggregated?: number  // Aggregated占比
  qa_ratio_multi_hop?: number  // Multi-hop占比
  qa_ratio_cot?: number  // CoT占比
  qa_ratio_hierarchical?: number  // Hierarchical占比
  // Hierarchical partitioner and generator configuration
  hierarchical_relations?: string[]  // 层次关系类型列表
  structure_format?: string  // 树结构格式
  max_hierarchical_depth?: number  // 最大层次深度
  max_siblings_per_community?: number  // 每个社区的最大兄弟节点数
  // 去重优化
  persistent_deduplication?: boolean  // 是否启用持久化去重
  question_first?: boolean  // 是否启用先问后答流程
  // 语言控制
  chinese_only?: boolean  // 只生成中文问答（默认不限制）
}

export interface TaskInfo {
  task_id: string
  task_name: string  // 任务名称
  task_description?: string  // 任务简介
  filenames: string[]  // 文件名列表
  filepaths: string[]  // 文件路径列表
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
  output_file?: string
  token_usage?: {
    synthesizer_tokens: number
    synthesizer_input_tokens?: number
    synthesizer_output_tokens?: number
    trainee_tokens: number
    trainee_input_tokens?: number
    trainee_output_tokens?: number
    total_tokens: number
    total_input_tokens?: number
    total_output_tokens?: number
  }
  processing_time?: number
  qa_count?: number  // 问答对数量
  config?: TaskConfig  // 任务配置
  synthesizer_model?: string  // 合成器模型
  trainee_model?: string  // 训练模型
  // 向后兼容
  filename?: string
  file_path?: string
}

export interface TaskResponse<T = any> {
  success: boolean
  message?: string
  data?: T
  error?: string
}

export interface TaskStats {
  total: number
  pending: number
  processing: number
  completed: number
  failed: number
}

// 审核相关类型
export type ReviewStatus = 
  | 'pending' 
  | 'approved' 
  | 'rejected' 
  | 'modified' 
  | 'auto_approved' 
  | 'auto_rejected'

// 不同数据格式的 content 结构
export interface AlpacaContent {
  instruction: string
  input?: string
  output: string
  mode?: string
  reasoning_path?: string  // 推理路径（COT 和 Multi-hop）
  thinking_process?: string  // 思考过程（COT 特有）
  final_answer?: string  // 最终答案（COT 特有）
  context?: {
    nodes?: Array<{ name: string; description?: string }>
    edges?: Array<{ source: string; target: string; description?: string }>
  }
  graph?: {
    entities?: string[]
    relationships?: string[][]
  }
  source_chunks?: any[]
  source_documents?: any[]
  metadata?: {
    generation_mode?: string
    [key: string]: any
  }
  [key: string]: any
}

export interface SharegptContent {
  conversations: Array<{
    from: string
    value: string
  }>
  mode?: string
  reasoning_path?: string  // 推理路径（COT 和 Multi-hop）
  thinking_process?: string  // 思考过程（COT 特有）
  final_answer?: string  // 最终答案（COT 特有）
  context?: {
    nodes?: Array<{ name: string; description?: string }>
    edges?: Array<{ source: string; target: string; description?: string }>
  }
  graph?: {
    entities?: string[]
    relationships?: string[][]
  }
  source_chunks?: any[]
  source_documents?: any[]
  metadata?: {
    generation_mode?: string
    [key: string]: any
  }
  [key: string]: any
}

export interface ChatMLContent {
  messages: Array<{
    role: string
    content: string
  }>
  mode?: string
  reasoning_path?: string  // 推理路径（COT 和 Multi-hop）
  thinking_process?: string  // 思考过程（COT 特有）
  final_answer?: string  // 最终答案（COT 特有）
  context?: {
    nodes?: Array<{ name: string; description?: string }>
    edges?: Array<{ source: string; target: string; description?: string }>
  }
  graph?: {
    entities?: string[]
    relationships?: string[][]
  }
  source_chunks?: any[]
  source_documents?: any[]
  metadata?: {
    generation_mode?: string
    [key: string]: any
  }
  [key: string]: any
}

// 联合类型，支持所有数据格式
export type DataContent = AlpacaContent | SharegptContent | ChatMLContent

export interface DataItem {
  item_id: string
  task_id: string
  content: DataContent
  review_status: ReviewStatus
  review_comment?: string
  reviewer?: string
  review_time?: string
  auto_review_score?: number
  auto_review_reason?: string
  modified_content?: DataContent
}

export interface ReviewRequest {
  task_id: string  // 添加 task_id
  item_id: string
  review_status: ReviewStatus
  review_comment?: string
  reviewer?: string
  modified_content?: Record<string, any>
}

export interface BatchReviewRequest {
  task_id: string  // 添加 task_id
  item_ids: string[]
  review_status: ReviewStatus
  review_comment?: string
  reviewer?: string
}

export interface AutoReviewRequest {
  item_ids: string[]
  threshold?: number
  auto_approve?: boolean
  auto_reject?: boolean
}

export interface ReviewStats {
  total: number
  pending: number
  approved: number
  rejected: number
  modified: number
  auto_approved: number
  auto_rejected: number
}

