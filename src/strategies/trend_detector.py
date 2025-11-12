"""
趋势识别模块

功能:
1. 分析市场数据，识别趋势方向
2. 计算趋势强度评分
3. 提供交易建议（暂停买入/卖出）
4. 缓存和更新趋势状态

作者: GridBNB-USDT Team
创建日期: 2025-10-28
设计文档: docs/TREND_DETECTOR_DESIGN.md
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

from src.strategies.risk_manager import RiskState


class TrendDirection(Enum):
    """趋势方向枚举"""
    STRONG_UP = "strong_up"          # 强上涨趋势
    MODERATE_UP = "moderate_up"      # 温和上涨趋势
    SIDEWAYS = "sideways"            # 震荡整理
    MODERATE_DOWN = "moderate_down"  # 温和下跌趋势
    STRONG_DOWN = "strong_down"      # 强下跌趋势


@dataclass
class TrendSignal:
    """
    趋势信号数据类

    Attributes:
        direction: 趋势方向
        strength: 趋势强度（0-100）
        confidence: 置信度（0-1）
        timestamp: 信号生成时间
        indicators: 各项技术指标值
        reason: 判断理由描述
    """
    direction: TrendDirection
    strength: float
    confidence: float
    timestamp: float
    indicators: Dict[str, float] = field(default_factory=dict)
    reason: str = ""

    def __repr__(self) -> str:
        return (
            f"TrendSignal(direction={self.direction.value}, "
            f"strength={self.strength:.1f}, "
            f"confidence={self.confidence:.2f})"
        )


class TrendDetector:
    """
    趋势识别器

    核心职责:
    1. 分析K线数据，计算技术指标（EMA, ADX, 动量等）
    2. 综合判断趋势方向和强度
    3. 提供交易建议（是否暂停买入/卖出）
    4. 实现缓存机制，减少重复计算

    示例:
        detector = TrendDetector(
            symbol='BNB/USDT',
            ema_short=20,
            ema_long=50,
            strong_trend_threshold=60.0
        )

        signal = await detector.detect_trend(exchange)

        if detector.should_pause_buy(signal):
            print("强下跌趋势，暂停买入")
        elif detector.should_pause_sell(signal):
            print("强上涨趋势，暂停卖出")
    """

    def __init__(
        self,
        symbol: str,
        ema_short: int = 20,
        ema_long: int = 50,
        adx_period: int = 14,
        strong_trend_threshold: float = 60.0,
        cache_ttl: int = 300
    ):
        """
        初始化趋势识别器

        Args:
            symbol: 交易对（如 'BNB/USDT'）
            ema_short: EMA短周期（默认20）
            ema_long: EMA长周期（默认50）
            adx_period: ADX计算周期（默认14）
            strong_trend_threshold: 强趋势阈值（默认60.0）
            cache_ttl: 缓存有效期（秒，默认300）
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        self.symbol = symbol
        self.ema_short = ema_short
        self.ema_long = ema_long
        self.adx_period = adx_period
        self.strong_trend_threshold = strong_trend_threshold
        self.cache_ttl = cache_ttl

        # 缓存
        self.last_signal: Optional[TrendSignal] = None
        self.last_update: float = 0

        self.logger.info(
            f"趋势识别器初始化 | "
            f"交易对: {symbol} | "
            f"EMA: {ema_short}/{ema_long} | "
            f"ADX周期: {adx_period} | "
            f"强趋势阈值: {strong_trend_threshold}"
        )

    async def detect_trend(self, exchange) -> TrendSignal:
        """
        检测当前市场趋势

        Args:
            exchange: 交易所客户端（IExchange接口）

        Returns:
            TrendSignal: 趋势信号对象

        Raises:
            Exception: K线数据获取失败或计算异常
        """
        # 1. 检查缓存
        if self._is_cache_valid():
            self.logger.debug(
                f"使用缓存的趋势信号 | {self.last_signal.direction.value}"
            )
            return self.last_signal

        # 2. 获取K线数据（4小时级别，最近100根）
        try:
            ohlcv = await exchange.fetch_ohlcv(
                self.symbol,
                timeframe='4h',
                limit=100
            )
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            # 返回上次信号或默认震荡市
            if self.last_signal:
                return self.last_signal
            return self._create_default_signal()

        # 3. 计算技术指标
        indicators = self._calculate_indicators(ohlcv)

        # 4. 判断趋势方向
        direction = self._determine_direction(indicators)

        # 5. 计算趋势强度
        strength = self._calculate_strength(indicators)

        # 6. 计算置信度
        confidence = self._calculate_confidence(indicators)

        # 7. 生成判断理由
        reason = self._generate_reason(direction, strength, indicators)

        # 8. 创建趋势信号
        signal = TrendSignal(
            direction=direction,
            strength=strength,
            confidence=confidence,
            timestamp=time.time(),
            indicators=indicators,
            reason=reason
        )

        # 9. 更新缓存
        self.last_signal = signal
        self.last_update = time.time()

        self.logger.info(
            f"趋势检测完成 | {signal.direction.value} | "
            f"强度: {signal.strength:.1f} | "
            f"置信度: {signal.confidence:.2f} | "
            f"{reason}"
        )

        return signal

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.last_signal:
            return False

        elapsed = time.time() - self.last_update
        return elapsed < self.cache_ttl

    def _create_default_signal(self) -> TrendSignal:
        """创建默认信号（震荡市）"""
        return TrendSignal(
            direction=TrendDirection.SIDEWAYS,
            strength=0.0,
            confidence=0.5,
            timestamp=time.time(),
            indicators={},
            reason="数据获取失败，默认震荡市"
        )

    def _calculate_indicators(
        self,
        ohlcv: List[List[float]]
    ) -> Dict[str, float]:
        """
        计算技术指标

        Args:
            ohlcv: K线数据 [[timestamp, open, high, low, close, volume], ...]

        Returns:
            Dict: 包含所有计算指标的字典
        """
        # 提取价格和成交量数据
        closes = np.array([candle[4] for candle in ohlcv])
        highs = np.array([candle[2] for candle in ohlcv])
        lows = np.array([candle[3] for candle in ohlcv])
        volumes = np.array([candle[5] for candle in ohlcv])

        # 1. EMA 计算
        ema_short = self._calculate_ema(closes, self.ema_short)
        ema_long = self._calculate_ema(closes, self.ema_long)

        # EMA 分离度（标准化，相对于长期EMA）
        ema_divergence = (ema_short[-1] - ema_long[-1]) / ema_long[-1]

        # 2. ADX 计算
        adx = self._calculate_adx(highs, lows, closes, self.adx_period)

        # 3. 动量计算（14周期价格变化率）
        momentum = self._calculate_momentum(closes, period=14)

        # 4. 成交量分析
        volume_ma = np.mean(volumes[-20:])  # 20周期均量
        current_volume = volumes[-1]
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0

        # 5. 连续涨跌计数
        consecutive_ups = self._count_consecutive(closes, direction='up')
        consecutive_downs = self._count_consecutive(closes, direction='down')

        return {
            'ema_short': float(ema_short[-1]),
            'ema_long': float(ema_long[-1]),
            'ema_divergence': float(ema_divergence),
            'adx': float(adx[-1]),
            'momentum': float(momentum[-1]),
            'volume_ratio': float(volume_ratio),
            'consecutive_ups': int(consecutive_ups),
            'consecutive_downs': int(consecutive_downs),
            'current_price': float(closes[-1])
        }

    def _calculate_ema(
        self,
        data: np.ndarray,
        period: int
    ) -> np.ndarray:
        """
        计算指数移动平均（EMA）

        Args:
            data: 价格数据
            period: EMA周期

        Returns:
            np.ndarray: EMA序列
        """
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]

        return ema

    def _calculate_adx(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int
    ) -> np.ndarray:
        """
        计算平均趋向指数（ADX）

        Args:
            highs: 最高价序列
            lows: 最低价序列
            closes: 收盘价序列
            period: ADX周期

        Returns:
            np.ndarray: ADX序列
        """
        # 1. 计算 +DM 和 -DM
        high_diff = np.diff(highs)
        low_diff = -np.diff(lows)

        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        # 2. 计算 TR (True Range)
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        # 3. 计算平滑的 +DI 和 -DI
        atr = self._calculate_ema(tr, period)

        plus_di = 100 * self._calculate_ema(plus_dm, period) / atr
        minus_di = 100 * self._calculate_ema(minus_dm, period) / atr

        # 4. 计算 DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)

        # 5. 计算 ADX
        adx = self._calculate_ema(dx, period)

        # 补齐第一个元素（因为diff减少了一个元素）
        adx = np.concatenate([[adx[0]], adx])

        return adx

    def _calculate_momentum(
        self,
        data: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """
        计算价格动量（变化率）

        Args:
            data: 价格数据
            period: 动量周期

        Returns:
            np.ndarray: 动量序列（百分比）
        """
        momentum = np.zeros_like(data)

        for i in range(period, len(data)):
            momentum[i] = (data[i] - data[i-period]) / data[i-period] * 100

        return momentum

    def _count_consecutive(
        self,
        data: np.ndarray,
        direction: str = 'up'
    ) -> int:
        """
        计算连续涨跌根数

        Args:
            data: 价格数据
            direction: 'up' 或 'down'

        Returns:
            int: 连续根数
        """
        if len(data) < 2:
            return 0

        count = 0
        for i in range(len(data)-1, 0, -1):
            if direction == 'up':
                if data[i] > data[i-1]:
                    count += 1
                else:
                    break
            else:  # down
                if data[i] < data[i-1]:
                    count += 1
                else:
                    break

        return count

    def _determine_direction(
        self,
        indicators: Dict[str, float]
    ) -> TrendDirection:
        """
        判断趋势方向

        Args:
            indicators: 技术指标字典

        Returns:
            TrendDirection: 趋势方向枚举
        """
        ema_div = indicators['ema_divergence']
        adx = indicators['adx']
        momentum = indicators['momentum']
        consecutive_ups = indicators['consecutive_ups']
        consecutive_downs = indicators['consecutive_downs']

        # 强上涨趋势条件
        if (ema_div > 0.02 and  # EMA 上穿 2%以上
            adx > 40 and  # ADX 强趋势
            momentum > 5 and  # 动量强
            consecutive_ups >= 3):  # 连续3根上涨
            return TrendDirection.STRONG_UP

        # 温和上涨趋势
        elif ema_div > 0.005 and adx > 25:
            return TrendDirection.MODERATE_UP

        # 强下跌趋势
        elif (ema_div < -0.02 and
              adx > 40 and
              momentum < -5 and
              consecutive_downs >= 3):
            return TrendDirection.STRONG_DOWN

        # 温和下跌趋势
        elif ema_div < -0.005 and adx > 25:
            return TrendDirection.MODERATE_DOWN

        # 震荡市场
        else:
            return TrendDirection.SIDEWAYS

    def _calculate_strength(
        self,
        indicators: Dict[str, float]
    ) -> float:
        """
        计算趋势强度（0-100）

        Args:
            indicators: 技术指标字典

        Returns:
            float: 趋势强度评分
        """
        # 1. ADX 评分（0-50）
        adx = min(indicators['adx'], 100)
        adx_score = (adx / 100) * 50

        # 2. EMA 分离度评分（0-30）
        ema_div = abs(indicators['ema_divergence'])
        ema_score = min(ema_div * 500, 30)  # 6%分离度 = 满分30

        # 3. 动量评分（0-15）
        momentum = abs(indicators['momentum'])
        momentum_score = min(momentum / 10 * 15, 15)

        # 4. 成交量评分（0-5）
        volume_ratio = indicators['volume_ratio']
        volume_score = min((volume_ratio - 1) * 5, 5) if volume_ratio > 1 else 0

        # 总分
        total_score = adx_score + ema_score + momentum_score + volume_score

        return min(max(total_score, 0), 100)

    def _calculate_confidence(
        self,
        indicators: Dict[str, float]
    ) -> float:
        """
        计算置信度（0-1）

        Args:
            indicators: 技术指标字典

        Returns:
            float: 置信度
        """
        # 基于多个指标的一致性计算置信度
        confidence = 0.5  # 基础置信度

        # ADX 贡献（越高越自信）
        if indicators['adx'] > 40:
            confidence += 0.2
        elif indicators['adx'] > 25:
            confidence += 0.1

        # EMA 分离度贡献
        if abs(indicators['ema_divergence']) > 0.02:
            confidence += 0.15

        # 动量贡献
        if abs(indicators['momentum']) > 5:
            confidence += 0.1

        # 连续涨跌贡献
        if indicators['consecutive_ups'] >= 3 or indicators['consecutive_downs'] >= 3:
            confidence += 0.05

        return min(confidence, 1.0)

    def _generate_reason(
        self,
        direction: TrendDirection,
        strength: float,
        indicators: Dict[str, float]
    ) -> str:
        """
        生成趋势判断理由

        Args:
            direction: 趋势方向
            strength: 趋势强度
            indicators: 技术指标字典

        Returns:
            str: 判断理由描述
        """
        reasons = []

        # EMA 状态
        ema_div = indicators['ema_divergence']
        if ema_div > 0.01:
            reasons.append(f"EMA金叉 {ema_div*100:.1f}%")
        elif ema_div < -0.01:
            reasons.append(f"EMA死叉 {abs(ema_div)*100:.1f}%")

        # ADX 状态
        adx = indicators['adx']
        if adx > 40:
            reasons.append(f"ADX强趋势 {adx:.0f}")
        elif adx > 25:
            reasons.append(f"ADX中等趋势 {adx:.0f}")

        # 动量状态
        momentum = indicators['momentum']
        if abs(momentum) > 5:
            direction_text = "上涨" if momentum > 0 else "下跌"
            reasons.append(f"{direction_text}动量 {abs(momentum):.1f}%")

        # 连续涨跌
        if indicators['consecutive_ups'] >= 3:
            reasons.append(f"连续{indicators['consecutive_ups']}根上涨")
        elif indicators['consecutive_downs'] >= 3:
            reasons.append(f"连续{indicators['consecutive_downs']}根下跌")

        # 成交量
        volume_ratio = indicators['volume_ratio']
        if volume_ratio > 1.5:
            reasons.append(f"成交量放大 {volume_ratio:.1f}x")

        if not reasons:
            reasons.append("震荡整理")

        return ", ".join(reasons)

    def should_pause_buy(self, signal: TrendSignal) -> bool:
        """
        判断是否应暂停买入

        Args:
            signal: 趋势信号

        Returns:
            bool: True表示应暂停买入
        """
        return (
            signal.direction == TrendDirection.STRONG_DOWN and
            signal.strength > self.strong_trend_threshold and
            signal.confidence > 0.7
        )

    def should_pause_sell(self, signal: TrendSignal) -> bool:
        """
        判断是否应暂停卖出

        Args:
            signal: 趋势信号

        Returns:
            bool: True表示应暂停卖出
        """
        return (
            signal.direction == TrendDirection.STRONG_UP and
            signal.strength > self.strong_trend_threshold and
            signal.confidence > 0.7
        )

    def get_risk_state(self, signal: TrendSignal) -> RiskState:
        """
        获取建议的风控状态

        Args:
            signal: 趋势信号

        Returns:
            RiskState: 风控状态枚举
        """
        if self.should_pause_buy(signal):
            return RiskState.ALLOW_SELL_ONLY
        elif self.should_pause_sell(signal):
            return RiskState.ALLOW_BUY_ONLY
        else:
            return RiskState.ALLOW_ALL

    def clear_cache(self):
        """清除缓存，强制下次检测时重新计算"""
        self.last_signal = None
        self.last_update = 0
        self.logger.debug("趋势缓存已清除")
