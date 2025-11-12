"""
FastAPI 主应用

集成了认证、配置管理、SSE推送等功能。
"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("FastAPI 应用启动")
    yield
    logger.info("FastAPI 应用关闭")


def create_app(traders: dict = None, trader_registry=None) -> FastAPI:
    """创建 FastAPI 应用实例

    Args:
        traders: 交易器字典 {symbol: trader}
        trader_registry: 交易器注册表（可选）

    Returns:
        FastAPI 应用实例
    """
    app = FastAPI(
        title="GridBNB Trading System API",
        description="网格交易系统后端 API",
        version="v3.2.0",
        lifespan=lifespan
    )

    # 存储依赖到 app.state
    app.state.traders = traders or {}
    app.state.trader_registry = trader_registry

    # ====== 1. 配置 CORS 中间件 ======
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该设置具体的域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ====== 2. 健康检查端点（必须在通配符路由之前） ======
    @app.get("/api/health")
    async def health_check():
        """健康检查"""
        return {
            "status": "healthy",
            "service": "GridBNB Trading System",
            "version": "v3.2.0"
        }

    # ====== 3. 注册路由 ======
    from src.fastapi_app.routers import auth, config, history, template, sse, dashboard, logs, trades

    app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
    app.include_router(config.router, prefix="/api/configs", tags=["配置管理"])
    app.include_router(history.router, prefix="/api/configs", tags=["配置历史"])
    app.include_router(template.router, prefix="/api/templates", tags=["配置模板"])
    app.include_router(sse.router, prefix="/api/sse", tags=["实时推送"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["运行状态"])
    app.include_router(logs.router, prefix="/api/logs", tags=["日志查看"])
    app.include_router(trades.router, prefix="/api/trades", tags=["交易历史"])

    logger.info("✓ 所有路由已注册")

    # ====== 4. 配置静态文件服务（前端） ======
    web_dist = Path(__file__).parent.parent.parent / "web" / "dist"

    if web_dist.exists():
        # 静态资源（CSS, JS, images 等）
        app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="static")
        logger.info(f"✓ 静态文件目录: {web_dist}")

        # SPA 路由：所有非 API 请求都返回 index.html（必须最后注册）
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """服务前端 SPA 应用"""
            # 返回 index.html
            index_file = web_dist / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"detail": "Frontend not built"}

        logger.info("✓ 前端 SPA 路由已配置")
    else:
        logger.warning(f"⚠ 前端构建目录不存在: {web_dist}")
        logger.warning("  请运行: cd web && npm run build")

    logger.info("=" * 60)
    logger.info("FastAPI 应用创建完成")
    logger.info("=" * 60)
    logger.info("API 端点:")
    logger.info("  认证:     POST /api/auth/login")
    logger.info("  配置:     GET  /api/configs")
    logger.info("  日志:     GET  /api/logs/list")
    logger.info("  交易:     GET  /api/trades/list")
    logger.info("  SSE:      GET  /api/sse/events")
    logger.info("  健康检查: GET  /api/health")
    logger.info("  API文档:  GET  /docs")
    logger.info("前端:")
    logger.info("  主页:     GET  /")
    logger.info("=" * 60)

    return app
