"""
多时间周期分析模块单元测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.strategies.multi_timeframe_analyzer import (
    MultiTimeframeAnalyzer,
    TimeframeTrend,
    KeyLevel
)


class TestMultiTimeframeAnalyzer:
    """多时间周期分析器测试"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return MultiTimeframeAnalyzer()

    @pytest.fixture
    def mock_exchange(self):
        """创建模拟交易所"""
        exchange = AsyncMock()

        # 模拟K线数据
        def generate_klines(limit, trend='neutral'):
            """生成模拟K线数据"""
            base_price = 600.0
            klines = []

            for i in range(limit):
                # 根据趋势生成价格
                if trend == 'uptrend':
                    price = base_price + i * 0.5
                elif trend == 'downtrend':
                    price = base_price - i * 0.5
                else:  # neutral/ranging
                    price = base_price + (i % 10 - 5) * 0.2

                kline = [
                    1697500000000 + i * 3600000,  # timestamp
                    price,  # open
                    price + 2,  # high
                    price - 2,  # low
                    price + 0.5,  # close
                    1000.0  # volume
                ]
                klines.append(kline)

            return klines

        exchange.fetch_ohlcv = AsyncMock(side_effect=lambda symbol, tf, limit: generate_klines(limit))

        return exchange

    @pytest.mark.asyncio
    async def test_analyze_timeframes_success(self, analyzer, mock_exchange):
        """测试成功分析多个时间周期"""
        result = await analyzer.analyze_timeframes(
            mock_exchange,
            "BNB/USDT",
            600.0
        )

        # 验证返回数据结构
        assert "macro_daily" in result
        assert "medium_4h" in result
        assert "micro_1h" in result
        assert "alignment" in result
        assert "key_levels" in result
        assert "overall_strength" in result
        assert "trading_recommendation" in result

        # 验证日线数据
        daily = result["macro_daily"]
        assert "trend" in daily
        assert daily["trend"] in ["uptrend", "downtrend", "ranging"]
        assert "strength" in daily
        assert 0 <= daily["strength"] <= 100

        # 验证4小时数据
        four_h = result["medium_4h"]
        assert "trend" in four_h
        assert "rsi" in four_h

        # 验证1小时数据
        one_h = result["micro_1h"]
        assert "trend" in one_h
        assert "rsi" in one_h

    @pytest.mark.asyncio
    async def test_check_alignment_bullish_resonance(self, analyzer):
        """测试看涨共振检测"""
        alignment = analyzer._check_alignment(
            "uptrend",
            "uptrend",
            "uptrend"
        )

        assert alignment == "strong_bullish_resonance"

    @pytest.mark.asyncio
    async def test_check_alignment_bearish_resonance(self, analyzer):
        """测试看跌共振检测"""
        alignment = analyzer._check_alignment(
            "downtrend",
            "downtrend",
            "downtrend"
        )

        assert alignment == "strong_bearish_resonance"

    @pytest.mark.asyncio
    async def test_check_alignment_dangerous_bounce(self, analyzer):
        """测试危险背离检测（接飞刀）"""
        alignment = analyzer._check_alignment(
            "downtrend",
            "ranging",
            "uptrend"
        )

        assert alignment == "dangerous_counter_trend_bounce"

    @pytest.mark.asyncio
    async def test_check_alignment_healthy_pullback(self, analyzer):
        """测试健康回调检测"""
        alignment = analyzer._check_alignment(
            "uptrend",
            "ranging",
            "downtrend"
        )

        assert alignment == "healthy_pullback"

    @pytest.mark.asyncio
    async def test_determine_trend_uptrend(self, analyzer):
        """测试上涨趋势判断"""
        prices = [100 + i * 0.5 for i in range(100)]  # 持续上涨

        rsi = {"value": 65, "trend": "neutral", "signal": "neutral"}
        macd = {"trend": "bullish", "histogram": 0.5}
        price_change = 10.0

        trend = analyzer._determine_trend(prices, rsi, macd, price_change)

        assert trend == "uptrend"

    @pytest.mark.asyncio
    async def test_determine_trend_downtrend(self, analyzer):
        """测试下跌趋势判断"""
        prices = [100 - i * 0.5 for i in range(100)]  # 持续下跌

        rsi = {"value": 35, "trend": "neutral", "signal": "neutral"}
        macd = {"trend": "bearish", "histogram": -0.5}
        price_change = -10.0

        trend = analyzer._determine_trend(prices, rsi, macd, price_change)

        assert trend == "downtrend"

    @pytest.mark.asyncio
    async def test_calculate_trend_strength_strong(self, analyzer):
        """测试强趋势强度计算"""
        prices = [100 + i * 0.5 for i in range(100)]

        rsi = {"value": 65}  # 强势但未超买
        macd = {"histogram": 0.6}  # 强MACD

        strength = analyzer._calculate_trend_strength(
            prices, rsi, macd, "uptrend"
        )

        assert strength >= 70  # 强趋势应该>=70分

    @pytest.mark.asyncio
    async def test_calculate_trend_strength_weak(self, analyzer):
        """测试弱趋势强度计算"""
        prices = [100 + (i % 10 - 5) * 0.1 for i in range(100)]  # 震荡

        rsi = {"value": 50}  # 中性
        macd = {"histogram": 0.05}  # 弱MACD

        strength = analyzer._calculate_trend_strength(
            prices, rsi, macd, "ranging"
        )

        assert strength <= 60  # 弱趋势应该<=60分

    @pytest.mark.asyncio
    async def test_find_support_resistance(self, analyzer):
        """测试支撑阻力位识别"""
        # 生成有明显高低点的数据
        highs = [610, 605, 612, 608, 615, 607, 613, 609, 616, 610,
                 611, 606, 614, 608, 617, 609, 612, 607, 615, 610]
        lows = [590, 595, 588, 592, 585, 593, 587, 591, 584, 592,
                589, 594, 586, 590, 583, 591, 588, 593, 585, 589]
        closes = [600, 602, 598, 605, 601, 604, 599, 606, 602, 607,
                  603, 608, 604, 609, 605, 610, 606, 611, 607, 612]

        levels = analyzer._find_support_resistance(highs, lows, closes)

        assert "resistance" in levels or "support" in levels
        if levels.get("resistance"):
            assert levels["resistance"] > closes[-1]  # 阻力应在当前价格上方
        if levels.get("support"):
            assert levels["support"] < closes[-1]  # 支撑应在当前价格下方

    @pytest.mark.asyncio
    async def test_identify_key_levels(self, analyzer):
        """测试关键价位识别"""
        daily_data = {
            "levels": {"resistance": 650, "support": 580}
        }
        four_h_data = {
            "levels": {"resistance": 630, "support": 590}
        }
        one_h_data = {
            "levels": {"resistance": 620, "support": 595}
        }

        current_price = 605.0

        key_levels = analyzer._identify_key_levels(
            daily_data, four_h_data, one_h_data, current_price
        )

        assert "strong_resistance" in key_levels
        assert "strong_support" in key_levels
        assert "nearest_resistance" in key_levels
        assert "nearest_support" in key_levels

    @pytest.mark.asyncio
    async def test_calculate_overall_strength_with_resonance(self, analyzer):
        """测试共振时的综合强度"""
        daily = {"strength": 80}
        four_h = {"strength": 75}
        one_h = {"strength": 70}
        alignment = "strong_bullish_resonance"

        overall = analyzer._calculate_overall_strength(
            daily, four_h, one_h, alignment
        )

        assert overall >= 80  # 共振应该提升强度

    @pytest.mark.asyncio
    async def test_calculate_overall_strength_with_divergence(self, analyzer):
        """测试背离时的综合强度"""
        daily = {"strength": 60}
        four_h = {"strength": 50}
        one_h = {"strength": 70}
        alignment = "dangerous_counter_trend_bounce"

        overall = analyzer._calculate_overall_strength(
            daily, four_h, one_h, alignment
        )

        assert overall <= 50  # 背离应该降低强度

    @pytest.mark.asyncio
    async def test_error_handling_insufficient_data(self, analyzer):
        """测试数据不足时的错误处理"""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=[])  # 空数据

        result = await analyzer.analyze_timeframes(
            mock_exchange,
            "BNB/USDT",
            600.0
        )

        # 应该返回空分析结果，而不是抛出异常
        assert result["alignment"] == "unknown"
        assert result["overall_strength"] == 0

    @pytest.mark.asyncio
    async def test_error_handling_api_failure(self, analyzer):
        """测试API调用失败时的错误处理"""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=Exception("API Error"))

        result = await analyzer.analyze_timeframes(
            mock_exchange,
            "BNB/USDT",
            600.0
        )

        # 应该返回空分析结果
        assert "alignment" in result
        assert result["alignment"] == "unknown"

    @pytest.mark.asyncio
    async def test_generate_recommendation_bullish(self, analyzer):
        """测试看涨建议生成"""
        alignment = "strong_bullish_resonance"
        daily = {"strength": 85, "trend": "uptrend"}
        four_h = {"strength": 80, "trend": "uptrend"}
        one_h = {"strength": 75, "trend": "uptrend"}
        key_levels = {"nearest_resistance": 650, "nearest_support": 580}
        overall_strength = 85

        recommendation = analyzer._generate_recommendation(
            alignment, daily, four_h, one_h, key_levels, overall_strength
        )

        assert "共振" in recommendation or "看涨" in recommendation
        assert isinstance(recommendation, str)
        assert len(recommendation) > 0

    @pytest.mark.asyncio
    async def test_generate_recommendation_dangerous(self, analyzer):
        """测试危险情况建议生成"""
        alignment = "dangerous_counter_trend_bounce"
        daily = {"strength": 40, "trend": "downtrend"}
        four_h = {"strength": 45, "trend": "ranging"}
        one_h = {"strength": 60, "trend": "uptrend"}
        key_levels = {}
        overall_strength = 35

        recommendation = analyzer._generate_recommendation(
            alignment, daily, four_h, one_h, key_levels, overall_strength
        )

        assert "警告" in recommendation or "接飞刀" in recommendation or "风险" in recommendation


class TestTimeframeTrendDataClass:
    """测试TimeframeTrend数据类"""

    def test_timeframe_trend_creation(self):
        """测试创建TimeframeTrend"""
        trend = TimeframeTrend(
            timeframe="1d",
            trend="uptrend",
            strength=85,
            rsi=65.0,
            macd_signal="golden_cross",
            price_change_percent=10.5
        )

        assert trend.timeframe == "1d"
        assert trend.trend == "uptrend"
        assert trend.strength == 85
        assert trend.rsi == 65.0


class TestKeyLevelDataClass:
    """测试KeyLevel数据类"""

    def test_key_level_creation(self):
        """测试创建KeyLevel"""
        level = KeyLevel(
            price=650.0,
            level_type="resistance",
            strength=80,
            distance_percent=5.2
        )

        assert level.price == 650.0
        assert level.level_type == "resistance"
        assert level.strength == 80
        assert level.distance_percent == 5.2
