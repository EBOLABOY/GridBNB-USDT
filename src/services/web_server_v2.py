"""
新版Web服务器（集成企业级API）

集成了新的配置管理API和JWT认证系统，同时保留原有的监控界面。
"""

import logging
import os
from aiohttp import web

# 导入新的API模块
from src.api.app import setup_api_routes
from src.api.middleware import setup_middlewares

# 导入现有的监控服务器路由（保持兼容）
from src.services.web_server import (
    handle_log,
    handle_status,
    handle_symbols,
    handle_ai_decision,
    IPLogger,
    METRICS_AVAILABLE
)

logger = logging.getLogger(__name__)

# 全局IP记录器
ip_logger = IPLogger()


async def create_web_app(traders: dict, trader_registry=None) -> web.Application:
    """创建完整的Web应用（包含新API和旧监控界面）

    Args:
        traders: 交易器字典 {symbol: trader}
        trader_registry: 交易器注册表（可选）

    Returns:
        配置完成的 aiohttp Application
    """
    app = web.Application()

    # 注入依赖
    app['traders'] = traders
    app['ip_logger'] = ip_logger
    if trader_registry:
        app['trader_registry'] = trader_registry

    # ====== 1. 设置中间件（新API的中间件）======
    setup_middlewares(app)

    # ====== 2. 注册新的API路由 ======
    setup_api_routes(app)

    # ====== 3. 注册旧的监控界面路由（保持向后兼容）======
    # 旧的监控页面使用不同的路径前缀，避免冲突
    routes = web.RouteTableDef()

    @routes.get('/')
    @routes.get('/monitor')
    async def index_wrapper(request):
        """原有的监控首页"""
        return await handle_log(request)

    @routes.get('/api/status')
    async def status_wrapper(request):
        """原有的状态API"""
        return await handle_status(request)

    @routes.get('/api/log')
    async def log_wrapper(request):
        """原有的日志API"""
        return await handle_log(request)

    @routes.get('/api/symbols')
    async def symbols_wrapper(request):
        """原有的交易对列表API"""
        return await handle_symbols(request)

    @routes.get('/api/ai-decision')
    async def ai_decision_wrapper(request):
        """原有的AI决策API"""
        return await handle_ai_decision(request)

    # 如果启用Prometheus监控
    if METRICS_AVAILABLE:
        from src.monitoring.metrics import get_metrics
        from prometheus_client import CONTENT_TYPE_LATEST

        @routes.get('/metrics')
        async def metrics_handler(request):
            """Prometheus metrics endpoint"""
            metrics = get_metrics()
            return web.Response(
                text=metrics,
                content_type=CONTENT_TYPE_LATEST
            )
        logger.info("✓ Prometheus metrics端点已启用")

    # 注册旧路由
    app.add_routes(routes)

    logger.info("=" * 60)
    logger.info("Web应用创建完成")
    logger.info("=" * 60)
    logger.info("新API端点:")
    logger.info("  认证: POST /api/auth/login")
    logger.info("  配置: GET /api/configs")
    logger.info("  SSE:  GET /api/sse/events")
    logger.info("原有监控端点:")
    logger.info("  监控页面: GET /")
    logger.info("  状态API:  GET /api/status")
    logger.info("=" * 60)

    return app


async def start_web_server_v2(traders: dict, trader_registry=None, port: int = 58181):
    """启动新版Web服务器

    Args:
        traders: 交易器字典
        trader_registry: 交易器注册表（可选）
        port: 端口号（默认58181）
    """
    app = await create_web_app(traders, trader_registry)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"✓ Web服务器已启动在端口 {port}")
    logger.info(f"  监控页面: http://localhost:{port}/")
    logger.info(f"  配置页面: http://localhost:{port}/api/configs")
    logger.info(f"  API文档: 参见 docs/API.md")


# 导出
__all__ = ['create_web_app', 'start_web_server_v2']
