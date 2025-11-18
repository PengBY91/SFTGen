"""
服务层初始化
"""

from backend.services.task_service import TaskService
from backend.services.file_service import FileService
from backend.services.config_service import ConfigService

__all__ = ["TaskService", "FileService", "ConfigService"]

