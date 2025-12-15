"""
Pydantic 数据模型
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr
from enum import Enum
from datetime import datetime


class TaskConfig(BaseModel):
    """任务配置模型"""
    if_trainee_model: bool = False
    tokenizer: str = "cl100k_base"
    synthesizer_url: str = "https://api.siliconflow.cn/v1"
    synthesizer_model: str = "Qwen/Qwen2.5-7B-Instruct"
    trainee_url: str = "https://api.siliconflow.cn/v1"
    trainee_model: str = "Qwen/Qwen2.5-7B-Instruct"
    api_key: str
    trainee_api_key: Optional[str] = None
    chunk_size: int = 1024
    chunk_overlap: int = 100
    quiz_samples: int = 2
    partition_method: str = "ece"
    dfs_max_units: int = 5
    bfs_max_units: int = 5
    leiden_max_size: int = 20
    leiden_use_lcc: bool = False
    leiden_random_seed: int = 42
    ece_max_units: int = 20
    ece_min_units: int = 3
    ece_max_tokens: int = 10240
    ece_unit_sampling: str = "random"
    mode: str | List[str] = "aggregated"  # 支持单个模式或多个模式
    data_format: str = "Alpaca"
    rpm: int = 1000
    tpm: int = 50000
    # 优化配置
    enable_extraction_cache: bool = True  # 启用提取缓存（默认开启）
    dynamic_chunk_size: bool = False  # 动态chunk大小调整（默认关闭）
    use_multi_template: bool = True  # 多模板采样（默认开启）
    template_seed: Optional[int] = None  # 模板随机种子（可选）
    # 批量请求配置（知识抽取阶段）
    enable_batch_requests: bool = True  # 启用批量请求（默认开启）
    batch_size: int = 10  # 批量大小
    max_wait_time: float = 0.5  # 最大等待时间（秒）
    # 批量生成配置（问题生成阶段）
    use_adaptive_batching: bool = False  # 启用自适应批量大小（默认关闭）
    min_batch_size: int = 5  # 最小批量大小（用于自适应批量）
    max_batch_size: int = 50  # 最大批量大小（用于自适应批量）
    enable_prompt_cache: bool = True  # 启用提示缓存（默认开启）
    cache_max_size: int = 10000  # 缓存最大大小
    cache_ttl: Optional[int] = None  # 缓存TTL（秒，None表示不过期）
    # 生成数量与比例配置
    qa_pair_limit: Optional[int] = None  # 目标生成QA数量（None表示不限制）
    qa_ratio_atomic: float = 25.0  # Atomic 类型占比（百分比）
    qa_ratio_aggregated: float = 25.0  # Aggregated 类型占比
    qa_ratio_multi_hop: float = 25.0  # Multi-hop 类型占比
    qa_ratio_cot: float = 25.0  # CoT 类型占比
    # 去重优化
    persistent_deduplication: bool = True  # 默认启用持久化去重
    question_first: bool = True  # 默认启用"先问后答"流程（在不支持的模式下会被忽略）
    # 语言控制
    chinese_only: bool = False  # 只生成中文问答（默认不限制）
    # 评测配置
    evaluation_enabled: bool = False
    evaluation_dataset_name: str = "Domain Knowledge Evaluation Dataset"
    evaluation_description: str = "Evaluation dataset for domain model assessment"
    evaluation_target_items: int = 200
    evaluation_type_distribution: Optional[Dict[str, float]] = None
    evaluation_difficulty_distribution: Optional[Dict[str, float]] = None
    evaluation_output_format: str = "benchmark"
    evaluation_min_quality_score: float = 0.5


class APITestRequest(BaseModel):
    """API 连接测试请求"""
    base_url: str
    api_key: str
    model_name: str
    
    model_config = {'protected_namespaces': ()}


class TaskType(str, Enum):
    """任务类型枚举"""
    SFT = "sft"
    EVALUATION = "evaluation"


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    task_name: str  # 任务名称
    task_description: Optional[str] = None  # 任务简介
    task_type: TaskType = TaskType.SFT  # 任务类型
    filenames: List[str]  # 文件名列表（支持多文件）
    filepaths: List[str]  # 文件路径列表（支持多文件）


class TaskResponse(BaseModel):
    """任务响应模型"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None  # 改为 Any 类型，支持字典、列表等
    error: Optional[str] = None


