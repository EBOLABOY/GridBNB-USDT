"""
API 中间件

提供认证、CORS、错误处理等中间件功能。
"""

import logging
import json
from functools import wraps
from typing import Callable, Optional

from aiohttp import web

from src.api.auth import verify_token, get_current_user_from_token
from src.database import db_manager

logger = logging.getLogger(__name__)


def auth_required(func: Callable) -> Callable:
    """认证装饰器 - 要求请求携带有效的 JWT token

    用法:
        @routes.get('/api/protected')
        @auth_required
        async def protected_handler(request):
            user = request['user']  # 认证成功后，用户对象会被注入到 request 中
            return web.json_response({'message': f'Hello, {user.username}'})
    """
    @wraps(func)
    async def wrapper(request: web.Request) -> web.Response:
        # 从 Authorization header 获取 token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return web.json_response(
                {'error': 'Missing authorization header'},
                status=401
            )

        # 解析 Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return web.json_response(
                {'error': 'Invalid authorization header format. Expected: Bearer <token>'},
                status=401
            )

        token = parts[1]

        # 验证 token 并获取用户
        with db_manager.get_session() as session:
            user = get_current_user_from_token(token, session)
            if not user:
                return web.json_response(
                    {'error': 'Invalid or expired token'},
                    status=401
                )

            # 将用户对象注入到 request 中
            request['user'] = user
            request['user_id'] = user.id

        # 调用实际的处理函数
        return await func(request)

    return wrapper


def admin_required(func: Callable) -> Callable:
    """管理员权限装饰器 - 要求用户是管理员

    用法:
        @routes.delete('/api/admin/users/{id}')
        @admin_required
        async def delete_user(request):
            # 只有管理员可以访问
            pass
    """
    @wraps(func)
    @auth_required
    async def wrapper(request: web.Request) -> web.Response:
        user = request['user']
        if not user.is_admin:
            return web.json_response(
                {'error': 'Admin permission required'},
                status=403
            )

        return await func(request)

    return wrapper


@web.middleware
async def cors_middleware(request: web.Request, handler: Callable) -> web.Response:
    """CORS 中间件 - 允许跨域请求（用于前端开发）"""
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = web.Response()
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex

    # 添加 CORS 头
    response.headers['Access-Control-Allow-Origin'] = '*'  # 生产环境应该设置具体的域名
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'

    return response


@web.middleware
async def error_middleware(request: web.Request, handler: Callable) -> web.Response:
    """错误处理中间件 - 捕获所有未处理的异常并返回统一的JSON格式"""
    try:
        response = await handler(request)
        return response
    except web.HTTPException as ex:
        # HTTP 异常（如 404, 405 等）
        return web.json_response(
            {
                'error': ex.reason,
                'status': ex.status,
            },
            status=ex.status
        )
    except json.JSONDecodeError as e:
        # JSON 解析错误
        logger.error(f"JSON 解析错误: {e}")
        return web.json_response(
            {'error': 'Invalid JSON format'},
            status=400
        )
    except Exception as e:
        # 其他未捕获的异常
        logger.error(f"未处理的异常: {e}", exc_info=True)
        return web.json_response(
            {
                'error': 'Internal server error',
                'message': str(e),
            },
            status=500
        )


@web.middleware
async def logging_middleware(request: web.Request, handler: Callable) -> web.Response:
    """日志中间件 - 记录所有API请求"""
    logger.info(f"{request.method} {request.path} - IP: {request.remote}")

    response = await handler(request)

    logger.info(f"{request.method} {request.path} - Status: {response.status}")
    return response


def setup_middlewares(app: web.Application) -> None:
    """设置所有中间件

    Args:
        app: aiohttp Application 实例
    """
    app.middlewares.append(logging_middleware)
    app.middlewares.append(cors_middleware)
    app.middlewares.append(error_middleware)

    logger.info("中间件设置完成")
