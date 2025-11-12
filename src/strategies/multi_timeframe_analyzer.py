"""
多时间周期分析模块
Multi-Timeframe Analysis Module

功能:
- 宏观周期分析 (Daily/Weekly) - 定大格局
- 中观周期分析 (4H) - 定中期趋势
- 微观周期分析 (1H) - 当前执行周期
- 多周期共振检测
- 关键支撑阻力位识别
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from .technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


@dataclass
class TimeframeTrend:
    """单个时间周期的趋势分析结果"""
    timeframe: str  # 时间周期
    trend: str  # uptrend/downtrend/ranging
    strength: int  # 趋势强度 0-100
    rsi: float
    macd_signal: str
    price_change_percent: float  # 周期内价格变化百分比


@dataclass
class KeyLevel:
    """关键支撑/阻力位"""
    price: float
    level_type: str  # 'support' or 'resistance'
    strength: int  # 强度 0-100
    distance_percent: float  # 距离当前价格的百分比


class MultiTimeframeAnalyzer:
    """
    多时间周期趋势分析器

    同时分析多个时间周期，识别趋势共振和背离
    """

    def __init__(self):
        """初始化多时间周期分析器"""
        self.indicator_calculator = TechnicalIndicators()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze_timeframes(
        self,
        exchange,
        symbol: str,
        current_price: float
    ) -> Dict[str, Any]:
        """
        分析多个时间周期的趋势

        Args:
            exchange: 交易所客户端
            symbol: 交易对
            current_price: 当前价格

        Returns:
            多时间周期分析结果
        """
        try:
            # 并行获取多个时间周期的数据
            daily_data = await self._fetch_and_analyze(
                exchange, symbol, '1d', 30, 'macro_daily'
            )
            four_hour_data = await self._fetch_and_analyze(
                exchange, symbol, '4h', 42, 'medium_4h'
            )
            one_hour_data = await self._fetch_and_analyze(
                exchange, symbol, '1h', 100, 'micro_1h'
            )

            # 检查多周期趋势一致性
            alignment = self._check_alignment(
                daily_data['trend'],
                four_hour_data['trend'],
                one_hour_data['trend']
            )

            # 识别关键支撑阻力位
            key_levels = self._identify_key_levels(
                daily_data,
                four_hour_data,
                one_hour_data,
                current_price
            )

            # 计算综合趋势强度
            overall_strength = self._calculate_overall_strength(
                daily_data,
                four_hour_data,
                one_hour_data,
                alignment
            )

            # 生成交易建议
            trading_recommendation = self._generate_recommendation(
                alignment,
                daily_data,
                four_hour_data,
                one_hour_data,
                key_levels,
                overall_strength
            )

            return {
                "macro_daily": {
                    "trend": daily_data['trend'],
                    "strength": daily_data['strength'],
                    "price_change": daily_data['price_change'],
                    "rsi": daily_data['rsi']['value'],
                    "macd_state": daily_data['macd']['trend'],
                    "key_levels": daily_data.get('levels', {})
                },
                "medium_4h": {
                    "trend": four_hour_data['trend'],
                    "strength": four_hour_data['strength'],
                    "price_change": four_hour_data['price_change'],
                    "rsi": four_hour_data['rsi']['value'],
                    "macd_state": four_hour_data['macd']['trend'],
                    "macd_crossover": four_hour_data['macd']['crossover']
                },
                "micro_1h": {
                    "trend": one_hour_data['trend'],
                    "strength": one_hour_data['strength'],
                    "price_change": one_hour_data['price_change'],
                    "rsi": one_hour_data['rsi']['value'],
                    "macd_state": one_hour_data['macd']['trend'],
                    "bollinger_position": one_hour_data['bollinger']['position']
                },
                "alignment": alignment,
                "key_levels": key_levels,
                "overall_strength": overall_strength,
                "trading_recommendation": trading_recommendation,
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"多时间周期分析失败: {e}", exc_info=True)
            return self._get_empty_analysis()

    async def _fetch_and_analyze(
        self,
        exchange,
        symbol: str,
        timeframe: str,
        limit: int,
        name: str
    ) -> Dict[str, Any]:
        """
        获取并分析单个时间周期的数据

        Args:
            exchange: 交易所客户端
            symbol: 交易对
            timeframe: 时间周期 (1h, 4h, 1d等)
            limit: K线数量
            name: 周期名称

        Returns:
            分析结果
        """
        try:
            # 获取K线数据
            klines = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            if not klines or len(klines) < 20:
                self.logger.warning(f"{name} K线数据不足")
                return self._get_empty_timeframe_data()

            # 提取价格数据
            close_prices = [k[4] for k in klines]
            high_prices = [k[2] for k in klines]
            low_prices = [k[3] for k in klines]

            # 计算技术指标
            rsi = self.indicator_calculator.calculate_rsi(close_prices, period=14)
            macd = self.indicator_calculator.calculate_macd(close_prices)
            bollinger = self.indicator_calculator.calculate_bollinger_bands(close_prices)

            # 计算价格变化
            price_change = ((close_prices[-1] - close_prices[0]) / close_prices[0]) * 100

            # 判断趋势
            trend = self._determine_trend(close_prices, rsi, macd, price_change)

            # 计算趋势强度
            strength = self._calculate_trend_strength(
                close_prices,
                rsi,
                macd,
                trend
            )

            # 识别支撑阻力位
            levels = self._find_support_resistance(
                high_prices,
                low_prices,
                close_prices
            )

            return {
                'trend': trend,
                'strength': strength,
                'price_change': round(price_change, 2),
                'rsi': rsi,
                'macd': macd,
                'bollinger': bollinger,
                'levels': levels,
                'close_prices': close_prices,
                'high_prices': high_prices,
                'low_prices': low_prices
            }

        except Exception as e:
            self.logger.error(f"{name} 分析失败: {e}", exc_info=True)
            return self._get_empty_timeframe_data()

    def _determine_trend(
        self,
        prices: List[float],
        rsi: Dict,
        macd: Dict,
        price_change: float
    ) -> str:
        """
        判断趋势方向

        Args:
            prices: 价格列表
            rsi: RSI指标
            macd: MACD指标
            price_change: 价格变化百分比

        Returns:
            'uptrend', 'downtrend', 或 'ranging'
        """
        # 计算均线
        if len(prices) >= 50:
            ma20 = np.mean(prices[-20:])
            ma50 = np.mean(prices[-50:])
            current_price = prices[-1]

            # 多头排列：价格 > MA20 > MA50
            if current_price > ma20 > ma50:
                trend_score = 2
            # 空头排列：价格 < MA20 < MA50
            elif current_price < ma20 < ma50:
                trend_score = -2
            else:
                trend_score = 0
        else:
            trend_score = 0

        # MACD信号
        if macd['trend'] == 'bullish':
            trend_score += 1
        elif macd['trend'] == 'bearish':
            trend_score -= 1

        # 价格变化
        if price_change > 5:
            trend_score += 1
        elif price_change < -5:
            trend_score -= 1

        # 综合判断
        if trend_score >= 2:
            return 'uptrend'
        elif trend_score <= -2:
            return 'downtrend'
        else:
            return 'ranging'

    def _calculate_trend_strength(
        self,
        prices: List[float],
        rsi: Dict,
        macd: Dict,
        trend: str
    ) -> int:
        """
        计算趋势强度 (0-100)

        Args:
            prices: 价格列表
            rsi: RSI指标
            macd: MACD指标
            trend: 趋势方向

        Returns:
            趋势强度分数
        """
        strength = 50  # 基础分数

        # RSI强度
        rsi_value = rsi['value']
        if trend == 'uptrend':
            # 上涨趋势中，RSI越高（但不超买）越强
            if 50 < rsi_value < 70:
                strength += 20
            elif rsi_value >= 70:
                strength += 10  # 超买减分
        elif trend == 'downtrend':
            # 下跌趋势中，RSI越低（但不超卖）越强
            if 30 < rsi_value < 50:
                strength += 20
            elif rsi_value <= 30:
                strength += 10  # 超卖减分

        # MACD强度
        histogram = abs(macd.get('histogram', 0))
        if histogram > 0.5:
            strength += 15
        elif histogram > 0.2:
            strength += 10
        elif histogram > 0.1:
            strength += 5

        # 价格动能
        if len(prices) >= 20:
            recent_volatility = np.std(prices[-20:])
            avg_volatility = np.std(prices)
            if recent_volatility > avg_volatility * 1.2:
                strength += 15  # 波动率增加表示趋势强化

        # 限制在0-100范围
        return max(0, min(100, strength))

    def _find_support_resistance(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Dict[str, float]:
        """
        识别支撑和阻力位

        Args:
            highs: 最高价列表
            lows: 最低价列表
            closes: 收盘价列表

        Returns:
            关键支撑阻力位
        """
        if len(closes) < 20:
            return {}

        # 取最近20个交易日
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        recent_closes = closes[-20:]

        # 寻找局部高点和低点
        resistance_candidates = []
        support_candidates = []

        for i in range(1, len(recent_closes) - 1):
            # 局部高点：比前后都高
            if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i+1]:
                resistance_candidates.append(recent_highs[i])

            # 局部低点：比前后都低
            if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i+1]:
                support_candidates.append(recent_lows[i])

        # 选择最强的支撑和阻力
        current_price = closes[-1]

        # 阻力位：高于当前价格的最低高点
        resistance = None
        if resistance_candidates:
            above_price = [r for r in resistance_candidates if r > current_price]
            if above_price:
                resistance = min(above_price)

        # 支撑位：低于当前价格的最高低点
        support = None
        if support_candidates:
            below_price = [s for s in support_candidates if s < current_price]
            if below_price:
                support = max(below_price)

        return {
            'resistance': round(resistance, 2) if resistance else None,
            'support': round(support, 2) if support else None
        }

    def _check_alignment(
        self,
        daily_trend: str,
        four_h_trend: str,
        one_h_trend: str
    ) -> str:
        """
        检查多周期趋势一致性

        Args:
            daily_trend: 日线趋势
            four_h_trend: 4小时趋势
            one_h_trend: 1小时趋势

        Returns:
            共振状态描述
        """
        trends = [daily_trend, four_h_trend, one_h_trend]

        # 如果任何周期数据不可用，返回未知状态
        if any(t == 'unknown' for t in trends):
            return "unknown"

        # 三周期完全一致
        if all(t == 'uptrend' for t in trends):
            return "strong_bullish_resonance"  # 强烈看涨共振
        elif all(t == 'downtrend' for t in trends):
            return "strong_bearish_resonance"  # 强烈看跌共振

        # 危险背离：日线与1小时相反
        if daily_trend == 'downtrend' and one_h_trend == 'uptrend':
            return "dangerous_counter_trend_bounce"  # 危险的逆势反弹（接飞刀）
        elif daily_trend == 'uptrend' and one_h_trend == 'downtrend':
            return "healthy_pullback"  # 健康回调

        # 部分一致
        uptrend_count = trends.count('uptrend')
        downtrend_count = trends.count('downtrend')

        if uptrend_count >= 2:
            return "partial_bullish_alignment"  # 部分看涨一致
        elif downtrend_count >= 2:
            return "partial_bearish_alignment"  # 部分看跌一致
        else:
            return "mixed_signals"  # 混合信号

    def _identify_key_levels(
        self,
        daily: Dict,
        four_h: Dict,
        one_h: Dict,
        current_price: float
    ) -> Dict[str, Any]:
        """
        识别关键支撑阻力位

        Args:
            daily: 日线数据
            four_h: 4小时数据
            one_h: 1小时数据
            current_price: 当前价格

        Returns:
            关键价位信息
        """
        levels = {
            'strong_resistance': None,
            'strong_support': None,
            'nearest_resistance': None,
            'nearest_support': None
        }

        # 收集所有支撑阻力位
        all_resistances = []
        all_supports = []

        for data, weight in [(daily, 3), (four_h, 2), (one_h, 1)]:
            daily_levels = data.get('levels', {})
            if daily_levels.get('resistance'):
                all_resistances.append({
                    'price': daily_levels['resistance'],
                    'weight': weight
                })
            if daily_levels.get('support'):
                all_supports.append({
                    'price': daily_levels['support'],
                    'weight': weight
                })

        # 找到最强的阻力位（权重最高且最近的）
        if all_resistances:
            above_current = [r for r in all_resistances if r['price'] > current_price]
            if above_current:
                # 按权重和距离排序
                above_current.sort(key=lambda x: (-x['weight'], abs(x['price'] - current_price)))
                levels['strong_resistance'] = round(above_current[0]['price'], 2)
                levels['nearest_resistance'] = round(
                    min(above_current, key=lambda x: abs(x['price'] - current_price))['price'],
                    2
                )

        # 找到最强的支撑位
        if all_supports:
            below_current = [s for s in all_supports if s['price'] < current_price]
            if below_current:
                below_current.sort(key=lambda x: (-x['weight'], abs(x['price'] - current_price)))
                levels['strong_support'] = round(below_current[0]['price'], 2)
                levels['nearest_support'] = round(
                    max(below_current, key=lambda x: abs(x['price'] - current_price))['price'],
                    2
                )

        return levels

    def _calculate_overall_strength(
        self,
        daily: Dict,
        four_h: Dict,
        one_h: Dict,
        alignment: str
    ) -> int:
        """
        计算综合趋势强度

        Args:
            daily: 日线数据
            four_h: 4小时数据
            one_h: 1小时数据
            alignment: 共振状态

        Returns:
            综合强度分数 (0-100)
        """
        # 基础分数：各周期强度的加权平均
        weighted_strength = (
            daily['strength'] * 0.5 +
            four_h['strength'] * 0.3 +
            one_h['strength'] * 0.2
        )

        # 共振加成
        if 'strong_bullish_resonance' in alignment or 'strong_bearish_resonance' in alignment:
            weighted_strength += 20
        elif 'partial' in alignment:
            weighted_strength += 10
        elif 'dangerous' in alignment:
            weighted_strength -= 20  # 背离惩罚

        return max(0, min(100, int(weighted_strength)))

    def _generate_recommendation(
        self,
        alignment: str,
        daily: Dict,
        four_h: Dict,
        one_h: Dict,
        key_levels: Dict,
        overall_strength: int
    ) -> str:
        """
        生成交易建议

        Args:
            alignment: 共振状态
            daily: 日线数据
            four_h: 4小时数据
            one_h: 1小时数据
            key_levels: 关键价位
            overall_strength: 综合强度

        Returns:
            交易建议描述
        """
        recommendations = []

        # 共振分析
        if alignment == "strong_bullish_resonance":
            recommendations.append("三周期强烈看涨共振，趋势向上明确")
        elif alignment == "strong_bearish_resonance":
            recommendations.append("三周期强烈看跌共振，趋势向下明确")
        elif alignment == "dangerous_counter_trend_bounce":
            recommendations.append("⚠️ 警告：日线下跌但1H反弹，典型'接飞刀'场景，风险极高")
        elif alignment == "healthy_pullback":
            recommendations.append("日线上涨中的健康回调，可等待低位买入机会")

        # 趋势强度分析
        if overall_strength >= 70:
            recommendations.append(f"趋势强度极高({overall_strength}/100)，可顺势操作")
        elif overall_strength >= 50:
            recommendations.append(f"趋势强度中等({overall_strength}/100)，谨慎顺势")
        else:
            recommendations.append(f"趋势强度较弱({overall_strength}/100)，建议观望")

        # 关键价位分析
        if key_levels.get('nearest_resistance'):
            recommendations.append(
                f"上方{key_levels['nearest_resistance']}附近有阻力位，短期突破可能困难"
            )
        if key_levels.get('nearest_support'):
            recommendations.append(
                f"下方{key_levels['nearest_support']}附近有支撑位，回调可能有限"
            )

        return "; ".join(recommendations) if recommendations else "趋势不明确，建议观望"

    def _get_empty_timeframe_data(self) -> Dict[str, Any]:
        """返回空的时间周期数据"""
        return {
            'trend': 'unknown',
            'strength': 0,
            'price_change': 0,
            'rsi': {'value': 50, 'trend': 'neutral', 'signal': 'neutral'},
            'macd': {'trend': 'neutral', 'crossover': 'none'},
            'bollinger': {'position': 'unknown'},
            'levels': {}
        }

    def _get_empty_analysis(self) -> Dict[str, Any]:
        """返回空的分析结果"""
        return {
            "macro_daily": {
                "trend": "unknown",
                "strength": 0,
                "price_change": 0,
                "rsi": 50,
                "macd_state": "neutral",
                "key_levels": {}
            },
            "medium_4h": {
                "trend": "unknown",
                "strength": 0,
                "price_change": 0,
                "rsi": 50,
                "macd_state": "neutral",
                "macd_crossover": "none"
            },
            "micro_1h": {
                "trend": "unknown",
                "strength": 0,
                "price_change": 0,
                "rsi": 50,
                "macd_state": "neutral",
                "bollinger_position": "unknown"
            },
            "alignment": "unknown",
            "key_levels": {},
            "overall_strength": 0,
            "trading_recommendation": "数据不可用",
            "analysis_timestamp": datetime.now().isoformat()
        }


# 便捷函数
async def analyze_multi_timeframe(
    exchange,
    symbol: str,
    current_price: float
) -> Dict[str, Any]:
    """
    便捷的多时间周期分析函数

    Args:
        exchange: 交易所客户端
        symbol: 交易对
        current_price: 当前价格

    Returns:
        多时间周期分析结果
    """
    analyzer = MultiTimeframeAnalyzer()
    return await analyzer.analyze_timeframes(exchange, symbol, current_price)
