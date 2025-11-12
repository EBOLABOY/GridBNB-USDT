"""
FastAPI 依赖项

提供数据库会话、用户认证等依赖注入。
"""

import logging
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.database import db_manager, User

logger = logging.getLogger(__name__)

# HTTP Bearer 认证方案
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（依赖注入）

    Yields:
        数据库会话对象
    """
    with db_manager.get_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"数据库会话错误: {e}")
            session.rollback()
            raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前认证用户（依赖注入）

    Args:
        credentials: HTTP Bearer 凭证
        db: 数据库会话

    Returns:
        User 对象

    Raises:
        HTTPException: 认证失败
    """
    token = credentials.credentials

    user = get_current_user_from_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户（依赖注入）

    Args:
        current_user: 当前用户

    Returns:
        User 对象

    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取当前管理员用户（依赖注入）

    Args:
        current_user: 当前用户

    Returns:
        User 对���

    Raises:
        HTTPException: 用户不是管理员
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )

    return current_user


async def get_current_user_from_query(
    token: str = Query(..., description="认证令牌"),
    db: Session = Depends(get_db)
) -> User:
    """从URL参数获取当前用户（用于SSE等不支持headers的场景）

    Args:
        token: URL参数中的token
        db: 数据库会话

    Returns:
        User 对象

    Raises:
        HTTPException: 认证失败
    """
    user = get_current_user_from_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user
