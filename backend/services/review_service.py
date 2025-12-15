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
                # 先尝试作为 JSON 读取
                try:
                    data = json.load(f)
                    
                    # 检查是否是评测任务的数据结构（包含 'items' 数组）
                    if isinstance(data, dict) and 'items' in data:
                        # 评测任务：提取 items 数组
                        items = data['items']
                    elif isinstance(data, list):
                        # SFT任务：直接使用数组
                        items = data
                    else:
                        # 单个对象
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
                # 为评测任务生成特殊的 item_id（使用评测项的 id 字段）
                if 'id' in item and item['id'].startswith('eval_'):
                    item_id = item['id']
                else:
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
    
    def get_export_file(self, task_id: str, format: str = 'json', optional_fields: List[str] = []) -> Dict[str, Any]:
        """获取导出文件（下载时即时转换格式）
        
        Args:
            task_id: 任务ID
            format: 导出格式，'json' 或 'csv'
            optional_fields: 可选字段列表（仅对 CSV 有效）
        
        Returns:
            包含文件路径的字典
        """
        try:
            # 先检查是否有已导出的 JSON 文件
            json_export_file = os.path.join(self.review_dir, f"{task_id}_all_data.json")
            
            if not os.path.exists(json_export_file):
                return {
                    "success": False,
                    "error": "请先在审核页面点击导出数据"
                }
            
            # 如果请求 JSON，直接返回现有文件
            if format == 'json':
                return {
                    "success": True,
                    "export_file": json_export_file,
                    "filename": f"{task_id}_all_data.json"
                }
            
            # 如果请求 CSV，需要从 JSON 转换
            csv_export_file = os.path.join(self.review_dir, f"{task_id}_all_data.csv")
            
            # 读取 JSON 数据
            with open(json_export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换为 CSV（传递可选字段）
            self._convert_json_to_csv(data, csv_export_file, optional_fields)
            
            return {
                "success": True,
                "export_file": csv_export_file,
                "filename": f"{task_id}_all_data.csv"
            }
            
        except Exception as e:
            print(f"[ERROR] 获取导出文件失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"获取导出文件失败: {str(e)}"
            }
    
    def export_reviewed_data(self, task_id: str, status_filter: Optional[List[str]] = None, format: str = 'json') -> Dict[str, Any]:
        """导出审核后的数据（只生成 JSON，CSV 在下载时转换）
        
        Args:
            task_id: 任务ID
            status_filter: 状态过滤，如果为 ['all'] 则导出所有数据
            format: 导出格式参数（兼容性保留，实际只生成 JSON）
        """
        try:
            # 加载审核数据（从 reviews.json，不是原始任务数据）
            reviews = self._load_reviews(task_id)
            if not reviews:
                return {
                    "success": False,
                    "error": "没有找到审核数据"
                }
            
            # 将 reviews 字典转换为列表
            items = list(reviews.values())
            
            # 过滤状态（如果是 'all' 则不过滤）
            if status_filter and 'all' not in status_filter:
                items = [item for item in items if item.review_status in status_filter]
            
            # 只导出为 JSON 格式（CSV 在下载时即时转换）
            export_file = os.path.join(self.review_dir, f"{task_id}_all_data.json")
            self._export_to_json(items, export_file)
            
            return {
                "success": True,
                "message": f"导出成功，共 {len(items)} 条数据",
                "data": {
                    "export_file": export_file,
                    "count": len(items),
                    "format": "json"
                }
            }
        
        except Exception as e:
            print(f"[ERROR] 导出失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"导出失败: {str(e)}"
            }
    
    def _export_to_json(self, items: List, export_file: str):
        """导出为 JSON 格式，包含审核状态
        
        Args:
            items: DataItem 列表或字典列表
        """
        exported_data = []
        for item in items:
            # 处理 DataItem 对象或字典
            if hasattr(item, 'dict'):
                item_dict = item.dict()
            else:
                item_dict = item
            
            # 获取内容（优先使用修改后的内容）
            content = item_dict.get("modified_content") or item_dict.get("content", {})
            
            # 构建导出项
            export_item = {
                **content,  # 原始问答对内容
                "review_status": item_dict.get("review_status", "pending"),
                "review_comment": item_dict.get("review_comment", ""),
                "reviewer": item_dict.get("reviewer", ""),
                "review_time": item_dict.get("review_time", ""),
                "auto_review_score": item_dict.get("auto_review_score"),
                "item_id": item_dict.get("item_id", "")
            }
            exported_data.append(export_item)
        
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(exported_data, f, ensure_ascii=False, indent=2)
    
    def _convert_json_to_csv(self, json_data: List[Dict], csv_file: str, optional_fields: List[str] = []):
        """将 JSON 数据转换为 CSV 格式（用于下载）
        
        Args:
            json_data: JSON 数据列表
            csv_file: CSV 文件路径
            optional_fields: 可选字段列表（如 context, graph, source_chunks 等）
        """
        import csv
        import json as json_module
        
        if not json_data:
            # 如果没有数据，创建空文件
            with open(csv_file, "w", encoding="utf-8-sig", newline='') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                base_fields = [
                    'question', 'answer', 'mode',
                    'instruction', 'input', 'output',
                    'reasoning_path', 'thinking_process', 'final_answer',
                    'review_status', 'review_comment', 
                    'reviewer', 'review_time', 'review_score', 'item_id'
                ]
                writer.writerow(base_fields + optional_fields)
            return
        
        with open(csv_file, "w", encoding="utf-8-sig", newline='') as f:
            # 定义基础 CSV 列（必须的字段）
            base_fieldnames = [
                'question', 'answer', 'mode',
                'instruction', 'input', 'output',
                'reasoning_path', 'thinking_process', 'final_answer',
                'review_status', 'review_comment', 'reviewer', 
                'review_time', 'auto_review_score', 'item_id'
            ]
            
            # 添加可选字段
            all_fieldnames = base_fieldnames + optional_fields
            
            # 使用 QUOTE_NONNUMERIC 确保所有非数字字段都被引号包围
            writer = csv.DictWriter(
                f, 
                fieldnames=all_fieldnames, 
                extrasaction='ignore',
                quoting=csv.QUOTE_NONNUMERIC
            )
            writer.writeheader()
            
            # 处理字段值，确保特殊字符被正确转义
            def process_value(value):
                """处理字段值，将复杂对象转换为字符串"""
                if value is None:
                    return ''
                elif isinstance(value, (dict, list)):
                    # 将字典和列表转换为 JSON 字符串
                    return json_module.dumps(value, ensure_ascii=False)
                elif isinstance(value, (int, float)):
                    # 保持数字类型（避免被引号包围）
                    return value
                else:
                    # 转换为字符串，自动处理换行符等
                    return str(value)
            
            for item in json_data:
                # 构建 CSV 行（基础字段）
                row = {
                    'question': process_value(item.get('question', '')),
                    'answer': process_value(item.get('answer', '')),
                    'mode': process_value(item.get('mode', '')),
                    'instruction': process_value(item.get('instruction', '')),
                    'input': process_value(item.get('input', '')),
                    'output': process_value(item.get('output', '')),
                    'reasoning_path': process_value(item.get('reasoning_path', '')),
                    'thinking_process': process_value(item.get('thinking_process', '')),
                    'final_answer': process_value(item.get('final_answer', '')),
                    'review_status': process_value(item.get('review_status', 'pending')),
                    'review_comment': process_value(item.get('review_comment', '')),
                    'reviewer': process_value(item.get('reviewer', '')),
                    'review_time': process_value(item.get('review_time', '')),
                    'auto_review_score': process_value(item.get('auto_review_score', '')),
                    'item_id': process_value(item.get('item_id', ''))
                }
                
                # 添加可选字段
                for field in optional_fields:
                    row[field] = process_value(item.get(field, ''))
                
                writer.writerow(row)
    
    def _export_to_csv(self, items: List, export_file: str):
        """导出为 CSV 格式，包含审核状态
        
        Args:
            items: DataItem 列表或字典列表
        """
        import csv
        import json
        
        if not items:
            # 如果没有数据，创建空文件
            with open(export_file, "w", encoding="utf-8-sig", newline='') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['question', 'answer', 'mode', 'review_status', 'review_comment', 
                               'reviewer', 'review_time', 'auto_review_score', 'item_id'])
            return
        
        with open(export_file, "w", encoding="utf-8-sig", newline='') as f:
            # 定义 CSV 列
            fieldnames = [
                'question', 'answer', 'mode', 
                'review_status', 'review_comment', 'reviewer', 
                'review_time', 'auto_review_score', 'item_id'
            ]
            
            # 使用 QUOTE_NONNUMERIC 确保所有非数字字段都被引号包围
            writer = csv.DictWriter(
                f, 
                fieldnames=fieldnames, 
                extrasaction='ignore',
                quoting=csv.QUOTE_NONNUMERIC
            )
            writer.writeheader()
            
            for item in items:
                # 处理 DataItem 对象或字典
                if hasattr(item, 'dict'):
                    item_dict = item.dict()
                else:
                    item_dict = item
                
                # 获取内容（优先使用修改后的内容）
                content = item_dict.get("modified_content") or item_dict.get("content", {})
                
                # 处理字段值，确保特殊字符被正确转义
                def process_value(value):
                    """处理字段值，将复杂对象转换为字符串"""
                    if value is None:
                        return ''
                    elif isinstance(value, (dict, list)):
                        # 将字典和列表转换为 JSON 字符串
                        return json.dumps(value, ensure_ascii=False)
                    elif isinstance(value, (int, float)):
                        # 保持数字类型（避免被引号包围）
                        return value
                    else:
                        # 转换为字符串，自动处理换行符等
                        return str(value)
                
                # 构建 CSV 行
                row = {
                    'question': process_value(content.get('question', '')),
                    'answer': process_value(content.get('answer', '')),
                    'mode': process_value(content.get('mode', '')),
                    'review_status': process_value(item_dict.get("review_status", "pending")),
                    'review_comment': process_value(item_dict.get("review_comment", "")),
                    'reviewer': process_value(item_dict.get("reviewer", "")),
                    'review_time': process_value(item_dict.get("review_time", "")),
                    'auto_review_score': item_dict.get("auto_review_score") if item_dict.get("auto_review_score") is not None else '',
                    'item_id': process_value(item_dict.get("item_id", ""))
                }
                writer.writerow(row)


# 全局服务实例
review_service = ReviewService()

