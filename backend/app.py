"""
FastAPI Application
GraphGen 后端 API 服务
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.api import router
from backend.config import settings

# 加载环境变量
load_dotenv()

# 创建 FastAPI 应用
app = FastAPI(
    title="GraphGen API",
    version="2.0.0",
    description="GraphGen 数据生成平台 API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")

# 健康检查端点
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "GraphGen API",
        "version": "2.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def api_health_check():
    """API健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "message": "服务运行正常",
        "timestamp": datetime.now().isoformat()
    }

