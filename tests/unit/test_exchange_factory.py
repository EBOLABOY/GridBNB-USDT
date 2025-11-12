"""
交易所工厂和配置测试

测试交易所工厂模式的核心功能
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.core.exchanges.factory import ExchangeFactory, ExchangeConfig
from src.core.exchanges.base import IExchange, BaseExchange
from src.core.exchanges.binance import BinanceExchange
from src.core.exchanges.okx import OKXExchange


class TestExchangeConfig:
    """测试交易所配置类"""

    def test_basic_config(self):
        """测试基本配置创建"""
        config = ExchangeConfig(
            exchange_name='binance',
            api_key='test_key',
            api_secret='test_secret'
        )

        assert config.exchange_name == 'binance'
        assert config.api_key == 'test_key'
        assert config.api_secret == 'test_secret'
        assert config.enable_savings is True  # 默认值

    def test_config_with_optional_params(self):
        """测试包含可选参数的配置"""
        config = ExchangeConfig(
            exchange_name='okx',
            api_key='test_key',
            api_secret='test_secret',
            passphrase='test_passphrase',
            proxy='http://localhost:1080',
            enable_savings=False
        )

        assert config.passphrase == 'test_passphrase'
        assert config.proxy == 'http://localhost:1080'
        assert config.enable_savings is False

    def test_to_ccxt_config(self):
        """测试转换为CCXT配置"""
        config = ExchangeConfig(
            exchange_name='binance',
            api_key='test_key',
            api_secret='test_secret',
            proxy='http://localhost:1080',
            timeout=30000
        )

        ccxt_config = config.to_ccxt_config()

        assert ccxt_config['apiKey'] == 'test_key'
        assert ccxt_config['secret'] == 'test_secret'
        assert ccxt_config['aiohttp_proxy'] == 'http://localhost:1080'
        assert ccxt_config['timeout'] == 30000

    def test_config_validation_success(self):
        """测试配置验证成功"""
        config = ExchangeConfig(
            exchange_name='binance',
            api_key='test_key',
            api_secret='test_secret'
        )

        # 不应抛出异常
        config.validate()

    def test_config_validation_missing_api_key(self):
        """测试缺少API密钥的验证"""
        config = ExchangeConfig(
            exchange_name='binance',
            api_key='',
            api_secret='test_secret'
        )

        with pytest.raises(ValueError, match="api_key 不能为空"):
            config.validate()

    def test_config_validation_okx_passphrase(self):
        """测试OKX必须提供passphrase"""
        config = ExchangeConfig(
            exchange_name='okx',
            api_key='test_key',
            api_secret='test_secret'
        )

        with pytest.raises(ValueError, match="OKX交易所必须提供 passphrase"):
            config.validate()

    def test_config_validation_timeout(self):
        """测试超时值验证"""
        config = ExchangeConfig(
            exchange_name='binance',
            api_key='test_key',
            api_secret='test_secret',
            timeout=500  # 小于最小值
        )

        with pytest.raises(ValueError, match="timeout 不能小于 1000ms"):
            config.validate()


class MockExchange(IExchange):
    """Mock交易所，用于测试"""

    def __init__(self, config):
        self.config = config
        self._capabilities = []

    @property
    def name(self):
        return 'mock'

    @property
    def capabilities(self):
        return self._capabilities

    async def load_markets(self):
        return True

    async def fetch_ticker(self, symbol):
        return {'symbol': symbol, 'last': 100.0}

    async def fetch_order_book(self, symbol, limit=5):
        return {'bids': [], 'asks': []}

    async def fetch_ohlcv(self, symbol, timeframe='1h', limit=None):
        return []

    async def create_order(self, symbol, type, side, amount, price=None, params=None):
        return {'id': '12345', 'symbol': symbol, 'side': side}

    async def cancel_order(self, order_id, symbol):
        return {'id': order_id}

    async def fetch_order(self, order_id, symbol):
        return {'id': order_id, 'status': 'closed'}

    async def fetch_open_orders(self, symbol=None):
        return []

    async def fetch_balance(self, params=None):
        return {'free': {}, 'used': {}, 'total': {}}

    def get_symbol_precision(self, symbol):
        return {'amount': 8, 'price': 2}

    def adjust_amount_precision(self, symbol, amount):
        return amount

    def adjust_price_precision(self, symbol, price):
        return price

    async def sync_time(self):
        pass

    async def close(self):
        pass


class TestExchangeFactory:
    """测试交易所工厂类"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.factory = ExchangeFactory()

    def test_factory_initialization(self):
        """测试工厂初始化"""
        assert self.factory is not None
        assert len(self.factory.get_supported_exchanges()) == 0

    def test_register_exchange(self):
        """测试注册交易所"""
        self.factory.register('mock', MockExchange)

        assert self.factory.is_registered('mock')
        assert 'mock' in self.factory.get_supported_exchanges()

    def test_register_invalid_class(self):
        """测试注册无效类"""
        class InvalidExchange:
            pass

        with pytest.raises(ValueError, match="必须实现 IExchange 接口"):
            self.factory.register('invalid', InvalidExchange)

    def test_register_duplicate(self):
        """测试重复注册（应该覆盖）"""
        self.factory.register('mock', MockExchange)
        self.factory.register('mock', MockExchange)  # 应该警告但不报错

        assert self.factory.is_registered('mock')

    def test_unregister_exchange(self):
        """测试取消注册"""
        self.factory.register('mock', MockExchange)
        assert self.factory.is_registered('mock')

        self.factory.unregister('mock')
        assert not self.factory.is_registered('mock')

    def test_create_exchange(self):
        """测试创建交易所实例"""
        self.factory.register('mock', MockExchange)

        config = ExchangeConfig(
            exchange_name='mock',
            api_key='test_key',
            api_secret='test_secret'
        )

        exchange = self.factory.create('mock', config)

        assert exchange is not None
        assert isinstance(exchange, MockExchange)
        assert exchange.name == 'mock'

    def test_create_unregistered_exchange(self):
        """测试创建未注册的交易所"""
        config = ExchangeConfig(
            exchange_name='unknown',
            api_key='test_key',
            api_secret='test_secret'
        )

        with pytest.raises(ValueError, match="交易所 'unknown' 未注册"):
            self.factory.create('unknown', config)

    def test_create_with_invalid_config(self):
        """测试使用无效配置创建"""
        self.factory.register('mock', MockExchange)

        config = ExchangeConfig(
            exchange_name='mock',
            api_key='',  # 无效
            api_secret='test_secret'
        )

        with pytest.raises(ValueError, match="交易所配置无效"):
            self.factory.create('mock', config)

    def test_get_exchange_class(self):
        """测试获取交易所类"""
        self.factory.register('mock', MockExchange)

        exchange_class = self.factory.get_exchange_class('mock')
        assert exchange_class == MockExchange

    def test_get_unregistered_exchange_class(self):
        """测试获取未注册的交易所类"""
        with pytest.raises(ValueError, match="交易所 'unknown' 未注册"):
            self.factory.get_exchange_class('unknown')

    def test_factory_repr(self):
        """测试工厂字符串表示"""
        self.factory.register('binance', BinanceExchange)
        self.factory.register('okx', OKXExchange)

        repr_str = repr(self.factory)
        assert 'ExchangeFactory' in repr_str
        assert 'registered=2' in repr_str
