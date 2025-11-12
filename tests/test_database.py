"""
数据库操作验证测试脚本

测试内容：
1. 数据库连接
2. 表创建
3. CRUD操作
4. 事务管理
5. 异步操作
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import select
from src.database.models import (
    User,
    Configuration,
    ConfigurationHistory,
    ConfigurationTemplate,
    ConfigTypeEnum,
    ConfigStatusEnum,
)
from src.database.connection import db_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_health():
    """测试1: 数据库健康检查"""
    logger.info("\n测试 1: 数据库健康检查")
    try:
        result = db_manager.check_health()
        if result:
            logger.info("✓ 数据库连接正常")
            return True
        else:
            logger.error("✗ 数据库连接失败")
            return False
    except Exception as e:
        logger.error(f"✗ 健康检查异常: {e}")
        return False


def test_create_user():
    """测试2: 创建用户（同步操作）"""
    logger.info("\n测试 2: 创建用户（同步操作）")
    try:
        with db_manager.get_session() as session:
            # 创建测试用户
            test_user = User(
                username='test_user',
                password_hash='test_hash',
                is_active=True,
                is_admin=False,
                jwt_secret='test_secret',
            )
            session.add(test_user)
            session.commit()

            # 查询验证
            user = session.query(User).filter_by(username='test_user').first()
            if user:
                logger.info(f"✓ 用户创建成功: ID={user.id}, Username={user.username}")
                return user.id
            else:
                logger.error("✗ 用户创建失败")
                return None

    except Exception as e:
        logger.error(f"✗ 创建用户异常: {e}")
        return None


def test_create_configuration(user_id):
    """测试3: 创建配置（同步操作）"""
    logger.info("\n测试 3: 创建配置（同步操作）")
    try:
        with db_manager.get_session() as session:
            # 创建测试配置
            config = Configuration(
                config_key='TEST_SYMBOLS',
                config_value='BNB/USDT,ETH/USDT',
                config_type=ConfigTypeEnum.TRADING,
                display_name='交易对列表',
                description='测试配置项',
                data_type='string',
                default_value='BNB/USDT',
                status=ConfigStatusEnum.ACTIVE,
                is_required=True,
                requires_restart=False,
                created_by=user_id,
                updated_by=user_id,
            )
            session.add(config)
            session.commit()

            # 查询验证
            result = session.query(Configuration).filter_by(config_key='TEST_SYMBOLS').first()
            if result:
                logger.info(f"✓ 配置创建成功: ID={result.id}, Key={result.config_key}")
                return result.id
            else:
                logger.error("✗ 配置创建失败")
                return None

    except Exception as e:
        logger.error(f"✗ 创建配置异常: {e}")
        return None


async def test_async_query():
    """测试4: 异步查询操作"""
    logger.info("\n测试 4: 异步查询操作")
    try:
        async with db_manager.session_scope() as session:
            # 查询所有用户
            stmt = select(User)
            result = await session.execute(stmt)
            users = result.scalars().all()

            logger.info(f"✓ 异步查询成功: 找到 {len(users)} 个用户")
            for user in users:
                logger.info(f"  - User ID={user.id}, Username={user.username}")

            return len(users) > 0

    except Exception as e:
        logger.error(f"✗ 异步查询异常: {e}")
        return False


def test_update_configuration(config_id):
    """测试5: 更新配置"""
    logger.info("\n测试 5: 更新配置")
    try:
        with db_manager.get_session() as session:
            # 查询配置
            config = session.query(Configuration).filter_by(id=config_id).first()
            if not config:
                logger.error("✗ 配置不存在")
                return False

            old_value = config.config_value
            new_value = 'BNB/USDT,ETH/USDT,BTC/USDT'

            # 更新配置
            config.config_value = new_value
            config.updated_at = datetime.utcnow()

            # 创建历史记录
            history = ConfigurationHistory(
                config_id=config_id,
                old_value=old_value,
                new_value=new_value,
                change_reason='测试更新',
                version=1,
                changed_by=config.created_by,
            )
            session.add(history)
            session.commit()

            logger.info(f"✓ 配置更新成功: {old_value} -> {new_value}")
            return True

    except Exception as e:
        logger.error(f"✗ 更新配置异常: {e}")
        return False


def test_query_with_relationship(config_id):
    """测试6: 关系查询"""
    logger.info("\n测试 6: 关系查询（配置历史）")
    try:
        with db_manager.get_session() as session:
            # 查询配置及其历史记录
            config = session.query(Configuration).filter_by(id=config_id).first()
            if not config:
                logger.error("✗ 配置不存在")
                return False

            logger.info(f"✓ 配置: {config.config_key}")
            logger.info(f"  历史记录数量: {len(config.history)}")
            for hist in config.history:
                logger.info(f"  - Version {hist.version}: {hist.old_value} -> {hist.new_value}")

            return True

    except Exception as e:
        logger.error(f"✗ 关系查询异常: {e}")
        return False


def test_transaction_rollback():
    """测试7: 事务回滚"""
    logger.info("\n测试 7: 事务回滚")
    try:
        with db_manager.get_session() as session:
            # 创建测试配置
            config = Configuration(
                config_key='TEST_ROLLBACK',
                config_value='test',
                config_type=ConfigTypeEnum.SYSTEM,
                display_name='回滚测试',
                data_type='string',
                status=ConfigStatusEnum.DRAFT,
            )
            session.add(config)
            session.flush()  # 刷新以获取ID

            config_id = config.id
            logger.info(f"  创建测试配置: ID={config_id}")

            # 手动回滚
            session.rollback()
            logger.info("  执行回滚")

        # 验证配置未被保存
        with db_manager.get_session() as session:
            result = session.query(Configuration).filter_by(config_key='TEST_ROLLBACK').first()
            if result is None:
                logger.info("✓ 事务回滚成功: 配置未被保存")
                return True
            else:
                logger.error("✗ 事务回滚失败: 配置仍然存在")
                return False

    except Exception as e:
        logger.error(f"✗ 事务回滚测试异常: {e}")
        return False


def cleanup_test_data():
    """清理测试数据"""
    logger.info("\n清理测试数据...")
    try:
        with db_manager.get_session() as session:
            # 删除测试用户
            session.query(User).filter(User.username.like('test_%')).delete()

            # 删除测试配置
            session.query(Configuration).filter(Configuration.config_key.like('TEST_%')).delete()

            session.commit()
            logger.info("✓ 测试数据清理完成")
            return True

    except Exception as e:
        logger.error(f"✗ 清理测试数据异常: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "=" * 60)
    logger.info("数据库操作验证测试")
    logger.info("=" * 60)

    results = {}

    # 同步测试
    results['health_check'] = test_database_health()
    user_id = test_create_user()
    results['create_user'] = user_id is not None

    config_id = test_create_configuration(user_id) if user_id else None
    results['create_config'] = config_id is not None

    # 异步测试
    results['async_query'] = await test_async_query()

    # 更新和关系测试
    if config_id:
        results['update_config'] = test_update_configuration(config_id)
        results['relationship'] = test_query_with_relationship(config_id)

    # 事务测试
    results['transaction_rollback'] = test_transaction_rollback()

    # 清理
    cleanup_test_data()

    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{test_name:25s} {status}")

    logger.info("\n" + "-" * 60)
    logger.info(f"总计: {passed}/{total} 测试通过")
    logger.info("=" * 60 + "\n")

    return passed == total


if __name__ == '__main__':
    try:
        # 运行异步测试
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
