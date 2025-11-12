"""
BTC相关性分析模块单元测试
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock
from src.strategies.correlation_analyzer import CorrelationAnalyzer


class TestCorrelationAnalyzer:
    """BTC相关性分析器测试"""

    @pytest.fixture
    def analyzer(self):
        return CorrelationAnalyzer()

    @pytest.fixture
    def mock_exchange_correlated(self):
        """创建高相关性模拟交易所"""
        exchange = AsyncMock()

        async def fetch_ohlcv_correlated(symbol, timeframe, limit):
            """生成高度相关的价格数据"""
            if symbol == "BTC/USDT":
                # BTC价格序列
                prices = [40000 + i * 10 for i in range(limit)]
            else:
                # 目标币种价格（高度相关，比例约为BTC的1.5%）
                prices = [600 + i * 0.15 for i in range(limit)]

            return [[0, 0, 0, 0, price, 0] for price in prices]

        exchange.fetch_ohlcv = fetch_ohlcv_correlated
        return exchange

    @pytest.mark.asyncio
    async def test_high_correlation_detection(self, analyzer, mock_exchange_correlated):
        """测试高相关性检测"""
        result = await analyzer.analyze_btc_correlation(
            mock_exchange_correlated,
            "BNB/USDT",
            timeframe='1h',
            current_price=615.0
        )

        assert result["correlation_strength"] == "high"
        assert result["correlation_coefficient"] > 0.7

    @pytest.mark.asyncio
    async def test_calculate_correlation_positive(self, analyzer):
        """测试正相关计算"""
        # 生成正相关数据
        target_prices = [100 + i * 0.5 for i in range(100)]
        btc_prices = [40000 + i * 20 for i in range(100)]

        result = analyzer._calculate_correlation(target_prices, btc_prices)

        assert result["correlation_coefficient"] > 0
        assert result["direction"] == "positive"

    @pytest.mark.asyncio
    async def test_btc_state_analysis(self, analyzer):
        """测试BTC状态分析"""
        # 上涨趋势
        btc_prices = [40000 + i * 50 for i in range(100)]

        state = analyzer._analyze_btc_state(btc_prices)

        assert state["short_term_trend"] in ["uptrend", "strong_uptrend"]
        assert state["24h_change"] > 0

    @pytest.mark.asyncio
    async def test_risk_warning_high_correlation_btc_down(self, analyzer):
        """测试高相关性+BTC下跌的风险警告"""
        correlation = {"coefficient": 0.85, "strength": "high", "direction": "positive"}
        btc_state = {
            "24h_change": -5.0,
            "short_term_trend": "downtrend",
            "momentum": "decelerating"
        }
        target_state = {"24h_change": -3.0}

        warning = analyzer._generate_risk_warning(correlation, btc_state, target_state)

        assert warning is not None
        assert "BTC下跌" in warning or "拖累" in warning

    @pytest.mark.asyncio
    async def test_risk_warning_divergence(self, analyzer):
        """测试背离风险警告"""
        correlation = {"coefficient": 0.75, "strength": "high"}
        btc_state = {"24h_change": -3.0}
        target_state = {"24h_change": 4.0}  # BTC跌但目标币涨

        warning = analyzer._generate_risk_warning(correlation, btc_state, target_state)

        assert warning is not None
        assert "背离" in warning

    @pytest.mark.asyncio
    async def test_impact_assessment(self, analyzer):
        """测试BTC影响评估"""
        correlation = {"coefficient": 0.8, "strength": "high"}
        btc_state = {"short_term_trend": "uptrend"}
        target_state = {}

        impact = analyzer._assess_btc_impact(correlation, btc_state, target_state)

        assert impact["dominance"] == "highly_follows_btc"
        assert impact["current_impact"] == "btc_boosting"

    @pytest.mark.asyncio
    async def test_low_correlation_independence(self, analyzer):
        """测试低相关性独立性判断"""
        correlation = {"coefficient": 0.3, "strength": "low"}
        btc_state = {"short_term_trend": "downtrend"}
        target_state = {}

        impact = analyzer._assess_btc_impact(correlation, btc_state, target_state)

        assert impact["dominance"] == "independent"

    @pytest.mark.asyncio
    async def test_error_handling_insufficient_data(self, analyzer):
        """测试数据不足处理"""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=[])  # 空数据

        result = await analyzer.analyze_btc_correlation(
            mock_exchange,
            "BNB/USDT"
        )

        assert result["correlation_strength"] == "unknown"
        assert result["trading_insight"] == "数据不可用"
