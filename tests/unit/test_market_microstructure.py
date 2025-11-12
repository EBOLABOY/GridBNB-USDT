"""
订单簿深度分析模块单元测试
"""

import pytest
from unittest.mock import AsyncMock
from src.strategies.market_microstructure import OrderBookAnalyzer, OrderWall


class TestOrderBookAnalyzer:
    """订单簿分析器测试"""

    @pytest.fixture
    def analyzer(self):
        return OrderBookAnalyzer()

    @pytest.fixture
    def mock_orderbook(self):
        """模拟订单簿数据"""
        return {
            'bids': [  # 买盘 [[price, amount], ...]
                [599.5, 10.0],
                [599.0, 15.0],
                [598.5, 20.0],
                [598.0, 50.0],  # 大单
                [597.5, 12.0],
            ],
            'asks': [  # 卖盘
                [600.5, 10.0],
                [601.0, 15.0],
                [601.5, 20.0],
                [602.0, 60.0],  # 大单墙
                [602.5, 12.0],
            ]
        }

    @pytest.mark.asyncio
    async def test_analyze_order_book_success(self, analyzer, mock_orderbook):
        """测试成功分析订单簿"""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_order_book = AsyncMock(return_value=mock_orderbook)

        result = await analyzer.analyze_order_book(mock_exchange, "BNB/USDT", 600.0)

        assert "spread" in result
        assert "imbalance" in result
        assert "depth_ratio" in result
        assert "resistance_walls" in result
        assert "support_walls" in result
        assert "liquidity_signal" in result

    @pytest.mark.asyncio
    async def test_detect_resistance_walls(self, analyzer, mock_orderbook):
        """测试检测阻力墙"""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_order_book = AsyncMock(return_value=mock_orderbook)

        result = await analyzer.analyze_order_book(mock_exchange, "BNB/USDT", 600.0)

        # 应该检测到602.0的大单墙
        resistance_walls = result["resistance_walls"]
        assert len(resistance_walls) > 0
        assert any(w["price"] == 602.0 for w in resistance_walls)

    @pytest.mark.asyncio
    async def test_calculate_imbalance(self, analyzer, mock_orderbook):
        """测试买卖失衡度计算"""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_order_book = AsyncMock(return_value=mock_orderbook)

        result = await analyzer.analyze_order_book(mock_exchange, "BNB/USDT", 600.0)

        imbalance = result["imbalance"]
        assert -1 <= imbalance <= 1  # 失衡度应在-1到1之间

    @pytest.mark.asyncio
    async def test_liquidity_signal_bullish(self, analyzer):
        """测试看涨流动性信号"""
        signal = analyzer._generate_liquidity_signal(
            imbalance=0.35,  # 买盘强
            depth_ratio=1.6,
            buy_walls_count=2,
            sell_walls_count=0
        )

        assert signal == "strong_bullish"

    @pytest.mark.asyncio
    async def test_liquidity_signal_bearish(self, analyzer):
        """测试看跌流动性信号"""
        signal = analyzer._generate_liquidity_signal(
            imbalance=-0.35,  # 卖盘强
            depth_ratio=0.6,
            buy_walls_count=0,
            sell_walls_count=2
        )

        assert signal == "strong_bearish"

    @pytest.mark.asyncio
    async def test_error_handling_empty_orderbook(self, analyzer):
        """测试空订单簿处理"""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_order_book = AsyncMock(return_value={'bids': [], 'asks': []})

        result = await analyzer.analyze_order_book(mock_exchange, "BNB/USDT", 600.0)

        assert result["liquidity_signal"] == "unknown"
        assert result["trading_insight"] == "订单簿数据不可用"
