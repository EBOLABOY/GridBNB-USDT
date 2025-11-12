"""
数据库模型定义 (ORM Models)

使用 SQLAlchemy ORM 定义配置管理所需的数据库表结构。
支持配置存储、版本历史、模板管理和用户认证。
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class ConfigTypeEnum(enum.Enum):
    """配置类型枚举"""
    EXCHANGE = "exchange"  # 交易所配置
    TRADING = "trading"  # 交易策略配置
    RISK = "risk"  # 风控配置
    AI = "ai"  # AI策略配置
    NOTIFICATION = "notification"  # 通知配置
    SYSTEM = "system"  # 系统配置


class ConfigStatusEnum(enum.Enum):
    """配置状态枚举"""
    DRAFT = "draft"  # 草稿（未应用）
    ACTIVE = "active"  # 活跃（当前使用）
    INACTIVE = "inactive"  # 非活跃（已停用）
    ARCHIVED = "archived"  # 已归档


class Configuration(Base):
    """配置主表 - 存储所有配置项"""
    __tablename__ = 'configurations'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 配置基本信息
    config_key = Column(String(100), unique=True, nullable=False, index=True, comment="配置键（如 SYMBOLS, MIN_TRADE_AMOUNT）")
    config_value = Column(Text, nullable=False, comment="配置值（JSON或字符串）")
    config_type = Column(Enum(ConfigTypeEnum), nullable=False, index=True, comment="配置类型")

    # 配置元数据
    display_name = Column(String(100), nullable=False, comment="显示名称（用于前端展示）")
    description = Column(Text, nullable=True, comment="配置描述")
    data_type = Column(String(50), nullable=False, comment="数据类型（string/number/boolean/json）")
    default_value = Column(Text, nullable=True, comment="默认值")

    # 配置验证规则（JSON格式）
    validation_rules = Column(JSON, nullable=True, comment="验证规则（min/max/pattern/enum等）")

    # 配置状态
    status = Column(Enum(ConfigStatusEnum), nullable=False, default=ConfigStatusEnum.ACTIVE, index=True, comment="配置状态")
    is_required = Column(Boolean, default=False, comment="是否必填")
    is_sensitive = Column(Boolean, default=False, comment="是否敏感数据（如API密钥）")
    requires_restart = Column(Boolean, default=False, comment="修改后是否需要重启")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True, comment="创建用户ID")
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True, comment="更新用户ID")

    # 关系
    history = relationship("ConfigurationHistory", back_populates="configuration", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Configuration(id={self.id}, key={self.config_key}, type={self.config_type.value})>"


class ConfigurationHistory(Base):
    """配置历史表 - 记录配置变更历史"""
    __tablename__ = 'configuration_history'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联的配置ID
    config_id = Column(Integer, ForeignKey('configurations.id', ondelete='CASCADE'), nullable=False, index=True, comment="配置ID")

    # 历史记录内容
    old_value = Column(Text, nullable=True, comment="旧值")
    new_value = Column(Text, nullable=False, comment="新值")
    change_reason = Column(String(500), nullable=True, comment="变更原因")

    # 变更元数据
    version = Column(Integer, nullable=False, comment="版本号")
    is_backup = Column(Boolean, default=False, comment="是否为备份记录")
    backup_type = Column(String(50), nullable=True, comment="备份类型（manual/auto_daily/auto_weekly）")

    # 时间戳和操作用户
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="变更时间")
    changed_by = Column(Integer, ForeignKey('users.id'), nullable=True, comment="变更用户ID")

    # 关系
    configuration = relationship("Configuration", back_populates="history")

    def __repr__(self):
        return f"<ConfigurationHistory(id={self.id}, config_id={self.config_id}, version={self.version})>"


class ApiKeyReference(Base):
    """API密钥引用表 - 记录配置中引用的API密钥"""
    __tablename__ = 'api_key_references'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 配置关联
    config_id = Column(Integer, ForeignKey('configurations.id', ondelete='CASCADE'), nullable=False, index=True, comment="配置ID")

    # API密钥信息
    key_name = Column(String(100), nullable=False, comment="密钥名称（如 BINANCE_API_KEY）")
    key_type = Column(String(50), nullable=False, comment="密钥类型（api_key/api_secret/passphrase）")
    exchange = Column(String(50), nullable=False, comment="交易所名称（binance/okx）")

    # 引用元数据
    is_testnet = Column(Boolean, default=False, comment="是否为测试网密钥")
    last_validated = Column(DateTime, nullable=True, comment="最后验证时间")
    is_valid = Column(Boolean, default=True, comment="密钥是否有效")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")

    def __repr__(self):
        return f"<ApiKeyReference(id={self.id}, key_name={self.key_name}, exchange={self.exchange})>"


class ConfigurationTemplate(Base):
    """配置模板表 - 预设配置模板（保守型/平衡型/激进型）"""
    __tablename__ = 'configuration_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 模板基本信息
    template_name = Column(String(100), unique=True, nullable=False, index=True, comment="模板名称")
    template_type = Column(String(50), nullable=False, comment="模板类型（conservative/balanced/aggressive）")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    description = Column(Text, nullable=True, comment="模板描述")

    # 模板内容（JSON格式，包含所有配置项）
    config_json = Column(JSON, nullable=False, comment="配置JSON（完整的配置项集合）")

    # 模板元数据
    is_system = Column(Boolean, default=False, comment="是否为系统预设模板")
    is_active = Column(Boolean, default=True, comment="是否启用")
    usage_count = Column(Integer, default=0, comment="使用次数")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True, comment="创建用户ID")

    def __repr__(self):
        return f"<ConfigurationTemplate(id={self.id}, name={self.template_name}, type={self.template_type})>"


class User(Base):
    """用户表 - 单用户模式（简化版）"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 用户基本信息
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希（bcrypt）")

    # 用户状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_admin = Column(Boolean, default=True, comment="是否为管理员")

    # JWT相关
    jwt_secret = Column(String(255), nullable=True, comment="JWT密钥（用于撤销token）")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")
    login_count = Column(Integer, default=0, comment="登录次数")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


# 创建索引以优化查询性能
from sqlalchemy import Index

# 为常用查询添加复合索引
Index('idx_config_type_status', Configuration.config_type, Configuration.status)
Index('idx_history_config_time', ConfigurationHistory.config_id, ConfigurationHistory.changed_at.desc())
