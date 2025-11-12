"""
技术指标计算模块
计算常用的技术分析指标,用于AI辅助决策

支持的指标:
- RSI (相对强弱指标)
- MACD (指数平滑移动平均线)
- 布林带 (Bollinger Bands)
- EMA (指数移动平均线)
- 成交量分析

🆕 支持多时间周期分析:
- 宏观周期 (Daily/Weekly) - 定大方向
- 中观周期 (4H/1H) - 当前波段
- 微观周期 (15m/5m) - 精准入场点
"""

import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime


class TechnicalIndicators:
    """技术指标计算器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_rsi(self, prices: List[float], period: int = 14) -> Dict:
        """
        计算RSI指标

        Args:
            prices: 价格列表 (最新的在最后)
            period: RSI周期 (默认14)

        Returns:
            {
                'value': RSI值 (0-100),
                'trend': 趋势 (oversold/neutral/overbought),
                'signal': 信号 (strong_buy/buy/neutral/sell/strong_sell)
            }
        """
        if len(prices) < period + 1:
            self.logger.warning(f"RSI计算需要至少{period+1}个价格数据点")
            return {'value': 50.0, 'trend': 'neutral', 'signal': 'neutral'}

        # 计算价格变化
        deltas = np.diff(prices)

        # 分离涨跌
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # 计算平均涨跌
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        # 计算RSI
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # 判断趋势和信号
        if rsi < 30:
            trend = 'oversold'
            signal = 'strong_buy' if rsi < 20 else 'buy'
        elif rsi > 70:
            trend = 'overbought'
            signal = 'strong_sell' if rsi > 80 else 'sell'
        else:
            trend = 'neutral'
            signal = 'neutral'

        return {
            'value': round(rsi, 2),
            'trend': trend,
            'signal': signal
        }

    def calculate_macd(
        self,
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict:
        """
        计算MACD指标

        Args:
            prices: 价格列表
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期

        Returns:
            {
                'macd': MACD值,
                'signal': 信号线值,
                'histogram': 柱状图值,
                'trend': 趋势 (bullish/bearish/neutral),
                'crossover': 交叉状态 (golden_cross/death_cross/none)
            }
        """
        if len(prices) < slow_period + signal_period:
            self.logger.warning(f"MACD计算需要至少{slow_period + signal_period}个数据点")
            return {
                'macd': 0.0,
                'signal': 0.0,
                'histogram': 0.0,
                'trend': 'neutral',
                'crossover': 'none'
            }

        prices_array = np.array(prices)

        # 计算EMA
        ema_fast = self._calculate_ema(prices_array, fast_period)
        ema_slow = self._calculate_ema(prices_array, slow_period)

        # MACD线 = 快线 - 慢线
        macd_line = ema_fast - ema_slow

        # 信号线 = MACD的EMA
        signal_line = self._calculate_ema(macd_line, signal_period)

        # 柱状图 = MACD - 信号线
        histogram = macd_line - signal_line

        # 当前值
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_histogram = histogram[-1]

        # 判断趋势
        if current_histogram > 0:
            trend = 'bullish'
        elif current_histogram < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'

        # 判断交叉
        crossover = 'none'
        if len(histogram) > 1:
            prev_histogram = histogram[-2]
            # 金叉: 从负到正
            if prev_histogram < 0 and current_histogram > 0:
                crossover = 'golden_cross'
            # 死叉: 从正到负
            elif prev_histogram > 0 and current_histogram < 0:
                crossover = 'death_cross'

        return {
            'macd': round(current_macd, 4),
            'signal': round(current_signal, 4),
            'histogram': round(current_histogram, 4),
            'trend': trend,
            'crossover': crossover
        }

    def calculate_bollinger_bands(
        self,
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict:
        """
        计算布林带指标

        Args:
            prices: 价格列表
            period: 周期
            std_dev: 标准差倍数

        Returns:
            {
                'upper': 上轨,
                'middle': 中轨(SMA),
                'lower': 下轨,
                'width': 带宽,
                'position': 价格位置 (above/upper/middle/lower/below),
                'signal': 交易信号
            }
        """
        if len(prices) < period:
            self.logger.warning(f"布林带计算需要至少{period}个数据点")
            return {
                'upper': 0.0,
                'middle': 0.0,
                'lower': 0.0,
                'width': 0.0,
                'position': 'unknown',
                'signal': 'neutral'
            }

        prices_array = np.array(prices[-period:])

        # 中轨 = SMA
        middle = np.mean(prices_array)

        # 标准差
        std = np.std(prices_array)

        # 上下轨
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        # 带宽
        width = upper - lower

        # 当前价格
        current_price = prices[-1]

        # 判断价格位置
        if current_price > upper:
            position = 'above'
            signal = 'sell'  # 突破上轨,超买
        elif current_price > middle:
            position = 'upper'
            signal = 'neutral'
        elif current_price > lower:
            position = 'lower'
            signal = 'neutral'
        elif current_price < lower:
            position = 'below'
            signal = 'buy'  # 突破下轨,超卖
        else:
            position = 'middle'
            signal = 'neutral'

        return {
            'upper': round(upper, 2),
            'middle': round(middle, 2),
            'lower': round(lower, 2),
            'width': round(width, 2),
            'position': position,
            'signal': signal
        }

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """
        计算EMA (对外接口)

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            EMA值
        """
        if len(prices) < period:
            return np.mean(prices)

        prices_array = np.array(prices)
        ema_values = self._calculate_ema(prices_array, period)
        return round(ema_values[-1], 2)

    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """
        计算EMA (内部实现)

        Args:
            prices: 价格数组
            period: 周期

        Returns:
            EMA数组
        """
        if len(prices) < period:
            return prices

        ema = np.zeros_like(prices, dtype=float)
        ema[period - 1] = np.mean(prices[:period])

        multiplier = 2 / (period + 1)

        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]

        return ema

    def calculate_volume_analysis(
        self,
        volumes: List[float],
        prices: List[float],
        period: int = 20
    ) -> Dict:
        """
        计算成交量分析

        Args:
            volumes: 成交量列表
            prices: 价格列表
            period: 周期

        Returns:
            {
                'current_volume': 当前成交量,
                'avg_volume': 平均成交量,
                'volume_ratio': 成交量比率,
                'trend': 趋势 (increasing/decreasing/normal),
                'signal': 信号
            }
        """
        if len(volumes) < period or len(prices) < period:
            return {
                'current_volume': 0.0,
                'avg_volume': 0.0,
                'volume_ratio': 1.0,
                'trend': 'normal',
                'signal': 'neutral'
            }

        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-period:])
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # 判断趋势
        if volume_ratio > 2.0:
            trend = 'increasing'
            # 价格上涨+成交量放大 = 看涨
            price_trend = 'bullish' if prices[-1] > prices[-2] else 'bearish'
            signal = 'buy' if price_trend == 'bullish' else 'sell'
        elif volume_ratio < 0.5:
            trend = 'decreasing'
            signal = 'neutral'  # 成交量萎缩,观望
        else:
            trend = 'normal'
            signal = 'neutral'

        return {
            'current_volume': round(current_volume, 2),
            'avg_volume': round(avg_volume, 2),
            'volume_ratio': round(volume_ratio, 2),
            'trend': trend,
            'signal': signal
        }

    def calculate_all_indicators(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> Dict:
        """
        一次性计算所有指标

        Args:
            prices: 价格列表 (至少需要50个数据点以获得准确结果)
            volumes: 成交量列表

        Returns:
            包含所有指标的字典
        """
        return {
            'rsi': self.calculate_rsi(prices, period=14),
            'macd': self.calculate_macd(prices),
            'bollinger_bands': self.calculate_bollinger_bands(prices, period=20),
            'ema_20': self.calculate_ema(prices, period=20),
            'ema_50': self.calculate_ema(prices, period=50),
            'volume_analysis': self.calculate_volume_analysis(volumes, prices, period=20),
            'timestamp': datetime.now().isoformat()
        }

    def get_overall_signal(self, indicators: Dict) -> Dict:
        """
        综合所有指标,得出总体信号

        Args:
            indicators: calculate_all_indicators返回的指标字典

        Returns:
            {
                'signal': 'strong_buy/buy/neutral/sell/strong_sell',
                'score': -100到100的评分,
                'bullish_count': 看涨指标数量,
                'bearish_count': 看跌指标数量
            }
        """
        bullish_count = 0
        bearish_count = 0

        # RSI信号
        rsi_signal = indicators['rsi']['signal']
        if 'buy' in rsi_signal:
            bullish_count += 2 if rsi_signal == 'strong_buy' else 1
        elif 'sell' in rsi_signal:
            bearish_count += 2 if rsi_signal == 'strong_sell' else 1

        # MACD信号
        macd = indicators['macd']
        if macd['crossover'] == 'golden_cross':
            bullish_count += 2
        elif macd['crossover'] == 'death_cross':
            bearish_count += 2
        elif macd['trend'] == 'bullish':
            bullish_count += 1
        elif macd['trend'] == 'bearish':
            bearish_count += 1

        # 布林带信号
        bb_signal = indicators['bollinger_bands']['signal']
        if bb_signal == 'buy':
            bullish_count += 1
        elif bb_signal == 'sell':
            bearish_count += 1

        # 成交量信号
        vol_signal = indicators['volume_analysis']['signal']
        if vol_signal == 'buy':
            bullish_count += 1
        elif vol_signal == 'sell':
            bearish_count += 1

        # 计算总分
        score = (bullish_count - bearish_count) * 10

        # 判断总体信号
        if score >= 30:
            signal = 'strong_buy'
        elif score >= 10:
            signal = 'buy'
        elif score <= -30:
            signal = 'strong_sell'
        elif score <= -10:
            signal = 'sell'
        else:
            signal = 'neutral'

        return {
            'signal': signal,
            'score': score,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count
        }
