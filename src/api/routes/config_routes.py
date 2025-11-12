"""
配置管理 API 路由

提供配置的 CRUD 操作。
"""

import logging
from typing import List, Optional
from datetime import datetime

from aiohttp import web
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session

from src.api.middleware import auth_required
from src.database import (
    db_manager,
    Configuration,
    ConfigurationHistory,
    ConfigTypeEnum,
    ConfigStatusEnum
)

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.get('/api/configs')
@auth_required
async def list_configs(request: web.Request) -> web.Response:
    """获取配置列表（支持搜索、过滤、分页）

    查询参数:
        - page: 页码（默认1）
        - page_size: 每页数量（默认20）
        - search: 搜索关键词（搜索 config_key 和 display_name）
        - type: 配置类型过滤（exchange/trading/risk/ai/notification/system）
        - status: 配置状态过滤（draft/active/inactive/archived）
        - requires_restart: 是否需要重启（true/false）

    响应:
        {
            "total": 100,
            "page": 1,
            "page_size": 20,
            "items": [...]
        }
    """
    try:
        # 解析查询参数
        page = int(request.query.get('page', 1))
        page_size = int(request.query.get('page_size', 20))
        search = request.query.get('search', '').strip()
        config_type = request.query.get('type', '').strip()
        status = request.query.get('status', '').strip()
        requires_restart_str = request.query.get('requires_restart', '').strip()

        # 验证分页参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        async with db_manager.session_scope() as session:
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
            if config_type:
                try:
                    type_enum = ConfigTypeEnum(config_type)
                    query = query.where(Configuration.config_type == type_enum)
                except ValueError:
                    return web.json_response(
                        {'error': f'Invalid config type: {config_type}'},
                        status=400
                    )

            # 状态过滤
            if status:
                try:
                    status_enum = ConfigStatusEnum(status)
                    query = query.where(Configuration.status == status_enum)
                except ValueError:
                    return web.json_response(
                        {'error': f'Invalid status: {status}'},
                        status=400
                    )

            # requires_restart 过滤
            if requires_restart_str:
                requires_restart = requires_restart_str.lower() == 'true'
                query = query.where(Configuration.requires_restart == requires_restart)

            # 获取总数
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar()

            # 分页
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            # 排序（按更新时间倒序）
            query = query.order_by(Configuration.updated_at.desc())

            # 执行查询
            result = await session.execute(query)
            configs = result.scalars().all()

            # 序列化
            items = [
                {
                    'id': config.id,
                    'config_key': config.config_key,
                    'config_value': config.config_value,
                    'config_type': config.config_type.value,
                    'display_name': config.display_name,
                    'description': config.description,
                    'data_type': config.data_type,
                    'default_value': config.default_value,
                    'validation_rules': config.validation_rules,
                    'status': config.status.value,
                    'is_required': config.is_required,
                    'is_sensitive': config.is_sensitive,
                    'requires_restart': config.requires_restart,
                    'created_at': config.created_at.isoformat(),
                    'updated_at': config.updated_at.isoformat(),
                }
                for config in configs
            ]

            return web.json_response({
                'total': total,
                'page': page,
                'page_size': page_size,
                'items': items,
            })

    except Exception as e:
        logger.error(f"获取配置列表失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to fetch configurations', 'message': str(e)},
            status=500
        )


