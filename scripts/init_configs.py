"""
配置初始化脚本

将配置定义同步到数据库，创建默认配置项。
- 支持从 settings.py 读取当前配置值
- 支持增量更新（不会覆盖已修改的配置）
- 自动创建默认管理员用户
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import db_manager, Configuration, User, ConfigStatusEnum
from src.config.config_definitions import ALL_CONFIGS
from src.config.settings import settings
from sqlalchemy import select
from datetime import datetime
import bcrypt
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def create_default_admin():
    """创建默认管理员用户"""
    async with db_manager.session_scope() as session:
        # 检查是否已存在管理员
        query = select(User).where(User.username == 'admin')
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.info("✓ 管理员用户已存在，跳过创建")
            return

        # 创建默认管理员（密码: admin123）
        password = 'admin123'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        admin = User(
            username='admin',
            password_hash=password_hash,
            is_active=True,
            is_admin=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        session.add(admin)
        await session.commit()

        logger.info("✓ 默认管理员用户创建成功")
        logger.info("  用户名: admin")
        logger.info("  密码: admin123")
        logger.warning("  ⚠️  请在首次登录后立即修改密码！")


async def sync_configs_to_db(force_update: bool = False):
    """同步配置定义到数据库

    Args:
        force_update: 是否强制更新所有配置（会覆盖用户修改）
    """
    async with db_manager.session_scope() as session:
        # 获取管理员用户ID
        admin_query = select(User).where(User.username == 'admin')
        admin_result = await session.execute(admin_query)
        admin = admin_result.scalar_one_or_none()
        admin_id = admin.id if admin else None

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for config_def in ALL_CONFIGS:
            config_key = config_def['config_key']

            # 查询配置是否已存在
            query = select(Configuration).where(Configuration.config_key == config_key)
            result = await session.execute(query)
            existing_config = result.scalar_one_or_none()

            # 从 settings 获取当前值（如果存在）
            current_value = getattr(settings, config_key, None)
            if current_value is not None:
                # 将值转换为字符串
                if isinstance(current_value, bool):
                    config_value = str(current_value).lower()
                elif isinstance(current_value, (dict, list)):
                    import json
                    config_value = json.dumps(current_value, ensure_ascii=False)
                else:
                    config_value = str(current_value)
            else:
                config_value = config_def['default_value']

            if existing_config:
                # 配置已存在
                if force_update:
                    # 强制更新
                    existing_config.config_value = config_value
                    existing_config.display_name = config_def['display_name']
                    existing_config.description = config_def['description']
                    existing_config.data_type = config_def['data_type']
                    existing_config.default_value = config_def['default_value']
                    existing_config.validation_rules = config_def['validation_rules']
                    existing_config.is_required = config_def['is_required']
                    existing_config.is_sensitive = config_def['is_sensitive']
                    existing_config.requires_restart = config_def['requires_restart']
                    existing_config.updated_at = datetime.utcnow()
                    existing_config.updated_by = admin_id
                    updated_count += 1
                    logger.info(f"  更新: {config_key}")
                else:
                    # 只更新元数据，不更新值
                    existing_config.display_name = config_def['display_name']
                    existing_config.description = config_def['description']
                    existing_config.default_value = config_def['default_value']
                    existing_config.validation_rules = config_def['validation_rules']
                    existing_config.updated_at = datetime.utcnow()
                    skipped_count += 1
            else:
                # 创建新配置
                new_config = Configuration(
                    config_key=config_key,
                    config_value=config_value,
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
                    created_by=admin_id,
                    updated_by=admin_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(new_config)
                created_count += 1
                logger.info(f"  创建: {config_key}")

        await session.commit()

        logger.info(f"\n配置同步完成:")
        logger.info(f"  ✓ 新建: {created_count} 项")
        logger.info(f"  ✓ 更新: {updated_count} 项")
        logger.info(f"  - 跳过: {skipped_count} 项")
        logger.info(f"  总计: {len(ALL_CONFIGS)} 项配置")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='配置初始化脚本')
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制更新所有配置（会覆盖用户修改）'
    )
    parser.add_argument(
        '--create-admin',
        action='store_true',
        help='仅创建管理员用户'
    )

    args = parser.parse_args()

    try:
        # 初始化数据库连接
        await db_manager.init()
        logger.info("✓ 数据库连接初始化成功")

        if args.create_admin:
            # 仅创建管理员
            await create_default_admin()
        else:
            # 完整初始化流程
            logger.info("\n========================================")
            logger.info("  配置初始化脚本")
            logger.info("========================================\n")

            # 1. 创建默认管理员
            logger.info("步骤 1/2: 创建默认管理员用户")
            await create_default_admin()

            # 2. 同步配置到数据库
            logger.info("\n步骤 2/2: 同步配置到数据库")
            await sync_configs_to_db(force_update=args.force)

            logger.info("\n========================================")
            logger.info("  初始化完成！")
            logger.info("========================================")
            logger.info("\n后续步骤:")
            logger.info("  1. 使用 admin/admin123 登录Web界面")
            logger.info("  2. 在Web界面配置交易所API密钥")
            logger.info("  3. 根据需要调整交易策略参数")
            logger.info("  4. 启动交易机器人")

    except Exception as e:
        logger.error(f"\n❌ 初始化失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await db_manager.close()


if __name__ == '__main__':
    asyncio.run(main())
