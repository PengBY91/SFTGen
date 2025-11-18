"""
配置服务
"""

import os
import json
from typing import Dict, Any

from backend.schemas import TaskConfig


class ConfigService:
    """配置服务类"""
    
    def __init__(self):
        self.config_file = "cache/user_config.json"
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
    
    def save_config(self, config: TaskConfig) -> Dict[str, Any]:
        """保存配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config.dict(), f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": "配置已保存"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if not os.path.exists(self.config_file):
                return {
                    "success": False,
                    "error": "配置文件不存在"
                }
            
            with open(self.config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            return {
                "success": True,
                "data": config_data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局服务实例
config_service = ConfigService()

