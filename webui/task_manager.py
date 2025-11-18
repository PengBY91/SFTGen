"""
任务管理模块
提供任务创建、状态跟踪、结果管理等功能
"""

import json
import os
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import shutil


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 未开始
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败


@dataclass
class TaskInfo:
    """任务信息数据类"""
    task_id: str
    task_name: str  # 任务名称
    task_description: Optional[str]  # 任务简介
    filenames: List[str]  # 文件名列表（支持多文件）
    filepaths: List[str]  # 文件路径列表（支持多文件）
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    processing_time: Optional[float] = None
    qa_count: Optional[int] = None  # 问答对数量
    config: Optional[Dict[str, Any]] = None  # 任务配置
    
    # 向后兼容的属性
    @property
    def filename(self) -> str:
        """获取第一个文件名（向后兼容）"""
        return self.filenames[0] if self.filenames else ""
    
    @property
    def file_path(self) -> str:
        """获取第一个文件路径（向后兼容）"""
        return self.filepaths[0] if self.filepaths else ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


class TaskManager:
    """任务管理器"""
    
    def __init__(self, tasks_dir: str = "tasks"):
        self.tasks_dir = tasks_dir
        self.tasks: Dict[str, TaskInfo] = {}
        self.lock = threading.Lock()
        
        # 确保任务目录存在
        os.makedirs(self.tasks_dir, exist_ok=True)
        os.makedirs(os.path.join(self.tasks_dir, "outputs"), exist_ok=True)
        
        # 加载已存在的任务
        self._load_tasks()
    
    def _load_tasks(self):
        """从磁盘加载任务信息"""
        tasks_file = os.path.join(self.tasks_dir, "tasks.json")
        if os.path.exists(tasks_file):
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        # 向后兼容：如果是旧格式，转换为新格式
                        if 'filename' in task_data and 'filenames' not in task_data:
                            filenames = [task_data['filename']]
                            filepaths = [task_data['file_path']]
                        else:
                            filenames = task_data.get('filenames', [])
                            filepaths = task_data.get('filepaths', [])
                        
                        task = TaskInfo(
                            task_id=task_data['task_id'],
                            task_name=task_data.get('task_name', task_data.get('filename', '未命名任务')),
                            task_description=task_data.get('task_description'),
                            filenames=filenames,
                            filepaths=filepaths,
                            status=TaskStatus(task_data['status']),
                            created_at=datetime.fromisoformat(task_data['created_at']),
                            started_at=datetime.fromisoformat(task_data['started_at']) if task_data.get('started_at') else None,
                            completed_at=datetime.fromisoformat(task_data['completed_at']) if task_data.get('completed_at') else None,
                            error_message=task_data.get('error_message'),
                            output_file=task_data.get('output_file'),
                            token_usage=task_data.get('token_usage'),
                            processing_time=task_data.get('processing_time'),
                            qa_count=task_data.get('qa_count'),
                            config=task_data.get('config')
                        )
                        self.tasks[task.task_id] = task
            except Exception as e:
                print(f"加载任务信息失败: {e}")
    
    def _save_tasks(self):
        """保存任务信息到磁盘"""
        tasks_file = os.path.join(self.tasks_dir, "tasks.json")
        try:
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'tasks': [task.to_dict() for task in self.tasks.values()]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务信息失败: {e}")
    
    def create_task(self, task_name: str, filenames: List[str], filepaths: List[str],
                    task_description: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> str:
        """创建新任务"""
        with self.lock:
            task_id = str(uuid.uuid4())
            task = TaskInfo(
                task_id=task_id,
                task_name=task_name,
                task_description=task_description,
                filenames=filenames,
                filepaths=filepaths,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                config=config
            )
            self.tasks[task_id] = task
            self._save_tasks()
            return task_id
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        task = self.tasks.get(task_id)
        if task:
            # 如果任务已完成但没有 qa_count，尝试从输出文件计算
            if task.status == TaskStatus.COMPLETED and task.qa_count is None and task.output_file:
                task.qa_count = self._calculate_qa_count(task.output_file)
                # 保存更新后的任务信息
                if task.qa_count is not None:
                    self._save_tasks()
        return task
    
    def get_all_tasks(self) -> List[TaskInfo]:
        """获取所有任务"""
        tasks = list(self.tasks.values())
        # 为已完成但没有 qa_count 的任务计算问答对数量
        updated = False
        for task in tasks:
            if task.status == TaskStatus.COMPLETED and task.qa_count is None and task.output_file:
                task.qa_count = self._calculate_qa_count(task.output_file)
                if task.qa_count is not None:
                    updated = True
        # 如果有更新，保存任务信息
        if updated:
            self._save_tasks()
        return tasks
    
    def _calculate_qa_count(self, output_file: str) -> Optional[int]:
        """从输出文件计算问答对数量"""
        if not os.path.exists(output_file):
            return None
        
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                # 尝试读取为 JSON 数组
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        return len(data)
                    return None
                except json.JSONDecodeError:
                    # 如果不是 JSON 数组，尝试按 JSONL 格式读取
                    f.seek(0)
                    count = 0
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                json.loads(line)
                                count += 1
                            except json.JSONDecodeError:
                                continue
                    return count if count > 0 else None
        except Exception as e:
            print(f"计算问答对数量失败: {e}")
            return None
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          error_message: Optional[str] = None,
                          output_file: Optional[str] = None,
                          token_usage: Optional[Dict[str, int]] = None,
                          qa_count: Optional[int] = None):
        """更新任务状态"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = status
                
                if status == TaskStatus.PROCESSING:
                    task.started_at = datetime.now()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    task.completed_at = datetime.now()
                    if task.started_at:
                        task.processing_time = (task.completed_at - task.started_at).total_seconds()
                
                if error_message:
                    task.error_message = error_message
                if output_file:
                    task.output_file = output_file
                if token_usage:
                    task.token_usage = token_usage
                if qa_count is not None:
                    task.qa_count = qa_count
                
                self._save_tasks()
    
    def has_new_files_to_process(self, task_id: str) -> bool:
        """检查任务是否有新文件需要处理"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        # 如果任务已完成，检查是否有新文件
        if task.status == TaskStatus.COMPLETED:
            # 检查任务是否有多个文件，但只处理了第一个文件
            # 这里简化处理：如果文件数量大于1，认为有新文件需要处理
            return len(task.filenames) > 1
        
        # 失败的任务可以恢复
        if task.status == TaskStatus.FAILED:
            return True
            
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """恢复中断的任务或处理新文件"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                # 失败的任务可以恢复
                if task.status == TaskStatus.FAILED:
                    task.status = TaskStatus.PENDING
                    task.error_message = None
                    self._save_tasks()
                    return True
                # 已完成但有新文件的任务可以继续处理
                elif task.status == TaskStatus.COMPLETED and len(task.filenames) > 1:
                    task.status = TaskStatus.PENDING
                    task.error_message = None
                    # 清除之前的输出文件，因为要重新处理
                    if task.output_file and os.path.exists(task.output_file):
                        try:
                            os.remove(task.output_file)
                        except Exception as e:
                            print(f"删除旧输出文件失败: {e}")
                    task.output_file = None
                    task.qa_count = None
                    task.token_usage = None
                    task.processing_time = None
                    self._save_tasks()
                    return True
            return False
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # 删除输出文件
                if task.output_file and os.path.exists(task.output_file):
                    try:
                        os.remove(task.output_file)
                    except Exception as e:
                        print(f"删除输出文件失败: {e}")
                
                # 删除任务记录
                del self.tasks[task_id]
                self._save_tasks()
                return True
            return False
    
    def get_task_output_path(self, task_id: str) -> str:
        """获取任务输出文件路径"""
        return os.path.join(self.tasks_dir, "outputs", f"{task_id}_output.jsonl")
    
    def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务（超过指定天数的已完成任务）"""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        with self.lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and 
                    task.created_at.timestamp() < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                self.delete_task(task_id)
    
    def add_files_to_task(self, task_id: str, filepaths: list) -> bool:
        """添加文件到任务"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == TaskStatus.PENDING:
                    task.filepaths.extend(filepaths)
                    # 从文件路径提取文件名
                    import os
                    new_filenames = [os.path.basename(path) for path in filepaths]
                    task.filenames.extend(new_filenames)
                    self._save_tasks()
                    return True
            return False
    
    def remove_file_from_task(self, task_id: str, file_index: int) -> bool:
        """从任务中删除文件"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if (task.status == TaskStatus.PENDING and 
                    len(task.filenames) > 1 and 
                    0 <= file_index < len(task.filenames)):
                    task.filenames.pop(file_index)
                    task.filepaths.pop(file_index)
                    self._save_tasks()
                    return True
            return False


# 全局任务管理器实例
task_manager = TaskManager()
