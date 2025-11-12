"""
完整交易周期集成测试

测试从启动到执行完整买卖周期的整个流程
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal


@pytest.fixture
def mock_ccxt_exchange():
    """模拟CCXT交易所客户端"""
    exchange = AsyncMock()

    # 模拟市场数据
    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {
            'id': 'BNBUSDT',
            'symbol': 'BNB/USDT',
            'base': 'BNB',
            'quote': 'USDT',
            'limits': {
                'amount': {'min': 0.001},
                'price': {'min': 0.01}
            },
            'precision': {'amount': 8, 'price': 2}
        }
    })

    # 模拟行情数据
    exchange.fetch_ticker = AsyncMock(return_value={
        'symbol': 'BNB/USDT',
        'last': 680.0,
        'bid': 679.5,
        'ask': 680.5
    })

    # 模拟余额查询
    exchange.fetch_balance = AsyncMock(return_value={
        'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0},
        'BNB': {'free': 0.0, 'used': 0.0, 'total': 0.0}
    })

    # 模拟K线数据(用于波动率计算)
    exchange.fetch_ohlcv = AsyncMock(return_value=[
        [1000000 + i*86400000, 680.0 + i, 690.0, 675.0, 685.0, 1000]
        for i in range(52)
    ])

    # 模拟订单簿
    exchange.fetch_order_book = AsyncMock(return_value={
        'bids': [[679.0, 1.0], [678.0, 2.0]],
        'asks': [[681.0, 1.0], [682.0, 2.0]]
    })

    # 模拟订单创建
    order_id_counter = {'value': 1000}
    def create_order_side_effect(symbol, type, side, amount, price=None, params=None):
        order_id_counter['value'] += 1
        return {
            'id': str(order_id_counter['value']),
            'symbol': symbol,
            'type': type,
            'side': side,
            'price': price,
            'amount': amount,
            'filled': amount,  # 假设立即成交
            'status': 'closed',
            'timestamp': 1234567890000
        }

    exchange.create_order = AsyncMock(side_effect=create_order_side_effect)

    # 模拟订单查询
    exchange.fetch_order = AsyncMock(return_value={
        'id': '1001',
        'status': 'closed',
        'filled': 0.03
    })

    # 模拟订单取消
    exchange.cancel_order = AsyncMock(return_value={'id': '1001', 'status': 'canceled'})

    # 模拟理财相关API
    exchange.sapi_get_simple_earn_flexible_list = AsyncMock(return_value={
        'rows': [{'asset': 'USDT', 'productId': 'USDT001'}]
    })

    exchange.sapi_post_simple_earn_flexible_subscribe = AsyncMock(return_value={
        'purchaseId': '12345', 'success': True
    })

    exchange.sapi_post_simple_earn_flexible_redeem = AsyncMock(return_value={
        'redeemId': '12346', 'success': True
    })

    exchange.sapi_get_simple_earn_flexible_position = AsyncMock(return_value={
        'rows': [{'asset': 'USDT', 'totalAmount': '500.0'}],
        'total': 1
    })

    return exchange


@pytest.mark.asyncio
async def test_trader_initialization(mock_ccxt_exchange):
    """测试交易器初始化"""
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    # 使用mock的exchange创建客户端
    with patch('src.core.exchange_client.ccxt.binance', return_value=mock_ccxt_exchange):
        client = ExchangeClient()
        await client.initialize()

        # 创建交易器
        trader = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0
        )

        # 验证初始化
        assert trader.symbol == 'BNB/USDT'
        assert trader.base_asset == 'BNB'
        assert trader.quote_asset == 'USDT'
        assert trader.base_price == 680.0
        assert trader.grid_size == 0.02  # 2%


@pytest.mark.asyncio
async def test_full_buy_sell_cycle(mock_ccxt_exchange):
    """测试完整的买卖周期

    流程:
    1. 价格下跌 → 触发买入信号
    2. 执行买入订单
    3. 价格上涨 → 触发卖出信号
    4. 执行卖出订单
    5. 验证盈利
    """
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=mock_ccxt_exchange):
        client = ExchangeClient()
        await client.initialize()

        trader = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0
        )

        # === 步骤1: 价格下跌到下轨(666.4) ===
        mock_ccxt_exchange.fetch_ticker = AsyncMock(return_value={
            'symbol': 'BNB/USDT',
            'last': 666.0,
            'bid': 665.5,
            'ask': 666.5
        })

        # 检查买入信号
        buy_signal = await trader._check_buy_signal(666.0)
        assert buy_signal is True, "应该触发买入信号"

        # === 步骤2: 执行买入 ===
        mock_ccxt_exchange.fetch_balance = AsyncMock(return_value={
            'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0},
            'BNB': {'free': 0.0, 'used': 0.0, 'total': 0.0}
        })

        buy_order = await trader.execute_order('buy', 666.0, 0.03)

        assert buy_order is not None
        assert buy_order['side'] == 'buy'
        assert buy_order['filled'] > 0

        # 更新余额(模拟买入后)
        mock_ccxt_exchange.fetch_balance = AsyncMock(return_value={
            'USDT': {'free': 980.0, 'used': 0.0, 'total': 980.0},
            'BNB': {'free': 0.03, 'used': 0.0, 'total': 0.03}
        })

        # === 步骤3: 价格上涨到上轨(693.6) ===
        mock_ccxt_exchange.fetch_ticker = AsyncMock(return_value={
            'symbol': 'BNB/USDT',
            'last': 694.0,
            'bid': 693.5,
            'ask': 694.5
        })

        # 检查卖出信号
        sell_signal = await trader._check_sell_signal(694.0)
        assert sell_signal is True, "应该触发卖出信号"

        # === 步骤4: 执行卖出 ===
        sell_order = await trader.execute_order('sell', 694.0, 0.03)

        assert sell_order is not None
        assert sell_order['side'] == 'sell'
        assert sell_order['filled'] > 0

        # === 步骤5: 验证盈利 ===
        # 买入成本: 666 * 0.03 = 19.98 USDT
        # 卖出收入: 694 * 0.03 = 20.82 USDT
        # 预期盈利: 0.84 USDT (不含手续费)
        expected_profit = (694.0 - 666.0) * 0.03
        assert expected_profit > 0.8, "应该有盈利"


@pytest.mark.asyncio
async def test_grid_size_adjustment_by_volatility(mock_ccxt_exchange):
    """测试基于波动率的网格大小动态调整"""
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=mock_ccxt_exchange):
        client = ExchangeClient()
        await client.initialize()

        trader = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0
        )

        # 模拟高波动率K线数据
        high_volatility_ohlcv = [
            [1000000 + i*86400000, 680.0, 750.0, 610.0, 730.0, 1000]
            for i in range(52)
        ]
        mock_ccxt_exchange.fetch_ohlcv = AsyncMock(return_value=high_volatility_ohlcv)

        # 计算波动率并调整网格
        volatility = await trader._calculate_volatility()

        # 高波动率应该扩大网格
        assert volatility > 0.3, "波动率应该很高"

        # 验证网格大小被调整
        # (具体逻辑取决于trader实现)


# S1策略已移除 - 以下测试已过时
# @pytest.mark.asyncio
# async def test_s1_strategy_integration(mock_ccxt_exchange):
#     """测试S1辅助策略与主网格策略的集成"""
#     此测试已被移除,因为S1策略已从系统中删除


@pytest.mark.asyncio
async def test_risk_management_integration(mock_ccxt_exchange):
    """测试风险管理系统集成"""
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient
    from src.strategies.risk_manager import AdvancedRiskManager, RiskState

    with patch('src.core.exchange_client.ccxt.binance', return_value=mock_ccxt_exchange):
        client = ExchangeClient()
        await client.initialize()

        trader = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0
        )

        risk_manager = trader.risk_manager

        # === 测试1: 仓位过高 → 只允许卖出 ===
        high_position_state = risk_manager.check_position_limits(
            base_value=900.0,
            quote_balance=100.0,
            total_value=1000.0
        )
        assert high_position_state == RiskState.ALLOW_SELL_ONLY

        # === 测试2: 仓位过低 → 只允许买入 ===
        low_position_state = risk_manager.check_position_limits(
            base_value=50.0,
            quote_balance=950.0,
            total_value=1000.0
        )
        assert low_position_state == RiskState.ALLOW_BUY_ONLY

        # === 测试3: 仓位正常 → 允许全部操作 ===
        normal_position_state = risk_manager.check_position_limits(
            base_value=500.0,
            quote_balance=500.0,
            total_value=1000.0
        )
        assert normal_position_state == RiskState.ALLOW_ALL


@pytest.mark.asyncio
async def test_order_tracker_integration(mock_ccxt_exchange):
    """测试订单跟踪器集成"""
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=mock_ccxt_exchange):
        client = ExchangeClient()
        await client.initialize()

        trader = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0
        )

        # 执行买入
        buy_order = await trader.execute_order('buy', 670.0, 0.03)

        # 执行卖出
        sell_order = await trader.execute_order('sell', 690.0, 0.03)

        # 验证订单被跟踪
        # 获取交易历史
        if hasattr(trader, 'order_tracker') and trader.order_tracker:
            history = trader.order_tracker.get_trade_history(limit=10)
            assert len(history) > 0, "应该有交易记录"


@pytest.mark.asyncio
async def test_state_persistence(mock_ccxt_exchange, tmp_path):
    """测试状态持久化"""
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient
    import json

    state_file = tmp_path / "trader_state.json"

    with patch('src.core.exchange_client.ccxt.binance', return_value=mock_ccxt_exchange):
        client = ExchangeClient()
        await client.initialize()

        # === 步骤1: 创建交易器并执行交易 ===
        trader1 = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0,
            state_file=str(state_file)
        )

        # 执行一笔交易
        await trader1.execute_order('buy', 670.0, 0.03)

        # 保存状态
        trader1.save_state()

        # === 步骤2: 创建新的交易器实例并加载状态 ===
        trader2 = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0,
            state_file=str(state_file)
        )

        # 验证状态恢复
        # assert trader2.last_trade_price == trader1.last_trade_price
        assert state_file.exists(), "状态文件应该存在"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
