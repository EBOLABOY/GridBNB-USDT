"""
新旧架构对比示例

展示如何从旧的 ExchangeClient 迁移到新的多交易所架构
"""

import asyncio
from src.core.exchanges import get_exchange_factory, ExchangeConfig
from src.config.settings import settings


# ============================================================================
# 旧架构使用方式
# ============================================================================

async def old_architecture_example():
    """旧架构示例（仅限Binance）"""
    from src.core.exchange_client import ExchangeClient

    # 创建交易所客户端
    exchange = ExchangeClient()

    try:
        # 加载市场
        await exchange.load_markets()

        # 获取行情
        ticker = await exchange.fetch_ticker('BNB/USDT')
        print(f"BNB价格: {ticker['last']}")

        # 查询余额
        balance = await exchange.fetch_balance()
        print(f"现货余额: {balance['total']}")

        # 查询理财余额
        if settings.ENABLE_SAVINGS_FUNCTION:
            funding_balance = await exchange.fetch_funding_balance()
            print(f"理财余额: {funding_balance}")

    finally:
        await exchange.close()


# ============================================================================
# 新架构使用方式
# ============================================================================

async def new_architecture_binance_example():
    """新架构示例 - Binance"""
    # 1. 获取工厂
    factory = get_exchange_factory()

    # 2. 创建配置
    config = ExchangeConfig(
        exchange_name='binance',
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET,
        enable_savings=settings.ENABLE_SAVINGS_FUNCTION,
        proxy=settings.HTTP_PROXY
    )

    # 3. 创建交易所实例
    exchange = factory.create('binance', config)

    try:
        # 4. 加载市场
        await exchange.load_markets()

        # 5. 获取行情
        ticker = await exchange.fetch_ticker('BNB/USDT')
        print(f"BNB价格: {ticker['last']}")

        # 6. 查询余额
        balance = await exchange.fetch_balance()
        print(f"现货余额: {balance['total']}")

        # 7. 查询理财余额（检查是否支持）
        if exchange.supports(ExchangeCapabilities.SAVINGS):
            funding_balance = await exchange.fetch_funding_balance()
            print(f"理财余额: {funding_balance}")

    finally:
        await exchange.close()


async def new_architecture_okx_example():
    """新架构示例 - OKX"""
    factory = get_exchange_factory()

    # OKX配置需要passphrase
    config = ExchangeConfig(
        exchange_name='okx',
        api_key=settings.OKX_API_KEY,
        api_secret=settings.OKX_API_SECRET,
        passphrase=settings.OKX_PASSPHRASE,  # OKX必需
        enable_savings=True
    )

    exchange = factory.create('okx', config)

    try:
        await exchange.load_markets()

        # 使用与Binance相同的接口
        ticker = await exchange.fetch_ticker('BNB/USDT')
        print(f"BNB价格: {ticker['last']}")

        # 理财功能（OKX使用资金账户）
        if exchange.supports(ExchangeCapabilities.SAVINGS):
            # 转入资金账户
            await exchange.transfer_to_savings('USDT', 100.0)

            # 查询资金账户余额
            funding_balance = await exchange.fetch_funding_balance()
            print(f"资金账户余额: {funding_balance}")

            # 转回交易账户
            await exchange.transfer_to_spot('USDT', 100.0)

    finally:
        await exchange.close()


# ============================================================================
# 多交易所并行使用示例
# ============================================================================

async def multi_exchange_example():
    """同时使用多个交易所"""
    factory = get_exchange_factory()

    # 创建多个交易所实例
    binance_config = ExchangeConfig(
        exchange_name='binance',
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET
    )

    okx_config = ExchangeConfig(
        exchange_name='okx',
        api_key=settings.OKX_API_KEY,
        api_secret=settings.OKX_API_SECRET,
        passphrase=settings.OKX_PASSPHRASE
    )

    binance = factory.create('binance', binance_config)
    okx = factory.create('okx', okx_config)

    try:
        # 并行初始化
        await asyncio.gather(
            binance.load_markets(),
            okx.load_markets()
        )

        # 并行获取行情
        binance_ticker, okx_ticker = await asyncio.gather(
            binance.fetch_ticker('BNB/USDT'),
            okx.fetch_ticker('BNB/USDT')
        )

        print(f"Binance BNB价格: {binance_ticker['last']}")
        print(f"OKX BNB价格: {okx_ticker['last']}")

        # 价差套利机会检测
        price_diff = abs(binance_ticker['last'] - okx_ticker['last'])
        print(f"价差: {price_diff}")

    finally:
        await asyncio.gather(
            binance.close(),
            okx.close()
        )


