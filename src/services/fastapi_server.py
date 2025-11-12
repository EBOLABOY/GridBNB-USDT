"""
FastAPI Web 服务器启动脚本

替代 src/services/web_server_v2.py，使用 FastAPI 提供 RESTful API 和静态文件服务。
"""

import logging
import uvicorn
from src.fastapi_app.main import create_app

logger = logging.getLogger(__name__)


def start_fastapi_server(traders: dict = None, trader_registry=None, port: int = 58181, host: str = "0.0.0.0"):
    """
    启动 FastAPI 服务器

    Args:
        traders: 交易器字典
        trader_registry: 交易器注册表（可选）
        port: 端口号（默认58181）
        host: 主机地址（默认0.0.0.0）
    """
    app = create_app(traders, trader_registry)

    logger.info("=" * 80)
    logger.info(f"启动 FastAPI 服务器: http://{host}:{port}")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📡 API 端点:")
    logger.info(f"  - 认证:     POST http://localhost:{port}/api/auth/login")
    logger.info(f"  - 配置列表: GET  http://localhost:{port}/api/configs")
    logger.info(f"  - SSE推送:  GET  http://localhost:{port}/api/sse/events")
    logger.info(f"  - 健康检查: GET  http://localhost:{port}/api/health")
    logger.info("")
    logger.info("📄 文档:")
    logger.info(f"  - Swagger:  http://localhost:{port}/docs")
    logger.info(f"  - ReDoc:    http://localhost:{port}/redoc")
    logger.info("")
    logger.info("🌐 前端:")
    logger.info(f"  - 主页:     http://localhost:{port}/")
    logger.info("=" * 80)
    logger.info("")

    # 使用 uvicorn 运行（生产环境配置）
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        # workers=4,  # 可选：启用多进程
    )


# 用于独立启动（python -m src.services.fastapi_server）
if __name__ == "__main__":
    start_fastapi_server()
