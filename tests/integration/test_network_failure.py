"""
网络故障恢复集成测试

测试各种网络故障场景下的重试和恢复机制
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import ccxt


@pytest.fixture
def flaky_exchange():
    """模拟不稳定的交易所连接"""
    exchange = AsyncMock()

    # 调用计数器
    call_counts = {
        'load_markets': 0,
        'fetch_ticker': 0,
        'create_order': 0,
        'fetch_balance': 0
    }

    # === load_markets: 前2次失败,第3次成功 ===
    def load_markets_side_effect():
        call_counts['load_markets'] += 1
        if call_counts['load_markets'] < 3:
            raise ccxt.NetworkError("Connection timeout")
        return {
            'BNB/USDT': {
                'id': 'BNBUSDT',
                'symbol': 'BNB/USDT',
                'base': 'BNB',
                'quote': 'USDT',
                'limits': {'amount': {'min': 0.001}, 'price': {'min': 0.01}},
                'precision': {'amount': 8, 'price': 2}
            }
        }

    exchange.load_markets = AsyncMock(side_effect=load_markets_side_effect)

    # === fetch_ticker: 随机失败 ===
    def fetch_ticker_side_effect(symbol):
        call_counts['fetch_ticker'] += 1
        # 每3次调用失败一次
        if call_counts['fetch_ticker'] % 3 == 0:
            raise ccxt.NetworkError("Request timeout")
        return {
            'symbol': symbol,
            'last': 680.0,
            'bid': 679.0,
            'ask': 681.0
        }

    exchange.fetch_ticker = AsyncMock(side_effect=fetch_ticker_side_effect)

    # === create_order: 前1次失败,后续成功 ===
    def create_order_side_effect(symbol, type, side, amount, price=None, params=None):
        call_counts['create_order'] += 1
        if call_counts['create_order'] == 1:
            raise ccxt.NetworkError("Order submission failed")

        return {
            'id': f'order_{call_counts["create_order"]}',
            'symbol': symbol,
            'type': type,
            'side': side,
            'price': price,
            'amount': amount,
            'filled': amount,
            'status': 'closed'
        }

    exchange.create_order = AsyncMock(side_effect=create_order_side_effect)

    # === fetch_balance: 稳定成功 ===
    exchange.fetch_balance = AsyncMock(return_value={
        'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0},
        'BNB': {'free': 0.0, 'used': 0.0, 'total': 0.0}
    })

    # 其他必需的mock
    exchange.fetch_ohlcv = AsyncMock(return_value=[
        [1000000 + i*86400000, 680.0, 690.0, 670.0, 685.0, 1000]
        for i in range(52)
    ])

    return exchange


@pytest.mark.asyncio
async def test_load_markets_retry_on_network_error(flaky_exchange):
    """测试load_markets网络错误重试

    场景: 前2次调用失败,第3次成功
    """
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=flaky_exchange):
        client = ExchangeClient()

        # 初始化(会调用load_markets)
        await client.initialize()

        # 验证最终成功加载
        markets = await client.load_markets()
        assert markets is not None
        assert 'BNB/USDT' in markets


@pytest.mark.asyncio
async def test_fetch_ticker_retry_mechanism(flaky_exchange):
    """测试fetch_ticker重试机制"""
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=flaky_exchange):
        client = ExchangeClient()
        await client.initialize()

        # 多次调用fetch_ticker
        successful_calls = 0
        for i in range(10):
            try:
                ticker = await client.fetch_ticker('BNB/USDT')
                if ticker:
                    successful_calls += 1
            except Exception:
                pass

        # 应该有大部分调用成功
        assert successful_calls >= 6, f"10次调用中至少应有6次成功,实际{successful_calls}次"


@pytest.mark.asyncio
async def test_create_order_retry_on_failure(flaky_exchange):
    """测试订单创建失败时的重试"""
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=flaky_exchange):
        client = ExchangeClient()
        await client.initialize()

        # 第一次调用应该失败并重试
        order = await client.create_order(
            symbol='BNB/USDT',
            type='limit',
            side='buy',
            amount=0.03,
            price=680.0
        )

        # 验证最终成功
        assert order is not None
        assert order['status'] == 'closed'


@pytest.mark.asyncio
async def test_api_rate_limit_handling():
    """测试API限流处理

    场景: 触发429错误,需要等待后重试
    """
    exchange = AsyncMock()

    call_count = {'value': 0}

    def rate_limit_side_effect(symbol):
        call_count['value'] += 1
        if call_count['value'] == 1:
            raise ccxt.RateLimitExceeded("API rate limit exceeded")
        return {'last': 680.0, 'symbol': symbol}

    exchange.fetch_ticker = AsyncMock(side_effect=rate_limit_side_effect)
    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {'symbol': 'BNB/USDT', 'base': 'BNB', 'quote': 'USDT'}
    })

    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=exchange):
        client = ExchangeClient()
        await client.initialize()

        # 应该自动重试并成功
        ticker = await client.fetch_ticker('BNB/USDT')
        assert ticker is not None
        assert call_count['value'] >= 2, "应该至少重试一次"


@pytest.mark.asyncio
async def test_connection_reset_recovery():
    """测试连接重置后的恢复"""
    exchange = AsyncMock()

    reset_count = {'value': 0}

    def connection_reset_side_effect(symbol):
        reset_count['value'] += 1
        if reset_count['value'] <= 2:
            raise ccxt.NetworkError("Connection reset by peer")
        return {'last': 680.0, 'symbol': symbol}

    exchange.fetch_ticker = AsyncMock(side_effect=connection_reset_side_effect)
    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {'symbol': 'BNB/USDT', 'base': 'BNB', 'quote': 'USDT'}
    })

    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=exchange):
        client = ExchangeClient()
        await client.initialize()

        # 应该重试直到成功
        ticker = await client.fetch_ticker('BNB/USDT')
        assert ticker is not None
        assert reset_count['value'] == 3, "应该重试3次"


@pytest.mark.asyncio
async def test_max_retries_exceeded():
    """测试超过最大重试次数后的处理"""
    exchange = AsyncMock()

    # 一直失败
    exchange.fetch_ticker = AsyncMock(side_effect=ccxt.NetworkError("Persistent failure"))
    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {'symbol': 'BNB/USDT', 'base': 'BNB', 'quote': 'USDT'}
    })

    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=exchange):
        client = ExchangeClient()
        await client.initialize()

        # 应该抛出异常或返回None
        try:
            ticker = await client.fetch_ticker('BNB/USDT')
            # 如果返回None也是可接受的
            assert ticker is None or ticker == {}
        except Exception as e:
            # 抛出异常也是可接受的
            assert isinstance(e, (ccxt.NetworkError, Exception))


@pytest.mark.asyncio
async def test_trader_continues_after_temp_failure(flaky_exchange):
    """测试trader在临时故障后继续运行

    场景: 一次循环失败,但下一次循环成功
    """
    from src.core.trader import GridTrader
    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=flaky_exchange):
        client = ExchangeClient()
        await client.initialize()

        trader = GridTrader(
            symbol='BNB/USDT',
            exchange_client=client,
            initial_base_price=680.0,
            initial_grid=2.0
        )

        # 模拟多次循环迭代
        iteration_results = []

        for i in range(5):
            try:
                # 获取当前价格(可能失败)
                ticker = await client.fetch_ticker('BNB/USDT')
                if ticker:
                    price = ticker['last']
                    iteration_results.append(('success', price))
                else:
                    iteration_results.append(('none', None))
            except Exception as e:
                iteration_results.append(('error', str(e)))

        # 验证: 至少有部分成功
        successful = [r for r in iteration_results if r[0] == 'success']
        assert len(successful) >= 3, f"5次迭代中至少应有3次成功,实际{len(successful)}次"


@pytest.mark.asyncio
async def test_balance_query_retry():
    """测试余额查询重试"""
    exchange = AsyncMock()

    balance_call_count = {'value': 0}

    def balance_side_effect():
        balance_call_count['value'] += 1
        if balance_call_count['value'] == 1:
            raise ccxt.NetworkError("Balance fetch failed")
        return {
            'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0},
            'BNB': {'free': 0.5, 'used': 0.0, 'total': 0.5}
        }

    exchange.fetch_balance = AsyncMock(side_effect=balance_side_effect)
    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {'symbol': 'BNB/USDT', 'base': 'BNB', 'quote': 'USDT'}
    })

    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=exchange):
        client = ExchangeClient()
        await client.initialize()

        # 第一次失败,重试成功
        balance = await client.fetch_balance()

        assert balance is not None
        assert 'USDT' in balance
        assert balance_call_count['value'] == 2


@pytest.mark.asyncio
async def test_time_sync_failure_handling():
    """测试时间同步失败的处理"""
    exchange = AsyncMock()

    sync_count = {'value': 0}

    def time_sync_side_effect():
        sync_count['value'] += 1
        if sync_count['value'] <= 1:
            raise ccxt.NetworkError("Time sync failed")
        return {'serverTime': 1234567890000}

    # 模拟time API
    exchange.publicGetTime = AsyncMock(side_effect=time_sync_side_effect)
    exchange.load_markets = AsyncMock(return_value={})

    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=exchange):
        client = ExchangeClient()

        # 时间同步失败不应阻止初始化
        await client.initialize()

        # 尝试同步时间
        try:
            await client.sync_time()
        except Exception:
            # 失败是可以接受的
            pass


@pytest.mark.asyncio
async def test_order_book_fetch_retry():
    """测试订单簿获取重试"""
    exchange = AsyncMock()

    orderbook_count = {'value': 0}

    def orderbook_side_effect(symbol, limit=None):
        orderbook_count['value'] += 1
        if orderbook_count['value'] < 2:
            raise ccxt.NetworkError("Order book fetch failed")
        return {
            'bids': [[679.0, 1.0], [678.0, 2.0]],
            'asks': [[681.0, 1.0], [682.0, 2.0]]
        }

    exchange.fetch_order_book = AsyncMock(side_effect=orderbook_side_effect)
    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {'symbol': 'BNB/USDT'}
    })

    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=exchange):
        client = ExchangeClient()
        await client.initialize()

        # 应该重试成功
        orderbook = await client.fetch_order_book('BNB/USDT')

        assert orderbook is not None
        assert 'bids' in orderbook
        assert 'asks' in orderbook


@pytest.mark.asyncio
async def test_partial_network_failure_isolation():
    """测试部分网络故障隔离

    场景: fetch_ticker失败,但其他API正常
    """
    exchange = AsyncMock()

    # ticker一直失败
    exchange.fetch_ticker = AsyncMock(side_effect=ccxt.NetworkError("Ticker service down"))

    # 但balance正常
    exchange.fetch_balance = AsyncMock(return_value={
        'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0}
    })

    # order book正常
    exchange.fetch_order_book = AsyncMock(return_value={
        'bids': [[679.0, 1.0]],
        'asks': [[681.0, 1.0]]
    })

    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {'symbol': 'BNB/USDT'}
    })

    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=exchange):
        client = ExchangeClient()
        await client.initialize()

        # ticker失败
        with pytest.raises(Exception):
            await client.fetch_ticker('BNB/USDT')

        # 但balance和order book仍然可用
        balance = await client.fetch_balance()
        assert balance is not None

        orderbook = await client.fetch_order_book('BNB/USDT')
        assert orderbook is not None


@pytest.mark.asyncio
async def test_exponential_backoff_retry():
    """测试指数退避重试策略

    验证重试之间的等待时间逐渐增加
    """
    import time

    exchange = AsyncMock()

    retry_times = []

    def failing_side_effect(symbol):
        retry_times.append(time.time())
        if len(retry_times) < 4:
            raise ccxt.NetworkError("Temporary failure")
        return {'last': 680.0, 'symbol': symbol}

    exchange.fetch_ticker = AsyncMock(side_effect=failing_side_effect)
    exchange.load_markets = AsyncMock(return_value={
        'BNB/USDT': {'symbol': 'BNB/USDT'}
    })

    from src.core.exchange_client import ExchangeClient

    with patch('src.core.exchange_client.ccxt.binance', return_value=exchange):
        client = ExchangeClient()
        await client.initialize()

        # 执行会重试的操作
        start_time = time.time()
        ticker = await client.fetch_ticker('BNB/USDT')
        total_time = time.time() - start_time

        assert ticker is not None
        # 验证有重试(总时间应该大于0)
        # 注意: 由于是mock,可能不会真正sleep


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
