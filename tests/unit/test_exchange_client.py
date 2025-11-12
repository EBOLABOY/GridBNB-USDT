"""
ExchangeClient 单元测试

测试交易所客户端的核心功能,包括:
- 初始化和配置
- 市场数据获取
- 订单操作
- 余额查询
- 理财功能
- 时间同步
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
import time

from src.core.exchange_client import ExchangeClient


class TestExchangeClientInit:
    """测试 ExchangeClient 初始化"""

    @patch('src.core.exchange_client.settings')
    @patch('src.core.exchange_client.ccxt.binance')
    def test_init_basic(self, mock_binance, mock_settings):
        """测试基础初始化"""
        mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
        mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
        mock_settings.DEBUG_MODE = False
        mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}

        with patch.dict('os.environ', {}, clear=True):
            client = ExchangeClient()

            assert client.markets_loaded is False
            assert client.time_diff == 0
            assert client.cache_ttl == 30
            mock_binance.assert_called_once()

    @patch('src.core.exchange_client.settings')
    @patch('src.core.exchange_client.ccxt.binance')
    @patch.dict('os.environ', {'HTTP_PROXY': 'http://proxy.example.com:8080'})
    def test_init_with_proxy(self, mock_binance, mock_settings):
        """测试带代理的初始化"""
        mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
        mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
        mock_settings.DEBUG_MODE = False
        mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}

        client = ExchangeClient()

        # 验证 binance 被调用时传入了代理配置
        call_kwargs = mock_binance.call_args[0][0]
        assert call_kwargs['aiohttp_proxy'] == 'http://proxy.example.com:8080'


class TestMarketData:
    """测试市场数据获取功能"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                yield client

    @pytest.mark.asyncio
    async def test_load_markets_success(self, mock_client):
        """测试成功加载市场数据"""
        mock_client.exchange.load_markets = AsyncMock()
        mock_client.sync_time = AsyncMock()

        result = await mock_client.load_markets()

        assert result is True
        assert mock_client.markets_loaded is True
        mock_client.exchange.load_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_markets_retry(self, mock_client):
        """测试加载市场数据失败后重试"""
        # 前两次失败,第三次成功
        mock_client.exchange.load_markets = AsyncMock(
            side_effect=[Exception("Network error"), Exception("Timeout"), None]
        )
        mock_client.sync_time = AsyncMock()

        result = await mock_client.load_markets()

        assert result is True
        assert mock_client.exchange.load_markets.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_ticker_success(self, mock_client):
        """测试成功获取行情数据"""
        mock_ticker = {
            'symbol': 'BNB/USDT',
            'last': 683.5,
            'bid': 683.4,
            'ask': 683.6,
            'high': 690.0,
            'low': 675.0
        }

        mock_client.exchange.market = MagicMock(return_value={'id': 'BNBUSDT'})
        mock_client.exchange.fetch_ticker = AsyncMock(return_value=mock_ticker)

        ticker = await mock_client.fetch_ticker('BNB/USDT')

        assert ticker['last'] == 683.5
        assert ticker['symbol'] == 'BNB/USDT'

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_with_limit(self, mock_client):
        """测试获取K线数据"""
        mock_ohlcv = [
            [1634000000000, 680.0, 685.0, 678.0, 683.0, 1000.0],
            [1634003600000, 683.0, 688.0, 681.0, 686.0, 1200.0]
        ]

        mock_client.exchange.fetch_ohlcv = AsyncMock(return_value=mock_ohlcv)

        ohlcv = await mock_client.fetch_ohlcv('BNB/USDT', '1h', limit=100)

        assert len(ohlcv) == 2
        assert ohlcv[0][4] == 683.0  # 收盘价
        mock_client.exchange.fetch_ohlcv.assert_called_once()


