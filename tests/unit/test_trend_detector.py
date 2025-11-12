"""
趋势识别器单元测试

测试覆盖:
- 趋势方向识别 (强上涨/强下跌/震荡)
- 技术指标计算 (EMA, ADX, 动量)
- 趋势强度评分
- 交易建议 (暂停买入/卖出)
- 缓存机制
- 风控状态覆盖

创建日期: 2025-10-28
"""
import pytest
import numpy as np
import time
from unittest.mock import MagicMock, AsyncMock, patch

from src.strategies.trend_detector import (
    TrendDetector,
    TrendDirection,
    TrendSignal
)
from src.strategies.risk_manager import RiskState


@pytest.fixture
def trend_detector():
    """创建趋势识别器实例"""
    detector = TrendDetector(
        symbol='BNB/USDT',
        ema_short=20,
        ema_long=50,
        adx_period=14,
        strong_trend_threshold=60.0,
        cache_ttl=300
    )
    return detector


@pytest.fixture
def mock_exchange():
    """创建模拟的交易所客户端"""
    exchange = AsyncMock()
    return exchange


@pytest.fixture
def generate_uptrend_ohlcv():
    """生成强上涨趋势的K线数据"""
    def _generate():
        # 模拟强上涨趋势: 600 → 700 (连续上涨)
        base_price = 600.0
        ohlcv = []

        for i in range(100):
            # 价格逐步上涨，模拟强上涨趋势
            price_increase = i * 1.0  # 每根K线上涨1 USDT
            close = base_price + price_increase
            high = close * 1.02
            low = close * 0.98
            open_price = close * 0.99
            volume = 10000 + i * 100  # 成交量逐渐放大
            timestamp = 1640000000000 + i * 3600000  # 4小时间隔

            ohlcv.append([timestamp, open_price, high, low, close, volume])

        return ohlcv

    return _generate


@pytest.fixture
def generate_downtrend_ohlcv():
    """生成强下跌趋势的K线数据"""
    def _generate():
        # 模拟强下跌趋势: 700 → 600 (连续下跌)
        base_price = 700.0
        ohlcv = []

        for i in range(100):
            # 价格逐步下跌，模拟强下跌趋势
            price_decrease = i * 1.0  # 每根K线下跌1 USDT
            close = base_price - price_decrease
            high = close * 1.02
            low = close * 0.98
            open_price = close * 1.01
            volume = 10000 + i * 100  # 成交量逐渐放大
            timestamp = 1640000000000 + i * 3600000

            ohlcv.append([timestamp, open_price, high, low, close, volume])

        return ohlcv

    return _generate


@pytest.fixture
def generate_sideways_ohlcv():
    """生成震荡市的K线数据"""
    def _generate():
        # 模拟震荡市: 价格在 600 ± 10 之间波动
        base_price = 600.0
        ohlcv = []

        for i in range(100):
            # 价格在窄幅区间内随机波动
            noise = (i % 10 - 5) * 2.0  # ±10 USDT 的震荡
            close = base_price + noise
            high = close * 1.01
            low = close * 0.99
            open_price = close
            volume = 10000
            timestamp = 1640000000000 + i * 3600000

            ohlcv.append([timestamp, open_price, high, low, close, volume])

        return ohlcv

    return _generate


class TestTrendDirection:
    """测试趋势方向枚举"""

    def test_trend_direction_values(self):
        """测试趋势方向枚举值"""
        assert TrendDirection.STRONG_UP.value == "strong_up"
        assert TrendDirection.MODERATE_UP.value == "moderate_up"
        assert TrendDirection.SIDEWAYS.value == "sideways"
        assert TrendDirection.MODERATE_DOWN.value == "moderate_down"
        assert TrendDirection.STRONG_DOWN.value == "strong_down"


