"""
任务管理 API 接口
提供任务管理的 HTTP API 端点
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from webui.task_manager import task_manager, TaskStatus, TaskInfo
from webui.task_processor import TaskProcessor
from webui.base import WebuiParams


class TaskAPI:
    """任务管理 API 类"""
    
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.task_processor = TaskProcessor(root_dir)
    
    def create_task(self, filename: str, file_path: str) -> Dict[str, Any]:
        """创建新任务"""
        try:
            task_id = task_manager.create_task(filename, file_path)
            task = task_manager.get_task(task_id)
            return {
                "success": True,
                "task_id": task_id,
                "task": task.to_dict()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """获取任务信息"""
        try:
            task = task_manager.get_task(task_id)
            if task:
                return {
                    "success": True,
                    "task": task.to_dict()
                }
            else:
                return {
                    "success": False,
                    "error": "任务不存在"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务"""
        try:
            tasks = task_manager.get_all_tasks()
            return {
                "success": True,
                "tasks": [task.to_dict() for task in tasks]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def start_task(self, task_id: str, params: WebuiParams) -> Dict[str, Any]:
        """启动任务处理"""
        try:
            task = task_manager.get_task(task_id)
            if not task:
                return {
                    "success": False,
                    "error": "任务不存在"
                }
            
            if task.status != TaskStatus.PENDING:
                return {
                    "success": False,
                    "error": f"任务状态为 {task.status.value}，无法启动"
                }
            
            if self.task_processor.is_task_processing(task_id):
                return {
                    "success": False,
                    "error": "任务正在处理中"
                }
            
            success = self.task_processor.start_task(task_id, params)
            if success:
                return {
                    "success": True,
                    "message": "任务已启动"
                }
            else:
                return {
                    "success": False,
                    "error": "启动任务失败"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """删除任务"""
        try:
            success = task_manager.delete_task(task_id)
            if success:
                return {
                    "success": True,
                    "message": "任务已删除"
                }
            else:
                return {
                    "success": False,
                    "error": "任务不存在"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def download_task_output(self, task_id: str) -> Dict[str, Any]:
        """获取任务输出文件下载信息"""
        try:
            task = task_manager.get_task(task_id)
            if not task:
                return {
                    "success": False,
                    "error": "任务不存在"
                }
            
            if task.status != TaskStatus.COMPLETED:
                return {
                    "success": False,
                    "error": f"任务状态为 {task.status.value}，无法下载"
                }
            
            if not task.output_file or not os.path.exists(task.output_file):
                return {
                    "success": False,
                    "error": "输出文件不存在"
                }
            
            return {
                "success": True,
                "output_file": task.output_file,
                "filename": f"{task.filename}_output.jsonl"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_task_status_summary(self) -> Dict[str, Any]:
        """获取任务状态统计"""
        try:
            tasks = task_manager.get_all_tasks()
            summary = {
                "total": len(tasks),
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            }
            
            for task in tasks:
                summary[task.status.value] += 1
            
            return {
                "success": True,
                "summary": summary
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_old_tasks(self, days: int = 7) -> Dict[str, Any]:
        """清理旧任务"""
        try:
            task_manager.cleanup_old_tasks(days)
            return {
                "success": True,
                "message": f"已清理 {days} 天前的旧任务"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局 API 实例
task_api = None

def get_task_api(root_dir: str) -> TaskAPI:
    """获取任务 API 实例"""
    global task_api
    if task_api is None:
        task_api = TaskAPI(root_dir)
    return task_api
