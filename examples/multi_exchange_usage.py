"""
企业级多交易所架构 - 使用示例

演示如何使用新的多交易所架构进行开发。
"""

import asyncio
import logging
from src.core.exchange import (
    ExchangeFactory,
    ExchangeType,
    ExchangeFeature,
    create_exchange_from_config
)
from src.core.exchange.validator import validate_and_create_exchange

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 示例1：最简单的使用方式 ====================

async def example_1_simple():
    """
    示例1：使用配置验证器自动创建交易所实例

    推荐在生产环境使用，会自动：
    - 验证配置
    - 打印诊断报告
    - 创建实例
    - 初始化连接
    """
    logger.info("=" * 60)
    logger.info("示例1：使用配置验证器（推荐）")
    logger.info("=" * 60)

    try:
        # 一行代码完成所有工作！
        exchange = await validate_and_create_exchange()

        # 使用交易所
        balance = await exchange.fetch_balance()
        logger.info(f"现货余额: {balance.get('free', {})}")

        ticker = await exchange.fetch_ticker('BTC/USDT')
        logger.info(f"BTC价格: {ticker.get('last')}")

        # 关闭连接
        await exchange.close()

    except Exception as e:
        logger.error(f"示例1失败: {e}")


# ==================== 示例2：使用工厂类手动创建 ====================

async def example_2_factory():
    """
    示例2：使用工厂类手动创建交易所实例

    适用于需要精细控制的场景
    """
    logger.info("=" * 60)
    logger.info("示例2：使用工厂类手动创建")
    logger.info("=" * 60)

    try:
        # 方式1：创建币安实例
        binance = ExchangeFactory.create(
            ExchangeType.BINANCE,
            api_key="your_key",
            api_secret="your_secret"
        )
        await binance.initialize()

        # 方式2：创建OKX实例
        okx = ExchangeFactory.create(
            ExchangeType.OKX,
            api_key="your_key",
            api_secret="your_secret",
            passphrase="your_passphrase"  # OKX特有
        )
        await okx.initialize()

        # 获取实例（单例模式）
        binance_again = ExchangeFactory.get_instance(ExchangeType.BINANCE)
        assert binance is binance_again  # True

        logger.info(f"✅ 币安实例: {binance}")
        logger.info(f"✅ OKX实例: {okx}")

        # 关闭所有连接
        await ExchangeFactory.close_all()

    except Exception as e:
        logger.error(f"示例2失败: {e}")


# ==================== 示例3：功能检测和降级处理 ====================

async def example_3_capabilities():
    """
    示例3：功能检测和优雅降级

    演示如何检测交易所支持的功能并优雅降级
    """
    logger.info("=" * 60)
    logger.info("示例3：功能检测和降级处理")
    logger.info("=" * 60)

    try:
        exchange = await validate_and_create_exchange()

        # 检查是否支持现货交易（必须支持）
        if exchange.capabilities.supports(ExchangeFeature.SPOT_TRADING):
            logger.info("✅ 支持现货交易")
        else:
            logger.error("❌ 不支持现货交易，无法使用")
            return

        # 检查是否支持理财功能（可选）
        if exchange.capabilities.supports(ExchangeFeature.FUNDING_ACCOUNT):
            logger.info("✅ 支持理财功能")

            # 获取理财余额
            funding_balance = await exchange.fetch_funding_balance()
            logger.info(f"理财余额: {funding_balance}")

            # 尝试申购理财
            # success = await exchange.transfer_to_funding('USDT', 100.0)
            # logger.info(f"申购结果: {success}")

        else:
            logger.warning("⚠️  当前交易所不支持理财功能，将跳过理财操作")

        await exchange.close()

    except Exception as e:
        logger.error(f"示例3失败: {e}")


# ==================== 示例4：多交易对并发交易 ====================

async def example_4_multi_symbol():
    """
    示例4：多交易对并发交易

    演示如何在多个交易对上共享同一个交易所实例
    """
    logger.info("=" * 60)
    logger.info("示例4：多交易对并发交易")
    logger.info("=" * 60)

    try:
        # 创建单个交易所实例
        exchange = await validate_and_create_exchange()

        # 多个交易对
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

        # 并发获取所有交易对行情
        tasks = [exchange.fetch_ticker(symbol) for symbol in symbols]
        tickers = await asyncio.gather(*tasks)

        for symbol, ticker in zip(symbols, tickers):
            logger.info(f"{symbol}: {ticker.get('last')} USDT")

        await exchange.close()

    except Exception as e:
        logger.error(f"示例4失败: {e}")


# ==================== 示例5：健康检查 ====================

