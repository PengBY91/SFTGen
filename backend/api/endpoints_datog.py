"""
DA-ToG (Domain-Agnostic Tree-of-Graphs) API endpoints.

Provides endpoints for:
- DA-ToG configuration management
- Taxonomy tree management
- DA-ToG pipeline execution
"""

import json
import os
from pathlib import Path
from time import time

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.dependencies import get_current_user, require_admin
from backend.schemas import TaskResponse, User

router = APIRouter()


# ─── Request/Response Models ─────────────────────────────


class DAToGConfig(BaseModel):
    """DA-ToG configuration request/response model."""

    taxonomy_path: str = ""
    domain: str = ""
    sampling_strategy: str = "coverage"  # coverage, uniform_branch, depth_weighted
    graph_max_hops: int = 2
    graph_max_nodes: int = 20
    serialization_format: str = "natural_language"  # natural_language, markdown, json
    critic_type: str = "rule"  # llm, rule, none
    critic_min_score: float = 0.6
    generation_target_qa_pairs: int = 100
    batch_size: int = 10


class DAToGPipelineConfig(BaseModel):
    """DA-ToG pipeline execution request."""

    domain_config_path: str = ""
    taxonomy_path: str = ""
    input_file: str = ""
    kg_path: str = ""
    output_path: str = ""
    generate_taxonomy: bool = False
    source_document: str = ""


class SaveDAToGConfigRequest(BaseModel):
    """Save DA-ToG configuration request."""

    domain: str = ""
    taxonomy_path: str = ""
    sampling_strategy: str = "coverage"
    graph_max_hops: int = 2
    graph_max_nodes: int = 20
    serialization_format: str = "natural_language"
    critic_type: str = "rule"
    critic_min_score: float = 0.6
    generation_target_qa_pairs: int = 100
    batch_size: int = 10


class RunDAToGPipelineRequest(BaseModel):
    """Run DA-ToG pipeline request."""

    domain_config_path: str = ""
    taxonomy_path: str = ""
    input_file: str = ""
    kg_path: str = ""
    output_path: str = ""


# ─── DA-ToG Configuration Endpoints ─────────────────────────────


@router.post("/datog/config/save")
async def save_datog_config(
    request: SaveDAToGConfigRequest,
    current_user: User = Depends(get_current_user),
):
    """保存 DA-ToG 配置"""
    # Check if user is admin (for now, all users can manage)
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    # TODO: Integrate with config_service for proper persistence
    # For now, save to user-specific file
    user_config_dir = PROJECT_ROOT / "cache/user_config"
    user_config_dir.mkdir(parents=True, exist_ok=True)

    config_file = user_config_dir / f"{current_user.username}_datog.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(request.dict(), f, ensure_ascii=False, indent=2)

    return JSONResponse(content={"success": True, "message": "配置保存成功"})


@router.get("/datog/config/load")
async def load_datog_config(
    current_user: User = Depends(get_current_user),
):
    """加载 DA-ToG 配置"""
    # Load user's DA-ToG config from file
    user_config_dir = PROJECT_ROOT / "cache/user_config"
    config_file = user_config_dir / f"{current_user.username}_datog.json"

    if not config_file.exists():
        return JSONResponse(content={
            "success": True,
            "message": "配置不存在，使用默认值",
            "data": DAToGConfig().dict()
        })

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        return JSONResponse(content={"success": True, "message": "配置加载成功", "data": config})
    except Exception as e:
        return JSONResponse(content={"success": False, "message": "配置加载失败", "error": str(e)})


# ─── DA-ToG Taxonomy Endpoints ─────────────────────────────


