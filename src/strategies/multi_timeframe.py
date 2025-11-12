"""
多时间周期分析模块

提供跨时间周期的市场趋势分析,让AI能够：
- 宏观周期 (Daily/Weekly): 定大方向 (牛/熊/震荡)
- 中观周期 (4H/1H): 当前波段判断
- 微观周期 (15m/5m): 精准入场点

核心思想：
"日线看方向，小时看波段，分钟找入场"
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np


class MultiTimeframeAnalyzer:
    """多时间周期分析器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze_multi_timeframe(
        self,
        exchange,
        symbol: str,
        technical_calculator
    ) -> Dict:
        """
        执行多时间周期分析

        Args:
            exchange: 交易所实例
            symbol: 交易对
            technical_calculator: TechnicalIndicators 实例

        Returns:
            多时间周期分析结果
        """
        try:
            # 获取不同周期的K线数据
            timeframes_data = await self._fetch_multi_timeframe_data(
                exchange, symbol
            )

            # 分析每个时间周期
            macro_analysis = self._analyze_macro_trend(
                timeframes_data['1d'],
                technical_calculator
            )

            meso_analysis = self._analyze_meso_trend(
                timeframes_data['4h'],
                technical_calculator
            )

            micro_analysis = self._analyze_micro_trend(
                timeframes_data['15m'],
                technical_calculator
            )

            # 综合判断
            overall_context = self._综合多周期判断(
                macro_analysis,
                meso_analysis,
                micro_analysis
            )

            return {
                'macro_trend': macro_analysis,  # 宏观趋势
                'meso_trend': meso_analysis,    # 中观波段
                'micro_trend': micro_analysis,  # 微观入场点
                'overall_context': overall_context,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"多时间周期分析失败: {e}", exc_info=True)
            return self._get_default_analysis()

    async def _fetch_multi_timeframe_data(
        self,
        exchange,
        symbol: str
    ) -> Dict[str, List]:
        """
        获取多个时间周期的K线数据

        Args:
            exchange: 交易所实例
            symbol: 交易对

        Returns:
            {'1d': [...], '4h': [...], '15m': [...]}
        """
        timeframes = {
            '1d': 100,   # 日线: 100根足够分析趋势
            '4h': 100,   # 4小时: 100根覆盖约2周
            '15m': 100   # 15分钟: 100根覆盖约1天
        }

        result = {}

        for timeframe, limit in timeframes.items():
            try:
                klines = await exchange.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    limit=limit
                )

                if klines and len(klines) >= 50:
                    result[timeframe] = klines
                    self.logger.debug(f"成功获取 {timeframe} K线: {len(klines)}根")
                else:
                    self.logger.warning(f"{timeframe} K线数据不足")
                    result[timeframe] = []

            except Exception as e:
                self.logger.error(f"获取 {timeframe} K线失败: {e}")
                result[timeframe] = []

        return result

    def _analyze_macro_trend(
        self,
        klines: List,
        calc
    ) -> Dict:
        """
        分析宏观趋势 (日线级别)

        关键判断：
        - 价格相对 EMA200 的位置 (多空分水岭)
        - MACD 状态 (趋势强度)
        - RSI 是否极端 (超买超卖)

        Returns:
            {
                'direction': 'bullish/bearish/neutral',
                'strength': 'strong/moderate/weak',
                'description': '文字描述',
                'key_levels': {'support': x, 'resistance': y}
            }
        """
        if not klines or len(klines) < 50:
            return self._default_macro_trend()

        prices = [float(k[4]) for k in klines]  # 收盘价
        current_price = prices[-1]

        # 计算关键指标
        ema_200 = calc.calculate_ema(prices, period=200) if len(prices) >= 200 else calc.calculate_ema(prices, period=50)
        ema_50 = calc.calculate_ema(prices, period=50)
        macd_info = calc.calculate_macd(prices)
        rsi_info = calc.calculate_rsi(prices, period=14)

        # 判断趋势方向
        if current_price > ema_200 and current_price > ema_50:
            direction = 'bullish'
            description = f"价格位于EMA200({ema_200:.2f})上方，日线多头趋势"
        elif current_price < ema_200 and current_price < ema_50:
            direction = 'bearish'
            description = f"价格位于EMA200({ema_200:.2f})下方，日线空头趋势"
        else:
            direction = 'neutral'
            description = "价格在关键均线之间震荡，趋势不明"

        # 判断趋势强度
        macd_histogram = abs(macd_info['histogram'])
        if macd_histogram > 0.5 and macd_info['trend'] in ['bullish', 'bearish']:
            strength = 'strong'
        elif macd_histogram > 0.2:
            strength = 'moderate'
        else:
            strength = 'weak'

        # 计算关键支撑阻力位 (简化版: 最近的高低点)
        recent_high = max(prices[-20:])
        recent_low = min(prices[-20:])

        return {
            'direction': direction,
            'strength': strength,
            'description': description,
            'key_levels': {
                'ema_200': round(ema_200, 2),
                'resistance': round(recent_high, 2),
                'support': round(recent_low, 2)
            },
            'rsi_extreme': rsi_info['trend'],  # oversold/neutral/overbought
            'macd_state': macd_info['trend']
        }

    def _analyze_meso_trend(
        self,
        klines: List,
        calc
    ) -> Dict:
        """
        分析中观波段 (4小时级别)

        关键判断：
        - 短期趋势 (EMA20/50)
        - 波段高低点
        - MACD 交叉情况
        """
        if not klines or len(klines) < 50:
            return self._default_meso_trend()

        prices = [float(k[4]) for k in klines]
        current_price = prices[-1]

        ema_20 = calc.calculate_ema(prices, period=20)
        ema_50 = calc.calculate_ema(prices, period=50)
        macd_info = calc.calculate_macd(prices)

        # 波段方向
        if current_price > ema_20 > ema_50:
            wave_direction = 'upward'
            description = "4小时级别上升波段"
        elif current_price < ema_20 < ema_50:
            wave_direction = 'downward'
            description = "4小时级别下降波段"
        else:
            wave_direction = 'sideways'
            description = "4小时级别横盘震荡"

        # MACD 状态
        macd_signal = "金叉" if macd_info['crossover'] == 'golden_cross' else \
                      "死叉" if macd_info['crossover'] == 'death_cross' else \
                      "持续" + macd_info['trend']

        return {
            'wave_direction': wave_direction,
            'description': description,
            'ema_alignment': f"EMA20: {ema_20:.2f}, EMA50: {ema_50:.2f}",
            'macd_signal': macd_signal,
            'recent_swing_high': round(max(prices[-20:]), 2),
            'recent_swing_low': round(min(prices[-20:]), 2)
        }

    def _analyze_micro_trend(
        self,
        klines: List,
        calc
    ) -> Dict:
        """
        分析微观入场点 (15分钟级别)

        关键判断：
        - 短期动量 (RSI)
        - 布林带位置
        - 是否超买超卖
        """
        if not klines or len(klines) < 30:
            return self._default_micro_trend()

        prices = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]

        rsi_info = calc.calculate_rsi(prices, period=14)
        bb_info = calc.calculate_bollinger_bands(prices, period=20)
        vol_info = calc.calculate_volume_analysis(volumes, prices, period=20)

        # 入场时机判断
        if rsi_info['value'] < 30 and bb_info['position'] == 'below':
            entry_signal = 'buy_opportunity'
            description = "15分钟超卖，接近布林下轨，可能反弹"
        elif rsi_info['value'] > 70 and bb_info['position'] == 'above':
            entry_signal = 'sell_opportunity'
            description = "15分钟超买，接近布林上轨，可能回调"
        elif vol_info['trend'] in ['surge', 'high']:
            entry_signal = 'high_momentum'
            description = "15分钟成交量放大，动量强劲"
        else:
            entry_signal = 'wait'
            description = "15分钟无明显入场信号，等待"

        return {
            'entry_signal': entry_signal,
            'description': description,
            'rsi_value': rsi_info['value'],
            'bb_position': bb_info['position'],
            'volume_state': vol_info['trend']
        }

    def _综合多周期判断(
        self,
        macro: Dict,
        meso: Dict,
        micro: Dict
    ) -> Dict:
        """
        综合多个时间周期的信息，给出整体判断

        核心逻辑：
        - 日线定方向 (最重要)
        - 4小时看波段
        - 15分钟找入场点

        返回一个"市场环境描述"给AI
        """
        # 趋势一致性判断
        macro_dir = macro['direction']
        meso_dir = meso['wave_direction']

        if macro_dir == 'bullish' and meso_dir == 'upward':
            market_state = "多头趋势"
            confidence = 'high'
            advice = "日线和4小时共振向上，可以考虑顺势做多，但需注意15分钟入场时机"

        elif macro_dir == 'bearish' and meso_dir == 'downward':
            market_state = "空头趋势"
            confidence = 'high'
            advice = "日线和4小时共振向下，建议观望或轻仓做空，网格策略更合适"

        elif macro_dir == 'bullish' and meso_dir == 'downward':
            market_state = "多头回调"
            confidence = 'medium'
            advice = "日线多头但4小时回调，如果15分钟出现超卖信号，可能是加仓机会"

        elif macro_dir == 'bearish' and meso_dir == 'upward':
            market_state = "空头反弹"
            confidence = 'medium'
            advice = "日线空头但4小时反弹，属于下跌中的反弹，谨慎做多，更适合减仓"

        else:  # macro_dir == 'neutral'
            market_state = "震荡市"
            confidence = 'low'
            advice = "多个周期趋势不一致，市场方向不明，建议让网格策略自动运行"

        # 特殊情况：多周期共振信号
        resonance_signals = []

        if micro['entry_signal'] == 'buy_opportunity':
            if macro_dir == 'bullish' and meso_dir == 'upward':
                resonance_signals.append("✨ 多周期共振买入信号: 日线多头 + 4小时上涨 + 15分钟超卖")
            elif macro_dir == 'bullish':
                resonance_signals.append("⚡ 部分共振: 日线多头背景下的15分钟超卖反弹")

        if micro['entry_signal'] == 'sell_opportunity':
            if macro_dir == 'bearish' and meso_dir == 'downward':
                resonance_signals.append("✨ 多周期共振卖出信号: 日线空头 + 4小时下跌 + 15分钟超买")

        return {
            'market_state': market_state,
            'confidence_level': confidence,
            'trading_advice': advice,
            'resonance_signals': resonance_signals if resonance_signals else ["无特殊共振信号"],
            'summary': self._generate_summary(macro, meso, micro, market_state)
        }

    def _generate_summary(
        self,
        macro: Dict,
        meso: Dict,
        micro: Dict,
        market_state: str
    ) -> str:
        """生成易读的总结"""
        parts = []

        # 宏观
        parts.append(f"日线: {macro['description']}")

        # 中观
        parts.append(f"4小时: {meso['description']}")

        # 微观
        parts.append(f"15分钟: {micro['description']}")

        # 结论
        parts.append(f"综合判断: {market_state}")

        return " | ".join(parts)

    def _default_macro_trend(self) -> Dict:
        """默认宏观趋势 (数据不足时)"""
        return {
            'direction': 'neutral',
            'strength': 'weak',
            'description': '数据不足，无法判断日线趋势',
            'key_levels': {'ema_200': 0, 'resistance': 0, 'support': 0},
            'rsi_extreme': 'neutral',
            'macd_state': 'neutral'
        }

    def _default_meso_trend(self) -> Dict:
        """默认中观波段"""
        return {
            'wave_direction': 'sideways',
            'description': '数据不足',
            'ema_alignment': 'N/A',
            'macd_signal': 'N/A',
            'recent_swing_high': 0,
            'recent_swing_low': 0
        }

    def _default_micro_trend(self) -> Dict:
        """默认微观趋势"""
        return {
            'entry_signal': 'wait',
            'description': '数据不足',
            'rsi_value': 50,
            'bb_position': 'middle',
            'volume_state': 'normal'
        }

    def _get_default_analysis(self) -> Dict:
        """获取默认分析结果 (异常情况)"""
        return {
            'macro_trend': self._default_macro_trend(),
            'meso_trend': self._default_meso_trend(),
            'micro_trend': self._default_micro_trend(),
            'overall_context': {
                'market_state': '数据不足',
                'confidence_level': 'none',
                'trading_advice': '无法分析',
                'resonance_signals': [],
                'summary': '多时间周期数据获取失败'
            },
            'timestamp': datetime.now().isoformat()
        }