async def example_5_health_check():
    """
    示例5：健康检查

    演示如何执行健康检查
    """
    logger.info("=" * 60)
    logger.info("示例5：健康检查")
    logger.info("=" * 60)

    try:
        exchange = await validate_and_create_exchange()

        # 执行健康检查
        is_healthy, message = await exchange.health_check()

        if is_healthy:
            logger.info(f"✅ 交易所健康: {message}")
        else:
            logger.error(f"❌ 交易所异常: {message}")

        await exchange.close()

    except Exception as e:
        logger.error(f"示例5失败: {e}")


# ==================== 示例6：从配置字典创建 ====================

async def example_6_from_config():
    """
    示例6：从配置字典创建交易所实例

    适用于动态配置场景
    """
    logger.info("=" * 60)
    logger.info("示例6：从配置字典创建")
    logger.info("=" * 60)

    try:
        # 币安配置
        binance_config = {
            'exchange': 'binance',
            'api_key': 'your_key',
            'api_secret': 'your_secret'
        }

        binance = await create_exchange_from_config(binance_config)
        logger.info(f"✅ 币安实例: {binance.exchange_type.value}")

        # OKX配置
        okx_config = {
            'exchange': 'okx',
            'api_key': 'your_key',
            'api_secret': 'your_secret',
            'passphrase': 'your_passphrase'
        }

        okx = await create_exchange_from_config(okx_config)
        logger.info(f"✅ OKX实例: {okx.exchange_type.value}")

        await ExchangeFactory.close_all()

    except Exception as e:
        logger.error(f"示例6失败: {e}")


# ==================== 示例7：精度调整 ====================

async def example_7_precision():
    """
    示例7：价格和数量精度调整

    演示如何使用交易所特定的精度规则
    """
    logger.info("=" * 60)
    logger.info("示例7：精度调整")
    logger.info("=" * 60)

    try:
        exchange = await validate_and_create_exchange()

        symbol = 'BTC/USDT'

        # 调整数量精度
        amount = 0.123456789
        adjusted_amount = exchange.amount_to_precision(symbol, amount)
        logger.info(f"原始数量: {amount}")
        logger.info(f"调整后数量: {adjusted_amount}")

        # 调整价格精度
        price = 45678.123456789
        adjusted_price = exchange.price_to_precision(symbol, price)
        logger.info(f"原始价格: {price}")
        logger.info(f"调整后价格: {adjusted_price}")

        # 获取市场信息
        market_info = exchange.get_market_info(symbol)
        if market_info:
            logger.info(f"市场精度: {market_info.get('precision')}")

        await exchange.close()

    except Exception as e:
        logger.error(f"示例7失败: {e}")


# ==================== 示例8：错误处理 ====================

async def example_8_error_handling():
    """
    示例8：错误处理

    演示如何优雅地处理错误
    """
    logger.info("=" * 60)
    logger.info("示例8：错误处理")
    logger.info("=" * 60)

    try:
        # 尝试使用无效配置
        invalid_config = {
            'exchange': 'invalid_exchange',  # 不支持的交易所
            'api_key': 'xxx',
            'api_secret': 'yyy'
        }

        try:
            exchange = await create_exchange_from_config(invalid_config)
        except ValueError as e:
            logger.error(f"预期的错误: {e}")

        # 正确的配置
        from src.config.settings import settings

        if settings.EXCHANGE == 'binance':
            config = {
                'exchange': 'binance',
                'api_key': settings.BINANCE_API_KEY,
                'api_secret': settings.BINANCE_API_SECRET
            }
        elif settings.EXCHANGE == 'okx':
            config = {
                'exchange': 'okx',
                'api_key': settings.OKX_API_KEY,
                'api_secret': settings.OKX_API_SECRET,
                'passphrase': settings.OKX_PASSPHRASE
            }

        exchange = await create_exchange_from_config(config)

        # 尝试获取不存在的交易对
        try:
            ticker = await exchange.fetch_ticker('INVALID/SYMBOL')
        except Exception as e:
            logger.error(f"预期的错误: {e}")

        await exchange.close()

    except Exception as e:
        logger.error(f"示例8失败: {e}")


# ==================== 主程序 ====================

async def main():
    """运行所有示例"""

    # 运行示例（根据需要取消注释）

    # await example_1_simple()           # 最简单的使用方式
    # await example_2_factory()          # 工厂类手动创建
    # await example_3_capabilities()     # 功能检测
    # await example_4_multi_symbol()     # 多交易对
    # await example_5_health_check()     # 健康检查
    # await example_6_from_config()      # 从配置创建
    # await example_7_precision()        # 精度调整
    await example_8_error_handling()   # 错误处理


if __name__ == '__main__':
    asyncio.run(main())
