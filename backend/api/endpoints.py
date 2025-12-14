"""
API 端点定义
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse

from backend.schemas import (
    TaskConfig,
    APITestRequest,
    TaskResponse,
    CreateTaskRequest,
    ReviewRequest,
    BatchReviewRequest,
    AutoReviewRequest,
    User,
    UserCreate,
    UserLogin,
    UserUpdate,
    ChangePasswordRequest,
    EvaluationConfig,
    EvaluationDatasetResponse,
    EvaluationStatsResponse
)
from backend.services.task_service import task_service
from backend.services.file_service import file_service
from backend.services.config_service import config_service
from backend.services.review_service import review_service
from backend.services.auto_review_service import auto_review_service
from backend.services.auth_service import auth_service
from backend.dependencies import (
    get_current_user,
    get_current_active_user,
    require_admin,
    require_admin_or_reviewer
)

router = APIRouter()


@router.post("/test-connection", response_model=TaskResponse)
async def test_connection(
    request: APITestRequest,
    current_user: User = Depends(require_admin)
):
    """测试 API 连接（需要管理员权限）"""
    from backend.utils.api_test import test_api_connection
    try:
        test_api_connection(request.base_url, request.api_key, request.model_name)
        return TaskResponse(success=True, message="连接成功")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload", response_model=TaskResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    """上传文件（仅管理员）"""
    try:
        file_info = await file_service.save_upload_file(file)
        return TaskResponse(
            success=True,
            message="文件上传成功",
            data=file_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.get("/tasks", response_model=TaskResponse)
async def get_all_tasks(current_user: User = Depends(get_current_active_user)):
    """获取所有任务（需要登录）"""
    result = task_service.get_all_tasks()
    return result


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, current_user: User = Depends(get_current_active_user)):
    """获取单个任务详情（需要登录）"""
    result = task_service.get_task(task_id)
    return result


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(require_admin)
):
    """创建新任务（仅管理员）"""
    result = task_service.create_task(
        task_name=request.task_name,
        filenames=request.filenames,
        filepaths=request.filepaths,
        task_description=request.task_description
    )
    # 确保 task_id 在响应的顶层
    if result.get("success") and result.get("task_id"):
        result["data"] = result.get("data", {})
        if isinstance(result["data"], dict):
            result["data"]["task_id"] = result["task_id"]
    return result


@router.post("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: str,
    config: TaskConfig,
    current_user: User = Depends(require_admin)
):
    """启动任务（仅管理员）"""
    result = task_service.start_task(task_id, config)
    return result


@router.post("/tasks/{task_id}/resume", response_model=TaskResponse)
async def resume_task(
    task_id: str,
    config: TaskConfig,
    current_user: User = Depends(require_admin)
):
    """恢复中断的任务（仅管理员）"""
    result = task_service.resume_task(task_id, config)
    return result


@router.post("/tasks/{task_id}/files", response_model=TaskResponse)
async def add_files_to_task(
    task_id: str,
    request_data: dict,
    current_user: User = Depends(require_admin)
):
    """添加文件到任务（仅管理员）"""
    filepaths = request_data.get('filepaths', [])
    result = task_service.add_files_to_task(task_id, filepaths)
    return result


@router.delete("/tasks/{task_id}/files/{file_index}", response_model=TaskResponse)
async def remove_file_from_task(
    task_id: str,
    file_index: int,
    current_user: User = Depends(require_admin)
):
    """从任务中删除文件（仅管理员）"""
    result = task_service.remove_file_from_task(task_id, file_index)
    return result


@router.delete("/tasks/{task_id}", response_model=TaskResponse)
async def delete_task(
    task_id: str,
    current_user: User = Depends(require_admin)
):
    """删除任务（仅管理员）"""
    result = task_service.delete_task(task_id)
    return result


@router.get("/tasks/{task_id}/source", response_model=TaskResponse)
async def get_task_source(
    task_id: str,
    file_index: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    """获取任务的原始输入文件内容（需要登录）
    
    Args:
        task_id: 任务ID
        file_index: 文件索引，默认为0（第一个文件）
    """
    result = task_service.get_task_source(task_id, file_index)
    return result


@router.get("/tasks/{task_id}/download")
async def download_task_output(task_id: str, format: str = 'json', optional_fields: str = ''):
    """下载任务输出文件
    
    Args:
        task_id: 任务ID
        format: 下载格式，'json' 或 'csv'
        optional_fields: 可选字段，逗号分隔（仅对 CSV 有效）
    """
    # 解析可选字段
    fields_list = [f.strip() for f in optional_fields.split(',') if f.strip()] if optional_fields else []
    
    result = task_service.get_task_output(task_id, format, fields_list)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "文件不存在"))
    
    output_file = result.get("output_file")
    filename = result.get("filename")
    
    # 根据格式设置 MIME 类型
    media_type = "text/csv" if format == "csv" else "application/json"
    
    return FileResponse(
        path=output_file,
        filename=filename,
        media_type=media_type
    )


@router.get("/tasks/stats/summary", response_model=TaskResponse)
async def get_task_summary():
    """获取任务统计摘要"""
    result = task_service.get_task_stats()
    return result


@router.post("/config/save", response_model=TaskResponse)
async def save_config(config: TaskConfig):
    """保存配置"""
    result = config_service.save_config(config)
    return result


@router.get("/config/load", response_model=TaskResponse)
async def load_config():
    """加载配置"""
    result = config_service.load_config()
    return result


# ==================== 审核相关端点 ====================

@router.get("/reviews/{task_id}/data", response_model=TaskResponse)
async def get_review_data(
    task_id: str,
    current_user: User = Depends(require_admin_or_reviewer)
):
    """获取任务的审核数据（管理员和审核员）"""
    result = review_service.load_task_data(task_id)
    return result


@router.get("/reviews/{task_id}/stats", response_model=TaskResponse)
async def get_review_stats(
    task_id: str,
    current_user: User = Depends(require_admin_or_reviewer)
):
    """获取审核统计（管理员和审核员）"""
    result = review_service.get_review_stats(task_id)
    return result


@router.post("/reviews/review", response_model=TaskResponse)
async def review_item(
    request: ReviewRequest,
    current_user: User = Depends(require_admin_or_reviewer)
):
    """审核单个数据项（管理员和审核员）"""
    # 自动填充审核人
    if not request.reviewer:
        request.reviewer = current_user.username
    result = review_service.review_item(request)
    return result


@router.post("/reviews/batch-review", response_model=TaskResponse)
async def batch_review(
    request: BatchReviewRequest,
    current_user: User = Depends(require_admin_or_reviewer)
):
    """批量审核数据项（管理员和审核员）"""
    # 自动填充审核人
    if not request.reviewer:
        request.reviewer = current_user.username
    result = review_service.batch_review(request)
    return result


@router.post("/reviews/auto-review", response_model=TaskResponse)
async def auto_review(
    request: AutoReviewRequest,
    current_user: User = Depends(require_admin_or_reviewer)
):
    """自动审核数据项（管理员和审核员）"""
    result = await auto_review_service.auto_review_batch(request)
    return result


@router.get("/reviews/{task_id}/export", response_model=TaskResponse)
async def export_reviewed_data(task_id: str, status_filter: str = None, format: str = 'json'):
    """导出审核后的数据
    
    Args:
        task_id: 任务ID
        status_filter: 状态过滤，用逗号分隔，如 'approved,modified'，或 'all' 表示所有
        format: 导出格式，'json' 或 'csv'
    """
    status_list = status_filter.split(",") if status_filter else None
    result = review_service.export_reviewed_data(task_id, status_list, format)
    return result


@router.get("/reviews/{task_id}/download")
async def download_reviewed_data(task_id: str, format: str = 'json', optional_fields: str = ''):
    """下载审核后的数据文件
    
    Args:
        task_id: 任务ID
        format: 下载格式，'json' 或 'csv'
        optional_fields: 可选字段，逗号分隔（仅对 CSV 有效）
    """
    import os
    from backend.services.review_service import review_service
    
    # 解析可选字段
    fields_list = [f.strip() for f in optional_fields.split(',') if f.strip()] if optional_fields else []
    
    # 获取导出文件路径（根据格式动态转换）
    result = review_service.get_export_file(task_id, format, fields_list)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "文件不存在"))
    
    export_file = result.get("export_file")
    filename = result.get("filename")
    
    # 根据格式设置 MIME 类型
    media_type = "text/csv" if format == "csv" else "application/json"
    
    return FileResponse(
        path=export_file,
        filename=filename,
        media_type=media_type
    )


# ==================== 认证相关端点 ====================

@router.post("/auth/login", response_model=TaskResponse)
async def login(login_data: UserLogin):
    """用户登录"""
    result = auth_service.login(login_data)
    return result


@router.post("/auth/register", response_model=TaskResponse)
async def register(user_data: UserCreate, current_user: User = Depends(require_admin)):
    """注册新用户（仅管理员）"""
    result = auth_service.create_user(user_data)
    return result


@router.get("/auth/me", response_model=TaskResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return {
        "success": True,
        "data": current_user.dict()
    }


@router.post("/auth/change-password", response_model=TaskResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user)
):
    """修改密码"""
    result = auth_service.change_password(
        current_user.username,
        request.old_password,
        request.new_password
    )
    return result


@router.get("/auth/users", response_model=TaskResponse)
async def get_users(current_user: User = Depends(require_admin)):
    """获取所有用户（仅管理员）"""
    result = auth_service.get_all_users()
    return result


@router.put("/auth/users/{username}", response_model=TaskResponse)
async def update_user(
    username: str,
    update_data: UserUpdate,
    current_user: User = Depends(require_admin)
):
    """更新用户（仅管理员）"""
    result = auth_service.update_user(username, update_data)
    return result


@router.delete("/auth/users/{username}", response_model=TaskResponse)
async def delete_user(
    username: str,
    current_user: User = Depends(require_admin)
):
    """删除用户（仅管理员）"""
    result = auth_service.delete_user(username)
    return result


# ==================== 评测集相关端点 ====================

@router.get("/tasks/{task_id}/evaluation", response_model=TaskResponse)
async def get_evaluation_dataset(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取任务的评测集（需要登录）"""
    import os
    import json
    from webui.task_manager import task_manager
    
    # 获取任务信息
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 构建评测集文件路径
    cache_folder = task.cache_folder if hasattr(task, 'cache_folder') else f"cache/{task_id}"
    eval_file = os.path.join(cache_folder, "data", "evaluation", f"{task_id}_eval.json")
    
    if not os.path.exists(eval_file):
        return TaskResponse(
            success=False,
            error="评测集不存在，可能未启用评测集生成"
        )
    
    try:
        with open(eval_file, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        
        return TaskResponse(
            success=True,
            data=eval_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取评测集失败: {str(e)}")


@router.get("/tasks/{task_id}/evaluation/stats", response_model=TaskResponse)
async def get_evaluation_stats(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取评测集统计信息（需要登录）"""
    import os
    import json
    from webui.task_manager import task_manager
    
    # 获取任务信息
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 构建评测集文件路径
    cache_folder = task.cache_folder if hasattr(task, 'cache_folder') else f"cache/{task_id}"
    eval_file = os.path.join(cache_folder, "data", "evaluation", f"{task_id}_eval.json")
    
    if not os.path.exists(eval_file):
        return TaskResponse(
            success=False,
            error="评测集不存在"
        )
    
    try:
        with open(eval_file, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        
        # 提取统计信息
        stats = {
            "task_id": task_id,
            "total_items": eval_data.get("statistics", {}).get("total_items", 0),
            "type_distribution": eval_data.get("statistics", {}).get("type_distribution", {}),
            "difficulty_distribution": eval_data.get("statistics", {}).get("difficulty_distribution", {}),
            "generated_at": eval_data.get("metadata", {}).get("generated_at"),
        }
        
        return TaskResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取评测统计失败: {str(e)}")


@router.get("/tasks/{task_id}/evaluation/download")
async def download_evaluation_dataset(
    task_id: str,
    format: str = 'json',
    current_user: User = Depends(get_current_active_user)
):
    """下载评测集文件
    
    Args:
        task_id: 任务ID
        format: 下载格式，'json' 或 'csv'
    """
    import os
    from webui.task_manager import task_manager
    
    # 获取任务信息
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 构建评测集文件路径
    cache_folder = task.cache_folder if hasattr(task, 'cache_folder') else f"cache/{task_id}"
    eval_file = os.path.join(cache_folder, "data", "evaluation", f"{task_id}_eval.json")
    
    if not os.path.exists(eval_file):
        raise HTTPException(status_code=404, detail="评测集文件不存在")
    
    # 根据格式返回文件
    if format == 'json':
        return FileResponse(
            path=eval_file,
            filename=f"{task_id}_evaluation.json",
            media_type="application/json"
        )
    elif format == 'csv':
        # TODO: 实现CSV格式转换
        raise HTTPException(status_code=501, detail="CSV格式暂不支持")
    else:
        raise HTTPException(status_code=400, detail="不支持的格式")