class TestBalance:
    """测试余额查询功能"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}
            mock_settings.ENABLE_SAVINGS_FUNCTION = True

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                yield client

    @pytest.mark.asyncio
    async def test_fetch_balance_with_cache(self, mock_client):
        """测试余额查询缓存机制"""
        mock_balance = {
            'free': {'USDT': 1000.0, 'BNB': 10.0},
            'used': {'USDT': 0.0, 'BNB': 0.0},
            'total': {'USDT': 1000.0, 'BNB': 10.0}
        }

        mock_client.exchange.fetch_balance = AsyncMock(return_value=mock_balance)

        # 第一次调用
        balance1 = await mock_client.fetch_balance()
        assert balance1['total']['USDT'] == 1000.0

        # 第二次调用应该使用缓存
        balance2 = await mock_client.fetch_balance()
        assert balance2['total']['USDT'] == 1000.0

        # exchange.fetch_balance 应该只被调用一次
        assert mock_client.exchange.fetch_balance.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_funding_balance_disabled(self, mock_client):
        """测试理财功能关闭时的行为"""
        with patch('src.core.exchange_client.settings.ENABLE_SAVINGS_FUNCTION', False):
            balance = await mock_client.fetch_funding_balance()

            assert balance == {}
            assert mock_client.funding_balance_cache['data'] == {}

    @pytest.mark.asyncio
    async def test_fetch_funding_balance_pagination(self, mock_client):
        """测试理财余额分页获取"""
        # 模拟分页数据 - 第一页有100条(触发分页),第二页少于100条(结束)
        mock_page1 = {
            'rows': [
                {'asset': 'USDT', 'totalAmount': '500.0'},
                {'asset': 'BNB', 'totalAmount': '5.0'}
            ] + [{'asset': 'FILLER', 'totalAmount': '1.0'}] * 98  # 补齐到100条
        }
        mock_page2 = {
            'rows': [
                {'asset': 'USDT', 'totalAmount': '300.0'},
                {'asset': 'ETH', 'totalAmount': '2.0'}
            ]  # 少于100条,触发结束条件
        }

        mock_client.exchange.sapi_get_simple_earn_flexible_position = AsyncMock(
            side_effect=[mock_page1, mock_page2]
        )

        balance = await mock_client.fetch_funding_balance()

        # 验证余额合并
        assert balance['USDT'] == 800.0  # 500 + 300
        assert balance['BNB'] == 5.0
        assert balance['ETH'] == 2.0
        assert balance['FILLER'] == 98.0  # 98条填充数据


class TestOrders:
    """测试订单操作功能"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                client.time_diff = 0
                yield client

    @pytest.mark.asyncio
    async def test_create_order_success(self, mock_client):
        """测试成功创建订单"""
        mock_order = {
            'id': '12345',
            'symbol': 'BNB/USDT',
            'type': 'limit',
            'side': 'buy',
            'price': 683.0,
            'amount': 1.0,
            'status': 'open'
        }

        mock_client.sync_time = AsyncMock()
        mock_client.exchange.create_order = AsyncMock(return_value=mock_order)

        order = await mock_client.create_order('BNB/USDT', 'limit', 'buy', 1.0, 683.0)

        assert order['id'] == '12345'
        assert order['side'] == 'buy'
        mock_client.sync_time.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_market_order(self, mock_client):
        """测试创建市价单"""
        mock_order = {
            'id': '67890',
            'symbol': 'BNB/USDT',
            'type': 'market',
            'side': 'buy',
            'amount': 1.0,
            'status': 'closed'
        }

        mock_client.sync_time = AsyncMock()
        mock_client.exchange.create_order = AsyncMock(return_value=mock_order)

        order = await mock_client.create_market_order('BNB/USDT', 'buy', 1.0)

        assert order['type'] == 'market'
        # 验证 create_order 被调用时 price 参数为 None
        call_args = mock_client.exchange.create_order.call_args
        assert call_args[1]['price'] is None

    @pytest.mark.asyncio
    async def test_cancel_order(self, mock_client):
        """测试取消订单"""
        mock_client.exchange.cancel_order = AsyncMock(return_value={'status': 'canceled'})

        result = await mock_client.cancel_order('12345', 'BNB/USDT')

        assert result['status'] == 'canceled'
        mock_client.exchange.cancel_order.assert_called_once()


