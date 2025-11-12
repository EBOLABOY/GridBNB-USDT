"""
API 应用集成

将所有 API 路由注册到 aiohttp 应用。
"""

import logging
from aiohttp import web

from src.api.middleware import setup_middlewares
from src.api.routes import (
    auth_routes,
    config_routes,
    history_routes,
    template_routes,
    sse_routes
)

logger = logging.getLogger(__name__)


def setup_api_routes(app: web.Application) -> None:
    """注册所有 API 路由到应用

    Args:
        app: aiohttp Application 实例
    """
    # 注册认证路由
    app.add_routes(auth_routes.routes)
    logger.info("✓ 认证路由已注册")

    # 注册配置管理路由
    app.add_routes(config_routes.routes)
    logger.info("✓ 配置管理路由已注册")

    # 注册配置历史路由
    app.add_routes(history_routes.routes)
    logger.info("✓ 配置历史路由已注册")

    # 注册配置模板路由
    app.add_routes(template_routes.routes)
    logger.info("✓ 配置模板路由已注册")

    # 注册SSE路由
    app.add_routes(sse_routes.routes)
    logger.info("✓ SSE实时推送路由已注册")

    logger.info("所有API路由注册完成")


def create_api_app() -> web.Application:
    """创建独立的API应用（可选）

    Returns:
        配置完成的 aiohttp Application
    """
    app = web.Application()

    # 设置中间件
    setup_middlewares(app)

    # 设置路由
    setup_api_routes(app)

    logger.info("API应用创建完成")
    return app


# 导出
__all__ = ['setup_api_routes', 'create_api_app']
