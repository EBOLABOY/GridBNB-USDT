"""
配置模板 API 路由

提供配置模板的查询和应用功能。
"""

import logging
from aiohttp import web
from sqlalchemy import select

from src.api.middleware import auth_required
from src.database import db_manager, ConfigurationTemplate

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.get('/api/templates')
@auth_required
async def list_templates(request: web.Request) -> web.Response:
    """获取配置模板列表

    查询参数:
        - type: 模板类型（conservative/balanced/aggressive）
        - is_system: 是否为系统模板（true/false）
    """
    try:
        template_type = request.query.get('type', '').strip()
        is_system_str = request.query.get('is_system', '').strip()

        async with db_manager.session_scope() as session:
            query = select(ConfigurationTemplate).where(
                ConfigurationTemplate.is_active == True
            )

            if template_type:
                query = query.where(ConfigurationTemplate.template_type == template_type)

            if is_system_str:
                is_system = is_system_str.lower() == 'true'
                query = query.where(ConfigurationTemplate.is_system == is_system)

            query = query.order_by(ConfigurationTemplate.usage_count.desc())

            result = await session.execute(query)
            templates = result.scalars().all()

            items = [
                {
                    'id': template.id,
                    'template_name': template.template_name,
                    'template_type': template.template_type,
                    'display_name': template.display_name,
                    'description': template.description,
                    'config_json': template.config_json,
                    'is_system': template.is_system,
                    'usage_count': template.usage_count,
                    'created_at': template.created_at.isoformat(),
                }
                for template in templates
            ]

            return web.json_response({
                'total': len(items),
                'items': items,
            })

    except Exception as e:
        logger.error(f"获取模板列表失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to fetch templates', 'message': str(e)},
            status=500
        )


@routes.get('/api/templates/{template_id}')
@auth_required
async def get_template(request: web.Request) -> web.Response:
    """获取模板详情"""
    try:
        template_id = int(request.match_info['template_id'])

        async with db_manager.session_scope() as session:
            query = select(ConfigurationTemplate).where(ConfigurationTemplate.id == template_id)
            result = await session.execute(query)
            template = result.scalar_one_or_none()

            if not template:
                return web.json_response({'error': 'Template not found'}, status=404)

            return web.json_response({
                'id': template.id,
                'template_name': template.template_name,
                'template_type': template.template_type,
                'display_name': template.display_name,
                'description': template.description,
                'config_json': template.config_json,
                'is_system': template.is_system,
                'usage_count': template.usage_count,
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat(),
            })

    except ValueError:
        return web.json_response({'error': 'Invalid template ID'}, status=400)
    except Exception as e:
        logger.error(f"获取模板详情失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to fetch template', 'message': str(e)},
            status=500
        )


@routes.post('/api/templates/{template_id}/apply')
@auth_required
async def apply_template(request: web.Request) -> web.Response:
    """应用配置模板（批量更新配置）

    响应:
        {
            "applied": 5,
            "message": "Template applied successfully"
        }
    """
    try:
        user = request['user']
        template_id = int(request.match_info['template_id'])

        async with db_manager.session_scope() as session:
            # 查询模板
            template_query = select(ConfigurationTemplate).where(
                ConfigurationTemplate.id == template_id
            )
            template_result = await session.execute(template_query)
            template = template_result.scalar_one_or_none()

            if not template:
                return web.json_response({'error': 'Template not found'}, status=404)

            # 应用模板配置
            from src.database import Configuration, ConfigurationHistory
            from datetime import datetime

            applied_count = 0
            config_json = template.config_json

            for config_key, config_value in config_json.items():
                # 查询配置是否存在
                config_query = select(Configuration).where(
                    Configuration.config_key == config_key
                )
                config_result = await session.execute(config_query)
                config = config_result.scalar_one_or_none()

                if config:
                    # 更新现有配置
                    old_value = config.config_value
                    config.config_value = str(config_value)
                    config.updated_by = user.id
                    config.updated_at = datetime.utcnow()

                    # 创建历史记录
                    from sqlalchemy import func
                    max_version_query = select(func.max(ConfigurationHistory.version)).where(
                        ConfigurationHistory.config_id == config.id
                    )
                    max_version_result = await session.execute(max_version_query)
                    max_version = max_version_result.scalar() or 0

                    history = ConfigurationHistory(
                        config_id=config.id,
                        old_value=old_value,
                        new_value=str(config_value),
                        change_reason=f'Applied template: {template.template_name}',
                        version=max_version + 1,
                        changed_by=user.id,
                        changed_at=datetime.utcnow(),
                    )
                    session.add(history)

                    applied_count += 1

            # 增加模板使用次数
            template.usage_count += 1

            await session.commit()

            logger.info(
                f"模板应用成功: {template.template_name} ({applied_count} configs) "
                f"by {user.username}"
            )

            return web.json_response({
                'applied': applied_count,
                'template_name': template.template_name,
                'message': 'Template applied successfully',
            })

    except ValueError:
        return web.json_response({'error': 'Invalid template ID'}, status=400)
    except Exception as e:
        logger.error(f"应用模板失败: {e}", exc_info=True)
        return web.json_response(
            {'error': 'Failed to apply template', 'message': str(e)},
            status=500
        )