class TestSavingsOperations:
    """测试理财功能"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'USDT': 2, 'BNB': 4, 'DEFAULT': 2}

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                client.time_diff = 0
                yield client

    @pytest.mark.asyncio
    async def test_get_flexible_product_id(self, mock_client):
        """测试获取理财产品ID"""
        mock_products = {
            'rows': [
                {'asset': 'USDT', 'productId': 'USDT001', 'status': 'PURCHASING'},
                {'asset': 'BNB', 'productId': 'BNB001', 'status': 'SOLD_OUT'}
            ]
        }

        mock_client.exchange.sapi_get_simple_earn_flexible_list = AsyncMock(
            return_value=mock_products
        )

        product_id = await mock_client.get_flexible_product_id('USDT')

        assert product_id == 'USDT001'

    @pytest.mark.asyncio
    async def test_transfer_to_savings(self, mock_client):
        """测试申购理财"""
        mock_client.get_flexible_product_id = AsyncMock(return_value='USDT001')
        mock_client.exchange.sapi_post_simple_earn_flexible_subscribe = AsyncMock(
            return_value={'success': True}
        )

        result = await mock_client.transfer_to_savings('USDT', 1000.5)

        assert result['success'] is True
        # 验证金额格式化(USDT精度为2)
        call_params = mock_client.exchange.sapi_post_simple_earn_flexible_subscribe.call_args[0][0]
        assert call_params['amount'] == '1000.50'

    @pytest.mark.asyncio
    async def test_transfer_to_spot(self, mock_client):
        """测试赎回理财"""
        mock_client.get_flexible_product_id = AsyncMock(return_value='BNB001')
        mock_client.exchange.sapi_post_simple_earn_flexible_redeem = AsyncMock(
            return_value={'success': True}
        )

        result = await mock_client.transfer_to_spot('BNB', 10.123456)

        assert result['success'] is True
        # 验证金额格式化(BNB精度为4)
        call_params = mock_client.exchange.sapi_post_simple_earn_flexible_redeem.call_args[0][0]
        assert call_params['amount'] == '10.1235'  # 四舍五入到4位小数


class TestTimeSync:
    """测试时间同步功能"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                yield client

    @pytest.mark.asyncio
    async def test_sync_time(self, mock_client):
        """测试时间同步"""
        server_time = 1634000000000
        local_time = 1633999990000
        expected_diff = server_time - local_time

        mock_client.exchange.fetch_time = AsyncMock(return_value=server_time)

        with patch('time.time', return_value=local_time / 1000):
            await mock_client.sync_time()

        assert mock_client.time_diff == expected_diff

    @pytest.mark.asyncio
    async def test_periodic_time_sync_start(self, mock_client):
        """测试启动周期性时间同步"""
        mock_client.sync_time = AsyncMock()

        await mock_client.start_periodic_time_sync(interval_seconds=1)

        assert mock_client.time_sync_task is not None
        assert not mock_client.time_sync_task.done()

        # 清理
        await mock_client.stop_periodic_time_sync()

    @pytest.mark.asyncio
    async def test_periodic_time_sync_stop(self, mock_client):
        """测试停止周期性时间同步"""
        mock_client.sync_time = AsyncMock()

        await mock_client.start_periodic_time_sync(interval_seconds=1)
        await mock_client.stop_periodic_time_sync()

        assert mock_client.time_sync_task is None


