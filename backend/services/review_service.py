"""
审核服务
负责数据审核、自动审核等功能
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.schemas import DataItem, ReviewStatus, ReviewRequest, BatchReviewRequest, AutoReviewRequest
from backend.config import settings


class ReviewService:
    """审核服务类"""
    
    def __init__(self):
        self.review_dir = "tasks/reviews"
        os.makedirs(self.review_dir, exist_ok=True)
    
    def _get_review_file(self, task_id: str) -> str:
        """获取审核文件路径"""
        return os.path.join(self.review_dir, f"{task_id}_reviews.json")
    
    def _load_reviews(self, task_id: str) -> Dict[str, DataItem]:
        """加载任务的审核数据"""
        review_file = self._get_review_file(task_id)
        if not os.path.exists(review_file):
            return {}
        
        try:
            with open(review_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {k: DataItem(**v) for k, v in data.items()}
        except Exception as e:
            print(f"加载审核数据失败: {e}")
            return {}
    
    def _save_reviews(self, task_id: str, reviews: Dict[str, DataItem]):
        """保存审核数据"""
        review_file = self._get_review_file(task_id)
        try:
            data = {k: v.dict() for k, v in reviews.items()}
            with open(review_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存审核数据失败: {e}")
    
    def load_task_data(self, task_id: str) -> Dict[str, Any]:
        """加载任务生成的数据"""
        try:
            # 首先尝试从 task_manager 获取任务信息
            from webui.task_manager import task_manager
            task = task_manager.get_task(task_id)
            
            if not task:
                return {"success": False, "error": "任务不存在"}
            
            if task.status.value != "completed":
                return {"success": False, "error": f"任务状态为 {task.status.value}，只能审核已完成的任务"}
            
            if not task.output_file or not os.path.exists(task.output_file):
                return {"success": False, "error": "任务输出文件不存在"}
            
            output_file = task.output_file
            
            # 读取数据
            items = []
            with open(output_file, "r", encoding="utf-8") as f:
                # 先尝试作为 JSON 数组读取
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        items = data
                    else:
                        items = [data]
                except json.JSONDecodeError:
                    # 如果失败，尝试作为 JSONL 读取
                    f.seek(0)
                    for line in f:
                        if line.strip():
                            try:
                                items.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            
            # 加载现有审核数据
            reviews = self._load_reviews(task_id)
            
            # 转换为 DataItem
            data_items = []
            for idx, item in enumerate(items):
                item_id = f"{task_id}_{idx}"
                
                if item_id in reviews:
                    data_items.append(reviews[item_id])
                else:
                    data_item = DataItem(
                        item_id=item_id,
                        task_id=task_id,
                        content=item,
                        review_status=ReviewStatus.PENDING
                    )
                    data_items.append(data_item)
            
            return {
                "success": True,
                "data": [item.dict() for item in data_items],
                "total": len(data_items)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"加载任务数据失败: {str(e)}"
            }
    
    def review_item(self, request: ReviewRequest) -> Dict[str, Any]:
        """审核单个数据项"""
        try:
            # 使用 request 中的 task_id，如果没有则从 item_id 提取
            task_id = request.task_id if hasattr(request, 'task_id') and request.task_id else "_".join(request.item_id.split("_")[:-1])
            
            # 加载任务数据以获取原始内容
            task_data_result = self.load_task_data(task_id)
            if not task_data_result["success"]:
                return task_data_result
            
            all_items = {item["item_id"]: item for item in task_data_result["data"]}
            
            if request.item_id not in all_items:
                return {"success": False, "error": "数据项不存在"}
            
            # 加载现有审核数据
            reviews = self._load_reviews(task_id)
            
            # 获取或创建数据项
            if request.item_id in reviews:
                item = reviews[request.item_id]
            else:
                item = DataItem(**all_items[request.item_id])
            
            # 更新审核信息
            item.review_status = request.review_status
            item.review_comment = request.review_comment
            item.reviewer = request.reviewer
            item.review_time = datetime.now().isoformat()
            
            if request.modified_content:
                item.modified_content = request.modified_content
                item.review_status = ReviewStatus.MODIFIED
            
            # 保存
            reviews[request.item_id] = item
            self._save_reviews(task_id, reviews)
            
            return {
                "success": True,
                "message": "审核成功",
                "data": item.dict()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"审核失败: {str(e)}"
            }
    
    def batch_review(self, request: BatchReviewRequest) -> Dict[str, Any]:
        """批量审核数据项（优化版）"""
        try:
            results = []
            errors = []
            
            # 【优化1】只加载一次任务数据
            task_data_result = self.load_task_data(request.task_id)
            if not task_data_result["success"]:
                return task_data_result
            
            all_items = {item["item_id"]: item for item in task_data_result["data"]}
            
            # 【优化2】只加载一次审核数据
            reviews = self._load_reviews(request.task_id)
            
            # 【优化3】批量更新审核数据
            for item_id in request.item_ids:
                try:
                    if item_id not in all_items:
                        errors.append({"item_id": item_id, "error": "数据项不存在"})
                        continue
                    
                    # 获取或创建数据项
                    if item_id in reviews:
                        item = reviews[item_id]
                    else:
                        item = DataItem(**all_items[item_id])
                    
                    # 更新审核信息
                    item.review_status = request.review_status
                    item.review_comment = request.review_comment
                    item.reviewer = request.reviewer
                    item.review_time = datetime.now().isoformat()
                    
                    # 保存到内存中
                    reviews[item_id] = item
                    results.append(item_id)
                    
                except Exception as e:
                    errors.append({"item_id": item_id, "error": str(e)})
            
            # 【优化4】只保存一次文件
            if results:  # 只有成功审核的才保存
                self._save_reviews(request.task_id, reviews)
            
            return {
                "success": True,
                "message": f"批量审核完成，成功 {len(results)} 个，失败 {len(errors)} 个",
                "data": {
                    "success_count": len(results),
                    "error_count": len(errors),
                    "errors": errors
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"批量审核失败: {str(e)}"
            }
    
    def get_review_stats(self, task_id: str) -> Dict[str, Any]:
        """获取审核统计"""
        try:
            result = self.load_task_data(task_id)
            if not result["success"]:
                return result
            
            items = result["data"]
            stats = {
                "total": len(items),
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "modified": 0,
                "auto_approved": 0,
                "auto_rejected": 0
            }
            
            for item in items:
                status = item["review_status"]
                if status == ReviewStatus.PENDING:
                    stats["pending"] += 1
                elif status == ReviewStatus.APPROVED:
                    stats["approved"] += 1
                elif status == ReviewStatus.REJECTED:
                    stats["rejected"] += 1
                elif status == ReviewStatus.MODIFIED:
                    stats["modified"] += 1
                elif status == ReviewStatus.AUTO_APPROVED:
                    stats["auto_approved"] += 1
                elif status == ReviewStatus.AUTO_REJECTED:
                    stats["auto_rejected"] += 1
            
            return {
                "success": True,
                "data": stats
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"获取统计失败: {str(e)}"
            }
    
    def export_reviewed_data(self, task_id: str, status_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """导出审核后的数据"""
        try:
            result = self.load_task_data(task_id)
            if not result["success"]:
                return result
            
            items = result["data"]
            
            # 过滤状态
            if status_filter:
                items = [item for item in items if item["review_status"] in status_filter]
            
            # 提取最终内容（优先使用修改后的内容）
            exported_data = []
            for item in items:
                if item.get("modified_content"):
                    exported_data.append(item["modified_content"])
                else:
                    exported_data.append(item["content"])
            
            # 保存导出文件
            export_file = os.path.join(self.review_dir, f"{task_id}_reviewed.json")
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(exported_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": f"导出成功，共 {len(exported_data)} 条数据",
                "data": {
                    "export_file": export_file,
                    "count": len(exported_data)
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"导出失败: {str(e)}"
            }


# 全局服务实例
review_service = ReviewService()

