"""
JWT 认证系统

提供用户认证、密码验证、JWT token 生成和验证功能。
"""

import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.database import User, db_manager
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时


def hash_password(password: str) -> str:
    """哈希密码（使用bcrypt）"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token

    Args:
        data: 要编码的数据（通常包含 user_id, username 等）
        expires_delta: 过期时间增量（可选）

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的payload，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token 验证失败: {e}")
        return None


def authenticate_user(username: str, password: str, session: Session) -> Optional[User]:
    """验证用户身份

    Args:
        username: 用户名
        password: 明文密码
        session: 数据库会话

    Returns:
        验证成功返回 User 对象，失败返回 None
    """
    try:
        # 查询用户
        user = session.query(User).filter_by(username=username).first()
        if not user:
            logger.warning(f"用户不存在: {username}")
            return None

        # 检查用户是否启用
        if not user.is_active:
            logger.warning(f"用户已禁用: {username}")
            return None

        # 验证密码
        if not verify_password(password, user.password_hash):
            logger.warning(f"密码错误: {username}")
            return None

        # 更新登录信息
        user.last_login = datetime.utcnow()
        user.login_count += 1
        session.commit()

        logger.info(f"用户登录成功: {username}")
        return user

    except Exception as e:
        logger.error(f"用户认证失败: {e}")
        return None


def create_user_token(user: User) -> Dict[str, Any]:
    """为用户创建 token

    Args:
        user: User 对象

    Returns:
        包含 token 和用户信息的字典
    """
    token_data = {
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
    }

    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 秒
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
        }
    }


def get_current_user_from_token(token: str, session: Session) -> Optional[User]:
    """从 token 获取当前用户

    Args:
        token: JWT token 字符串
        session: 数据库会话

    Returns:
        User 对象，验证失败返回 None
    """
    payload = verify_token(token)
    if not payload:
        return None

    user_id = payload.get("user_id")
    if not user_id:
        logger.warning("Token payload 缺少 user_id")
        return None

    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            logger.warning(f"用户不存在: user_id={user_id}")
            return None

        if not user.is_active:
            logger.warning(f"用户已禁用: user_id={user_id}")
            return None

        return user

    except Exception as e:
        logger.error(f"获取用户失败: {e}")
        return None


def change_password(user: User, old_password: str, new_password: str, session: Session) -> bool:
    """修改用户密码

    Args:
        user: User 对象
        old_password: 旧密码（明文）
        new_password: 新密码（明文）
        session: 数据库会话

    Returns:
        修改成功返回 True，失败返回 False
    """
    try:
        # 验证旧密码
        if not verify_password(old_password, user.password_hash):
            logger.warning(f"旧密码错误: user_id={user.id}")
            return False

        # 更新密码
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()

        # 更新 JWT secret 以使旧 token 失效
        user.jwt_secret = secrets.token_urlsafe(32)

        session.commit()

        logger.info(f"密码修改成功: user_id={user.id}")
        return True

    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        session.rollback()
        return False


# 兼容旧版本的简单哈希（仅用于初始化脚本）
def simple_hash_password(password: str) -> str:
    """简单的SHA256哈希（不推荐，仅用于向后兼容）"""
    return hashlib.sha256(password.encode()).hexdigest()