class TestUtilityMethods:
    """测试工具方法"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {
                'USDT': 2,
                'BNB': 4,
                'ETH': 6,
                'DEFAULT': 2
            }

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                yield client

    def test_format_savings_amount(self, mock_client):
        """测试理财金额格式化"""
        # USDT精度为2
        assert mock_client._format_savings_amount('USDT', 1000.123) == '1000.12'

        # BNB精度为4
        assert mock_client._format_savings_amount('BNB', 10.123456) == '10.1235'

        # ETH精度为6
        assert mock_client._format_savings_amount('ETH', 3.123456789) == '3.123457'

        # 未配置的资产使用默认精度
        assert mock_client._format_savings_amount('DOGE', 100.999) == '101.00'

    def test_is_funding_balance_changed_significantly(self, mock_client):
        """测试理财余额重大变化检测"""
        old_balances = {'USDT': 1000.0, 'BNB': 10.0}

        # 微小变化(利息) - 不应该触发
        new_balances_minor = {'USDT': 1000.05, 'BNB': 10.001}
        assert not mock_client._is_funding_balance_changed_significantly(
            old_balances, new_balances_minor
        )

        # 重大变化 - 应该触发
        new_balances_major = {'USDT': 1050.0, 'BNB': 10.0}
        assert mock_client._is_funding_balance_changed_significantly(
            old_balances, new_balances_major
        )

        # 新增资产 - 应该触发
        new_balances_new_asset = {'USDT': 1000.0, 'BNB': 10.0, 'ETH': 1.0}
        assert mock_client._is_funding_balance_changed_significantly(
            old_balances, new_balances_new_asset
        )

        # 完全相同 - 不应该触发
        assert not mock_client._is_funding_balance_changed_significantly(
            old_balances, old_balances.copy()
        )


class TestCalculateTotalValue:
    """测试总资产计算功能"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                yield client

    @pytest.mark.asyncio
    async def test_calculate_total_account_value(self, mock_client):
        """测试计算总资产价值"""
        # Mock 现货余额
        mock_spot_balance = {
            'total': {
                'USDT': 1000.0,
                'BNB': 10.0,
                'LDBNB': 5.0  # 理财凭证,应该被排除
            }
        }

        # Mock 理财余额
        mock_funding_balance = {
            'USDT': 500.0,
            'BNB': 5.0
        }

        # Mock BNB价格
        mock_bnb_ticker = {'last': 680.0}

        mock_client.fetch_balance = AsyncMock(return_value=mock_spot_balance)
        mock_client.fetch_funding_balance = AsyncMock(return_value=mock_funding_balance)
        mock_client.fetch_ticker = AsyncMock(return_value=mock_bnb_ticker)

        total_value = await mock_client.calculate_total_account_value('USDT')

        # 计算期望值:
        # USDT: 1000 (现货) + 500 (理财) = 1500
        # BNB: 10 (现货) + 5 (理财) = 15, 价值 = 15 * 680 = 10200
        # 总计: 1500 + 10200 = 11700
        # 注意: LDBNB 应该被排除,不参与计算
        expected_value = 1500.0 + (15.0 * 680.0)

        assert abs(total_value - expected_value) < 0.01  # 允许小的浮点误差


