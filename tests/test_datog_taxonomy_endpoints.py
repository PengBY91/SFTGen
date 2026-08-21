"""DA-ToG 意图树内置示例接口测试。

验证 /datog/taxonomy/list 展示仓库内置领域示例、
详情接口可解析 builtin_ 前缀、更新/删除接口拒绝内置示例。
"""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.endpoints_datog import router
from backend.dependencies import get_current_user
from backend.schemas import User

app = FastAPI()
app.include_router(router, prefix="/api")

# 覆盖鉴权依赖，模拟普通登录用户
FAKE_USER = User(user_id="u1", username="tester", password_hash="", role="admin", email="t@t.com")
app.dependency_overrides[get_current_user] = lambda: FAKE_USER

client = TestClient(app)

PROJECT_ROOT = Path(__file__).parent.parent


def test_list_contains_builtin_examples():
    """列表应包含 graphgen/configs/datog 下的内置示例，且带 builtin=True"""
    resp = client.get("/api/datog/taxonomy/list")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"]

    builtin = [t for t in body["taxonomies"] if t.get("builtin")]
    builtin_domains = {t["domain"] for t in builtin}
    # 仓库当前内置四个领域示例
    expected = {
        p.parent.name
        for p in (PROJECT_ROOT / "graphgen" / "configs" / "datog").glob("*/taxonomy.json")
    }
    assert builtin_domains == expected
    for t in builtin:
        assert t["id"].startswith("builtin_")
        assert Path(t["path"]).exists()


def test_get_builtin_taxonomy_detail():
    """builtin_ 前缀的详情应能读到内置意图树的节点并算出统计"""
    resp = client.get("/api/datog/taxonomy/builtin_strategic_evaluation")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nodes"], "内置意图树应包含节点"
    # nodes 为嵌套格式（只含根节点），statistics 递归统计全部节点
    # 战略评估树是 43 节点 / 6 根 / 35 叶子
    assert data["statistics"]["total_nodes"] == 43
    assert data["statistics"]["root_count"] == len(data["nodes"]) == 6
    assert data["statistics"]["leaf_count"] == 35


def test_update_builtin_rejected():
    """内置示例只读，更新应返回 400"""
    resp = client.put(
        "/api/datog/taxonomy/builtin_finance",
        json={"domain": "finance", "taxonomy_path": "x"},
    )
    assert resp.status_code == 400


def test_delete_builtin_rejected():
    """内置示例只读，删除应返回 400"""
    resp = client.delete("/api/datog/taxonomy/builtin_finance")
    assert resp.status_code == 400
    # 文件仍在
    assert (PROJECT_ROOT / "graphgen" / "configs" / "datog" / "finance" / "taxonomy.json").exists()
