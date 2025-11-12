"""
配置历史 API 路由

提供配置历史查询、版本回滚等功能。
"""

import logging
from aiohttp import web
from sqlalchemy import select

from src.api.middleware import auth_required
from src.database import db_manager, Configuration, ConfigurationHistory

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.get('/api/configs/{config_id}/history')
@auth_required
async def get_config_history(request: web.Request) -> web.Response:
    """获取配置的历史记录

    查询参数:
        - limit: 返回记录数（默认50）
    """
    try:
        config_id = int(request.match_info['config_id'])
        limit = int(request.query.get('limit', 50))

        async with db_manager.session_scope() as session:
            # 检查配置是否存在
            config_query = select(Configuration).where(Configuration.id == config_id)
            config_result = await session.execute(config_query)
            config = config_result.scalar_one_or_none()

            if not config:
                return web.json_response(
                    {'error': 'Configuration not found'},
                    status=404
                )

            # 查询历史记录
            history_query = select(ConfigurationHistory).where(
                ConfigurationHistory.config_id == config_id
            ).order_by(ConfigurationHistory.changed_at.desc()).limit(limit)

            result = await session.execute(history_query)
            history_records = result.scalars().all()

            items = [
                {
                    'id': record.id,
                    'version': record.version,
                    'old_value': record.old_value,
                    'new_value': record.new_value,
                    'change_reason': record.change_reason,
                    'changed_at': record.changed_at.isoformat(),
                    'changed_by': record.changed_by,
                }
                for record in history_records
            ]

            return web.json_response({
                'config_id': config_id,
                'config_key': config.config_key,
                'total': len(items),
                'items': items,
            })

    except ValueError:
        return web.json_response({'error': 'Invalid config ID'}, status=400)
    except Exception as e:
        logger.error(f"获取配置历史失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to fetch configuration history', 'message': str(e)},
            status=500
        )


@routes.post('/api/configs/{config_id}/rollback')
@auth_required
async def rollback_config(request: web.Request) -> web.Response:
    """回滚配置到指定版本

    请求体:
        {
            "version": 3,
            "reason": "Rollback to previous stable version"
        }
    """
    try:
        user = request['user']
        config_id = int(request.match_info['config_id'])
        data = await request.json()

        target_version = data.get('version')
        reason = data.get('reason', 'Rollback')

        if not target_version:
            return web.json_response(
                {'error': 'Missing required field: version'},
                status=400
            )

        async with db_manager.session_scope() as session:
            # 查询配置
            config_query = select(Configuration).where(Configuration.id == config_id)
            config_result = await session.execute(config_query)
            config = config_result.scalar_one_or_none()

            if not config:
                return web.json_response(
                    {'error': 'Configuration not found'},
                    status=404
                )

            # 查询目标版本
            history_query = select(ConfigurationHistory).where(
                ConfigurationHistory.config_id == config_id,
                ConfigurationHistory.version == target_version
            )
            history_result = await session.execute(history_query)
            target_history = history_result.scalar_one_or_none()

            if not target_history:
                return web.json_response(
                    {'error': f'Version {target_version} not found'},
                    status=404
                )

            # 回滚配置值
            from datetime import datetime
            old_value = config.config_value
            config.config_value = target_history.new_value
            config.updated_by = user.id
            config.updated_at = datetime.utcnow()

            # 创建新的历史记录
            from sqlalchemy import func
            max_version_query = select(func.max(ConfigurationHistory.version)).where(
                ConfigurationHistory.config_id == config_id
            )
            max_version_result = await session.execute(max_version_query)
            max_version = max_version_result.scalar() or 0

            new_history = ConfigurationHistory(
                config_id=config_id,
                old_value=old_value,
                new_value=target_history.new_value,
                change_reason=f'{reason} (rollback to v{target_version})',
                version=max_version + 1,
                changed_by=user.id,
                changed_at=datetime.utcnow(),
            )
            session.add(new_history)

            await session.commit()

            logger.info(
                f"配置回滚成功: {config.config_key} v{max_version + 1} "
                f"(rollback to v{target_version}) by {user.username}"
            )

            return web.json_response({
                'message': 'Configuration rolled back successfully',
                'config_key': config.config_key,
                'from_version': max_version,
                'to_version': target_version,
                'new_version': max_version + 1,
                'requires_restart': config.requires_restart,
            })

    except ValueError:
        return web.json_response({'error': 'Invalid config ID or version'}, status=400)
    except Exception as e:
        logger.error(f"配置回滚失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to rollback configuration', 'message': str(e)},
            status=500
        )
