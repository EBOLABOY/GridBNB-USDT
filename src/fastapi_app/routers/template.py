"""
配置模板路由

提供配置模板的查询和应用功能。
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.fastapi_app.dependencies import get_db, get_current_active_user
from src.fastapi_app.schemas import TemplateResponse, TemplateListResponse, TemplateApplyResponse
from src.database import ConfigurationTemplate, Configuration, ConfigurationHistory, User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=TemplateListResponse, summary="获取模板列表")
async def list_templates(
    type: str = Query(None, description="模板类型"),
    is_system: bool = Query(None, description="是否为系统模板"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取配置模板列表
    """
    query = db.query(ConfigurationTemplate).filter(
        ConfigurationTemplate.is_active == True
    )

    if type:
        query = query.filter(ConfigurationTemplate.template_type == type)

    if is_system is not None:
        query = query.filter(ConfigurationTemplate.is_system == is_system)

    templates = query.order_by(ConfigurationTemplate.usage_count.desc()).all()

    return {
        "total": len(templates),
        "items": templates
    }


@router.get("/{template_id}", response_model=TemplateResponse, summary="获取模板详情")
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取单个模板的详细信息
    """
    template = db.query(ConfigurationTemplate).filter(
        ConfigurationTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return template


@router.post("/{template_id}/apply", response_model=TemplateApplyResponse, summary="应用模板")
async def apply_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    应用配置模板（批量更新配置）
    """
    # 查询模板
    template = db.query(ConfigurationTemplate).filter(
        ConfigurationTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # 应用模板配置
    applied_count = 0
    config_json = template.config_json

    for config_key, config_value in config_json.items():
        # 查询配置是否存在
        config = db.query(Configuration).filter(
            Configuration.config_key == config_key
        ).first()

        if config:
            # 更新现有配置
            old_value = config.config_value
            config.config_value = str(config_value)
            config.updated_by = current_user.id
            config.updated_at = datetime.utcnow()

            # 创建历史记录
            max_version = db.query(func.max(ConfigurationHistory.version)).filter(
                ConfigurationHistory.config_id == config.id
            ).scalar() or 0

            history = ConfigurationHistory(
                config_id=config.id,
                old_value=old_value,
                new_value=str(config_value),
                change_reason=f'Applied template: {template.template_name}',
                version=max_version + 1,
                changed_by=current_user.id,
                changed_at=datetime.utcnow(),
            )
            db.add(history)

            applied_count += 1

    # 增加模板使用次数
    template.usage_count += 1

    db.commit()

    logger.info(
        f"模板应用成功: {template.template_name} ({applied_count} configs) "
        f"by {current_user.username}"
    )

    return {
        "applied": applied_count,
        "message": f"Template '{template.template_name}' applied successfully"
    }