@router.post("/datog/taxonomy/save")
async def save_taxonomy_tree(
    data: DAToGConfig,
    current_user: User = Depends(require_admin),
):
    """保存 DA-ToG 意图树"""
    # Create taxonomy file path
    user_taxonomies_dir = PROJECT_ROOT / "data/taxonomies" / current_user.username
    user_taxonomies_dir.mkdir(parents=True, exist_ok=True)

    taxonomy_filename = f"{data.domain or 'default'}_{int(time())}.json"
    taxonomy_path = user_taxonomies_dir / taxonomy_filename

    with open(taxonomy_path, "w", encoding="utf-8") as f:
        json.dump(data.dict(), f, ensure_ascii=False, indent=2)

    return JSONResponse(content={
        "success": True,
        "taxonomy_path": str(taxonomy_path),
        "taxonomy_id": taxonomy_filename.replace(".json", ""),
        "domain": data.domain,
        "message": "意图树保存成功"
    })


@router.get("/datog/taxonomy/list")
async def list_taxonomy_trees(
    current_user: User = Depends(get_current_user),
):
    """获取用户的所有 DA-ToG 意图树（含仓库内置领域示例）"""
    user_taxonomies_dir = PROJECT_ROOT / "data/taxonomies" / current_user.username

    taxonomies = []

    # 内置领域示例（graphgen/configs/datog/<domain>/taxonomy.json），只读展示
    builtin_dir = PROJECT_ROOT / "graphgen" / "configs" / "datog"
    if builtin_dir.exists():
        for file_path in sorted(builtin_dir.glob("*/taxonomy.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    taxonomy_data = json.load(f)
                taxonomies.append({
                    "id": f"builtin_{file_path.parent.name}",
                    "name": taxonomy_data.get("name", "") or file_path.parent.name,
                    "path": str(file_path),
                    "domain": taxonomy_data.get("domain", "") or file_path.parent.name,
                    "created_at": None,
                    "builtin": True,
                })
            except Exception:
                pass

    # 用户自建意图树
    if user_taxonomies_dir.exists():
        for file_path in sorted(user_taxonomies_dir.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    taxonomy_data = json.load(f)
                taxonomies.append({
                    "id": file_path.stem,
                    "name": file_path.stem,
                    "path": str(file_path),
                    "domain": taxonomy_data.get("domain", ""),
                    "created_at": None,
                    "builtin": False,
                })
            except Exception:
                pass

    return JSONResponse(content={
        "success": True,
        "taxonomies": taxonomies,
        "message": f"找到 {len(taxonomies)} 个意图树"
    })


def _compute_taxonomy_statistics(nodes: list) -> dict:
    """计算意图树的统计信息"""
    total_nodes = 0
    max_depth = 0
    leaf_count = 0
    dimension_counts = {}
    depth_counts = {}

    def traverse(node_list, depth=0):
        nonlocal total_nodes, max_depth, leaf_count
        for node in node_list:
            total_nodes += 1
            max_depth = max(max_depth, depth)
            depth_counts[depth] = depth_counts.get(depth, 0) + 1

            # 统计认知维度
            dim = node.get("cognitive_dimension")
            if dim:
                dimension_counts[dim] = dimension_counts.get(dim, 0) + 1

            children = node.get("children", [])
            if children:
                traverse(children, depth + 1)
            else:
                leaf_count += 1

    traverse(nodes)

    return {
        "total_nodes": total_nodes,
        "root_count": len(nodes),
        "leaf_count": leaf_count,
        "max_depth": max_depth,
        "dimension_distribution": dimension_counts,
        "depth_distribution": depth_counts
    }


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


@router.get("/datog/taxonomy/{taxonomy_id}")
async def get_taxonomy_tree(
    taxonomy_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取单个 DA-ToG 意图树详情"""
    # builtin_ 前缀指向仓库内置领域示例，其余在用户目录查找
    if taxonomy_id.startswith("builtin_"):
        taxonomy_path = (
            PROJECT_ROOT / "graphgen" / "configs" / "datog"
            / taxonomy_id[len("builtin_"):] / "taxonomy.json"
        )
    else:
        user_taxonomies_dir = PROJECT_ROOT / "data/taxonomies" / current_user.username
        taxonomy_path = user_taxonomies_dir / f"{taxonomy_id}.json"

    if not taxonomy_path.exists():
        raise HTTPException(status_code=404, detail=f"未找到意图树 {taxonomy_id}")

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        taxonomy_data = json.load(f)

    # 获取节点数据：优先使用自身 nodes，否则尝试读取 taxonomy_path 指向的文件
    nodes = taxonomy_data.get("nodes", [])
    if not nodes:
        # 尝试读取 taxonomy_path 指向的实际意图树文件
        taxonomy_file_path = taxonomy_data.get("taxonomy_path", "")
        if taxonomy_file_path:
            # 支持相对路径和绝对路径
            ref_path = PROJECT_ROOT / taxonomy_file_path if not Path(taxonomy_file_path).is_absolute() else Path(taxonomy_file_path)
            if ref_path.exists():
                with open(ref_path, "r", encoding="utf-8") as f:
                    ref_data = json.load(f)
                    nodes = ref_data.get("nodes", [])

    # 计算统计信息
    statistics = _compute_taxonomy_statistics(nodes)

    return JSONResponse(content={
        "success": True,
        "data": {
            "taxonomy": taxonomy_data,
            "nodes": nodes,
            "statistics": statistics
        },
        "message": "意图树获取成功"
    })


@router.put("/datog/taxonomy/{taxonomy_id}")
async def update_taxonomy_tree(
    taxonomy_id: str,
    data: DAToGConfig,
    current_user: User = Depends(require_admin),
):
    """更新 DA-ToG 意图树"""
    if taxonomy_id.startswith("builtin_"):
        raise HTTPException(status_code=400, detail="内置领域示例为只读，不可编辑")
    # Find and load the taxonomy
    user_taxonomies_dir = PROJECT_ROOT / "data/taxonomies" / current_user.username
    taxonomy_path = user_taxonomies_dir / f"{taxonomy_id}.json"

    if not taxonomy_path.exists():
        raise HTTPException(status_code=404, detail=f"意图树不存在: {taxonomy_id}")

    with open(taxonomy_path, "w", encoding="utf-8") as f:
        json.dump(data.dict(), f, ensure_ascii=False, indent=2)

    return JSONResponse(content={
        "success": True,
        "message": f"意图树 {taxonomy_id} 更新成功"
    })


@router.delete("/datog/taxonomy/{taxonomy_id}")
async def delete_taxonomy_tree(
    taxonomy_id: str,
    current_user: User = Depends(require_admin),
):
    """删除 DA-ToG 意图树"""
    if taxonomy_id.startswith("builtin_"):
        raise HTTPException(status_code=400, detail="内置领域示例为只读，不可删除")
    # Find and delete the taxonomy file
    user_taxonomies_dir = PROJECT_ROOT / "data/taxonomies" / current_user.username
    taxonomy_path = user_taxonomies_dir / f"{taxonomy_id}.json"

    if not taxonomy_path.exists():
        raise HTTPException(status_code=404, detail=f"意图树不存在: {taxonomy_id}")

    # Delete the file
    taxonomy_path.unlink()

    return JSONResponse(content={"success": True, "message": f"意图树 {taxonomy_id} 删除成功"})


# ─── DA-ToG Pipeline Endpoints ─────────────────────────────


@router.post("/datog/pipeline/run")
async def run_datog_pipeline(
    request: DAToGPipelineConfig,
    current_user: User = Depends(get_current_user),
):
    """运行 DA-ToG 管道生成数据"""
    import asyncio

    # For now, this is a placeholder - actual implementation
    # should call the graphgen datog CLI via subprocess
    # or integrate DAToGPipeline into the web service

    # Simulate creating a task
    result = {
        "task_id": f"datog_{int(asyncio.get_event_loop().time())}",
        "status": "running",
        "output_file": request.output_path or "",
    }

    # Simulate starting the pipeline (async, would be better but this is synchronous endpoint)
    await asyncio.sleep(0.1)

    # Return the result
    return JSONResponse(content={"success": True, "data": result, "message": "DA-ToG 管道已启动"})


@router.get("/datog/pipeline/status/{task_id}")
async def get_pipeline_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取 DA-ToG 管道运行状态"""
    # For now, return placeholder status
    return JSONResponse(content={
        "success": True,
        "task_id": task_id,
        "status": "not_started",
        "message": "DA-ToG 管道功能开发中"
    })
