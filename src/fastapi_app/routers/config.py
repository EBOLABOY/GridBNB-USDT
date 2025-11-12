"""
配置管理路由

提供配置的 CRUD 操作、导入/导出和重载功能。
"""

import logging
import json
from typing import Optional
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from src.fastapi_app.dependencies import get_db, get_current_active_user
from src.fastapi_app.schemas import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    ConfigListResponse,
    MessageResponse
)
from src.database import (
    Configuration,
    ConfigurationHistory,
    ConfigTypeEnum,
    ConfigStatusEnum,
    User
)
from src.config.loader import config_loader

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ConfigListResponse, summary="获取配置列表")
async def list_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    type: Optional[str] = Query(None, description="配置类型"),
    status: Optional[str] = Query(None, description="配置状态"),
    requires_restart: Optional[bool] = Query(None, description="是否需要重启"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取配置列表，支持搜索、过滤和分页

    - **page**: 页码（从1开始）
    - **page_size**: 每页数量（1-100）
    - **search**: 搜索配置键、显示名称或描述
    - **type**: 按类型过滤
    - **status**: 按状态过滤
    - **requires_restart**: 按是否需要重启过滤
    """
    # 构建查询
    query = select(Configuration)

    # 搜索过滤
    if search:
        query = query.where(
            or_(
                Configuration.config_key.ilike(f'%{search}%'),
                Configuration.display_name.ilike(f'%{search}%'),
                Configuration.description.ilike(f'%{search}%')
            )
        )

    # 类型过滤
    if type:
        try:
            type_enum = ConfigTypeEnum(type)
            query = query.where(Configuration.config_type == type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid config type: {type}"
            )

    # 状态过滤
    if status:
        try:
            status_enum = ConfigStatusEnum(status)
            query = query.where(Configuration.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )

    # requires_restart 过滤
    if requires_restart is not None:
        query = query.where(Configuration.requires_restart == requires_restart)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar()

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # 排序（按更新时间倒序）
    query = query.order_by(Configuration.updated_at.desc())

    # 执行查询
    configs = db.execute(query).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": configs
    }


@router.get("/{config_id}", response_model=ConfigResponse, summary="获取配置详情")
async def get_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取单个配置的详细信息
    """
    config = db.query(Configuration).filter(Configuration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    return config


@router.post("", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED, summary="创建配置")
async def create_config(
    config_data: ConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建新配置项
    """
    # 验证枚举值
    try:
        config_type_enum = ConfigTypeEnum(config_data.config_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid config_type: {config_data.config_type}"
        )

    try:
        status_enum = ConfigStatusEnum(config_data.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {config_data.status}"
        )

    # 检查 config_key 是否已存在
    existing = db.query(Configuration).filter(
        Configuration.config_key == config_data.config_key
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration key already exists: {config_data.config_key}"
        )

    # 创建配置
    config = Configuration(
        config_key=config_data.config_key,
        config_value=config_data.config_value,
        config_type=config_type_enum,
        display_name=config_data.display_name,
        description=config_data.description,
        data_type=config_data.data_type,
        default_value=config_data.default_value,
        validation_rules=config_data.validation_rules,
        status=status_enum,
        is_required=config_data.is_required,
        is_sensitive=config_data.is_sensitive,
        requires_restart=config_data.requires_restart,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(config)
    db.flush()  # 刷新以获取ID

    # 创建历史记录
    history = ConfigurationHistory(
        config_id=config.id,
        old_value=None,
        new_value=config.config_value,
        change_reason='Initial creation',
        version=1,
        changed_by=current_user.id,
        changed_at=datetime.utcnow(),
    )
    db.add(history)
    db.commit()
    db.refresh(config)

    logger.info(f"配置创建成功: {config.config_key} by user {current_user.username}")

    return config


@router.put("/{config_id}", response_model=ConfigResponse, summary="更新配置")
async def update_config(
    config_id: int,
    config_data: ConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新配置项
    """
    # 查询配置
    config = db.query(Configuration).filter(Configuration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    old_value = config.config_value

    # 更新配置
    update_data = config_data.model_dump(exclude_unset=True, exclude={'change_reason'})

    # 处理状态枚举
    if 'status' in update_data:
        try:
            update_data['status'] = ConfigStatusEnum(update_data['status'])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {update_data['status']}"
            )

    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_by = current_user.id
    config.updated_at = datetime.utcnow()

    # 创建历史记录
    max_version = db.query(func.max(ConfigurationHistory.version)).filter(
        ConfigurationHistory.config_id == config_id
    ).scalar() or 0

    history = ConfigurationHistory(
        config_id=config_id,
        old_value=old_value,
        new_value=config.config_value,
        change_reason=config_data.change_reason or 'Manual update',
        version=max_version + 1,
        changed_by=current_user.id,
        changed_at=datetime.utcnow(),
    )
    db.add(history)
    db.commit()
    db.refresh(config)

    logger.info(f"配置更新成功: {config.config_key} by user {current_user.username}")

    return config


@router.delete("/{config_id}", response_model=MessageResponse, summary="删除配置")
async def delete_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除配置项（会级联删除相关的历史记录）
    """
    config = db.query(Configuration).filter(Configuration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    # 检查是否为必需配置
    if config.is_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete required configuration"
        )

    config_key = config.config_key

    # 删除配置（会级联删除历史记录）
    db.delete(config)
    db.commit()

    logger.info(f"配置删除成功: {config_key} by user {current_user.username}")

    return {
        "message": "Configuration deleted successfully",
        "config_key": config_key
    }


@router.post("/batch-update", summary="批量更新配置")
async def batch_update_configs(
    updates: list[dict],
    change_reason: str = "Batch update",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    批量更新多个配置项

    请求体示例:
    ```json
    {
        "updates": [
            {"id": 1, "config_value": "new_value_1"},
            {"id": 2, "config_value": "new_value_2"}
        ],
        "change_reason": "Batch update"
    }
    ```
    """
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )

    results = {
        'updated': 0,
        'failed': 0,
        'requires_restart': False,
        'details': []
    }

    for update_item in updates:
        try:
            config_id = update_item.get('id')
            new_value = update_item.get('config_value')

            if not config_id or new_value is None:
                results['failed'] += 1
                results['details'].append({
                    'id': config_id,
                    'status': 'failed',
                    'error': 'Missing id or config_value'
                })
                continue

            # 查询配置
            config = db.query(Configuration).filter(Configuration.id == config_id).first()

            if not config:
                results['failed'] += 1
                results['details'].append({
                    'id': config_id,
                    'status': 'failed',
                    'error': 'Configuration not found'
                })
                continue

            old_value = config.config_value

            # 更新配置
            config.config_value = new_value
            config.updated_by = current_user.id
            config.updated_at = datetime.utcnow()

            # 记录是否需要重启
            if config.requires_restart:
                results['requires_restart'] = True

            # 创建历史记录
            max_version = db.query(func.max(ConfigurationHistory.version)).filter(
                ConfigurationHistory.config_id == config_id
            ).scalar() or 0

            history = ConfigurationHistory(
                config_id=config_id,
                old_value=old_value,
                new_value=new_value,
                change_reason=change_reason,
                version=max_version + 1,
                changed_by=current_user.id,
                changed_at=datetime.utcnow(),
            )
            db.add(history)

            results['updated'] += 1
            results['details'].append({
                'id': config_id,
                'config_key': config.config_key,
                'status': 'success'
            })

        except Exception as e:
            logger.error(f"批量更新失败 (config_id={config_id}): {e}")
            results['failed'] += 1
            results['details'].append({
                'id': config_id,
                'status': 'failed',
                'error': str(e)
            })

    db.commit()

    logger.info(f"批量更新完成: {results['updated']} 成功, {results['failed']} 失败")

    return results


@router.post("/reload", response_model=MessageResponse, summary="重新加载配置")
async def reload_configs(
    current_user: User = Depends(get_current_active_user),
):
    """
    重新从数据库加载配置到内存缓存

    适用场景：
    - 修改配置后，需要立即生效但不需要重启系统
    - 仅对标记为 requires_restart=False 的配置生效
    - requires_restart=True 的配置仍然需要重启系统才能生效
    """
    try:
        config_loader.reload()

        logger.info(f"配置重新加载成功 by user {current_user.username}")

        return {
            "message": "配置已重新加载到缓存",
            "cache_size": config_loader.get_cache_size(),
            "warning": "标记为 requires_restart=True 的配置需要重启系统才能生效"
        }

    except Exception as e:
        logger.error(f"配置重新加载失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置重新加载失败: {str(e)}"
        )


@router.get("/export", summary="导出配置")
async def export_configs(
    config_type: Optional[str] = Query(None, description="配置类型过滤"),
    include_sensitive: bool = Query(False, description="是否包含敏感配置"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    导出配置为JSON文件

    - **config_type**: 可选，按配置类型过滤（exchange/trading/risk/ai/notification/system）
    - **include_sensitive**: 是否包含敏感配置（默认不包含）

    返回JSON文件下载
    """
    try:
        # 构建查询
        query = select(Configuration).where(Configuration.status == ConfigStatusEnum.ACTIVE)

        # 类型过滤
        if config_type:
            try:
                type_enum = ConfigTypeEnum(config_type)
                query = query.where(Configuration.config_type == type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid config type: {config_type}"
                )

        # 查询配置
        configs = db.execute(query).scalars().all()

        # 构建导出数据
        export_data = {
            "version": "3.2.0",
            "export_time": datetime.utcnow().isoformat(),
            "exported_by": current_user.username,
            "total_configs": len(configs),
            "configs": {}
        }

        for config in configs:
            # 跳过敏感配置（除非明确要求导出）
            if config.is_sensitive and not include_sensitive:
                continue

            config_data = {
                "value": config.config_value,
                "type": config.config_type.value,
                "data_type": config.data_type,
                "display_name": config.display_name,
                "description": config.description,
                "requires_restart": config.requires_restart,
            }

            export_data["configs"][config.config_key] = config_data

        # 转换为JSON
        json_content = json.dumps(export_data, ensure_ascii=False, indent=2)

        # 生成文件名
        filename_suffix = f"_{config_type}" if config_type else "_all"
        filename = f"gridbnb_config{filename_suffix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        # 创建响应
        buffer = BytesIO(json_content.encode('utf-8'))

        logger.info(f"配置导出成功: {len(export_data['configs'])} 项 by user {current_user.username}")

        return StreamingResponse(
            buffer,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"配置导出失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置导出失败: {str(e)}"
        )


@router.post("/import", summary="导入配置")
async def import_configs(
    file: UploadFile = File(...),
    overwrite: bool = Query(False, description="是否覆盖已存在的配置"),
    create_backup: bool = Query(True, description="是否创建备份"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    从JSON文件导入配置

    - **file**: JSON配置文件
    - **overwrite**: 是否覆盖已存在的配置（默认false，冲突时跳过）
    - **create_backup**: 是否在导入前创建备份（默认true）

    返回导入结果统计
    """
    try:
        # 读取文件内容
        content = await file.read()

        # 解析JSON
        try:
            import_data = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"JSON格式错误: {str(e)}"
            )

        # 验证文件格式
        if "configs" not in import_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的配置文件格式：缺少 'configs' 字段"
            )

        configs_to_import = import_data["configs"]

        results = {
            'imported': 0,
            'skipped': 0,
            'failed': 0,
            'requires_restart': False,
            'details': []
        }

        # 导入每个配置
        for config_key, config_data in configs_to_import.items():
            try:
                # 查找现有配置
                existing_config = db.query(Configuration).filter(
                    Configuration.config_key == config_key
                ).first()

                if existing_config:
                    if not overwrite:
                        results['skipped'] += 1
                        results['details'].append({
                            'key': config_key,
                            'status': 'skipped',
                            'reason': '配置已存在且未启用覆盖模式'
                        })
                        continue

                    # 创建备份（历史记录）
                    if create_backup:
                        max_version = db.query(func.max(ConfigurationHistory.version)).filter(
                            ConfigurationHistory.config_id == existing_config.id
                        ).scalar() or 0

                        backup = ConfigurationHistory(
                            config_id=existing_config.id,
                            old_value=existing_config.config_value,
                            new_value=config_data['value'],
                            change_reason='导入配置前自动备份',
                            version=max_version + 1,
                            is_backup=True,
                            backup_type='manual',
                            changed_by=current_user.id,
                            changed_at=datetime.utcnow(),
                        )
                        db.add(backup)

                    # 更新配置
                    existing_config.config_value = config_data['value']
                    existing_config.updated_by = current_user.id
                    existing_config.updated_at = datetime.utcnow()

                    if existing_config.requires_restart:
                        results['requires_restart'] = True

                    results['imported'] += 1
                    results['details'].append({
                        'key': config_key,
                        'status': 'updated',
                        'requires_restart': existing_config.requires_restart
                    })

                else:
                    # 配置不存在，跳过（不自动创建新配置，避免引入未知配置）
                    results['skipped'] += 1
                    results['details'].append({
                        'key': config_key,
                        'status': 'skipped',
                        'reason': '配置项不存在于数据库中'
                    })

            except Exception as e:
                logger.error(f"导入配置 {config_key} 失败: {e}")
                results['failed'] += 1
                results['details'].append({
                    'key': config_key,
                    'status': 'failed',
                    'error': str(e)
                })

        db.commit()

        # 重新加载配置缓存
        if results['imported'] > 0:
            config_loader.reload()

        logger.info(f"配置导入完成: {results['imported']} 成功, {results['skipped']} 跳过, {results['failed']} 失败")

        return {
            "message": "配置导入完成",
            **results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"配置导入失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置导入失败: {str(e)}"
        )
