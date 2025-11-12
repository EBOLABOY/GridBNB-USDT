"""
第三方市场数据获取模块
获取恐惧贪婪指数等市场情绪指标

数据源:
- Alternative.me Fear & Greed Index (免费)
"""

import aiohttp
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio


class MarketSentimentData:
    """市场情绪数据获取器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fear_greed_cache = {
            'data': None,
            'timestamp': None,
            'ttl': 3600  # 缓存1小时
        }

    async def get_fear_greed_index(self) -> Optional[Dict]:
        """
        获取恐惧贪婪指数

        API: https://api.alternative.me/fng/
        免费,无需API密钥

        Returns:
            {
                'value': 0-100的数值,
                'classification': 'Extreme Fear'/'Fear'/'Neutral'/'Greed'/'Extreme Greed',
                'timestamp': 时间戳,
                'trend': 'increasing'/'decreasing'/'stable'
            }
        """
        # 检查缓存
        if self._is_cache_valid('fear_greed'):
            self.logger.debug("使用缓存的Fear & Greed数据")
            return self.fear_greed_cache['data']

        try:
            url = "https://api.alternative.me/fng/?limit=2"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()

                        if 'data' in result and len(result['data']) > 0:
                            current = result['data'][0]
                            value = int(current['value'])

                            # 分类
                            if value <= 25:
                                classification = 'Extreme Fear'
                            elif value <= 45:
                                classification = 'Fear'
                            elif value <= 55:
                                classification = 'Neutral'
                            elif value <= 75:
                                classification = 'Greed'
                            else:
                                classification = 'Extreme Greed'

                            # 趋势判断 (对比前一天)
                            trend = 'stable'
                            if len(result['data']) > 1:
                                previous_value = int(result['data'][1]['value'])
                                if value > previous_value + 5:
                                    trend = 'increasing'
                                elif value < previous_value - 5:
                                    trend = 'decreasing'

                            data = {
                                'value': value,
                                'classification': classification,
                                'timestamp': current['timestamp'],
                                'trend': trend,
                                'time_until_update': current.get('time_until_update', 'unknown')
                            }

                            # 更新缓存
                            self.fear_greed_cache['data'] = data
                            self.fear_greed_cache['timestamp'] = datetime.now()

                            self.logger.info(
                                f"Fear & Greed Index: {value} ({classification}, {trend})"
                            )
                            return data
                    else:
                        self.logger.error(f"获取Fear & Greed指数失败: HTTP {response.status}")
                        return None

        except asyncio.TimeoutError:
            self.logger.error("获取Fear & Greed指数超时")
            return self._get_fallback_fear_greed()
        except Exception as e:
            self.logger.error(f"获取Fear & Greed指数异常: {e}")
            return self._get_fallback_fear_greed()

    def _is_cache_valid(self, cache_name: str) -> bool:
        """检查缓存是否有效"""
        if cache_name == 'fear_greed':
            cache = self.fear_greed_cache
            if cache['data'] is None or cache['timestamp'] is None:
                return False

            age = (datetime.now() - cache['timestamp']).total_seconds()
            return age < cache['ttl']

        return False

    def _get_fallback_fear_greed(self) -> Dict:
        """返回降级的Fear & Greed数据"""
        # 如果有缓存,返回过期的缓存
        if self.fear_greed_cache['data'] is not None:
            self.logger.warning("Fear & Greed API失败,使用过期缓存")
            return self.fear_greed_cache['data']

        # 否则返回中性值
        self.logger.warning("Fear & Greed API失败,使用默认中性值")
        return {
            'value': 50,
            'classification': 'Neutral',
            'timestamp': int(datetime.now().timestamp()),
            'trend': 'stable',
            'time_until_update': 'unknown',
            'is_fallback': True
        }

    async def get_comprehensive_sentiment(self) -> Dict:
        """
        获取综合市场情绪数据

        Returns:
            {
                'fear_greed': Fear & Greed数据,
                'overall_sentiment': 'bullish'/'bearish'/'neutral',
                'confidence': 0-100
            }
        """
        fear_greed = await self.get_fear_greed_index()

        # 综合判断市场情绪
        if fear_greed:
            fg_value = fear_greed['value']

            # 极度恐惧 = 买入机会
            if fg_value < 25:
                sentiment = 'bullish'
                confidence = 80
            # 恐惧 = 轻度看涨
            elif fg_value < 45:
                sentiment = 'bullish'
                confidence = 60
            # 中性
            elif fg_value < 55:
                sentiment = 'neutral'
                confidence = 50
            # 贪婪 = 轻度看跌
            elif fg_value < 75:
                sentiment = 'bearish'
                confidence = 60
            # 极度贪婪 = 卖出信号
            else:
                sentiment = 'bearish'
                confidence = 80
        else:
            sentiment = 'neutral'
            confidence = 0

        return {
            'fear_greed': fear_greed,
            'overall_sentiment': sentiment,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }


# 全局单例
_market_sentiment_instance = None


def get_market_sentiment() -> MarketSentimentData:
    """获取MarketSentimentData单例"""
    global _market_sentiment_instance
    if _market_sentiment_instance is None:
        _market_sentiment_instance = MarketSentimentData()
    return _market_sentiment_instance
