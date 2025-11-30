"""
自动审核服务
使用大模型对生成的数据进行自动审核
"""

import os
import sys
import json
from typing import Dict, Any, List
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from graphgen.models import OpenAIClient
from backend.schemas import DataItem, ReviewStatus, AutoReviewRequest
from backend.services.review_service import review_service
from backend.config import settings


class AutoReviewService:
    """自动审核服务类"""
    
    def __init__(self):
        self.review_prompt_template = """你是一个专业的数据质量审核员，负责评估AI生成的训练数据质量。

请对以下数据进行评估，从以下维度打分（每个维度0-1分）：

1. **相关性** (Relevance): 问题和答案是否相关，答案是否回答了问题
2. **准确性** (Accuracy): 答案内容是否准确、无明显错误
3. **完整性** (Completeness): 答案是否完整，信息是否充分
4. **清晰度** (Clarity): 表达是否清晰，逻辑是否连贯
5. **有用性** (Usefulness): 数据是否对模型训练有价值

数据内容：
```json
{data_content}
```

请以JSON格式返回评估结果：
{{
    "relevance": 0.0-1.0,
    "accuracy": 0.0-1.0,
    "completeness": 0.0-1.0,
    "clarity": 0.0-1.0,
    "usefulness": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "reason": "评估理由（简短说明）",
    "suggestions": "改进建议（如果有问题）"
}}

注意：
- overall_score 是综合评分，建议为各维度的加权平均
- 如果发现明显问题（如答非所问、内容错误等），overall_score 应该较低
- reason 应该简明扼要地说明评分理由
"""
    
    def _get_llm_client(self) -> OpenAIClient:
        """获取LLM客户端"""
        try:
            from graphgen.models.tokenizer.tiktoken_tokenizer import TiktokenTokenizer
            tokenizer = TiktokenTokenizer(model_name="cl100k_base")
            
            client = OpenAIClient(
                model_name=settings.SYNTHESIZER_MODEL,
                api_key=settings.SYNTHESIZER_API_KEY,
                base_url=settings.SYNTHESIZER_BASE_URL,
                tokenizer=tokenizer
            )
            return client
        except Exception as e:
            print(f"创建LLM客户端失败: {e}")
            return None
    
    async def review_single_item(self, item: DataItem) -> Dict[str, Any]:
        """自动审核单个数据项"""
        try:
            # 获取LLM客户端
            client = self._get_llm_client()
            if not client:
                return {
                    "success": False,
                    "error": "无法创建LLM客户端"
                }
            
            # 构建审核提示
            data_content = json.dumps(item.content, ensure_ascii=False, indent=2)
            prompt = self.review_prompt_template.format(data_content=data_content)
            
            # 调用LLM进行审核
            messages = [
                {"role": "system", "content": "你是一个专业的数据质量审核员。"},
                {"role": "user", "content": prompt}
            ]
            
            response = await client.async_call(messages=messages, temperature=0.3)
            
            # 解析响应
            try:
                # 尝试从响应中提取JSON
                response_text = response.strip()
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                review_result = json.loads(response_text)
                
                return {
                    "success": True,
                    "data": {
                        "item_id": item.item_id,
                        "score": review_result.get("overall_score", 0.0),
                        "reason": review_result.get("reason", ""),
                        "suggestions": review_result.get("suggestions", ""),
                        "details": review_result
                    }
                }
            
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"解析审核结果失败: {str(e)}",
                    "raw_response": response
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"自动审核失败: {str(e)}"
            }
    
    async def auto_review_batch(self, request: AutoReviewRequest) -> Dict[str, Any]:
        """批量自动审核（优化版）"""
        try:
            results = []
            errors = []
            
            # 从第一个item_id提取task_id
            if not request.item_ids:
                return {"success": False, "error": "未提供数据项ID"}
            
            task_id = "_".join(request.item_ids[0].split("_")[:-1])
            
            # 【优化1】一次性加载任务数据
            load_result = review_service.load_task_data(task_id)
            if not load_result["success"]:
                return load_result
            
            items_dict = {item["item_id"]: DataItem(**item) for item in load_result["data"]}
            
            # 【优化2】提前加载审核数据，避免后面重复加载
            reviews = review_service._load_reviews(task_id)
            
            # 逐个审核（这部分需要调用LLM，无法避免）
            for item_id in request.item_ids:
                if item_id not in items_dict:
                    errors.append({"item_id": item_id, "error": "数据项不存在"})
                    continue
                
                # 始终使用 items_dict 中的新鲜数据进行自动审核
                # 不使用 reviews 中可能被手动修改过的数据
                item = items_dict[item_id]
                
                # 调用自动审核
                review_result = await self.review_single_item(item)
                
                if review_result["success"]:
                    score = review_result["data"]["score"]
                    reason = review_result["data"]["reason"]
                    
                    # 更新数据项
                    item.auto_review_score = score
                    item.auto_review_reason = reason
                    
                    # 根据阈值自动设置状态
                    if request.auto_approve and score >= request.threshold:
                        item.review_status = ReviewStatus.AUTO_APPROVED
                        item.review_time = datetime.now().isoformat()
                    elif request.auto_reject and score < (request.threshold - 0.2):
                        item.review_status = ReviewStatus.AUTO_REJECTED
                        item.review_time = datetime.now().isoformat()
                    
                    # 【优化3】直接更新到reviews字典中
                    reviews[item_id] = item
                    
                    results.append({
                        "item_id": item_id,
                        "score": score,
                        "status": item.review_status,
                        "reason": reason
                    })
                else:
                    errors.append({
                        "item_id": item_id,
                        "error": review_result.get("error", "未知错误")
                    })
            
            # 【优化4】只保存一次文件（移除了重复的_load_reviews调用）
            if results:  # 只有成功审核的才保存
                review_service._save_reviews(task_id, reviews)
            
            return {
                "success": True,
                "message": f"自动审核完成，成功 {len(results)} 个，失败 {len(errors)} 个",
                "data": {
                    "results": results,
                    "errors": errors,
                    "success_count": len(results),
                    "error_count": len(errors)
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"批量自动审核失败: {str(e)}"
            }


# 全局服务实例
auto_review_service = AutoReviewService()

