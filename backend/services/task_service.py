"""
任务服务
"""

import os
import sys
import threading
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from webui.task_manager import task_manager, TaskStatus
from webui.base import WebuiParams
from backend.core.task_processor import TaskProcessor
from backend.schemas import TaskConfig


class TaskService:
    """任务服务类"""
    
    def __init__(self):
        self.task_processor = TaskProcessor()
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务"""
        try:
            tasks = task_manager.get_all_tasks()
            # 确保返回列表，即使为空
            task_list = [task.to_dict() for task in tasks] if tasks else []
            return {
                "success": True,
                "data": task_list
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "data": []  # 出错时也返回空数组
            }
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """获取任务信息"""
        try:
            task = task_manager.get_task(task_id)
            if task:
                return {
                    "success": True,
                    "data": task.to_dict()
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
    
    def create_task(self, task_name: str, filenames: list, filepaths: list, 
                    task_description: str = None) -> Dict[str, Any]:
        """创建新任务"""
        try:
            task_id = task_manager.create_task(
                task_name=task_name,
                filenames=filenames,
                filepaths=filepaths,
                task_description=task_description
            )
            task = task_manager.get_task(task_id)
            return {
                "success": True,
                "task_id": task_id,
                "data": task.to_dict() if task else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def start_task(
        self,
        task_id: str,
        config: TaskConfig
    ) -> Dict[str, Any]:
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
            
            # 保存配置到任务
            task.config = config.dict()
            # 提取并保存模型信息
            task.synthesizer_model = config.synthesizer_model
            task.trainee_model = config.trainee_model if config.if_trainee_model else None
            task_manager._save_tasks()
            
            # 在后台线程中启动任务，避免 Broken pipe 错误
            thread = threading.Thread(
                target=self._run_task_in_thread,
                args=(task_id, config),
                daemon=True
            )
            thread.start()
            
            # 只返回最小必要的数据，避免响应过大
            return {
                "success": True,
                "message": "任务已启动",
                "data": {"task_id": task_id}
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _run_task_in_thread(self, task_id: str, config: TaskConfig):
        """在线程中运行任务"""
        try:
            self.task_processor.process_task(task_id, config)
        except Exception as e:
            print(f"任务处理异常: {e}")
            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
    
    def resume_task(
        self,
        task_id: str,
        config: TaskConfig
    ) -> Dict[str, Any]:
        """恢复中断的任务或处理新文件"""
        try:
            task = task_manager.get_task(task_id)
            if not task:
                return {
                    "success": False,
                    "error": "任务不存在"
                }
            
            # 检查是否可以恢复
            if not task_manager.has_new_files_to_process(task_id):
                return {
                    "success": False,
                    "error": "任务没有新文件需要处理"
                }
            
            # 恢复任务状态
            success = task_manager.resume_task(task_id)
            if not success:
                return {
                    "success": False,
                    "error": "恢复任务失败"
                }
            
            # 保存配置到任务
            task.config = config.dict()
            
            # 在后台线程中重新启动任务，避免 Broken pipe 错误
            thread = threading.Thread(
                target=self._run_task_in_thread,
                args=(task_id, config),
                daemon=True
            )
            thread.start()
            
            return {
                "success": True,
                "message": "任务已恢复并重新启动",
                "data": {"task_id": task_id}
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
    
    def get_task_output(self, task_id: str) -> Dict[str, Any]:
        """获取任务输出文件信息"""
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
                "filename": f"{task.filename}_output.json"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计"""
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
                "data": summary
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_files_to_task(self, task_id: str, filepaths: list) -> Dict[str, Any]:
        """添加文件到任务"""
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
                    "error": f"任务状态为 {task.status.value}，无法添加文件"
                }
            
            # 添加新文件路径
            task.filepaths.extend(filepaths)
            
            # 从文件路径提取文件名
            import os
            new_filenames = [os.path.basename(path) for path in filepaths]
            task.filenames.extend(new_filenames)
            
            # 保存任务
            task_manager._save_tasks()
            
            return {
                "success": True,
                "message": f"成功添加 {len(filepaths)} 个文件",
                "data": task.to_dict()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def remove_file_from_task(self, task_id: str, file_index: int) -> Dict[str, Any]:
        """从任务中删除文件"""
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
                    "error": f"任务状态为 {task.status.value}，无法删除文件"
                }
            
            if len(task.filenames) <= 1:
                return {
                    "success": False,
                    "error": "任务至少需要保留一个文件"
                }
            
            if file_index < 0 or file_index >= len(task.filenames):
                return {
                    "success": False,
                    "error": "文件索引无效"
                }
            
            # 删除指定索引的文件
            removed_filename = task.filenames.pop(file_index)
            removed_filepath = task.filepaths.pop(file_index)
            
            # 保存任务
            task_manager._save_tasks()
            
            return {
                "success": True,
                "message": f"成功删除文件 {removed_filename}",
                "data": task.to_dict()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_task_source(self, task_id: str, file_index: int = 0) -> Dict[str, Any]:
        """获取任务的原始输入文件内容
        
        Args:
            task_id: 任务ID
            file_index: 文件索引，默认为0（第一个文件）
        """
        try:
            task = task_manager.get_task(task_id)
            if not task:
                return {
                    "success": False,
                    "error": "任务不存在"
                }
            
            # 检查文件索引是否有效
            if not task.filepaths or len(task.filepaths) == 0:
                return {
                    "success": False,
                    "error": "任务没有关联的文件"
                }
            
            if file_index < 0 or file_index >= len(task.filepaths):
                return {
                    "success": False,
                    "error": f"文件索引 {file_index} 超出范围，任务共有 {len(task.filepaths)} 个文件"
                }
            
            # 获取指定索引的文件路径和文件名
            file_path = task.filepaths[file_index]
            filename = task.filenames[file_index] if file_index < len(task.filenames) else os.path.basename(file_path)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}"
                }
            
            # 读取文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 获取文件大小和行数
                file_size = os.path.getsize(file_path)
                line_count = content.count('\n') + 1 if content else 0
                
                return {
                    "success": True,
                    "data": {
                        "filename": filename,
                        "file_path": file_path,
                        "content": content,
                        "file_size": file_size,
                        "line_count": line_count,
                        "encoding": "utf-8"
                    }
                }
            except UnicodeDecodeError:
                # 如果 UTF-8 解码失败，尝试其他编码
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    return {
                        "success": True,
                        "data": {
                            "filename": filename,
                            "file_path": file_path,
                            "content": content,
                            "file_size": os.path.getsize(file_path),
                            "line_count": content.count('\n') + 1 if content else 0,
                            "encoding": "gbk"
                        }
                    }
                except:
                    return {
                        "success": False,
                        "error": "无法读取文件，可能是二进制文件或编码不支持"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"获取文件内容失败: {str(e)}"
            }


# 全局服务实例
task_service = TaskService()

