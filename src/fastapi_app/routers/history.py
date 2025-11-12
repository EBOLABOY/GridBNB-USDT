"""
配置历史路由

提供配置历史查询、版本回滚等功能。
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.fastapi_app.dependencies import get_db, get_current_active_user
from src.fastapi_app.schemas import ConfigHistoryResponse, RollbackRequest
from src.database import Configuration, ConfigurationHistory, User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{config_id}/history", response_model=list[ConfigHistoryResponse], summary="获取配置历史")
async def get_config_history(
    config_id: int,
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取配置的历史变更记录
    """
    # 检查配置是否存在
    config = db.query(Configuration).filter(Configuration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    # 查询历史记录
    history_records = db.query(ConfigurationHistory).filter(
        ConfigurationHistory.config_id == config_id
    ).order_by(ConfigurationHistory.changed_at.desc()).limit(limit).all()

    return history_records


@router.post("/{config_id}/rollback", summary="回滚配置")
async def rollback_config(
    config_id: int,
    request: RollbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    回滚配置到指定版本
    """
    # 查询配置
    config = db.query(Configuration).filter(Configuration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    # 查询目标版本
    target_history = db.query(ConfigurationHistory).filter(
        ConfigurationHistory.config_id == config_id,
        ConfigurationHistory.version == request.version
    ).first()

    if not target_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {request.version} not found"
        )

    # 回滚配置值
    old_value = config.config_value
    config.config_value = target_history.new_value
    config.updated_by = current_user.id
    config.updated_at = datetime.utcnow()

    # 创建新的历史记录
    max_version = db.query(func.max(ConfigurationHistory.version)).filter(
        ConfigurationHistory.config_id == config_id
    ).scalar() or 0

    new_history = ConfigurationHistory(
        config_id=config_id,
        old_value=old_value,
        new_value=target_history.new_value,
        change_reason=f'{request.reason or "Rollback"} (rollback to v{request.version})',
        version=max_version + 1,
        changed_by=current_user.id,
        changed_at=datetime.utcnow(),
    )
    db.add(new_history)
    db.commit()

    logger.info(
        f"配置回滚成功: {config.config_key} v{max_version + 1} "
        f"(rollback to v{request.version}) by {current_user.username}"
    )

    return {
        "message": "Configuration rolled back successfully",
        "config_key": config.config_key,
        "from_version": max_version,
        "to_version": request.version,
        "new_version": max_version + 1,
        "requires_restart": config.requires_restart,
    }
