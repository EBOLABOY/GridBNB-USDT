"""
pytest 配置文件
为所有测试提供共享的fixtures和配置
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# 确保可以导入 src 模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 在导入任何src模块之前,设置测试环境变量
os.environ['PYTEST_CURRENT_TEST'] = 'true'
os.environ['BINANCE_API_KEY'] = 'test_' + 'x' * 60  # 满足64位长度要求的测试密钥
os.environ['BINANCE_API_SECRET'] = 'test_' + 'x' * 60
os.environ['SYMBOLS'] = 'BNB/USDT'
os.environ['MIN_TRADE_AMOUNT'] = '20.0'
os.environ['INITIAL_GRID'] = '2.0'


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """会话级别的测试环境设置"""
    # 设置测试环境标志
    os.environ['TESTING'] = '1'

    yield

    # 清理
    os.environ.pop('TESTING', None)


@pytest.fixture
def mock_exchange_client():
    """创建模拟的ExchangeClient实例"""
    from unittest.mock import AsyncMock, Mock

    client = Mock()
    client.client = Mock()

    # 模拟基础方法
    client.fetch_ticker = AsyncMock(return_value={'last': 680.0})
    client.fetch_balance = AsyncMock(return_value={
        'USDT': {'free': 1000.0, 'total': 1000.0},
        'BNB': {'free': 0.5, 'total': 0.5}
    })
    client.create_order = AsyncMock(return_value={
        'id': '123456',
        'status': 'closed',
        'filled': 0.0294
    })
    client.fetch_ohlcv = AsyncMock(return_value=[
        [1000000, 680.0, 690.0, 675.0, 685.0, 1000]
    ])

    # 模拟理财相关方法
    client.transfer_to_savings = AsyncMock(return_value=True)
    client.transfer_to_spot = AsyncMock(return_value=True)
    client.get_savings_balance = AsyncMock(return_value=500.0)

    return client


@pytest.fixture
def mock_trader():
    """创建模拟的GridTrader实例"""
    from unittest.mock import Mock, AsyncMock

    trader = Mock()
    trader.symbol = 'BNB/USDT'
    trader.base_asset = 'BNB'
    trader.quote_asset = 'USDT'
    trader.base_price = 680.0
    trader.grid_size = 0.02
    trader.last_trade_price = 680.0
    trader.last_trade_time = 1234567890
    trader.total_profit = 10.5

    # 模拟异步方法
    trader.main_loop = AsyncMock()
    trader.execute_order = AsyncMock()

    return trader


@pytest.fixture
def sample_trade_data():
    """提供样本交易数据"""
    return {
        'timestamp': '2025-10-21 10:00:00',
        'side': 'buy',
        'price': 680.0,
        'amount': 0.0294,
        'order_id': '123456',
        'profit': 0.5
    }


@pytest.fixture
def sample_config():
    """提供测试配置"""
    return {
        'symbol': 'BNB/USDT',
        'initial_base_price': 680.0,
        'initial_grid': 2.0,
        'min_trade_amount': 20.0,
        'initial_principal': 1000.0
    }
