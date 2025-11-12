"""
数据库初始化脚本

功能：
1. 创建数据库和所有表
2. 创建默认管理员用户
3. 插入系统预设配置模板
4. (可选) 从 .env 迁移现有配置
"""

import os
import sys
import logging
import secrets
from datetime import datetime
from passlib.context import CryptContext

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database.models import (
    User,
    Configuration,
    ConfigurationHistory,
    ConfigurationTemplate,
    ConfigTypeEnum,
    ConfigStatusEnum,
)
from src.database.connection import db_manager
from src.config.config_definitions import ALL_CONFIGS

# 由于迁移文件名以数字开头，使用直接调用create_tables代替导入
def create_schema():
    """创建数据库schema（直接调用）"""
    return db_manager.create_tables()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 密码加密上下文（与API认证系统保持一致）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """使用bcrypt哈希密码（与API认证系统一致）"""
    return pwd_context.hash(password)


def create_default_user(session):
    """创建默认管理员用户"""
    try:
        # 检查是否已存在用户
        existing_user = session.query(User).filter_by(username='admin').first()
        if existing_user:
            logger.info("管理员用户已存在，跳过创建")
            return existing_user

        # 生成默认密码
        default_password = "admin123"  # 首次登录后应立即修改
        password_hash = hash_password(default_password)

        # 创建用户
        user = User(
            username='admin',
            password_hash=password_hash,
            is_active=True,
            is_admin=True,
            jwt_secret=secrets.token_urlsafe(32),
            created_at=datetime.utcnow(),
        )

        session.add(user)
        session.commit()

        logger.info(f"✓ 默认管理员用户创建成功")
        logger.warning(f"  用户名: admin")
        logger.warning(f"  默认密码: {default_password}")
        logger.warning(f"  ⚠️  请在首次登录后立即修改密码！")

        return user

    except Exception as e:
        logger.error(f"创建默认用户失败: {e}")
        session.rollback()
        raise


def create_system_templates(session, user_id):
    """创建系统预设配置模板"""
    try:
        # 检查是否已存在模板
        existing_template = session.query(ConfigurationTemplate).filter_by(
            template_name='conservative'
        ).first()
        if existing_template:
            logger.info("系统模��已存在，跳过创建")
            return

        # 保守型模板
        conservative_template = ConfigurationTemplate(
            template_name='conservative',
            template_type='conservative',
            display_name='保守型策略',
            description='适合风险厌恶型投资者，网格较大，交易频率较低，仓位限制严格',
            config_json={
                'INITIAL_GRID': 3.0,
                'MIN_TRADE_AMOUNT': 50.0,
                'MAX_POSITION_RATIO': 0.7,
                'MIN_POSITION_RATIO': 0.3,
                'ENABLE_STOP_LOSS': True,
                'STOP_LOSS_PERCENTAGE': 10.0,
                'TAKE_PROFIT_DRAWDOWN': 15.0,
                'TREND_STRONG_THRESHOLD': 50.0,
                'AI_ENABLED': False,
            },
            is_system=True,
            is_active=True,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )

        # 平衡型模板（推荐）
        balanced_template = ConfigurationTemplate(
            template_name='balanced',
            template_type='balanced',
            display_name='平衡型策略（推荐）',
            description='适合大多数投资者，平衡风险与收益，网格适中，仓位灵活',
            config_json={
                'INITIAL_GRID': 2.0,
                'MIN_TRADE_AMOUNT': 20.0,
                'MAX_POSITION_RATIO': 0.9,
                'MIN_POSITION_RATIO': 0.1,
                'ENABLE_STOP_LOSS': True,
                'STOP_LOSS_PERCENTAGE': 15.0,
                'TAKE_PROFIT_DRAWDOWN': 20.0,
                'TREND_STRONG_THRESHOLD': 60.0,
                'AI_ENABLED': False,
            },
            is_system=True,
            is_active=True,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )

        # 激进型模板
        aggressive_template = ConfigurationTemplate(
            template_name='aggressive',
            template_type='aggressive',
            display_name='激进型策略',
            description='适合高风险偏好投资者，网格较小，交易频繁，追求最大收益',
            config_json={
                'INITIAL_GRID': 1.0,
                'MIN_TRADE_AMOUNT': 10.0,
                'MAX_POSITION_RATIO': 0.95,
                'MIN_POSITION_RATIO': 0.05,
                'ENABLE_STOP_LOSS': False,
                'STOP_LOSS_PERCENTAGE': 20.0,
                'TAKE_PROFIT_DRAWDOWN': 30.0,
                'TREND_STRONG_THRESHOLD': 70.0,
                'AI_ENABLED': True,
            },
            is_system=True,
            is_active=True,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )

        session.add_all([conservative_template, balanced_template, aggressive_template])
        session.commit()

        logger.info("✓ 系统预设模板创建成功:")
        logger.info("  - 保守型策��")
        logger.info("  - 平衡型策略（推荐）")
        logger.info("  - 激进型策略")

    except Exception as e:
        logger.error(f"创建系统模板失败: {e}")
        session.rollback()
        raise


