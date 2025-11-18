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
    trainee_tokens: number
    total_tokens: number
  }
  processing_time?: number
  qa_count?: number  // 问答对数量
  config?: TaskConfig  // 任务配置
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

export interface DataItem {
  item_id: string
  task_id: string
  content: Record<string, any>
  review_status: ReviewStatus
  review_comment?: string
  reviewer?: string
  review_time?: string
  auto_review_score?: number
  auto_review_reason?: string
  modified_content?: Record<string, any>
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

