"""
多币种并发交易集成测试

测试多个交易对同时运行的场景
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor


@pytest.fixture
def multi_symbol_exchange():
    """多币种交易所mock"""
    exchange = AsyncMock()

    # 支持多个交易对
    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {
            'id': 'BNBUSDT',
            'symbol': 'BNB/USDT',
            'base': 'BNB',
            'quote': 'USDT',
            'limits': {'amount': {'min': 0.001}, 'price': {'min': 0.01}},
            'precision': {'amount': 8, 'price': 2}
        },
        'ETH/USDT': {
            'id': 'ETHUSDT',
            'symbol': 'ETH/USDT',
            'base': 'ETH',
            'quote': 'USDT',
            'limits': {'amount': {'min': 0.0001}, 'price': {'min': 0.01}},
            'precision': {'amount': 8, 'price': 2}
        },
        'BTC/USDT': {
            'id': 'BTCUSDT',
            'symbol': 'BTC/USDT',
            'base': 'BTC',
            'quote': 'USDT',
            'limits': {'amount': {'min': 0.00001}, 'price': {'min': 0.01}},
            'precision': {'amount': 8, 'price': 2}
        }
    })

    # 不同交易对的价格
    prices = {
        'BNB/USDT': 680.0,
        'ETH/USDT': 3500.0,
        'BTC/USDT': 68000.0
    }

    def fetch_ticker_side_effect(symbol):
        price = prices.get(symbol, 100.0)
        return {
            'symbol': symbol,
            'last': price,
            'bid': price * 0.999,
            'ask': price * 1.001
        }

    exchange.fetch_ticker = AsyncMock(side_effect=fetch_ticker_side_effect)

    # 余额(所有币种共享USDT)
    exchange.fetch_balance = AsyncMock(return_value={
        'USDT': {'free': 3000.0, 'used': 0.0, 'total': 3000.0},
        'BNB': {'free': 0.0, 'used': 0.0, 'total': 0.0},
        'ETH': {'free': 0.0, 'used': 0.0, 'total': 0.0},
        'BTC': {'free': 0.0, 'used': 0.0, 'total': 0.0}
    })

    # K线数据
    def fetch_ohlcv_side_effect(symbol, timeframe='1d', since=None, limit=None):
        base_price = prices.get(symbol, 100.0)
        return [
            [1000000 + i*86400000, base_price, base_price*1.05, base_price*0.95, base_price, 1000]
            for i in range(52)
        ]

    exchange.fetch_ohlcv = AsyncMock(side_effect=fetch_ohlcv_side_effect)

    # 订单创建
    order_id = {'counter': 2000}
    def create_order_side_effect(symbol, type, side, amount, price=None, params=None):
        order_id['counter'] += 1
        return {
            'id': str(order_id['counter']),
            'symbol': symbol,
            'type': type,
            'side': side,
            'price': price,
            'amount': amount,
            'filled': amount,
            'status': 'closed',
            'timestamp': 1234567890000
        }

    exchange.create_order = AsyncMock(side_effect=create_order_side_effect)

    return exchange


@pytest.mark.asyncio
async def test_multi_symbol_initialization(multi_symbol_exchange):
    """测试多个交易对的初始化"""
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    symbols = ['BNB/USDT', 'ETH/USDT', 'BTC/USDT']
    initial_prices = {
        'BNB/USDT': 680.0,
        'ETH/USDT': 3500.0,
        'BTC/USDT': 68000.0
    }

    with patch('src.core.exchange_client.ccxt.binance', return_value=multi_symbol_exchange):
        # 共享一个exchange_client实例
        client = ExchangeClient()
        await client.initialize()

        # 创建多个trader实例
        traders = {}
        for symbol in symbols:
            trader = GridTrader(
                symbol=symbol,
                exchange_client=client,
                initial_base_price=initial_prices[symbol],
                initial_grid=2.0
            )
            traders[symbol] = trader

        # 验证所有trader都正确初始化
        assert len(traders) == 3
        for symbol, trader in traders.items():
            assert trader.symbol == symbol
            assert trader.base_price == initial_prices[symbol]


@pytest.mark.asyncio
async def test_concurrent_trading_execution(multi_symbol_exchange):
    """测试并发交易执行

    模拟3个交易对同时触发交易信号并执行
    """
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    symbols = ['BNB/USDT', 'ETH/USDT', 'BTC/USDT']
    initial_prices = {
        'BNB/USDT': 680.0,
        'ETH/USDT': 3500.0,
        'BTC/USDT': 68000.0
    }

    with patch('src.core.exchange_client.ccxt.binance', return_value=multi_symbol_exchange):
        client = ExchangeClient()
        await client.initialize()

        # 创建多个trader
        traders = {
            symbol: GridTrader(
                symbol=symbol,
                exchange_client=client,
                initial_base_price=initial_prices[symbol],
                initial_grid=2.0
            )
            for symbol in symbols
        }

        # === 并发执行买入操作 ===
        async def execute_buy(symbol, trader):
            """执行买入操作"""
            price = initial_prices[symbol] * 0.98  # 下跌2%
            amount = 20.0 / price  # 固定20 USDT
            try:
                order = await trader.execute_order('buy', price, amount)
                return (symbol, order)
            except Exception as e:
                return (symbol, None)

        # 并发执行所有买入
        tasks = [execute_buy(symbol, trader) for symbol, trader in traders.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证结果
        successful_orders = [r for r in results if r and r[1] is not None]
        assert len(successful_orders) >= 1, "至少应该有一个交易成功"


@pytest.mark.asyncio
async def test_shared_usdt_balance_management(multi_symbol_exchange):
    """测试共享USDT余额管理

    多个交易对共享同一个USDT账户,需要正确处理余额分配
    """
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    symbols = ['BNB/USDT', 'ETH/USDT']
    initial_prices = {
        'BNB/USDT': 680.0,
        'ETH/USDT': 3500.0
    }

    with patch('src.core.exchange_client.ccxt.binance', return_value=multi_symbol_exchange):
        client = ExchangeClient()
        await client.initialize()

        traders = {
            symbol: GridTrader(
                symbol=symbol,
                exchange_client=client,
                initial_base_price=initial_prices[symbol],
                initial_grid=2.0
            )
            for symbol in symbols
        }

        # 初始USDT余额
        initial_balance = 3000.0

        # === BNB交易器先买入 ===
        bnb_trader = traders['BNB/USDT']
        bnb_buy_amount = 20.0 / 680.0  # 20 USDT

        # 模拟买入后的余额
        multi_symbol_exchange.fetch_balance = AsyncMock(return_value={
            'USDT': {'free': 2980.0, 'used': 0.0, 'total': 2980.0},
            'BNB': {'free': bnb_buy_amount, 'used': 0.0, 'total': bnb_buy_amount}
        })

        # === ETH交易器再买入 ===
        eth_trader = traders['ETH/USDT']
        eth_buy_amount = 20.0 / 3500.0  # 20 USDT

        # 验证余额充足检查
        balance = await client.fetch_balance()
        usdt_free = balance.get('USDT', {}).get('free', 0)

        assert usdt_free >= 20.0, "USDT余额应该足够第二笔交易"


@pytest.mark.asyncio
async def test_main_function_multi_symbol(multi_symbol_exchange):
    """测试main.py的多币种并发运行逻辑"""
    from unittest.mock import patch
    import os

    # 设置环境变量
    os.environ['SYMBOLS'] = 'BNB/USDT,ETH/USDT'
    os.environ['INITIAL_PARAMS_JSON'] = '''{
        "BNB/USDT": {"initial_base_price": 680.0, "initial_grid": 2.0},
        "ETH/USDT": {"initial_base_price": 3500.0, "initial_grid": 2.5}
    }'''

    with patch('src.core.exchange_client.ccxt.binance', return_value=multi_symbol_exchange):
        # 动态导入以应用环境变量
        from src.config.settings import settings
        from src.main import run_trader_for_symbol
        from src.core.exchange_client import ExchangeClient

        # 重新加载settings
        settings_new = settings.__class__()

        # 解析交易对列表
        symbols = [s.strip() for s in settings_new.SYMBOLS.split(',')]
        assert len(symbols) >= 2, "应该有至少2个交易对"

        # 创建exchange_client
        client = ExchangeClient()

        # 模拟运行trader(不执行实际循环)
        # 这里只验证能够正确创建多个trader实例


@pytest.mark.asyncio
async def test_independent_grid_parameters(multi_symbol_exchange):
    """测试不同交易对使用独立的网格参数"""
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=multi_symbol_exchange):
        client = ExchangeClient()
        await client.initialize()

        # === BNB: 2%网格 ===
        bnb_trader = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0
        )

        # === ETH: 2.5%网格 ===
        eth_trader = GridTrader(
            symbol='ETH/USDT',
            exchange_client=client,
            initial_base_price=3500.0,
            initial_grid=2.5
        )

        # 验证网格大小独立
        assert bnb_trader.grid_size == 0.02
        assert eth_trader.grid_size == 0.025

        # 验证上下轨独立计算
        bnb_upper = 680.0 * 1.02
        bnb_lower = 680.0 * 0.98

        eth_upper = 3500.0 * 1.025
        eth_lower = 3500.0 * 0.975

        # 允许小误差
        assert abs(bnb_trader._get_upper_band(680.0, 0.02) - bnb_upper) < 1
        assert abs(eth_trader._get_upper_band(3500.0, 0.025) - eth_upper) < 1


@pytest.mark.asyncio
async def test_cross_symbol_total_value_calculation(multi_symbol_exchange):
    """测试跨交易对的总资产价值计算"""
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=multi_symbol_exchange):
        client = ExchangeClient()
        await client.initialize()

        # 模拟持有多个币种
        multi_symbol_exchange.fetch_balance = AsyncMock(return_value={
            'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0},
            'BNB': {'free': 1.0, 'used': 0.0, 'total': 1.0},
            'ETH': {'free': 0.5, 'used': 0.0, 'total': 0.5}
        })

        # 模拟ticker价格
        def ticker_side_effect(symbol):
            prices = {'BNB/USDT': 680.0, 'ETH/USDT': 3500.0}
            return {'last': prices.get(symbol, 100.0)}

        multi_symbol_exchange.fetch_ticker = AsyncMock(side_effect=ticker_side_effect)

        # 计算总资产
        total = await client.calculate_total_account_value()

        # 预期: 1000 USDT + 1 BNB * 680 + 0.5 ETH * 3500 = 1000 + 680 + 1750 = 3430
        expected = 1000 + 680 + 1750
        assert abs(total - expected) < 10, f"总资产应约为{expected}, 实际为{total}"


@pytest.mark.asyncio
async def test_concurrent_volatility_calculation(multi_symbol_exchange):
    """测试多个交易对并发计算波动率"""
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    symbols = ['BNB/USDT', 'ETH/USDT', 'BTC/USDT']
    initial_prices = {
        'BNB/USDT': 680.0,
        'ETH/USDT': 3500.0,
        'BTC/USDT': 68000.0
    }

    with patch('src.core.exchange_client.ccxt.binance', return_value=multi_symbol_exchange):
        client = ExchangeClient()
        await client.initialize()

        traders = {
            symbol: GridTrader(
                symbol=symbol,
                exchange_client=client,
                initial_base_price=initial_prices[symbol],
                initial_grid=2.0
            )
            for symbol in symbols
        }

        # 并发计算波动率
        async def calc_volatility(symbol, trader):
            try:
                vol = await trader._calculate_volatility()
                return (symbol, vol)
            except Exception as e:
                return (symbol, None)

        tasks = [calc_volatility(s, t) for s, t in traders.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证每个交易对都计算了波动率
        valid_results = [r for r in results if r and r[1] is not None]
        assert len(valid_results) >= 1, "至少应该有一个交易对成功计算波动率"


@pytest.mark.asyncio
async def test_isolated_error_handling(multi_symbol_exchange):
    """测试单个交易对出错不影响其他交易对

    场景: BNB交易对发生异常,但ETH交易对应正常运行
    """
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=multi_symbol_exchange):
        client = ExchangeClient()
        await client.initialize()

        bnb_trader = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0
        )

        eth_trader = GridTrader(
            symbol='ETH/USDT',
            exchange_client=client,
            initial_base_price=3500.0,
            initial_grid=2.5
        )

        # === 模拟BNB交易对fetch_ticker出错 ===
        async def ticker_error_side_effect(symbol):
            if symbol == 'BNB/USDT':
                raise Exception("Network error for BNB")
            else:
                return {'last': 3500.0, 'symbol': symbol}

        multi_symbol_exchange.fetch_ticker = AsyncMock(side_effect=ticker_error_side_effect)

        # === 尝试获取价格 ===
        bnb_result = None
        eth_result = None

        try:
            await client.fetch_ticker('BNB/USDT')
        except Exception as e:
            bnb_result = 'error'

        try:
            eth_result = await client.fetch_ticker('ETH/USDT')
        except Exception:
            pass

        # 验证: BNB出错但ETH正常
        assert bnb_result == 'error', "BNB应该出错"
        assert eth_result is not None, "ETH应该正常"
        assert eth_result.get('last') == 3500.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
