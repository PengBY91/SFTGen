"""
文件服务
"""

import os
import shutil
from typing import Dict, Any
from fastapi import UploadFile

from backend.config import settings


class FileService:
    """文件服务类"""
    
    async def save_upload_file(self, file: UploadFile) -> Dict[str, str]:
        """保存上传的文件"""
        # 确保上传目录存在
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "filename": file.filename,
            "filepath": file_path
        }
    
    def delete_file(self, filepath: str) -> bool:
        """删除文件"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception:
            return False


# 全局服务实例
file_service = FileService()

