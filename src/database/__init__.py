"""
数据库模块

提供数据库模型、连接管理和迁移功能。
"""

from src.database.models import (
    Base,
    Configuration,
    ConfigurationHistory,
    ApiKeyReference,
    ConfigurationTemplate,
    User,
    ConfigTypeEnum,
    ConfigStatusEnum,
)

from src.database.connection import (
    DatabaseManager,
    db_manager,
    get_db_session,
    get_async_db_session,
    get_db,
)

__all__ = [
    # Models
    'Base',
    'Configuration',
    'ConfigurationHistory',
    'ApiKeyReference',
    'ConfigurationTemplate',
    'User',
    'ConfigTypeEnum',
    'ConfigStatusEnum',
    # Connection
    'DatabaseManager',
    'db_manager',
    'get_db_session',
    'get_async_db_session',
    'get_db',
]
