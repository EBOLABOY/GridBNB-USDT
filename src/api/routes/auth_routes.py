"""
认证相关 API 路由

提供登录、注销、修改密码等功能。
"""

import logging
from aiohttp import web

from src.api.auth import authenticate_user, create_user_token, change_password
from src.api.middleware import auth_required
from src.database import db_manager

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.post('/api/auth/login')
async def login(request: web.Request) -> web.Response:
    """用户登录

    请求体:
        {
            "username": "admin",
            "password": "admin123"
        }

    响应:
        {
            "access_token": "eyJ...",
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": 1,
                "username": "admin",
                "is_admin": true
            }
        }
    """
    try:
        data = await request.json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return web.json_response(
                {'error': 'Username and password are required'},
                status=400
            )

        # 验证用户
        with db_manager.get_session() as session:
            user = authenticate_user(username, password, session)
            if not user:
                return web.json_response(
                    {'error': 'Invalid username or password'},
                    status=401
                )

            # 创建 token
            token_data = create_user_token(user)

        return web.json_response(token_data)

    except Exception as e:
        logger.error(f"登录失败: {e}")
        return web.json_response(
            {'error': 'Login failed', 'message': str(e)},
            status=500
        )


@routes.post('/api/auth/logout')
@auth_required
async def logout(request: web.Request) -> web.Response:
    """用户注销

    注意：由于使用JWT，实际上是客户端删除token。
    服务器端可以记录注销日志。
    """
    user = request['user']
    logger.info(f"用户注销: {user.username}")

    return web.json_response({
        'message': 'Logged out successfully'
    })


@routes.post('/api/auth/change-password')
@auth_required
async def change_password_handler(request: web.Request) -> web.Response:
    """修改密码

    请求体:
        {
            "old_password": "admin123",
            "new_password": "new_secure_password"
        }

    响应:
        {
            "message": "Password changed successfully",
            "access_token": "new_token..."
        }
    """
    try:
        user = request['user']
        data = await request.json()

        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return web.json_response(
                {'error': 'Old password and new password are required'},
                status=400
            )

        # 验证新密码强度
        if len(new_password) < 6:
            return web.json_response(
                {'error': 'New password must be at least 6 characters long'},
                status=400
            )

        # 修改密码
        with db_manager.get_session() as session:
            # 重新查询用户以确保使用最新数据
            from src.database import User
            user_obj = session.query(User).filter_by(id=user.id).first()

            if not user_obj:
                return web.json_response(
                    {'error': 'User not found'},
                    status=404
                )

            success = change_password(user_obj, old_password, new_password, session)

            if not success:
                return web.json_response(
                    {'error': 'Old password is incorrect'},
                    status=400
                )

            # 生成新的 token
            token_data = create_user_token(user_obj)

        return web.json_response({
            'message': 'Password changed successfully',
            'access_token': token_data['access_token'],
            'token_type': token_data['token_type'],
            'expires_in': token_data['expires_in'],
        })

    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return web.json_response(
            {'error': 'Failed to change password', 'message': str(e)},
            status=500
        )


@routes.get('/api/auth/me')
@auth_required
async def get_current_user(request: web.Request) -> web.Response:
    """获取当前登录用户信息

    响应:
        {
            "id": 1,
            "username": "admin",
            "is_admin": true,
            "is_active": true,
            "last_login": "2025-01-28T12:34:56",
            "login_count": 42
        }
    """
    user = request['user']

    return web.json_response({
        'id': user.id,
        'username': user.username,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'login_count': user.login_count,
    })


@routes.get('/api/auth/verify')
@auth_required
async def verify_token(request: web.Request) -> web.Response:
    """验证 token 是否有效

    响应:
        {
            "valid": true,
            "user_id": 1,
            "username": "admin"
        }
    """
    user = request['user']

    return web.json_response({
        'valid': True,
        'user_id': user.id,
        'username': user.username,
    })
