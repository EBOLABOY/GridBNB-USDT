"""
衍生品数据获取模块
Derivatives Data Fetcher Module

功能:
- 获取期货资金费率 (Funding Rate)
- 获取持仓量 (Open Interest) 及变化
- 支持 Binance 和 OKX 期货API
- 无需API密钥，使用公开端点
"""

import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ExchangeType(Enum):
    """交易所类型"""
    BINANCE = "binance"
    OKX = "okx"


class DerivativesDataFetcher:
    """
    衍生品数据获取器

    从期货市场获取资金费率和持仓量数据
    """

    # API端点配置
    BINANCE_FUTURES_BASE = "https://fapi.binance.com"
    OKX_API_BASE = "https://www.okx.com"

    def __init__(
        self,
        exchange_type: str = "binance",
        timeout: int = 10
    ):
        """
        初始化衍生品数据获取器

        Args:
            exchange_type: 交易所类型 (binance/okx)
            timeout: 请求超时时间（秒）
        """
        self.exchange_type = ExchangeType(exchange_type.lower())
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

        # 缓存机制（避免频繁请求）
        self._funding_rate_cache = {}
        self._oi_cache = {}
        self._cache_duration = 300  # 5分钟缓存

    async def fetch_funding_rate(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        获取资金费率

        Args:
            symbol: 交易对 (如 BNB/USDT)

        Returns:
            资金费率数据
        """
        # 检查缓存
        cache_key = f"{self.exchange_type.value}_{symbol}_funding"
        if cache_key in self._funding_rate_cache:
            cached_data, cached_time = self._funding_rate_cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self._cache_duration:
                self.logger.debug(f"使用缓存的资金费率数据: {symbol}")
                return cached_data

        try:
            if self.exchange_type == ExchangeType.BINANCE:
                data = await self._fetch_binance_funding_rate(symbol)
            elif self.exchange_type == ExchangeType.OKX:
                data = await self._fetch_okx_funding_rate(symbol)
            else:
                raise ValueError(f"不支持的交易所: {self.exchange_type}")

            # 更新缓存
            self._funding_rate_cache[cache_key] = (data, datetime.now())
            return data

        except Exception as e:
            self.logger.error(f"获取资金费率失败: {e}", exc_info=True)
            return self._get_empty_funding_rate()

    async def fetch_open_interest(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        获取持仓量及变化

        Args:
            symbol: 交易对

        Returns:
            持仓量数据
        """
        # 检查缓存
        cache_key = f"{self.exchange_type.value}_{symbol}_oi"
        if cache_key in self._oi_cache:
            cached_data, cached_time = self._oi_cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self._cache_duration:
                self.logger.debug(f"使用缓存的持仓量数据: {symbol}")
                return cached_data

        try:
            if self.exchange_type == ExchangeType.BINANCE:
                data = await self._fetch_binance_open_interest(symbol)
            elif self.exchange_type == ExchangeType.OKX:
                data = await self._fetch_okx_open_interest(symbol)
            else:
                raise ValueError(f"不支持的交易所: {self.exchange_type}")

            # 更新缓存
            self._oi_cache[cache_key] = (data, datetime.now())
            return data

        except Exception as e:
            self.logger.error(f"获取持仓量失败: {e}", exc_info=True)
            return self._get_empty_open_interest()

    async def _fetch_binance_funding_rate(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        获取 Binance 资金费率

        Args:
            symbol: 交易对 (如 BNB/USDT)

        Returns:
            资金费率数据
        """
        # 转换交易对格式: BNB/USDT -> BNBUSDT
        futures_symbol = symbol.replace("/", "")

        url = f"{self.BINANCE_FUTURES_BASE}/fapi/v1/fundingRate"
        params = {
            "symbol": futures_symbol,
            "limit": 2  # 获取最近2条记录用于对比
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Binance API错误: {response.status}")

                data = await response.json()

                if not data:
                    raise Exception("未获取到资金费率数据")

                # 最新一条
                latest = data[0]
                current_rate = float(latest['fundingRate']) * 100  # 转为百分比

                # 判断情绪
                if current_rate > 0.01:
                    sentiment = "bullish"
                elif current_rate < -0.01:
                    sentiment = "bearish"
                else:
                    sentiment = "neutral"

                # 判断是否异常
                warning = None
                if current_rate > 0.05:
                    warning = "funding_rate_very_high"  # 多头成本极高
                elif current_rate < -0.05:
                    warning = "funding_rate_very_low"  # 空头成本极高

                return {
                    "current_rate": round(current_rate, 4),
                    "current_rate_display": f"{current_rate:.4f}%",
                    "next_funding_time": datetime.fromtimestamp(
                        int(latest['fundingTime']) / 1000
                    ).isoformat(),
                    "sentiment": sentiment,
                    "warning": warning,
                    "source": "binance_futures"
                }

    async def _fetch_binance_open_interest(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        获取 Binance 持仓量

        Args:
            symbol: 交易对

        Returns:
            持仓量数据
        """
        futures_symbol = symbol.replace("/", "")

        # 获取当前持仓量
        url = f"{self.BINANCE_FUTURES_BASE}/fapi/v1/openInterest"
        params = {"symbol": futures_symbol}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Binance API错误: {response.status}")

                data = await response.json()
                current_oi = float(data['openInterest'])

        # 获取24小时前的持仓量（通过历史数据）
        try:
            historical_oi = await self._fetch_binance_historical_oi(
                futures_symbol,
                hours_ago=24
            )
            oi_change = ((current_oi - historical_oi) / historical_oi) * 100
        except Exception as e:
            self.logger.warning(f"获取历史持仓量失败，使用默认值: {e}")
            oi_change = 0

        # 判断趋势
        if oi_change > 2:
            trend = "increasing"
            signal = "money_entering"
        elif oi_change < -2:
            trend = "decreasing"
            signal = "money_leaving"
        else:
            trend = "stable"
            signal = "neutral"

        # 强信号判断
        if oi_change > 5:
            signal = "strong_money_entering"
        elif oi_change < -5:
            signal = "strong_money_leaving"

        return {
            "current": current_oi,
            "current_display": f"{current_oi:,.0f}",
            "24h_change": round(oi_change, 2),
            "24h_change_display": f"{oi_change:+.2f}%",
            "trend": trend,
            "signal": signal,
            "source": "binance_futures"
        }

    async def _fetch_binance_historical_oi(
        self,
        symbol: str,
        hours_ago: int = 24
    ) -> float:
        """
        获取 Binance 历史持仓量

        Args:
            symbol: 期货交易对符号
            hours_ago: 多少小时前

        Returns:
            历史持仓量值
        """
        # Binance 期货历史持仓量API
        url = f"{self.BINANCE_FUTURES_BASE}/futures/data/openInterestHist"

        # 计算时间戳（毫秒）
        end_time = int((datetime.now() - timedelta(hours=hours_ago)).timestamp() * 1000)

        params = {
            "symbol": symbol,
            "period": "1h",
            "limit": 1,
            "endTime": end_time
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"获取历史持仓量失败: {response.status}")

                data = await response.json()

                if not data:
                    raise Exception("历史持仓量数据为空")

                return float(data[0]['sumOpenInterest'])

    async def _fetch_okx_funding_rate(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        获取 OKX 资金费率

        Args:
            symbol: 交易对 (如 BNB/USDT)

        Returns:
            资金费率数据
        """
        # OKX 格式: BNB-USDT-SWAP
        okx_symbol = symbol.replace("/", "-") + "-SWAP"

        url = f"{self.OKX_API_BASE}/api/v5/public/funding-rate"
        params = {"instId": okx_symbol}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"OKX API错误: {response.status}")

                result = await response.json()

                if result['code'] != '0' or not result['data']:
                    raise Exception(f"OKX API返回错误: {result.get('msg')}")

                data = result['data'][0]
                current_rate = float(data['fundingRate']) * 100

                # 判断情绪
                if current_rate > 0.01:
                    sentiment = "bullish"
                elif current_rate < -0.01:
                    sentiment = "bearish"
                else:
                    sentiment = "neutral"

                # 警告
                warning = None
                if current_rate > 0.05:
                    warning = "funding_rate_very_high"
                elif current_rate < -0.05:
                    warning = "funding_rate_very_low"

                return {
                    "current_rate": round(current_rate, 4),
                    "current_rate_display": f"{current_rate:.4f}%",
                    "next_funding_time": datetime.fromtimestamp(
                        int(data['fundingTime']) / 1000
                    ).isoformat(),
                    "sentiment": sentiment,
                    "warning": warning,
                    "source": "okx_swap"
                }

    async def _fetch_okx_open_interest(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        获取 OKX 持仓量

        Args:
            symbol: 交易对

        Returns:
            持仓量数据
        """
        okx_symbol = symbol.replace("/", "-") + "-SWAP"

        url = f"{self.OKX_API_BASE}/api/v5/public/open-interest"
        params = {"instId": okx_symbol}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"OKX API错误: {response.status}")

                result = await response.json()

                if result['code'] != '0' or not result['data']:
                    raise Exception(f"OKX API返回错误: {result.get('msg')}")

                data = result['data'][0]
                current_oi = float(data['oi'])

        # 获取24小时前的持仓量
        try:
            historical_oi = await self._fetch_okx_historical_oi(okx_symbol, hours_ago=24)
            oi_change = ((current_oi - historical_oi) / historical_oi) * 100
        except Exception as e:
            self.logger.warning(f"获取OKX历史持仓量失败: {e}")
            oi_change = 0

        # 判断趋势
        if oi_change > 2:
            trend = "increasing"
            signal = "money_entering"
        elif oi_change < -2:
            trend = "decreasing"
            signal = "money_leaving"
        else:
            trend = "stable"
            signal = "neutral"

        if oi_change > 5:
            signal = "strong_money_entering"
        elif oi_change < -5:
            signal = "strong_money_leaving"

        return {
            "current": current_oi,
            "current_display": f"{current_oi:,.0f}",
            "24h_change": round(oi_change, 2),
            "24h_change_display": f"{oi_change:+.2f}%",
            "trend": trend,
            "signal": signal,
            "source": "okx_swap"
        }

    async def _fetch_okx_historical_oi(
        self,
        inst_id: str,
        hours_ago: int = 24
    ) -> float:
        """
        获取 OKX 历史持仓量

        Args:
            inst_id: OKX交易对ID
            hours_ago: 多少小时前

        Returns:
            历史持仓量
        """
        url = f"{self.OKX_API_BASE}/api/v5/rubik/stat/contracts/open-interest-history"

        # OKX使用毫秒时间戳
        end_time = int((datetime.now() - timedelta(hours=hours_ago)).timestamp() * 1000)

        params = {
            "instId": inst_id,
            "period": "1H",
            "limit": 1,
            "end": end_time
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"获取OKX历史持仓量失败: {response.status}")

                result = await response.json()

                if result['code'] != '0' or not result['data']:
                    raise Exception(f"OKX历史持仓量API错误: {result.get('msg')}")

                return float(result['data'][0]['oi'])

    def _get_empty_funding_rate(self) -> Dict[str, Any]:
        """返回空的资金费率数据"""
        return {
            "current_rate": 0,
            "current_rate_display": "0.0000%",
            "next_funding_time": None,
            "sentiment": "unknown",
            "warning": None,
            "source": "unavailable"
        }

    def _get_empty_open_interest(self) -> Dict[str, Any]:
        """返回空的持仓量数据"""
        return {
            "current": 0,
            "current_display": "0",
            "24h_change": 0,
            "24h_change_display": "+0.00%",
            "trend": "unknown",
            "signal": "unknown",
            "source": "unavailable"
        }


# 便捷函数
async def fetch_derivatives_data(
    symbol: str,
    exchange_type: str = "binance"
) -> Dict[str, Any]:
    """
    便捷的衍生品数据获取函数

    Args:
        symbol: 交易对
        exchange_type: 交易所类型

    Returns:
        包含资金费率和持仓量的完整数据
    """
    fetcher = DerivativesDataFetcher(exchange_type=exchange_type)

    # 并行获取资金费率和持仓量
    funding_rate, open_interest = await asyncio.gather(
        fetcher.fetch_funding_rate(symbol),
        fetcher.fetch_open_interest(symbol),
        return_exceptions=True
    )

    # 处理异常
    if isinstance(funding_rate, Exception):
        logger.error(f"获取资金费率异常: {funding_rate}")
        funding_rate = fetcher._get_empty_funding_rate()

    if isinstance(open_interest, Exception):
        logger.error(f"获取持仓量异常: {open_interest}")
        open_interest = fetcher._get_empty_open_interest()

    return {
        "funding_rate": funding_rate,
        "open_interest": open_interest,
        "timestamp": datetime.now().isoformat()
    }