# ============================================================================
# 适配器模式迁移示例
# ============================================================================

class ExchangeClientAdapter:
    """
    适配器：将旧的ExchangeClient包装为新接口

    用于渐进式迁移，保持向后兼容
    """

    def __init__(self, exchange_client):
        """
        Args:
            exchange_client: 旧的ExchangeClient实例
        """
        self._client = exchange_client

    @property
    def name(self):
        return 'binance'

    @property
    def capabilities(self):
        from src.core.exchanges.base import ExchangeCapabilities
        return [
            ExchangeCapabilities.SPOT_TRADING,
            ExchangeCapabilities.SAVINGS,
        ]

    async def load_markets(self):
        return await self._client.load_markets()

    async def fetch_ticker(self, symbol):
        ticker = await self._client.fetch_ticker(symbol)
        # 适配为新格式
        return {
            'symbol': symbol,
            'last': ticker.get('last', 0),
            'bid': ticker.get('bid', 0),
            'ask': ticker.get('ask', 0),
            'timestamp': ticker.get('timestamp', 0)
        }

    async def create_order(self, symbol, type, side, amount, price=None, params=None):
        return await self._client.create_order(symbol, type, side, amount, price)

    async def fetch_balance(self, params=None):
        return await self._client.fetch_balance(params)

    async def fetch_funding_balance(self):
        return await self._client.fetch_funding_balance()

    async def transfer_to_savings(self, asset, amount):
        return await self._client.transfer_to_savings(asset, amount)

    async def transfer_to_spot(self, asset, amount):
        return await self._client.transfer_to_spot(asset, amount)

    async def close(self):
        return await self._client.close()

    # 其他方法类似...


async def adapter_migration_example():
    """使用适配器进行渐进式迁移"""
    from src.core.exchange_client import ExchangeClient

    # 创建旧客户端
    old_client = ExchangeClient()

    # 包装为新接口
    adapter = ExchangeClientAdapter(old_client)

    # 现在可以使用新接口
    try:
        await adapter.load_markets()
        ticker = await adapter.fetch_ticker('BNB/USDT')
        print(f"价格: {ticker['last']}")
    finally:
        await adapter.close()


# ============================================================================
# GridTrader集成示例
# ============================================================================

async def grid_trader_integration_example():
    """展示如何在GridTrader中使用新架构"""
    from src.core.trader import GridTrader
    from src.config.settings import TradingConfig

    # 1. 根据配置选择交易所
    factory = get_exchange_factory()

    if settings.EXCHANGE_NAME == 'binance':
        config = ExchangeConfig(
            exchange_name='binance',
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET,
            enable_savings=settings.ENABLE_SAVINGS_FUNCTION
        )
    elif settings.EXCHANGE_NAME == 'okx':
        config = ExchangeConfig(
            exchange_name='okx',
            api_key=settings.OKX_API_KEY,
            api_secret=settings.OKX_API_SECRET,
            passphrase=settings.OKX_PASSPHRASE,
            enable_savings=settings.ENABLE_SAVINGS_FUNCTION
        )
    else:
        raise ValueError(f"不支持的交易所: {settings.EXCHANGE_NAME}")

    # 2. 创建交易所实例
    exchange = factory.create(settings.EXCHANGE_NAME, config)

    # 3. 创建GridTrader（现在接受IExchange接口）
    trading_config = TradingConfig()
    trader = GridTrader(
        exchange=exchange,  # 传入新接口
        config=trading_config,
        symbol='BNB/USDT'
    )

    # 4. 运行交易器
    try:
        await trader.initialize()
        await trader.main_loop()
    finally:
        await exchange.close()


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """运行所有示例"""
    print("=" * 60)
    print("新架构 - Binance示例")
    print("=" * 60)
    await new_architecture_binance_example()

    print("\n" + "=" * 60)
    print("新架构 - OKX示例")
    print("=" * 60)
    # await new_architecture_okx_example()  # 需要OKX API密钥

    print("\n" + "=" * 60)
    print("多交易所并行示例")
    print("=" * 60)
    # await multi_exchange_example()  # 需要多个交易所API密钥


if __name__ == '__main__':
    asyncio.run(main())
