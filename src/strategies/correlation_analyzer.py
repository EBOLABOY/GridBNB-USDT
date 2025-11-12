"""
加密货币相关性分析模块
Cryptocurrency Correlation Analysis Module

功能:
- 计算与BTC的相关性系数
- 分析BTC当前状态对目标币种的影响
- 识别是否受BTC拖累或带动
- 提供基于BTC走势的风险警告
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    加密货币相关性分析器

    分析目标币种与BTC的关联性，帮助判断是否受大盘影响
    """

    def __init__(
        self,
        lookback_periods: int = 100,
        high_correlation_threshold: float = 0.7,
        medium_correlation_threshold: float = 0.4
    ):
        """
        初始化相关性分析器

        Args:
            lookback_periods: 回溯周期数
            high_correlation_threshold: 高相关性阈值
            medium_correlation_threshold: 中等相关性阈值
        """
        self.lookback_periods = lookback_periods
        self.high_corr_threshold = high_correlation_threshold
        self.medium_corr_threshold = medium_correlation_threshold
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze_btc_correlation(
        self,
        exchange,
        symbol: str,
        timeframe: str = '1h',
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        分析与BTC的相关性

        Args:
            exchange: 交易所客户端
            symbol: 目标交易对 (如 BNB/USDT)
            timeframe: 时间周期
            current_price: 当前价格 (可选)

        Returns:
            相关性分析结果
        """
        try:
            # 并行获取两个币种的K线数据
            target_klines = await exchange.fetch_ohlcv(
                symbol,
                timeframe,
                limit=self.lookback_periods
            )

            btc_klines = await exchange.fetch_ohlcv(
                'BTC/USDT',
                timeframe,
                limit=self.lookback_periods
            )

            if not target_klines or not btc_klines:
                self.logger.warning(f"无法获取 {symbol} 或 BTC 的K线数据")
                return self._get_empty_analysis()

            if len(target_klines) < 30 or len(btc_klines) < 30:
                self.logger.warning("K线数据不足，无法计算相关性")
                return self._get_empty_analysis()

            # 提取收盘价
            target_prices = [k[4] for k in target_klines]
            btc_prices = [k[4] for k in btc_klines]

            # 确保数据长度一致
            min_length = min(len(target_prices), len(btc_prices))
            target_prices = target_prices[-min_length:]
            btc_prices = btc_prices[-min_length:]

            # 计算相关性
            correlation_result = self._calculate_correlation(
                target_prices,
                btc_prices
            )

            # 分析BTC当前状态
            btc_analysis = self._analyze_btc_state(btc_prices)

            # 计算目标币种状态
            target_analysis = self._analyze_target_state(
                target_prices,
                current_price
            )

            # 生成影响评估
            impact_assessment = self._assess_btc_impact(
                correlation_result,
                btc_analysis,
                target_analysis
            )

            # 生成风险警告
            risk_warning = self._generate_risk_warning(
                correlation_result,
                btc_analysis,
                target_analysis
            )

            # 生成交易建议
            trading_insight = self._generate_trading_insight(
                correlation_result,
                btc_analysis,
                target_analysis,
                impact_assessment
            )

            return {
                "correlation_coefficient": correlation_result['coefficient'],
                "correlation_strength": correlation_result['strength'],
                "correlation_direction": correlation_result['direction'],
                "btc_dominance_impact": impact_assessment['dominance'],
                "btc_current_state": {
                    "price": btc_analysis['current_price'],
                    "24h_change": btc_analysis['24h_change'],
                    "short_term_trend": btc_analysis['short_term_trend'],
                    "momentum": btc_analysis['momentum']
                },
                "target_state": {
                    "24h_change": target_analysis['24h_change'],
                    "short_term_trend": target_analysis['short_term_trend'],
                    "relative_strength": target_analysis['relative_strength']
                },
                "risk_warning": risk_warning,
                "trading_insight": trading_insight,
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"BTC相关性分析失败: {e}", exc_info=True)
            return self._get_empty_analysis()

    def _calculate_correlation(
        self,
        target_prices: List[float],
        btc_prices: List[float]
    ) -> Dict[str, Any]:
        """
        计算价格相关性

        Args:
            target_prices: 目标币种价格序列
            btc_prices: BTC价格序列

        Returns:
            相关性结果
        """
        # 计算对数收益率（更适合金融数据）
        target_returns = np.diff(np.log(target_prices))
        btc_returns = np.diff(np.log(btc_prices))

        # 计算皮尔逊相关系数
        correlation_matrix = np.corrcoef(target_returns, btc_returns)
        correlation_coefficient = correlation_matrix[0, 1]

        # 判断相关性强度
        abs_corr = abs(correlation_coefficient)
        if abs_corr >= self.high_corr_threshold:
            strength = "high"
        elif abs_corr >= self.medium_corr_threshold:
            strength = "medium"
        else:
            strength = "low"

        # 判断相关性方向
        if correlation_coefficient > 0.1:
            direction = "positive"  # 正相关，同涨同跌
        elif correlation_coefficient < -0.1:
            direction = "negative"  # 负相关，反向运动
        else:
            direction = "neutral"  # 基本无关

        return {
            'coefficient': round(correlation_coefficient, 3),
            'strength': strength,
            'direction': direction
        }

    def _analyze_btc_state(
        self,
        btc_prices: List[float]
    ) -> Dict[str, Any]:
        """
        分析BTC当前状态

        Args:
            btc_prices: BTC价格序列

        Returns:
            BTC状态分析
        """
        current_price = btc_prices[-1]

        # 计算24小时变化（假设1小时K线，24根即24小时）
        if len(btc_prices) >= 24:
            price_24h_ago = btc_prices[-24]
            change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
        else:
            # 数据不足，使用首尾价格
            change_24h = ((current_price - btc_prices[0]) / btc_prices[0]) * 100

        # 判断短期趋势（最近10根K线）
        if len(btc_prices) >= 10:
            recent_prices = btc_prices[-10:]
            first_price = recent_prices[0]
            last_price = recent_prices[-1]
            short_term_change = ((last_price - first_price) / first_price) * 100

            if short_term_change > 2:
                short_term_trend = "strong_uptrend"
            elif short_term_change > 0.5:
                short_term_trend = "uptrend"
            elif short_term_change < -2:
                short_term_trend = "strong_downtrend"
            elif short_term_change < -0.5:
                short_term_trend = "downtrend"
            else:
                short_term_trend = "ranging"
        else:
            short_term_trend = "unknown"

        # 计算动量（价格变化的加速度）
        if len(btc_prices) >= 20:
            recent_momentum = np.mean(np.diff(btc_prices[-10:]))
            earlier_momentum = np.mean(np.diff(btc_prices[-20:-10]))

            if recent_momentum > earlier_momentum * 1.5:
                momentum = "accelerating"
            elif recent_momentum < earlier_momentum * 0.5:
                momentum = "decelerating"
            else:
                momentum = "stable"
        else:
            momentum = "unknown"

        return {
            'current_price': round(current_price, 2),
            '24h_change': round(change_24h, 2),
            'short_term_trend': short_term_trend,
            'momentum': momentum
        }

    def _analyze_target_state(
        self,
        target_prices: List[float],
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        分析目标币种状态

        Args:
            target_prices: 目标币种价格序列
            current_price: 当前价格

        Returns:
            目标币种状态
        """
        if current_price is None:
            current_price = target_prices[-1]

        # 24小时变化
        if len(target_prices) >= 24:
            price_24h_ago = target_prices[-24]
            change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
        else:
            change_24h = ((current_price - target_prices[0]) / target_prices[0]) * 100

        # 短期趋势
        if len(target_prices) >= 10:
            recent_prices = target_prices[-10:]
            short_term_change = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100

            if short_term_change > 2:
                short_term_trend = "strong_uptrend"
            elif short_term_change > 0.5:
                short_term_trend = "uptrend"
            elif short_term_change < -2:
                short_term_trend = "strong_downtrend"
            elif short_term_change < -0.5:
                short_term_trend = "downtrend"
            else:
                short_term_trend = "ranging"
        else:
            short_term_trend = "unknown"

        # 相对强度（与自身历史波动相比）
        if len(target_prices) >= 30:
            volatility = np.std(target_prices[-30:])
            recent_move = abs(target_prices[-1] - target_prices[-5])

            if recent_move > volatility * 2:
                relative_strength = "very_strong"
            elif recent_move > volatility:
                relative_strength = "strong"
            else:
                relative_strength = "weak"
        else:
            relative_strength = "unknown"

        return {
            '24h_change': round(change_24h, 2),
            'short_term_trend': short_term_trend,
            'relative_strength': relative_strength
        }

    def _assess_btc_impact(
        self,
        correlation: Dict,
        btc_state: Dict,
        target_state: Dict
    ) -> Dict[str, Any]:
        """
        评估BTC对目标币种的影响

        Args:
            correlation: 相关性数据
            btc_state: BTC状态
            target_state: 目标币种状态

        Returns:
            影响评估
        """
        corr_coef = correlation['coefficient']
        corr_strength = correlation['strength']

        # 判断BTC主导性
        if corr_strength == "high" and abs(corr_coef) > 0.7:
            if corr_coef > 0:
                dominance = "highly_follows_btc"  # 高度跟随BTC
            else:
                dominance = "highly_inverse_to_btc"  # 与BTC高度负相关
        elif corr_strength == "medium":
            dominance = "partially_follows_btc"  # 部分跟随BTC
        else:
            dominance = "independent"  # 相对独立

        # 评估当前影响
        current_impact = "neutral"
        if corr_coef > 0.6:
            # 正相关
            if btc_state['short_term_trend'] in ['strong_uptrend', 'uptrend']:
                current_impact = "btc_boosting"  # BTC带动上涨
            elif btc_state['short_term_trend'] in ['strong_downtrend', 'downtrend']:
                current_impact = "btc_dragging_down"  # BTC拖累下跌

        return {
            'dominance': dominance,
            'current_impact': current_impact
        }

    def _generate_risk_warning(
        self,
        correlation: Dict,
        btc_state: Dict,
        target_state: Dict
    ) -> Optional[str]:
        """
        生成风险警告

        Args:
            correlation: 相关性数据
            btc_state: BTC状态
            target_state: 目标币种状态

        Returns:
            风险警告信息（如果有）
        """
        warnings = []

        corr_coef = correlation['coefficient']

        # 高相关性 + BTC下跌 = 风险
        if corr_coef > 0.7 and btc_state['short_term_trend'] in ['downtrend', 'strong_downtrend']:
            warnings.append(
                f"⚠️ 高相关性({corr_coef:.2f}) + BTC下跌({btc_state['24h_change']:.2f}%)，"
                f"目标币种可能继续受拖累"
            )

        # BTC下跌但目标币种上涨（背离风险）
        if (btc_state['24h_change'] < -2 and target_state['24h_change'] > 2 and
            corr_coef > 0.5):
            warnings.append(
                "⚠️ BTC下跌但目标币种上涨，存在背离风险，上涨可能不可持续"
            )

        # BTC动量衰减
        if btc_state['momentum'] == "decelerating" and corr_coef > 0.6:
            warnings.append(
                "⚠️ BTC上涨动能衰减，目标币种可能面临回调压力"
            )

        return "; ".join(warnings) if warnings else None

    def _generate_trading_insight(
        self,
        correlation: Dict,
        btc_state: Dict,
        target_state: Dict,
        impact: Dict
    ) -> str:
        """
        生成交易洞察

        Args:
            correlation: 相关性数据
            btc_state: BTC状态
            target_state: 目标币种状态
            impact: 影响评估

        Returns:
            交易洞察描述
        """
        insights = []

        corr_coef = correlation['coefficient']
        corr_strength = correlation['strength']

        # 相关性描述
        if corr_strength == "high":
            insights.append(
                f"与BTC高度相关(系数{corr_coef:.2f})，走势大概率跟随BTC"
            )
        elif corr_strength == "medium":
            insights.append(
                f"与BTC中度相关(系数{corr_coef:.2f})，部分受BTC影响"
            )
        else:
            insights.append(
                f"与BTC相关性低(系数{corr_coef:.2f})，走势相对独立"
            )

        # BTC状态描述
        btc_trend_desc = {
            "strong_uptrend": "强势上涨",
            "uptrend": "温和上涨",
            "ranging": "震荡整理",
            "downtrend": "温和下跌",
            "strong_downtrend": "大幅下跌"
        }.get(btc_state['short_term_trend'], "趋势不明")

        insights.append(
            f"BTC当前{btc_trend_desc}(24H {btc_state['24h_change']:+.2f}%)"
        )

        # 影响评估
        if impact['current_impact'] == "btc_boosting":
            insights.append("目前受益于BTC上涨带动")
        elif impact['current_impact'] == "btc_dragging_down":
            insights.append("目前受BTC下跌拖累")

        # 操作建议
        if corr_coef > 0.7:
            if btc_state['short_term_trend'] in ['strong_downtrend', 'downtrend']:
                insights.append("建议：等待BTC企稳后再考虑建仓")
            elif btc_state['short_term_trend'] in ['strong_uptrend', 'uptrend']:
                insights.append("建议：可顺应BTC上涨趋势操作")

        return "; ".join(insights)

    def _get_empty_analysis(self) -> Dict[str, Any]:
        """返回空的分析结果"""
        return {
            "correlation_coefficient": 0,
            "correlation_strength": "unknown",
            "correlation_direction": "unknown",
            "btc_dominance_impact": "unknown",
            "btc_current_state": {
                "price": 0,
                "24h_change": 0,
                "short_term_trend": "unknown",
                "momentum": "unknown"
            },
            "target_state": {
                "24h_change": 0,
                "short_term_trend": "unknown",
                "relative_strength": "unknown"
            },
            "risk_warning": None,
            "trading_insight": "数据不可用",
            "analysis_timestamp": datetime.now().isoformat()
        }


# 便捷函数
async def analyze_btc_correlation(
    exchange,
    symbol: str,
    timeframe: str = '1h',
    current_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    便捷的BTC相关性分析函数

    Args:
        exchange: 交易所客户端
        symbol: 目标交易对
        timeframe: 时间周期
        current_price: 当前价格

    Returns:
        BTC相关性分析结果
    """
    analyzer = CorrelationAnalyzer()
    return await analyzer.analyze_btc_correlation(
        exchange,
        symbol,
        timeframe,
        current_price
    )