class TestAdditionalMethods:
    """测试额外的交易所方法"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                yield client

    @pytest.mark.asyncio
    async def test_fetch_order_book(self, mock_client):
        """测试获取订单簿数据"""
        mock_orderbook = {
            'bids': [[683.0, 10.0], [682.5, 5.0]],
            'asks': [[683.5, 8.0], [684.0, 12.0]],
            'timestamp': 1634000000000
        }

        mock_client.exchange.market = MagicMock(return_value={'id': 'BNBUSDT'})
        mock_client.exchange.fetch_order_book = AsyncMock(return_value=mock_orderbook)

        orderbook = await mock_client.fetch_order_book('BNB/USDT', limit=5)

        assert len(orderbook['bids']) == 2
        assert len(orderbook['asks']) == 2
        assert orderbook['bids'][0][0] == 683.0
        mock_client.exchange.fetch_order_book.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_my_trades(self, mock_client):
        """测试获取成交记录"""
        mock_trades = [
            {
                'id': '123',
                'timestamp': 1634000000000,
                'symbol': 'BNB/USDT',
                'side': 'buy',
                'price': 683.0,
                'amount': 1.0
            },
            {
                'id': '124',
                'timestamp': 1634003600000,
                'symbol': 'BNB/USDT',
                'side': 'sell',
                'price': 685.0,
                'amount': 1.0
            }
        ]

        mock_client.markets_loaded = True
        mock_client.exchange.market = MagicMock(return_value={'id': 'BNBUSDT'})
        mock_client.exchange.fetch_my_trades = AsyncMock(return_value=mock_trades)

        trades = await mock_client.fetch_my_trades('BNB/USDT', limit=10)

        assert len(trades) == 2
        assert trades[0]['side'] == 'buy'
        assert trades[1]['side'] == 'sell'

    @pytest.mark.asyncio
    async def test_fetch_my_trades_error_handling(self, mock_client):
        """测试成交记录获取失败时的错误处理"""
        mock_client.markets_loaded = True
        mock_client.exchange.market = MagicMock(return_value={'id': 'BNBUSDT'})
        mock_client.exchange.fetch_my_trades = AsyncMock(side_effect=Exception("API error"))

        trades = await mock_client.fetch_my_trades('BNB/USDT')

        # 应该返回空列表而不是抛出异常
        assert trades == []

    @pytest.mark.asyncio
    async def test_fetch_order(self, mock_client):
        """测试查询单个订单"""
        mock_order = {
            'id': '12345',
            'symbol': 'BNB/USDT',
            'status': 'closed'
        }

        mock_client.exchange.fetch_order = AsyncMock(return_value=mock_order)

        order = await mock_client.fetch_order('12345', 'BNB/USDT')

        assert order['id'] == '12345'
        assert order['status'] == 'closed'

    @pytest.mark.asyncio
    async def test_fetch_open_orders(self, mock_client):
        """测试获取未成交订单"""
        mock_open_orders = [
            {'id': '123', 'status': 'open'},
            {'id': '124', 'status': 'open'}
        ]

        mock_client.exchange.fetch_open_orders = AsyncMock(return_value=mock_open_orders)

        orders = await mock_client.fetch_open_orders('BNB/USDT')

        assert len(orders) == 2
        assert all(order['status'] == 'open' for order in orders)

    @pytest.mark.asyncio
    async def test_close(self, mock_client):
        """测试关闭交易所连接"""
        mock_client.exchange.close = AsyncMock()

        await mock_client.close()

        mock_client.exchange.close.assert_called_once()


class TestCacheInvalidation:
    """测试缓存失效机制"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}
            mock_settings.ENABLE_SAVINGS_FUNCTION = True

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                yield client

    @pytest.mark.asyncio
    async def test_transfer_to_savings_clears_cache(self, mock_client):
        """测试申购理财后清除缓存"""
        # 设置初始缓存
        mock_client.balance_cache = {'timestamp': time.time(), 'data': {'total': {'USDT': 1000.0}}}
        mock_client.funding_balance_cache = {'timestamp': time.time(), 'data': {'USDT': 500.0}}

        mock_client.get_flexible_product_id = AsyncMock(return_value='USDT001')
        mock_client.exchange.sapi_post_simple_earn_flexible_subscribe = AsyncMock(
            return_value={'success': True}
        )

        await mock_client.transfer_to_savings('USDT', 100.0)

        # 验证缓存被清空
        assert mock_client.balance_cache['timestamp'] == 0
        assert mock_client.funding_balance_cache['timestamp'] == 0

    @pytest.mark.asyncio
    async def test_transfer_to_spot_clears_cache(self, mock_client):
        """测试赎回理财后清除缓存"""
        # 设置初始缓存
        mock_client.balance_cache = {'timestamp': time.time(), 'data': {'total': {'USDT': 1000.0}}}
        mock_client.funding_balance_cache = {'timestamp': time.time(), 'data': {'USDT': 500.0}}

        mock_client.get_flexible_product_id = AsyncMock(return_value='USDT001')
        mock_client.exchange.sapi_post_simple_earn_flexible_redeem = AsyncMock(
            return_value={'success': True}
        )

        await mock_client.transfer_to_spot('USDT', 100.0)

        # 验证缓存被清空
        assert mock_client.balance_cache['timestamp'] == 0
        assert mock_client.funding_balance_cache['timestamp'] == 0


