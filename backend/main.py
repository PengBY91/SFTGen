"""
KGE-Gen Backend API
FastAPI 服务入口
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import app

if __name__ == "__main__":
    import uvicorn
    # 增加超时和 keepalive 配置，避免 IncompleteRead 错误
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        timeout_keep_alive=300,  # 保持连接300秒
        timeout_graceful_shutdown=10  # 优雅关闭超时10秒
    )