class ReviewStatus(str, Enum):
    """审核状态枚举"""
    PENDING = "pending"          # 待审核
    APPROVED = "approved"        # 已通过
    REJECTED = "rejected"        # 已拒绝
    MODIFIED = "modified"        # 已修改
    AUTO_APPROVED = "auto_approved"  # 自动通过
    AUTO_REJECTED = "auto_rejected"  # 自动拒绝


class DataItem(BaseModel):
    """数据项模型"""
    item_id: str
    task_id: str
    content: Dict[str, Any]  # 原始内容（instruction, input, output等）
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_comment: Optional[str] = None
    reviewer: Optional[str] = None
    review_time: Optional[str] = None
    auto_review_score: Optional[float] = None  # 自动审核评分
    auto_review_reason: Optional[str] = None   # 自动审核原因
    modified_content: Optional[Dict[str, Any]] = None  # 修改后的内容


class ReviewRequest(BaseModel):
    """审核请求模型"""
    task_id: str
    item_id: str
    review_status: ReviewStatus
    review_comment: Optional[str] = None
    reviewer: Optional[str] = None
    modified_content: Optional[Dict[str, Any]] = None


class BatchReviewRequest(BaseModel):
    """批量审核请求模型"""
    task_id: str
    item_ids: List[str]
    review_status: ReviewStatus
    review_comment: Optional[str] = None
    reviewer: Optional[str] = None


class AutoReviewRequest(BaseModel):
    """自动审核请求模型"""
    item_ids: List[str]
    threshold: float = 0.7  # 审核通过阈值
    auto_approve: bool = True  # 是否自动通过高分数据
    auto_reject: bool = False  # 是否自动拒绝低分数据


# ==================== 用户认证相关 ====================

class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"          # 管理员
    REVIEWER = "reviewer"    # 审核员


class User(BaseModel):
    """用户模型"""
    user_id: str
    username: str
    email: Optional[EmailStr] = None
    role: UserRole
    is_active: bool = True
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str
    password: str
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.REVIEWER


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """更新用户请求"""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: User


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


# ==================== 评测集相关 ====================

class EvaluationType(str, Enum):
    """评测类型枚举"""
    KNOWLEDGE_COVERAGE = "knowledge_coverage"
    REASONING_ABILITY = "reasoning_ability"
    FACTUAL_ACCURACY = "factual_accuracy"
    COMPREHENSIVE = "comprehensive"


class DifficultyLevel(str, Enum):
    """难度等级枚举"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EvaluationConfig(BaseModel):
    """评测配置模型"""
    enabled: bool = False
    dataset_name: str = "Domain Knowledge Evaluation Dataset"
    description: str = "Evaluation dataset for domain model assessment"
    target_eval_items: int = 200
    type_distribution: Dict[str, float] = {
        "knowledge_coverage": 0.3,
        "reasoning_ability": 0.3,
        "factual_accuracy": 0.2,
        "comprehensive": 0.2,
    }
    difficulty_distribution: Dict[str, float] = {
        "easy": 0.3,
        "medium": 0.5,
        "hard": 0.2,
    }
    output_format: str = "benchmark"  # benchmark, qa_pair, multiple_choice
    min_quality_score: float = 0.5


class EvaluationItemResponse(BaseModel):
    """评测项响应模型"""
    id: str
    type: str
    difficulty: str
    question: str
    reference_answer: str
    evaluation_criteria: Dict[str, Any]
    metadata: Dict[str, Any]
    distractors: List[str] = []


class EvaluationDatasetResponse(BaseModel):
    """评测集响应模型"""
    name: str
    description: str
    items: List[EvaluationItemResponse]
    statistics: Dict[str, Any]
    metadata: Dict[str, Any]


class EvaluationStatsResponse(BaseModel):
    """评测集统计信息响应"""
    task_id: str
    total_items: int
    type_distribution: Dict[str, float]
    difficulty_distribution: Dict[str, float]
    quality_stats: Optional[Dict[str, Any]] = None
    generated_at: Optional[str] = None
