"""
交易所适配器单元测试

测试所有交易所适配器的核心功能。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.exchange import (
    ExchangeFactory,
    ExchangeType,
    BinanceAdapter,
    OKXAdapter,
    ExchangeFeature,
)


class TestExchangeFactory:
    """测试交易所工厂类"""

    def setup_method(self):
        """每个测试前清空实例缓存"""
        ExchangeFactory.clear_instances()

    def test_create_binance_adapter(self):
        """测试创建币安适配器"""
        adapter = ExchangeFactory.create(
            ExchangeType.BINANCE,
            api_key="test_key",
            api_secret="test_secret"
        )

        assert isinstance(adapter, BinanceAdapter)
        assert adapter.exchange_type == ExchangeType.BINANCE
        assert adapter.api_key == "test_key"

    def test_create_okx_adapter(self):
        """测试创建OKX适配器"""
        adapter = ExchangeFactory.create(
            ExchangeType.OKX,
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase"
        )

        assert isinstance(adapter, OKXAdapter)
        assert adapter.exchange_type == ExchangeType.OKX
        assert adapter.passphrase == "test_passphrase"

    def test_okx_requires_passphrase(self):
        """测试OKX必须提供passphrase"""
        with pytest.raises(ValueError, match="passphrase"):
            ExchangeFactory.create(
                ExchangeType.OKX,
                api_key="test_key",
                api_secret="test_secret"
                # 缺少 passphrase
            )

    def test_singleton_pattern(self):
        """测试单例模式"""
        adapter1 = ExchangeFactory.create(
            ExchangeType.BINANCE,
            api_key="test_key",
            api_secret="test_secret"
        )

        adapter2 = ExchangeFactory.get_instance(ExchangeType.BINANCE)

        assert adapter1 is adapter2

    def test_get_supported_exchanges(self):
        """测试获取支持的交易所列表"""
        exchanges = ExchangeFactory.get_supported_exchanges()

        assert 'binance' in exchanges
        assert 'okx' in exchanges


class TestBinanceAdapter:
    """测试币安适配器"""

    def setup_method(self):
        """每个测试前创建适配器实例"""
        self.adapter = BinanceAdapter(
            api_key="test_key",
            api_secret="test_secret"
        )

    def test_exchange_type(self):
        """测试交易所类型"""
        assert self.adapter.exchange_type == ExchangeType.BINANCE

    def test_capabilities(self):
        """测试功能支持"""
        caps = self.adapter.capabilities

        assert caps.supports(ExchangeFeature.SPOT_TRADING)
        assert caps.supports(ExchangeFeature.FUNDING_ACCOUNT)
        assert not caps.supports(ExchangeFeature.FUTURES_TRADING)

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化"""
        with patch('ccxt.async_support.binance') as mock_ccxt:
            mock_exchange = AsyncMock()
            mock_exchange.load_markets = AsyncMock(return_value={})
            mock_exchange.fetch_balance = AsyncMock(return_value={'free': {}})
            mock_ccxt.return_value = mock_exchange

            await self.adapter.initialize()

            assert self.adapter._exchange is not None
            mock_exchange.load_markets.assert_called_once()

    def test_amount_precision(self):
        """测试数量精度调整"""
        # Mock CCXT exchange
        self.adapter._exchange = Mock()
        self.adapter._exchange.amount_to_precision = Mock(return_value="0.001")

        result = self.adapter.amount_to_precision('BTC/USDT', 0.0012345)

        assert result == "0.001"
        self.adapter._exchange.amount_to_precision.assert_called_once()


class TestOKXAdapter:
    """测试OKX适配器"""

    def setup_method(self):
        """每个测试前创建适配器实例"""
        self.adapter = OKXAdapter(
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase"
        )

    def test_exchange_type(self):
        """测试交易所类型"""
        assert self.adapter.exchange_type == ExchangeType.OKX

    def test_capabilities(self):
        """测试功能支持"""
        caps = self.adapter.capabilities

        assert caps.supports(ExchangeFeature.SPOT_TRADING)
        assert caps.supports(ExchangeFeature.FUNDING_ACCOUNT)

    def test_get_exchange_symbol(self):
        """测试交易对格式转换"""
        result = self.adapter.get_exchange_symbol('BTC/USDT')

        # OKX使用 BTC-USDT 格式
        assert result == 'BTC-USDT'

    @pytest.mark.asyncio
    async def test_fetch_balance(self):
        """测试获取余额（账户类型映射）"""
        self.adapter._exchange = AsyncMock()
        self.adapter._exchange.fetch_balance = AsyncMock(return_value={'free': {}})

        # 请求 'spot' 账户
        await self.adapter.fetch_balance('spot')

        # OKX应该映射为 'trading'
        self.adapter._exchange.fetch_balance.assert_called_once_with({'type': 'trading'})


class TestExchangeCapabilities:
    """测试交易所能力类"""

    def test_supports_feature(self):
        """测试功能支持检查"""
        from src.core.exchange.base import ExchangeCapabilities

        caps = ExchangeCapabilities([
            ExchangeFeature.SPOT_TRADING,
            ExchangeFeature.FUNDING_ACCOUNT
        ])

        assert caps.supports(ExchangeFeature.SPOT_TRADING)
        assert caps.supports(ExchangeFeature.FUNDING_ACCOUNT)
        assert not caps.supports(ExchangeFeature.FUTURES_TRADING)

    def test_require_feature(self):
        """测试功能要求断言"""
        from src.core.exchange.base import ExchangeCapabilities

        caps = ExchangeCapabilities([ExchangeFeature.SPOT_TRADING])

        # 应该成功
        caps.require(ExchangeFeature.SPOT_TRADING)

        # 应该抛出异常
        with pytest.raises(NotImplementedError, match="不支持功能"):
            caps.require(ExchangeFeature.FUTURES_TRADING)


# ==================== 集成测试（需要真实API密钥） ====================

@pytest.mark.integration
@pytest.mark.skipif(True, reason="需要真实API密钥")
class TestBinanceIntegration:
    """币安集成测试（需要配置真实API）"""

    @pytest.mark.asyncio
    async def test_real_connection(self):
        """测试真实连接"""
        from src.config.settings import settings

        adapter = BinanceAdapter(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET
        )

        await adapter.initialize()

        # 测试获取余额
        balance = await adapter.fetch_balance()
        assert 'free' in balance

        # 测试获取行情
        ticker = await adapter.fetch_ticker('BTC/USDT')
        assert 'last' in ticker

        await adapter.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
