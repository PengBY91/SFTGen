"""
配置管理
"""

import os
import sys
from typing import List
from pydantic_settings import BaseSettings

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class Settings(BaseSettings):
    """应用配置"""
    
    # API 配置
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "KGE-Gen API"
    VERSION: str = "2.0.0"
    
    # 大模型配置
    SYNTHESIZER_MODEL: str = "gpt-3.5-turbo"
    SYNTHESIZER_BASE_URL: str = "https://api.openai.com/v1"
    SYNTHESIZER_API_KEY: str = ""
    
    # CORS 配置
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # 文件上传配置
    UPLOAD_DIR: str = "cache/uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # 任务配置
    TASKS_DIR: str = "tasks"
    TASK_OUTPUT_DIR: str = "tasks/outputs"
    
    # 日志配置
    LOG_DIR: str = "cache/logs"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 调试配置
    DEBUG: bool = False
    MOCK_MODE: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # 允许额外的字段


settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.TASKS_DIR, exist_ok=True)
os.makedirs(settings.TASK_OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.LOG_DIR, exist_ok=True)

