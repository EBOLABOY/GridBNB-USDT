"""
认证路由

提供登录、注销、修改密码等功能。
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.fastapi_app.dependencies import get_db, get_current_active_user
from src.fastapi_app.schemas import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    UserInfo,
    MessageResponse
)
from src.api.auth import authenticate_user, create_user_token, change_password
from src.database import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录接口

    - **username**: 用户名
    - **password**: 密码
    """
    # 验证用户
    user = authenticate_user(request.username, request.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建 token
    token_data = create_user_token(user)

    return token_data


@router.post("/logout", response_model=MessageResponse, summary="用户注销")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    用户注销

    注意：由于使用JWT，实际上是客户端删除token。
    服务器端可以记录注销日志。
    """
    logger.info(f"用户注销: {current_user.username}")

    return {"message": "Logged out successfully"}


@router.post("/change-password", summary="修改密码")
async def change_password_handler(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    修改密码

    - **old_password**: 旧密码
    - **new_password**: 新密码（至少6个字符）
    """
    # 修改密码
    success = change_password(
        current_user,
        request.old_password,
        request.new_password,
        db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )

    # 生成新的 token
    token_data = create_user_token(current_user)

    return {
        "message": "Password changed successfully",
        "access_token": token_data["access_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"],
    }


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户信息
    """
    return current_user


@router.get("/verify", summary="验证 Token")
async def verify_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    验证 token 是否有效
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
    }
