"""
市场微观结构分析模块
Market Microstructure Analysis Module

功能:
- 订单簿深度分析
- 买卖压力识别
- 大单墙检测
- 流动性评估
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OrderBookLevel:
    """订单簿单个价格档位"""
    price: float
    amount: float
    total: float  # 累计量


@dataclass
class OrderWall:
    """大单墙"""
    price: float
    amount: float
    distance_percent: float  # 距离当前价格的百分比
    wall_type: str  # 'resistance' or 'support'


class OrderBookAnalyzer:
    """
    订单簿深度分析器

    分析订单簿的买卖压力、识别大单墙、评估流动性
    """

    def __init__(
        self,
        depth_range_percent: float = 1.0,  # 分析范围：上下1%
        wall_threshold_multiplier: float = 10.0  # 大单墙阈值：平均量的10倍
    ):
        """
        初始化订单簿分析器

        Args:
            depth_range_percent: 分析深度范围（相对当前价格的百分比）
            wall_threshold_multiplier: 大单墙阈值倍数
        """
        self.depth_range_percent = depth_range_percent
        self.wall_threshold = wall_threshold_multiplier

    async def analyze_order_book(
        self,
        exchange,
        symbol: str,
        current_price: float
    ) -> Dict[str, Any]:
        """
        分析订单簿深度

        Args:
            exchange: 交易所客户端
            symbol: 交易对
            current_price: 当前价格

        Returns:
            订单簿分析结果
        """
        try:
            # 获取订单簿数据
            order_book = await exchange.fetch_order_book(symbol, limit=50)

            if not order_book or not order_book.get('bids') or not order_book.get('asks'):
                logger.warning(f"订单簿数据为空: {symbol}")
                return self._get_empty_analysis()

            bids = order_book['bids']  # [[price, amount], ...]
            asks = order_book['asks']

            # 计算分析范围
            upper_bound = current_price * (1 + self.depth_range_percent / 100)
            lower_bound = current_price * (1 - self.depth_range_percent / 100)

            # 分析买盘深度
            buy_analysis = self._analyze_side(
                bids,
                lower_bound,
                current_price,
                side='bid'
            )

            # 分析卖盘深度
            sell_analysis = self._analyze_side(
                asks,
                current_price,
                upper_bound,
                side='ask'
            )

            # 计算价差
            spread = asks[0][0] - bids[0][0]
            spread_percent = (spread / current_price) * 100

            # 计算买卖失衡度 (-1到1之间，正值表示买盘强)
            total_depth = buy_analysis['total_depth'] + sell_analysis['total_depth']
            if total_depth > 0:
                imbalance = (buy_analysis['total_depth'] - sell_analysis['total_depth']) / total_depth
            else:
                imbalance = 0

            # 计算深度比率
            depth_ratio = (
                buy_analysis['total_depth'] / sell_analysis['total_depth']
                if sell_analysis['total_depth'] > 0
                else 10.0
            )

            # 识别大单墙
            buy_walls = self._detect_walls(
                bids,
                buy_analysis['avg_amount'],
                current_price,
                wall_type='support'
            )

            sell_walls = self._detect_walls(
                asks,
                sell_analysis['avg_amount'],
                current_price,
                wall_type='resistance'
            )

            # 生成流动性信号
            liquidity_signal = self._generate_liquidity_signal(
                imbalance,
                depth_ratio,
                len(buy_walls),
                len(sell_walls)
            )

            # 生成交易建议
            trading_insight = self._generate_trading_insight(
                imbalance,
                buy_walls,
                sell_walls,
                current_price
            )

            return {
                "spread": round(spread, 4),
                "spread_percent": round(spread_percent, 4),
                "imbalance": round(imbalance, 4),
                "depth_ratio": round(depth_ratio, 2),
                "buy_depth": round(buy_analysis['total_depth'], 2),
                "sell_depth": round(sell_analysis['total_depth'], 2),
                "resistance_walls": [
                    {
                        "price": wall.price,
                        "amount": round(wall.amount, 2),
                        "distance_percent": round(wall.distance_percent, 2)
                    }
                    for wall in sell_walls[:3]  # 最多返回前3个
                ],
                "support_walls": [
                    {
                        "price": wall.price,
                        "amount": round(wall.amount, 2),
                        "distance_percent": round(wall.distance_percent, 2)
                    }
                    for wall in buy_walls[:3]
                ],
                "liquidity_signal": liquidity_signal,
                "trading_insight": trading_insight,
                "bid_ask_strength": {
                    "bid_levels": len(buy_analysis['levels']),
                    "ask_levels": len(sell_analysis['levels']),
                    "bid_avg_size": round(buy_analysis['avg_amount'], 2),
                    "ask_avg_size": round(sell_analysis['avg_amount'], 2)
                }
            }

        except Exception as e:
            logger.error(f"订单簿分析失败: {e}", exc_info=True)
            return self._get_empty_analysis()

    def _analyze_side(
        self,
        orders: List[List[float]],
        price_lower: float,
        price_upper: float,
        side: str
    ) -> Dict[str, Any]:
        """
        分析订单簿的单侧（买盘或卖盘）

        Args:
            orders: 订单列表 [[price, amount], ...]
            price_lower: 价格下界
            price_upper: 价格上界
            side: 'bid' 或 'ask'

        Returns:
            分析结果
        """
        total_depth = 0
        levels = []

        for price, amount in orders:
            if price_lower <= price <= price_upper:
                total_depth += amount
                levels.append(OrderBookLevel(
                    price=price,
                    amount=amount,
                    total=total_depth
                ))

        avg_amount = total_depth / len(levels) if levels else 0

        return {
            "total_depth": total_depth,
            "avg_amount": avg_amount,
            "levels": levels,
            "level_count": len(levels)
        }

    def _detect_walls(
        self,
        orders: List[List[float]],
        avg_amount: float,
        current_price: float,
        wall_type: str
    ) -> List[OrderWall]:
        """
        检测大单墙

        Args:
            orders: 订单列表
            avg_amount: 平均订单量
            current_price: 当前价格
            wall_type: 'resistance' 或 'support'

        Returns:
            大单墙列表
        """
        walls = []
        threshold = avg_amount * self.wall_threshold

        if threshold <= 0:
            return walls

        for price, amount in orders:
            if amount >= threshold:
                distance_percent = ((price - current_price) / current_price) * 100
                walls.append(OrderWall(
                    price=price,
                    amount=amount,
                    distance_percent=distance_percent,
                    wall_type=wall_type
                ))

        # 按距离当前价格从近到远排序
        walls.sort(key=lambda x: abs(x.distance_percent))

        return walls

    def _generate_liquidity_signal(
        self,
        imbalance: float,
        depth_ratio: float,
        buy_walls_count: int,
        sell_walls_count: int
    ) -> str:
        """
        生成流动性信号

        Args:
            imbalance: 买卖失衡度
            depth_ratio: 深度比率
            buy_walls_count: 买单墙数量
            sell_walls_count: 卖单墙数量

        Returns:
            流动性信号: 'strong_bullish', 'bullish', 'neutral', 'bearish', 'strong_bearish'
        """
        # 强看涨：买盘深度显著大于卖盘，且有支撑墙
        if imbalance > 0.3 and depth_ratio > 1.5 and buy_walls_count > 0:
            return "strong_bullish"

        # 看涨：买盘稍强
        elif imbalance > 0.15 and depth_ratio > 1.2:
            return "bullish"

        # 强看跌：卖盘深度显著大于买盘，且有阻力墙
        elif imbalance < -0.3 and depth_ratio < 0.67 and sell_walls_count > 0:
            return "strong_bearish"

        # 看跌：卖盘稍强
        elif imbalance < -0.15 and depth_ratio < 0.83:
            return "bearish"

        # 中性
        else:
            return "neutral"

    def _generate_trading_insight(
        self,
        imbalance: float,
        buy_walls: List[OrderWall],
        sell_walls: List[OrderWall],
        current_price: float
    ) -> str:
        """
        生成交易洞察

        Args:
            imbalance: 买卖失衡度
            buy_walls: 买单墙列表
            sell_walls: 卖单墙列表
            current_price: 当前价格

        Returns:
            交易洞察描述
        """
        insights = []

        # 分析买卖压力
        if imbalance > 0.3:
            insights.append(f"买盘压力强劲(失衡度{imbalance:.2%})")
        elif imbalance < -0.3:
            insights.append(f"卖盘压力强劲(失衡度{imbalance:.2%})")
        else:
            insights.append(f"买卖压力平衡(失衡度{imbalance:.2%})")

        # 分析阻力墙
        if sell_walls:
            nearest_resistance = sell_walls[0]
            insights.append(
                f"上方{nearest_resistance.price:.2f}有{nearest_resistance.amount:.0f}单位抛压墙"
                f"(+{nearest_resistance.distance_percent:.2f}%)"
            )

        # 分析支撑墙
        if buy_walls:
            nearest_support = buy_walls[0]
            insights.append(
                f"下方{nearest_support.price:.2f}有{nearest_support.amount:.0f}单位支撑墙"
                f"({nearest_support.distance_percent:.2f}%)"
            )

        # 生成建议
        if not sell_walls and imbalance > 0.2:
            insights.append("上方无明显阻力，有突破空间")
        elif sell_walls and sell_walls[0].distance_percent < 0.5:
            insights.append("短期突破阻力位困难，建议谨慎")

        if not buy_walls and imbalance < -0.2:
            insights.append("下方支撑薄弱，注意下跌风险")
        elif buy_walls and buy_walls[0].distance_percent > -0.5:
            insights.append("下方支撑扎实，回调可能有限")

        return "; ".join(insights)

    def _get_empty_analysis(self) -> Dict[str, Any]:
        """返回空分析结果"""
        return {
            "spread": 0,
            "spread_percent": 0,
            "imbalance": 0,
            "depth_ratio": 1.0,
            "buy_depth": 0,
            "sell_depth": 0,
            "resistance_walls": [],
            "support_walls": [],
            "liquidity_signal": "unknown",
            "trading_insight": "订单簿数据不可用",
            "bid_ask_strength": {
                "bid_levels": 0,
                "ask_levels": 0,
                "bid_avg_size": 0,
                "ask_avg_size": 0
            }
        }


# 便捷函数
async def analyze_orderbook(
    exchange,
    symbol: str,
    current_price: float,
    depth_range_percent: float = 1.0
) -> Dict[str, Any]:
    """
    便捷的订单簿分析函数

    Args:
        exchange: 交易所客户端
        symbol: 交易对
        current_price: 当前价格
        depth_range_percent: 分析深度范围

    Returns:
        订单簿分析结果
    """
    analyzer = OrderBookAnalyzer(depth_range_percent=depth_range_percent)
    return await analyzer.analyze_order_book(exchange, symbol, current_price)
