"""
初始化数据库Schema迁移脚本

版本: 001
创建时间: 2025-01-28
描述: 创建配置管理所需的所有表结构
"""

import logging
from sqlalchemy import text

from src.database.models import Base
from src.database.connection import db_manager

logger = logging.getLogger(__name__)


def upgrade():
    """执行升级迁移（创建表）"""
    try:
        logger.info("开始执行数据库迁移 001_initial_schema...")

        # 创建所有表
        db_manager.create_tables()

        # 创建额外的索引（如果需要）
        with db_manager.get_session() as session:
            # 验证表是否创建成功
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"已创建的表: {', '.join(tables)}")

        logger.info("数据库迁移 001_initial_schema 完成 ✓")
        return True

    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise


def downgrade():
    """执行降级迁移（删除表）"""
    try:
        logger.warning("开始回滚数据库迁移 001_initial_schema...")

        # 删除所有表
        db_manager.drop_tables()

        logger.warning("数据库迁移 001_initial_schema 已回滚")
        return True

    except Exception as e:
        logger.error(f"数据库迁移回滚失败: {e}")
        raise


def get_migration_info():
    """获取迁移信息"""
    return {
        'version': '001',
        'name': 'initial_schema',
        'description': '创建配置管理所需的所有表结构',
        'created_at': '2025-01-28',
    }


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 执行迁移
    print("\n" + "=" * 60)
    print("数据库迁移工具 - 初始化Schema")
    print("=" * 60 + "\n")

    info = get_migration_info()
    print(f"版本: {info['version']}")
    print(f"名称: {info['name']}")
    print(f"描述: {info['description']}")
    print(f"创建时间: {info['created_at']}\n")

    choice = input("执行操作: [1] 升级 (创建表) [2] 降级 (删除表) [q] 退出: ").strip()

    if choice == '1':
        confirm = input("确认创建所有数据库表？(yes/no): ").strip().lower()
        if confirm == 'yes':
            upgrade()
            print("\n✓ 数据库表创建成功！")
        else:
            print("操作已取消")
    elif choice == '2':
        confirm = input("⚠️  警告：此操作将删除所有数据！确认删除？(yes/no): ").strip().lower()
        if confirm == 'yes':
            downgrade()
            print("\n✓ 数据库表已删除")
        else:
            print("操作已取消")
    else:
        print("操作已取消")