class TestTrendSignal:
    """测试趋势信号数据类"""

    def test_trend_signal_creation(self):
        """测试趋势信号创建"""
        signal = TrendSignal(
            direction=TrendDirection.STRONG_UP,
            strength=75.0,
            confidence=0.85,
            timestamp=time.time(),
            indicators={'ema_short': 620.0, 'ema_long': 600.0},
            reason="EMA金叉, ADX强趋势"
        )

        assert signal.direction == TrendDirection.STRONG_UP
        assert signal.strength == 75.0
        assert signal.confidence == 0.85
        assert 'ema_short' in signal.indicators
        assert signal.reason == "EMA金叉, ADX强趋势"

    def test_trend_signal_repr(self):
        """测试趋势信号字符串表示"""
        signal = TrendSignal(
            direction=TrendDirection.SIDEWAYS,
            strength=30.0,
            confidence=0.6,
            timestamp=time.time()
        )

        repr_str = repr(signal)
        assert "sideways" in repr_str
        assert "30.0" in repr_str
        assert "0.60" in repr_str


class TestTrendDetector:
    """测试趋势识别器核心功能"""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试1: 强上涨趋势识别
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_strong_uptrend_detection(
        self,
        trend_detector,
        mock_exchange,
        generate_uptrend_ohlcv
    ):
        """测试强上涨趋势识别"""
        # 设置模拟K线数据
        mock_exchange.fetch_ohlcv.return_value = generate_uptrend_ohlcv()

        # 执行趋势检测
        signal = await trend_detector.detect_trend(mock_exchange)

        # 验证结果
        assert signal.direction in [
            TrendDirection.STRONG_UP,
            TrendDirection.MODERATE_UP
        ], f"预期上涨趋势，实际: {signal.direction.value}"

        # 验证指标
        assert signal.indicators['ema_divergence'] > 0, "EMA应该金叉"
        assert signal.strength > 40, f"强趋势的强度应该>40，实际: {signal.strength}"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试2: 强下跌趋势识别
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_strong_downtrend_detection(
        self,
        trend_detector,
        mock_exchange,
        generate_downtrend_ohlcv
    ):
        """测试强下跌趋势识别"""
        # 设置模拟K线数据
        mock_exchange.fetch_ohlcv.return_value = generate_downtrend_ohlcv()

        # 执行趋势检测
        signal = await trend_detector.detect_trend(mock_exchange)

        # 验证结果
        assert signal.direction in [
            TrendDirection.STRONG_DOWN,
            TrendDirection.MODERATE_DOWN
        ], f"预期下跌趋势，实际: {signal.direction.value}"

        # 验证指标
        assert signal.indicators['ema_divergence'] < 0, "EMA应该死叉"
        assert signal.strength > 40, f"强趋势的强度应该>40，实际: {signal.strength}"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试3: 震荡市识别
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_sideways_detection(
        self,
        trend_detector,
        mock_exchange,
        generate_sideways_ohlcv
    ):
        """测试震荡市识别"""
        # 设置模拟K线数据
        mock_exchange.fetch_ohlcv.return_value = generate_sideways_ohlcv()

        # 执行趋势检测
        signal = await trend_detector.detect_trend(mock_exchange)

        # 验证结果（震荡市或温和趋势）
        assert signal.direction in [
            TrendDirection.SIDEWAYS,
            TrendDirection.MODERATE_UP,
            TrendDirection.MODERATE_DOWN
        ], f"预期震荡或温和趋势，实际: {signal.direction.value}"

        # 震荡市的强度应该较低
        if signal.direction == TrendDirection.SIDEWAYS:
            assert signal.strength < 60, f"震荡市强度应该<60，实际: {signal.strength}"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试4: EMA计算准确性
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_ema_calculation(self, trend_detector):
        """测试EMA计算准确性"""
        # 简单的价格序列
        data = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110])
        period = 5

        # 计算EMA
        ema = trend_detector._calculate_ema(data, period)

        # 验证结果
        assert len(ema) == len(data), "EMA长度应该与输入数据相同"
        assert ema[0] == 100, "第一个EMA应该等于第一个价格"
        assert ema[-1] > ema[0], "上涨趋势中，EMA应该递增"

        # EMA应该比简单移动平均更接近最新价格
        assert ema[-1] > 105, "EMA应该反映近期价格上涨"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试5: ADX计算准确性
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_adx_calculation(self, trend_detector):
        """测试ADX计算准确性"""
        # 生成模拟的高低收价格数据
        n = 50
        highs = np.linspace(100, 110, n)  # 递增
        lows = np.linspace(95, 105, n)    # 递增
        closes = np.linspace(98, 108, n)  # 递增

        # 计算ADX
        adx = trend_detector._calculate_adx(highs, lows, closes, period=14)

        # 验证结果
        assert len(adx) == len(highs), "ADX长度应该与输入数据相同"
        assert np.all(adx >= 0), "ADX应该全为非负值"
        assert np.all(adx <= 100), "ADX应该全部<=100"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试6: 趋势强度评分
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_strength_scoring(self, trend_detector):
        """测试趋势强度评分逻辑"""
        # 强趋势指标
        strong_indicators = {
            'adx': 70.0,              # 高ADX
            'ema_divergence': 0.05,   # 强EMA分离
            'momentum': 10.0,         # 强动量
            'volume_ratio': 2.0,      # 成交量放大
        }

        strong_score = trend_detector._calculate_strength(strong_indicators)

        # 弱趋势指标
        weak_indicators = {
            'adx': 15.0,              # 低ADX
            'ema_divergence': 0.001,  # 弱EMA分离
            'momentum': 1.0,          # 弱动量
            'volume_ratio': 0.8,      # 成交量萎缩
        }

        weak_score = trend_detector._calculate_strength(weak_indicators)

        # 验证结果
        assert 0 <= strong_score <= 100, "强度评分应该在0-100之间"
        assert 0 <= weak_score <= 100, "强度评分应该在0-100之间"
        assert strong_score > weak_score, "强趋势的评分应该高于弱趋势"
        assert strong_score > 60, f"强趋势评分应该>60，实际: {strong_score}"
        assert weak_score < 40, f"弱趋势评分应该<40，实际: {weak_score}"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试7: 买入暂停判断
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_should_pause_buy(self, trend_detector):
        """测试买入暂停判断逻辑"""
        # 强下跌趋势 → 应该暂停买入
        strong_down_signal = TrendSignal(
            direction=TrendDirection.STRONG_DOWN,
            strength=70.0,
            confidence=0.85,
            timestamp=time.time(),
            indicators={},
            reason="强下跌趋势"
        )

        assert trend_detector.should_pause_buy(strong_down_signal) is True, \
            "强下跌趋势应该暂停买入"

        # 强上涨趋势 → 不应该暂停买入
        strong_up_signal = TrendSignal(
            direction=TrendDirection.STRONG_UP,
            strength=70.0,
            confidence=0.85,
            timestamp=time.time()
        )

        assert trend_detector.should_pause_buy(strong_up_signal) is False, \
            "强上涨趋势不应该暂停买入"

        # 震荡市 → 不应该暂停买入
        sideways_signal = TrendSignal(
            direction=TrendDirection.SIDEWAYS,
            strength=30.0,
            confidence=0.6,
            timestamp=time.time()
        )

        assert trend_detector.should_pause_buy(sideways_signal) is False, \
            "震荡市不应该暂停买入"

        # 强度不足的下跌趋势 → 不应该暂停买入
        weak_down_signal = TrendSignal(
            direction=TrendDirection.STRONG_DOWN,
            strength=50.0,  # 低于阈值60
            confidence=0.85,
            timestamp=time.time()
        )

        assert trend_detector.should_pause_buy(weak_down_signal) is False, \
            "强度不足的下跌趋势不应该暂停买入"

        # 置信度不足的下跌趋势 → 不应该暂停买入
        low_confidence_signal = TrendSignal(
            direction=TrendDirection.STRONG_DOWN,
            strength=70.0,
            confidence=0.6,  # 低于阈值0.7
            timestamp=time.time()
        )

        assert trend_detector.should_pause_buy(low_confidence_signal) is False, \
            "置信度不足的下跌趋势不应该暂停买入"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试8: 卖出暂停判断
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_should_pause_sell(self, trend_detector):
        """测试卖出暂停判断逻辑"""
        # 强上涨趋势 → 应该暂停卖出
        strong_up_signal = TrendSignal(
            direction=TrendDirection.STRONG_UP,
            strength=70.0,
            confidence=0.85,
            timestamp=time.time(),
            indicators={},
            reason="强上涨趋势"
        )

        assert trend_detector.should_pause_sell(strong_up_signal) is True, \
            "强上涨趋势应该暂停卖出"

        # 强下跌趋势 → 不应该暂停卖出
        strong_down_signal = TrendSignal(
            direction=TrendDirection.STRONG_DOWN,
            strength=70.0,
            confidence=0.85,
            timestamp=time.time()
        )

        assert trend_detector.should_pause_sell(strong_down_signal) is False, \
            "强下跌趋势不应该暂停卖出"

        # 震荡市 → 不应该暂停卖出
        sideways_signal = TrendSignal(
            direction=TrendDirection.SIDEWAYS,
            strength=30.0,
            confidence=0.6,
            timestamp=time.time()
        )

        assert trend_detector.should_pause_sell(sideways_signal) is False, \
            "震荡市不应该暂停卖出"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试9: 缓存机制
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_cache_mechanism(
        self,
        trend_detector,
        mock_exchange,
        generate_uptrend_ohlcv
    ):
        """测试缓存机制"""
        # 设置模拟K线数据
        mock_exchange.fetch_ohlcv.return_value = generate_uptrend_ohlcv()

        # 第一次调用 - 应该请求API
        signal1 = await trend_detector.detect_trend(mock_exchange)
        assert mock_exchange.fetch_ohlcv.call_count == 1, "第一次应该调用API"

        # 第二次调用（缓存有效期内） - 不应该请求API
        signal2 = await trend_detector.detect_trend(mock_exchange)
        assert mock_exchange.fetch_ohlcv.call_count == 1, "缓存有效期内不应该再次调用API"

        # 验证两次返回的信号相同
        assert signal1.direction == signal2.direction
        assert signal1.strength == signal2.strength
        assert signal1.timestamp == signal2.timestamp

        # 清除缓存后再次调用 - 应该请求API
        trend_detector.clear_cache()
        signal3 = await trend_detector.detect_trend(mock_exchange)
        assert mock_exchange.fetch_ohlcv.call_count == 2, "清除缓存后应该再次调用API"

    @pytest.mark.asyncio
    async def test_cache_expiration(
        self,
        trend_detector,
        mock_exchange,
        generate_uptrend_ohlcv
    ):
        """测试缓存过期机制"""
        # 设置短缓存时间
        trend_detector.cache_ttl = 1  # 1秒

        # 设置模拟K线数据
        mock_exchange.fetch_ohlcv.return_value = generate_uptrend_ohlcv()

        # 第一次调用
        signal1 = await trend_detector.detect_trend(mock_exchange)
        assert mock_exchange.fetch_ohlcv.call_count == 1

        # 等待缓存过期
        time.sleep(1.5)

        # 再次调用 - 缓存已过期，应该重新请求
        signal2 = await trend_detector.detect_trend(mock_exchange)
        assert mock_exchange.fetch_ohlcv.call_count == 2, "缓存过期后应该重新请求API"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试10: 风控状态映射
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_risk_state_mapping(self, trend_detector):
        """测试趋势信号到风控状态的映射"""
        # 强上涨 → 只允许买入
        strong_up = TrendSignal(
            direction=TrendDirection.STRONG_UP,
            strength=70.0,
            confidence=0.85,
            timestamp=time.time()
        )

        assert trend_detector.get_risk_state(strong_up) == RiskState.ALLOW_BUY_ONLY, \
            "强上涨应该只允许买入"

        # 强下跌 → 只允许卖出
        strong_down = TrendSignal(
            direction=TrendDirection.STRONG_DOWN,
            strength=70.0,
            confidence=0.85,
            timestamp=time.time()
        )

        assert trend_detector.get_risk_state(strong_down) == RiskState.ALLOW_SELL_ONLY, \
            "强下跌应该只允许卖出"

        # 震荡市 → 允许所有交易
        sideways = TrendSignal(
            direction=TrendDirection.SIDEWAYS,
            strength=30.0,
            confidence=0.6,
            timestamp=time.time()
        )

        assert trend_detector.get_risk_state(sideways) == RiskState.ALLOW_ALL, \
            "震荡市应该允许所有交易"

        # 温和上涨 → 允许所有交易
        moderate_up = TrendSignal(
            direction=TrendDirection.MODERATE_UP,
            strength=45.0,
            confidence=0.7,
            timestamp=time.time()
        )

        assert trend_detector.get_risk_state(moderate_up) == RiskState.ALLOW_ALL, \
            "温和上涨应该允许所有交易"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 边界情况和错误处理测试
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_api_failure_handling(
        self,
        trend_detector,
        mock_exchange
    ):
        """测试API失败时的降级处理"""
        # 模拟API调用失败
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")

        # 无缓存时 - 返回默认震荡市信号
        signal = await trend_detector.detect_trend(mock_exchange)
        assert signal.direction == TrendDirection.SIDEWAYS, \
            "API失败时应该返回默认震荡市信号"
        assert signal.strength == 0.0
        assert "数据获取失败" in signal.reason

        # 有缓存时 - 返回缓存的信号
        # 先设置一个有效的缓存
        mock_exchange.fetch_ohlcv.side_effect = None
        mock_exchange.fetch_ohlcv.return_value = [[
            1640000000000 + i * 3600000,
            600 + i, 602 + i, 598 + i, 601 + i, 10000
        ] for i in range(100)]

        cached_signal = await trend_detector.detect_trend(mock_exchange)

        # 再次模拟API失败
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")

        # 应该返回缓存的信号
        fallback_signal = await trend_detector.detect_trend(mock_exchange)
        assert fallback_signal.direction == cached_signal.direction
        assert fallback_signal.strength == cached_signal.strength

    def test_momentum_calculation(self, trend_detector):
        """测试动量计算"""
        # 测试上涨动量
        up_data = np.linspace(100, 120, 50)
        momentum = trend_detector._calculate_momentum(up_data, period=14)

        assert len(momentum) == len(up_data)
        # 后半段应该有正动量
        assert np.mean(momentum[-10:]) > 0, "上涨趋势应该有正动量"

        # 测试下跌动量
        down_data = np.linspace(120, 100, 50)
        momentum = trend_detector._calculate_momentum(down_data, period=14)

        # 后半段应该有负动量
        assert np.mean(momentum[-10:]) < 0, "下跌趋势应该有负动量"

    def test_consecutive_counting(self, trend_detector):
        """测试连续涨跌计数"""
        # 连续上涨
        up_data = np.array([100, 101, 102, 103, 104, 105])
        up_count = trend_detector._count_consecutive(up_data, direction='up')
        assert up_count == 5, f"应该有5根连续上涨，实际: {up_count}"

        # 连续下跌
        down_data = np.array([105, 104, 103, 102, 101, 100])
        down_count = trend_detector._count_consecutive(down_data, direction='down')
        assert down_count == 5, f"应该有5根连续下跌，实际: {down_count}"

        # 震荡
        sideways_data = np.array([100, 101, 100, 101, 100])
        up_count = trend_detector._count_consecutive(sideways_data, direction='up')
        assert up_count == 0, "震荡市应该没有连续上涨"

    def test_confidence_calculation(self, trend_detector):
        """测试置信度计算"""
        # 高置信度条件
        high_conf_indicators = {
            'adx': 50.0,
            'ema_divergence': 0.03,
            'momentum': 8.0,
            'consecutive_ups': 5,
            'consecutive_downs': 0
        }

        high_conf = trend_detector._calculate_confidence(high_conf_indicators)
        assert high_conf > 0.8, f"高置信度应该>0.8，实际: {high_conf}"

        # 低置信度条件
        low_conf_indicators = {
            'adx': 15.0,
            'ema_divergence': 0.001,
            'momentum': 1.0,
            'consecutive_ups': 0,
            'consecutive_downs': 0
        }

        low_conf = trend_detector._calculate_confidence(low_conf_indicators)
        assert low_conf < 0.7, f"低置信度应该<0.7，实际: {low_conf}"
        assert 0 <= low_conf <= 1, "置信度应该在0-1之间"
