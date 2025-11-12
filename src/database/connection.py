"""
数据库连接管理

提供 SQLite 数据库的连接、会话管理和上下文管理器。
支持异步操作和连接池管理。
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器 - 单例模式"""

    _instance = None
    _engine = None
    _async_engine = None
    _session_factory = None
    _async_session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化数据库管理器"""
        if self._engine is None:
            self._initialize()

    def _initialize(self):
        """初始化数据库引擎和会话工厂"""
        # 获取数据库路径（默认：项目根目录/data/trading_config.db）
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(project_root, 'data')
        os.makedirs(data_dir, exist_ok=True)

        db_path = os.path.join(data_dir, 'trading_config.db')
        database_url = f"sqlite:///{db_path}"
        async_database_url = f"sqlite+aiosqlite:///{db_path}"

        logger.info(f"数据库路径: {db_path}")

        # 创建同步引擎（用于迁移和初始化）
        self._engine = create_engine(
            database_url,
            connect_args={
                "check_same_thread": False,  # SQLite特定配置
                "timeout": 30,  # 30秒超时
            },
            poolclass=StaticPool,  # 单文件SQLite使用静态池
            echo=False,  # 生产环境关闭SQL日志
        )

        # 创建异步引擎（用于运行时操作）
        self._async_engine = create_async_engine(
            async_database_url,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
            },
            poolclass=StaticPool,
            echo=False,
        )

        # 创建会话工厂
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        # 启用SQLite外键约束
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        logger.info("数据库引擎初始化完成")

    def create_tables(self):
        """创建所有表（同步方法，用于初始化）"""
        try:
            Base.metadata.create_all(bind=self._engine)
            logger.info("数据库表创建成功")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise

    def drop_tables(self):
        """删除所有表（谨慎使用！）"""
        try:
            Base.metadata.drop_all(bind=self._engine)
            logger.warning("数据库表已删除")
        except Exception as e:
            logger.error(f"删除数据库表失败: {e}")
            raise

    def get_session(self) -> Session:
        """获取同步数据库会话"""
        return self._session_factory()

    def get_async_session(self) -> AsyncSession:
        """获取异步数据库会话"""
        return self._async_session_factory()

    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """异步会话上下文管理器（推荐使用）

        用法:
            async with db_manager.session_scope() as session:
                result = await session.execute(query)
                await session.commit()
        """
        session = self.get_async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库事务失败: {e}")
            raise
        finally:
            await session.close()

    async def close(self):
        """关闭数据库连接"""
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("异步数据库引擎已关闭")

        if self._engine:
            self._engine.dispose()
            logger.info("同步数据库引擎已关闭")

    def check_health(self) -> bool:
        """检查数据库健康状态"""
        try:
            from sqlalchemy import text
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False


# 全局数据库管理器实例
db_manager = DatabaseManager()


# 便捷函数
def get_db_session() -> Session:
    """获取同步数据库会话（便捷函数）"""
    return db_manager.get_session()


def get_async_db_session() -> AsyncSession:
    """获取异步数据库会话（便捷函数）"""
    return db_manager.get_async_session()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖注入风格的异步会话获取函数

    用法（在API路由中）:
        async def get_config(db: AsyncSession = Depends(get_db)):
            result = await db.execute(query)
    """
    async with db_manager.session_scope() as session:
        yield session
