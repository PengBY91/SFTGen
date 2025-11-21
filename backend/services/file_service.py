"""
文件服务
"""

import os
import shutil
from typing import Dict, Any
from datetime import datetime
from fastapi import UploadFile

from backend.config import settings


class FileService:
    """文件服务类"""
    
    async def save_upload_file(self, file: UploadFile) -> Dict[str, str]:
        """保存上传的文件，如果文件名相同则添加时间戳区分"""
        # 确保上传目录存在
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # 获取原始文件名和扩展名
        original_filename = file.filename
        if not original_filename:
            original_filename = "uploaded_file"
        
        # 分离文件名和扩展名
        name, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ""
        
        # 生成带时间戳的文件名（格式：原文件名_YYYYMMDD_HHMMSS.扩展名）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{name}_{timestamp}{ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "filename": original_filename,  # 返回原始文件名
            "saved_filename": safe_filename,  # 返回保存的文件名
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