@routes.get('/api/configs/{config_id}')
@auth_required
async def get_config(request: web.Request) -> web.Response:
    """获取单个配置详情

    响应:
        {
            "id": 1,
            "config_key": "SYMBOLS",
            "config_value": "BNB/USDT",
            ...
        }
    """
    try:
        config_id = int(request.match_info['config_id'])

        async with db_manager.session_scope() as session:
            query = select(Configuration).where(Configuration.id == config_id)
            result = await session.execute(query)
            config = result.scalar_one_or_none()

            if not config:
                return web.json_response(
                    {'error': 'Configuration not found'},
                    status=404
                )

            return web.json_response({
                'id': config.id,
                'config_key': config.config_key,
                'config_value': config.config_value,
                'config_type': config.config_type.value,
                'display_name': config.display_name,
                'description': config.description,
                'data_type': config.data_type,
                'default_value': config.default_value,
                'validation_rules': config.validation_rules,
                'status': config.status.value,
                'is_required': config.is_required,
                'is_sensitive': config.is_sensitive,
                'requires_restart': config.requires_restart,
                'created_at': config.created_at.isoformat(),
                'updated_at': config.updated_at.isoformat(),
                'created_by': config.created_by,
                'updated_by': config.updated_by,
            })

    except ValueError:
        return web.json_response(
            {'error': 'Invalid config ID'},
            status=400
        )
    except Exception as e:
        logger.error(f"获取配置详情失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to fetch configuration', 'message': str(e)},
            status=500
        )


