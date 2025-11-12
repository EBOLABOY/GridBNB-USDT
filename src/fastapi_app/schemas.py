"""
FastAPI Pydantic 模型

定义 API 请求和响应的数据模型。
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


# ============ 认证相关模��� ============

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: "UserInfo"


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    is_admin: bool
    is_active: bool = True
    last_login: Optional[datetime] = None
    login_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ============ 配置管理相关模型 ============

class ConfigBase(BaseModel):
    """配置基础模型"""
    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")
    config_type: str = Field(..., description="配置类型")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    data_type: Optional[str] = Field(None, description="数据类型")
    default_value: Optional[str] = Field(None, description="默认值")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    status: str = Field(default="draft", description="状态")
    is_required: bool = Field(default=False, description="是否必需")
    is_sensitive: bool = Field(default=False, description="是否敏感")
    requires_restart: bool = Field(default=False, description="是否需要重启")


class ConfigCreate(ConfigBase):
    """创建配置"""
    pass


class ConfigUpdate(BaseModel):
    """更新配置"""
    config_value: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    default_value: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    is_required: Optional[bool] = None
    is_sensitive: Optional[bool] = None
    requires_restart: Optional[bool] = None
    change_reason: Optional[str] = Field(None, description="修改原因")


class ConfigResponse(ConfigBase):
    """配置响应"""
    id: int
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConfigListResponse(BaseModel):
    """配置列表响应"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="页码")
    page_size: int = Field(..., description="每页数量")
    items: List[ConfigResponse] = Field(..., description="配置列表")


# ============ 配置历史相关模型 ============

class ConfigHistoryResponse(BaseModel):
    """配置历史响应"""
    id: int
    config_id: int
    old_value: str
    new_value: str
    change_reason: Optional[str] = None
    version: int
    changed_by: int
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RollbackRequest(BaseModel):
    """回滚请求"""
    version: int = Field(..., description="目标版本号")
    reason: Optional[str] = Field(None, description="回滚原因")


# ============ 配置模板相关模型 ============

class TemplateResponse(BaseModel):
    """配置模板响应"""
    id: int
    template_name: str
    template_type: str
    display_name: str
    description: Optional[str] = None
    config_json: Dict[str, Any]
    is_system: bool
    is_active: bool
    usage_count: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    """模板列表响应"""
    total: int = Field(..., description="总数")
    items: List[TemplateResponse] = Field(..., description="模板列表")


class TemplateApplyResponse(BaseModel):
    """模板应用响应"""
    applied: int = Field(..., description="已应用的配置项数量")
    message: str = Field(..., description="响应消息")


# ============ 通用响应模型 ============

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="消息内容")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细信息")