def initialize_default_configs(session, user_id):
    """从 config_definitions.py 初始化所有默认配置"""
    try:
        # 检查是否已存在配置
        existing_configs = session.query(Configuration).count()
        if existing_configs > 0:
            logger.info(f"数据库中已存在 {existing_configs} 个配置项，跳过配置初始化")
            return

        logger.info(f"正在从配置定义导入 {len(ALL_CONFIGS)} 个配置项...")

        # API密钥列表（这些配置不应存入数据库，仅在.env中管理）
        api_key_configs = {
            'BINANCE_API_KEY', 'BINANCE_API_SECRET',
            'BINANCE_TESTNET_API_KEY', 'BINANCE_TESTNET_API_SECRET',
            'OKX_API_KEY', 'OKX_API_SECRET', 'OKX_PASSPHRASE',
            'OKX_TESTNET_API_KEY', 'OKX_TESTNET_API_SECRET', 'OKX_TESTNET_PASSPHRASE',
            'AI_API_KEY',  # AI API密钥也应该敏感保护
        }

        # 敏感配置列表（这些配置存入数据库但标记为敏感）
        sensitive_configs = {
            'TELEGRAM_BOT_TOKEN', 'PUSHPLUS_TOKEN', 'WEBHOOK_URL', 'AI_API_KEY'
        }

        configs_to_insert = []
        skipped_count = 0

        for config_def in ALL_CONFIGS:
            config_key = config_def['config_key']

            # 跳过API密钥配置（仅在.env中管理）
            if config_key in api_key_configs:
                skipped_count += 1
                continue

            # 创建配置对象
            config = Configuration(
                config_key=config_key,
                config_value=config_def['default_value'],
                config_type=config_def['config_type'],
                display_name=config_def['display_name'],
                description=config_def['description'],
                data_type=config_def['data_type'],
                default_value=config_def['default_value'],
                validation_rules=config_def.get('validation_rules'),
                status=ConfigStatusEnum.ACTIVE,
                is_required=config_def.get('is_required', False),
                is_sensitive=config_key in sensitive_configs or config_def.get('is_sensitive', False),
                requires_restart=config_def.get('requires_restart', False),
                created_by=user_id,
                updated_by=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            configs_to_insert.append(config)

        # 批量插入配置
        session.add_all(configs_to_insert)
        session.flush()  # 刷新以获取配置ID

        # 为每个配置创建初始历史记录
        history_records = []
        for config in configs_to_insert:
            history = ConfigurationHistory(
                config_id=config.id,
                old_value=None,
                new_value=config.config_value,
                change_reason='系统初始化',
                version=1,
                changed_by=user_id,
                changed_at=datetime.utcnow(),
            )
            history_records.append(history)

        session.add_all(history_records)
        session.commit()

        logger.info(f"✓ 成功导入 {len(configs_to_insert)} 个配置项")
        logger.info(f"  跳过 {skipped_count} 个API密钥配置（仅在.env中管理）")

        # 按类型统计
        from collections import Counter
        type_counts = Counter([c.config_type for c in configs_to_insert])
        logger.info("  配置分类统计:")
        for config_type, count in type_counts.items():
            logger.info(f"    - {config_type.value}: {count} 项")

    except Exception as e:
        logger.error(f"初始化默认配置失败: {e}")
        session.rollback()
        raise


def initialize_database():
    """初始化数据库"""
    logger.info("\n" + "=" * 60)
    logger.info("GridBNB-USDT 交易系统 - 数据库初始化工具")
    logger.info("=" * 60 + "\n")

    try:
        # 步骤1: 创建数据库Schema
        logger.info("步骤 1/4: 创建数据库表结构...")
        create_schema()

        # 步骤2: 创建默认用户
        logger.info("\n步骤 2/4: 创建默认管理员用户...")
        with db_manager.get_session() as session:
            user = create_default_user(session)
            user_id = user.id

        # 步骤3: 初始化默认配置
        logger.info("\n步骤 3/4: 初始化默认配置项...")
        with db_manager.get_session() as session:
            initialize_default_configs(session, user_id)

        # 步骤4: 创建系统模板
        logger.info("\n步骤 4/4: 创建系统配置模板...")
        with db_manager.get_session() as session:
            create_system_templates(session, user_id)

        # 验证数据库健康状态
        logger.info("\n验证数据库健康状态...")
        if db_manager.check_health():
            logger.info("✓ 数据库健康检查通过")
        else:
            logger.error("✗ 数据库健康检查失败")
            return False

        logger.info("\n" + "=" * 60)
        logger.info("✓ 数据库初始化完成！")
        logger.info("=" * 60)
        logger.info("\n下一步:")
        logger.info("1. 配置.env文件中的API密钥:")
        logger.info("   - BINANCE_API_KEY 和 BINANCE_API_SECRET")
        logger.info("   - (可选) OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE")
        logger.info("2. 启动Web服务器: python -m src.services.fastapi_server")
        logger.info("3. 访问配置页面: http://localhost:8000")
        logger.info("4. 使用默认账号登录: admin / admin123")
        logger.info("5. ⚠️  立即修改默认密码！")
        logger.info("6. 在Web界面中调整策略配置")
        logger.info("7. 启动交易系统\n")

        return True

    except Exception as e:
        logger.error(f"\n✗ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def reset_database():
    """重置数据库（删除所有数据并重新初始化）"""
    logger.warning("\n" + "=" * 60)
    logger.warning("⚠️  警告：此操作将删除所有数据！")
    logger.warning("=" * 60 + "\n")

    confirm = input("确认重置数据库？输入 'YES' 继续: ").strip()
    if confirm != 'YES':
        logger.info("操作已取消")
        return False

    try:
        # 删除所有表
        logger.info("正在删除所有表...")
        db_manager.drop_tables()

        # 重新初始化
        logger.info("重新初始化数据库...")
        return initialize_database()

    except Exception as e:
        logger.error(f"数据库重置失败: {e}")
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='数据库初始化工具')
    parser.add_argument(
        '--reset',
        action='store_true',
        help='重置数据库（删除所有数据并重新初始化）'
    )

    args = parser.parse_args()

    if args.reset:
        success = reset_database()
    else:
        success = initialize_database()

    sys.exit(0 if success else 1)