class TestEdgeCases:
    """测试边界情况"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock 的交易所客户端"""
        with patch('src.core.exchange_client.settings') as mock_settings:
            mock_settings.BINANCE_API_KEY = 'test_' + 'x' * 60
            mock_settings.BINANCE_API_SECRET = 'test_' + 'y' * 60
            mock_settings.DEBUG_MODE = False
            mock_settings.SAVINGS_PRECISIONS = {'DEFAULT': 2}

            with patch('src.core.exchange_client.ccxt.binance'):
                client = ExchangeClient()
                client.exchange = AsyncMock()
                yield client

    @pytest.mark.asyncio
    async def test_load_markets_max_retries_exceeded(self, mock_client):
        """测试加载市场数据超过最大重试次数"""
        mock_client.exchange.load_markets = AsyncMock(side_effect=Exception("Network error"))
        mock_client.sync_time = AsyncMock()

        with pytest.raises(Exception):
            await mock_client.load_markets()

        # 应该重试3次
        assert mock_client.exchange.load_markets.call_count == 3
        assert mock_client.markets_loaded is False

    @pytest.mark.asyncio
    async def test_fetch_balance_error_returns_empty_dict(self, mock_client):
        """测试余额查询失败时返回空字典"""
        mock_client.exchange.fetch_balance = AsyncMock(side_effect=Exception("API error"))

        balance = await mock_client.fetch_balance()

        # 应该返回空但结构完整的字典
        assert balance == {'free': {}, 'used': {}, 'total': {}}

    @pytest.mark.asyncio
    async def test_get_flexible_product_id_not_found(self, mock_client):
        """测试未找到理财产品"""
        mock_products = {
            'rows': [
                {'asset': 'BNB', 'productId': 'BNB001', 'status': 'SOLD_OUT'}
            ]
        }

        mock_client.exchange.sapi_get_simple_earn_flexible_list = AsyncMock(
            return_value=mock_products
        )

        with pytest.raises(ValueError, match="未找到USDT的可用活期理财产品"):
            await mock_client.get_flexible_product_id('USDT')

    @pytest.mark.asyncio
    async def test_calculate_total_account_value_with_ld_assets(self, mock_client):
        """测试总资产计算时正确排除LD理财凭证"""
        mock_spot_balance = {
            'total': {
                'USDT': 1000.0,
                'BNB': 10.0,
                'LDBNB': 5.0,  # 理财凭证，应该被排除
                'LDUSDT': 500.0  # 理财凭证，应该被排除
            }
        }

        mock_funding_balance = {
            'USDT': 500.0,
            'BNB': 5.0
        }

        mock_bnb_ticker = {'last': 680.0}

        mock_client.fetch_balance = AsyncMock(return_value=mock_spot_balance)
        mock_client.fetch_funding_balance = AsyncMock(return_value=mock_funding_balance)
        mock_client.fetch_ticker = AsyncMock(return_value=mock_bnb_ticker)

        total_value = await mock_client.calculate_total_account_value('USDT')

        # USDT: 1000 (现货) + 500 (理财) = 1500
        # BNB: 10 (现货) + 5 (理财) = 15, 价值 = 15 * 680 = 10200
        # LDBNB 和 LDUSDT 应该被排除
        expected_value = 1500.0 + (15.0 * 680.0)

        assert abs(total_value - expected_value) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