@routes.post('/api/configs')
@auth_required
async def create_config(request: web.Request) -> web.Response:
    """创建新配置

    请求体:
        {
            "config_key": "NEW_CONFIG",
            "config_value": "value",
            "config_type": "trading",
            "display_name": "新配置",
            "description": "配置描述",
            "data_type": "string",
            "default_value": "default",
            "validation_rules": {},
            "status": "active",
            "is_required": false,
            "requires_restart": false
        }
    """
    try:
        user = request['user']
        data = await request.json()

        # 验证必需字段
        required_fields = ['config_key', 'config_value', 'config_type', 'display_name', 'data_type']
        for field in required_fields:
            if field not in data:
                return web.json_response(
                    {'error': f'Missing required field: {field}'},
                    status=400
                )

        # 验证枚举值
        try:
            config_type_enum = ConfigTypeEnum(data['config_type'])
        except ValueError:
            return web.json_response(
                {'error': f'Invalid config_type: {data["config_type"]}'},
                status=400
            )

        status_enum = ConfigStatusEnum.ACTIVE
        if 'status' in data:
            try:
                status_enum = ConfigStatusEnum(data['status'])
            except ValueError:
                return web.json_response(
                    {'error': f'Invalid status: {data["status"]}'},
                    status=400
                )

        async with db_manager.session_scope() as session:
            # 检查 config_key 是否已存在
            existing_query = select(Configuration).where(
                Configuration.config_key == data['config_key']
            )
            existing_result = await session.execute(existing_query)
            if existing_result.scalar_one_or_none():
                return web.json_response(
                    {'error': f'Configuration key already exists: {data["config_key"]}'},
                    status=400
                )

            # 创建配置
            config = Configuration(
                config_key=data['config_key'],
                config_value=data['config_value'],
                config_type=config_type_enum,
                display_name=data['display_name'],
                description=data.get('description'),
                data_type=data['data_type'],
                default_value=data.get('default_value'),
                validation_rules=data.get('validation_rules'),
                status=status_enum,
                is_required=data.get('is_required', False),
                is_sensitive=data.get('is_sensitive', False),
                requires_restart=data.get('requires_restart', False),
                created_by=user.id,
                updated_by=user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            session.add(config)
            await session.flush()  # 刷新以获取ID

            # 创建历史记录
            history = ConfigurationHistory(
                config_id=config.id,
                old_value=None,
                new_value=config.config_value,
                change_reason='Initial creation',
                version=1,
                changed_by=user.id,
                changed_at=datetime.utcnow(),
            )
            session.add(history)

            await session.commit()

            logger.info(f"配置创建成功: {config.config_key} by user {user.username}")

            return web.json_response({
                'id': config.id,
                'config_key': config.config_key,
                'message': 'Configuration created successfully',
            }, status=201)

    except Exception as e:
        logger.error(f"创建配置失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to create configuration', 'message': str(e)},
            status=500
        )


@routes.put('/api/configs/{config_id}')
@auth_required
async def update_config(request: web.Request) -> web.Response:
    """更新配置

    请求体:
        {
            "config_value": "new_value",
            "change_reason": "Updated for testing"
        }
    """
    try:
        user = request['user']
        config_id = int(request.match_info['config_id'])
        data = await request.json()

        if 'config_value' not in data:
            return web.json_response(
                {'error': 'Missing required field: config_value'},
                status=400
            )

        async with db_manager.session_scope() as session:
            # 查询配置
            query = select(Configuration).where(Configuration.id == config_id)
            result = await session.execute(query)
            config = result.scalar_one_or_none()

            if not config:
                return web.json_response(
                    {'error': 'Configuration not found'},
                    status=404
                )

            old_value = config.config_value
            new_value = data['config_value']

            # 更新配置
            config.config_value = new_value
            config.updated_by = user.id
            config.updated_at = datetime.utcnow()

            # 更新其他可选字段
            if 'display_name' in data:
                config.display_name = data['display_name']
            if 'description' in data:
                config.description = data['description']
            if 'status' in data:
                try:
                    config.status = ConfigStatusEnum(data['status'])
                except ValueError:
                    pass

            # 创建历史记录
            history_query = select(func.max(ConfigurationHistory.version)).where(
                ConfigurationHistory.config_id == config_id
            )
            version_result = await session.execute(history_query)
            max_version = version_result.scalar() or 0

            history = ConfigurationHistory(
                config_id=config_id,
                old_value=old_value,
                new_value=new_value,
                change_reason=data.get('change_reason', 'Manual update'),
                version=max_version + 1,
                changed_by=user.id,
                changed_at=datetime.utcnow(),
            )
            session.add(history)

            await session.commit()

            logger.info(f"配置更新成功: {config.config_key} by user {user.username}")

            return web.json_response({
                'id': config.id,
                'config_key': config.config_key,
                'message': 'Configuration updated successfully',
                'requires_restart': config.requires_restart,
            })

    except ValueError:
        return web.json_response(
            {'error': 'Invalid config ID'},
            status=400
        )
    except Exception as e:
        logger.error(f"更新配置失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to update configuration', 'message': str(e)},
            status=500
        )


@routes.delete('/api/configs/{config_id}')
@auth_required
async def delete_config(request: web.Request) -> web.Response:
    """删除配置

    注意：会级联删除相关的历史记录
    """
    try:
        user = request['user']
        config_id = int(request.match_info['config_id'])

        async with db_manager.session_scope() as session:
            # 查询配置
            query = select(Configuration).where(Configuration.id == config_id)
            result = await session.execute(query)
            config = result.scalar_one_or_none()

            if not config:
                return web.json_response(
                    {'error': 'Configuration not found'},
                    status=404
                )

            # 检查是否为必需配置
            if config.is_required:
                return web.json_response(
                    {'error': 'Cannot delete required configuration'},
                    status=400
                )

            config_key = config.config_key

            # 删除配置（会级联删除历史记录）
            await session.delete(config)
            await session.commit()

            logger.info(f"配置删除成功: {config_key} by user {user.username}")

            return web.json_response({
                'message': 'Configuration deleted successfully',
                'config_key': config_key,
            })

    except ValueError:
        return web.json_response(
            {'error': 'Invalid config ID'},
            status=400
        )
    except Exception as e:
        logger.error(f"删除配置失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to delete configuration', 'message': str(e)},
            status=500
        )


@routes.post('/api/configs/batch-update')
@auth_required
async def batch_update_configs(request: web.Request) -> web.Response:
    """批量更新配置

    请求体:
        {
            "updates": [
                {"id": 1, "config_value": "new_value_1"},
                {"id": 2, "config_value": "new_value_2"}
            ],
            "change_reason": "Batch update"
        }

    响应:
        {
            "updated": 2,
            "failed": 0,
            "requires_restart": true,
            "details": [...]
        }
    """
    try:
        user = request['user']
        data = await request.json()

        updates = data.get('updates', [])
        change_reason = data.get('change_reason', 'Batch update')

        if not updates:
            return web.json_response(
                {'error': 'No updates provided'},
                status=400
            )

        results = {
            'updated': 0,
            'failed': 0,
            'requires_restart': False,
            'details': []
        }

        async with db_manager.session_scope() as session:
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
                    query = select(Configuration).where(Configuration.id == config_id)
                    result = await session.execute(query)
                    config = result.scalar_one_or_none()

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
                    config.updated_by = user.id
                    config.updated_at = datetime.utcnow()

                    # 记录是否需要重启
                    if config.requires_restart:
                        results['requires_restart'] = True

                    # 创建历史记录
                    history_query = select(func.max(ConfigurationHistory.version)).where(
                        ConfigurationHistory.config_id == config_id
                    )
                    version_result = await session.execute(history_query)
                    max_version = version_result.scalar() or 0

                    history = ConfigurationHistory(
                        config_id=config_id,
                        old_value=old_value,
                        new_value=new_value,
                        change_reason=change_reason,
                        version=max_version + 1,
                        changed_by=user.id,
                        changed_at=datetime.utcnow(),
                    )
                    session.add(history)

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

            await session.commit()

        logger.info(f"批量更新完成: {results['updated']} 成功, {results['failed']} 失败")

        return web.json_response(results)

    except Exception as e:
        logger.error(f"批量更新配置失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to batch update configurations', 'message': str(e)},
            status=500
        )


@routes.get('/api/configs/export')
@auth_required
async def export_configs(request: web.Request) -> web.Response:
    """导出配置到JSON文件

    查询参数:
        - format: 导出格式 (json/env)，默认 json
        - type: 配置类型过滤（可选）
        - include_sensitive: 是否包含敏感信息（默认false）

    响应:
        JSON格式: 返回配置JSON对象
        ENV格式: 返回.env文件内容
    """
    try:
        export_format = request.query.get('format', 'json')
        config_type = request.query.get('type', '').strip()
        include_sensitive = request.query.get('include_sensitive', 'false').lower() == 'true'

        async with db_manager.session_scope() as session:
            # 构建查询
            query = select(Configuration).where(Configuration.status == ConfigStatusEnum.ACTIVE)

            # 类型过滤
            if config_type:
                try:
                    type_enum = ConfigTypeEnum(config_type)
                    query = query.where(Configuration.config_type == type_enum)
                except ValueError:
                    pass

            # 执行查询
            result = await session.execute(query)
            configs = result.scalars().all()

            if export_format == 'env':
                # 导出为 .env 格式
                lines = [
                    "# ============================================================================",
                    "# 配置文件 - 从数据库导出",
                    f"# 导出时间: {datetime.utcnow().isoformat()}",
                    "# ============================================================================\n",
                ]

                current_type = None
                for config in configs:
                    # 添加分类注释
                    if config.config_type != current_type:
                        current_type = config.config_type
                        lines.append(f"\n# {current_type.value.upper()}")
                        lines.append("# " + "-" * 60)

                    # 添加描述
                    if config.description:
                        lines.append(f"# {config.description}")

                    # 添加配置项
                    value = config.config_value
                    if config.is_sensitive and not include_sensitive:
                        value = "********"

                    lines.append(f"{config.config_key}={value}\n")

                content = "\n".join(lines)
                return web.Response(
                    text=content,
                    content_type='text/plain',
                    headers={
                        'Content-Disposition': f'attachment; filename="config_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.env"'
                    }
                )
            else:
                # 导出为 JSON 格式
                export_data = {
                    'export_time': datetime.utcnow().isoformat(),
                    'total_configs': len(configs),
                    'include_sensitive': include_sensitive,
                    'configs': []
                }

                for config in configs:
                    config_data = {
                        'config_key': config.config_key,
                        'config_value': config.config_value if (not config.is_sensitive or include_sensitive) else '********',
                        'config_type': config.config_type.value,
                        'display_name': config.display_name,
                        'description': config.description,
                        'data_type': config.data_type,
                        'is_required': config.is_required,
                        'is_sensitive': config.is_sensitive,
                    }
                    export_data['configs'].append(config_data)

                import json
                return web.Response(
                    text=json.dumps(export_data, ensure_ascii=False, indent=2),
                    content_type='application/json',
                    headers={
                        'Content-Disposition': f'attachment; filename="config_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json"'
                    }
                )

    except Exception as e:
        logger.error(f"导出配置失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to export configurations', 'message': str(e)},
            status=500
        )


@routes.post('/api/configs/import')
@auth_required
async def import_configs(request: web.Request) -> web.Response:
    """从JSON文件导入配置

    请求体:
        {
            "configs": [
                {
                    "config_key": "SYMBOLS",
                    "config_value": "BNB/USDT",
                    ...
                }
            ],
            "merge_mode": "update",  // update: 只更新已存在的, create: 只创建新的, replace: 全部替换
            "change_reason": "Import from file"
        }

    响应:
        {
            "imported": 10,
            "updated": 5,
            "created": 3,
            "skipped": 2,
            "failed": 0,
            "details": [...]
        }
    """
    try:
        user = request['user']
        data = await request.json()

        configs = data.get('configs', [])
        merge_mode = data.get('merge_mode', 'update')  # update / create / replace
        change_reason = data.get('change_reason', 'Import from file')

        if not configs:
            return web.json_response(
                {'error': 'No configs provided'},
                status=400
            )

        results = {
            'imported': 0,
            'updated': 0,
            'created': 0,
            'skipped': 0,
            'failed': 0,
            'requires_restart': False,
            'details': []
        }

        async with db_manager.session_scope() as session:
            for config_data in configs:
                try:
                    config_key = config_data.get('config_key')
                    new_value = config_data.get('config_value')

                    if not config_key or new_value is None:
                        results['failed'] += 1
                        results['details'].append({
                            'config_key': config_key,
                            'status': 'failed',
                            'error': 'Missing config_key or config_value'
                        })
                        continue

                    # 查询配置是否存在
                    query = select(Configuration).where(Configuration.config_key == config_key)
                    result = await session.execute(query)
                    existing_config = result.scalar_one_or_none()

                    if existing_config:
                        # 配置已存在
                        if merge_mode == 'create':
                            # 仅创建模式，跳过已存在的
                            results['skipped'] += 1
                            results['details'].append({
                                'config_key': config_key,
                                'status': 'skipped',
                                'reason': 'Already exists (create mode)'
                            })
                            continue

                        # 更新配置
                        old_value = existing_config.config_value
                        existing_config.config_value = new_value
                        existing_config.updated_by = user.id
                        existing_config.updated_at = datetime.utcnow()

                        if existing_config.requires_restart:
                            results['requires_restart'] = True

                        # 创建历史记录
                        history_query = select(func.max(ConfigurationHistory.version)).where(
                            ConfigurationHistory.config_id == existing_config.id
                        )
                        version_result = await session.execute(history_query)
                        max_version = version_result.scalar() or 0

                        history = ConfigurationHistory(
                            config_id=existing_config.id,
                            old_value=old_value,
                            new_value=new_value,
                            change_reason=change_reason,
                            version=max_version + 1,
                            changed_by=user.id,
                            changed_at=datetime.utcnow(),
                        )
                        session.add(history)

                        results['updated'] += 1
                        results['imported'] += 1
                        results['details'].append({
                            'config_key': config_key,
                            'status': 'updated'
                        })
                    else:
                        # 配置不存在
                        if merge_mode == 'update':
                            # 仅更新模式，跳过不存在的
                            results['skipped'] += 1
                            results['details'].append({
                                'config_key': config_key,
                                'status': 'skipped',
                                'reason': 'Not found (update mode)'
                            })
                            continue

                        # 创建新配置
                        # 需要从配置定义中获取元数据
                        from src.config.config_definitions import get_config_by_key, ConfigTypeEnum
                        try:
                            config_def = get_config_by_key(config_key)
                        except ValueError:
                            # 配置键不存在于定义中
                            results['failed'] += 1
                            results['details'].append({
                                'config_key': config_key,
                                'status': 'failed',
                                'error': 'Unknown config key'
                            })
                            continue

                        new_config = Configuration(
                            config_key=config_key,
                            config_value=new_value,
                            config_type=config_def['config_type'],
                            display_name=config_def['display_name'],
                            description=config_def['description'],
                            data_type=config_def['data_type'],
                            default_value=config_def['default_value'],
                            validation_rules=config_def['validation_rules'],
                            status=ConfigStatusEnum.ACTIVE,
                            is_required=config_def['is_required'],
                            is_sensitive=config_def['is_sensitive'],
                            requires_restart=config_def['requires_restart'],
                            created_by=user.id,
                            updated_by=user.id,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        session.add(new_config)
                        await session.flush()

                        # 创建历史记录
                        history = ConfigurationHistory(
                            config_id=new_config.id,
                            old_value=None,
                            new_value=new_value,
                            change_reason=change_reason,
                            version=1,
                            changed_by=user.id,
                            changed_at=datetime.utcnow(),
                        )
                        session.add(history)

                        results['created'] += 1
                        results['imported'] += 1
                        results['details'].append({
                            'config_key': config_key,
                            'status': 'created'
                        })

                except Exception as e:
                    logger.error(f"导入配置失败 (config_key={config_key}): {e}")
                    results['failed'] += 1
                    results['details'].append({
                        'config_key': config_key,
                        'status': 'failed',
                        'error': str(e)
                    })

            await session.commit()

        logger.info(f"配置导入完成: {results['imported']} 成功, {results['failed']} 失败")

        return web.json_response(results)

    except Exception as e:
        logger.error(f"导入配置失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to import configurations', 'message': str(e)},
            status=500
        )


@routes.get('/api/config-definitions')
@auth_required
async def get_config_definitions(request: web.Request) -> web.Response:
    """获取所有配置项的定义

    查询参数:
        - config_type: 配置类型过滤（可选）
        - config_key: 获取特定配置的定义（可选）

    响应:
        [
            {
                "config_key": "EXCHANGE",
                "display_name": "交易所选择",
                "description": "当前使用的交易所...",
                "config_type": "exchange",
                "data_type": "string",
                "default_value": "binance",
                "validation_rules": {...},
                "is_required": true,
                "is_sensitive": false,
                "requires_restart": true
            },
            ...
        ]
    """
    try:
        from src.config.config_definitions import ALL_CONFIGS, get_config_by_key, get_configs_by_type

        config_type = request.query.get('config_type', '').strip()
        config_key = request.query.get('config_key', '').strip()

        # 如果指定了 config_key，返回单个配置定义
        if config_key:
            try:
                config_def = get_config_by_key(config_key)
                # 将 Enum 转换为字符串
                result = dict(config_def)
                result['config_type'] = result['config_type'].value
                return web.json_response(result)
            except ValueError as e:
                return web.json_response(
                    {'error': str(e)},
                    status=404
                )

        # 如果指定了 config_type，返回该类型的所有配置定义
        if config_type:
            try:
                type_enum = ConfigTypeEnum(config_type)
                config_defs = get_configs_by_type(type_enum)
            except ValueError:
                return web.json_response(
                    {'error': f'Invalid config type: {config_type}'},
                    status=400
                )
        else:
            # 返回所有配置定义
            config_defs = ALL_CONFIGS

        # 将 Enum 转换为字符串
        result = []
        for config_def in config_defs:
            item = dict(config_def)
            item['config_type'] = item['config_type'].value
            result.append(item)

        return web.json_response(result)

    except Exception as e:
        logger.error(f"获取配置定义失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to get config definitions', 'message': str(e)},
            status=500
        )
