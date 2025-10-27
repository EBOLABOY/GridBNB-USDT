"""
AI辅助交易策略模块

基于技术指标、市场情绪和持仓信息,调用AI进行综合分析并给出交易建议。

核心流程:
1. 收集并计算技术指标
2. 获取第三方市场情绪数据
3. 封装当前持仓和交易历史
4. 发送给AI模型进行分析
5. 解析AI响应并执行交易决策

支持的AI提供商:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- 本地模型 (可扩展)
"""

import logging
import json
import time
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

# AI SDK导入 (优雅降级)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None
    logging.warning("OpenAI SDK未安装,无法使用OpenAI模型")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic SDK未安装,无法使用Claude模型")

from src.strategies.technical_indicators import TechnicalIndicators
from src.strategies.market_sentiment import get_market_sentiment
from src.strategies.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from src.strategies.market_microstructure import OrderBookAnalyzer
from src.strategies.derivatives_data import DerivativesDataFetcher
from src.strategies.correlation_analyzer import CorrelationAnalyzer
from src.config.settings import settings

# 导入Prometheus指标
try:
    from src.monitoring.metrics import get_metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logging.warning("Prometheus指标模块不可用")


class AIProvider(Enum):
    """AI提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class TriggerReason(Enum):
    """AI触发原因"""
    TECHNICAL_SIGNAL = "technical_signal"  # 技术指标重大变化
    TIME_INTERVAL = "time_interval"  # 时间周期到达
    POSITION_CHANGE = "position_change"  # 仓位变化
    MARKET_VOLATILITY = "market_volatility"  # 市场异常波动
    MANUAL = "manual"  # 手动触发


class AITradingStrategy:
    """AI辅助交易策略"""

    def __init__(self, trader_instance):
        """
        初始化AI策略

        Args:
            trader_instance: 主GridTrader实例
        """
        self.trader = trader_instance
        self.logger = logging.getLogger(self.__class__.__name__)

        # 技术指标计算器
        self.indicators_calculator = TechnicalIndicators()

        # 🆕 多时间周期分析器
        self.multi_timeframe_analyzer = MultiTimeframeAnalyzer()

        # 🆕 订单簿深度分析器
        self.orderbook_analyzer = OrderBookAnalyzer()

        # 🆕 衍生品数据获取器
        exchange_type = getattr(settings, 'EXCHANGE', 'binance').lower()
        self.derivatives_fetcher = DerivativesDataFetcher(exchange_type=exchange_type)

        # 🆕 BTC相关性分析器
        self.correlation_analyzer = CorrelationAnalyzer()

        # 市场情绪数据获取器
        self.sentiment_data = get_market_sentiment()

        # AI配置 (从环境变量读取)
        self.ai_enabled = getattr(settings, 'AI_ENABLED', False)
        self.ai_provider = AIProvider(getattr(settings, 'AI_PROVIDER', 'openai'))
        self.ai_model = getattr(settings, 'AI_MODEL', 'gpt-4-turbo')
        self.ai_api_key = getattr(settings, 'AI_API_KEY', None)
        self.ai_openai_base_url = getattr(settings, 'AI_OPENAI_BASE_URL', None)
        self.confidence_threshold = getattr(settings, 'AI_CONFIDENCE_THRESHOLD', 70)
        self.trigger_interval = getattr(settings, 'AI_TRIGGER_INTERVAL', 900)  # 15分钟
        self.max_calls_per_day = getattr(settings, 'AI_MAX_CALLS_PER_DAY', 100)
        self.fallback_to_grid = getattr(settings, 'AI_FALLBACK_TO_GRID', True)

        # 状态跟踪
        self.last_trigger_time = 0
        self.last_indicators = None
        self.ai_call_count_today = 0
        self.last_reset_date = datetime.now().date()
        self.consecutive_failures = 0
        self.ai_suggestions_history = []  # 保存历史建议用于学习
        self.last_ai_decision = None  # 🆕 保存最新的AI决策详情（用于Web UI展示）

        # 初始化AI客户端
        self._initialize_ai_client()

        self.logger.info(
            f"AI策略初始化完成 | "
            f"启用: {self.ai_enabled} | "
            f"提供商: {self.ai_provider.value} | "
            f"模型: {self.ai_model} | "
            f"置信度阈值: {self.confidence_threshold}%"
        )

    def _initialize_ai_client(self):
        """初始化AI客户端"""
        if not self.ai_enabled:
            self.ai_client = None
            return

        if self.ai_provider == AIProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                self.logger.error("OpenAI SDK未安装,无法使用OpenAI")
                self.ai_client = None
                return

            if not self.ai_api_key:
                self.logger.error("未配置OPENAI_API_KEY")
                self.ai_client = None
                return

            client_kwargs = {"api_key": self.ai_api_key}
            if self.ai_openai_base_url:
                client_kwargs["base_url"] = self.ai_openai_base_url

            if hasattr(openai, "OpenAI"):
                self.ai_client = openai.OpenAI(**client_kwargs)
            else:
                openai.api_key = self.ai_api_key
                if self.ai_openai_base_url:
                    setattr(openai, "base_url", self.ai_openai_base_url)
                    setattr(openai, "api_base", self.ai_openai_base_url)
                self.ai_client = openai

            base_info = self.ai_openai_base_url or "默认"
            self.logger.info(f"OpenAI客户端初始化成功 | Base URL: {base_info}")

        elif self.ai_provider == AIProvider.ANTHROPIC:
            if not ANTHROPIC_AVAILABLE:
                self.logger.error("Anthropic SDK未安装,无法使用Claude")
                self.ai_client = None
                return

            if not self.ai_api_key:
                self.logger.error("未配置ANTHROPIC_API_KEY")
                self.ai_client = None
                return

            self.ai_client = anthropic.Anthropic(api_key=self.ai_api_key)
            self.logger.info("Anthropic客户端初始化成功")

        else:
            self.logger.warning("不支持的AI提供商,AI功能禁用")
            self.ai_client = None

    async def should_trigger(self, current_price: float) -> Tuple[bool, Optional[TriggerReason]]:
        """
        判断是否应该触发AI分析

        Args:
            current_price: 当前价格

        Returns:
            (是否触发, 触发原因)
        """
        if not self.ai_enabled or self.ai_client is None:
            return False, None

        # 检查每日调用限制
        self._check_daily_limit()
        if self.ai_call_count_today >= self.max_calls_per_day:
            self.logger.warning(f"今日AI调用已达上限: {self.max_calls_per_day}")
            return False, None

        now = time.time()

        # 触发条件1: 时间周期触发
        if now - self.last_trigger_time >= self.trigger_interval:
            self.logger.info(f"时间周期触发: 距上次{(now - self.last_trigger_time)/60:.1f}分钟")
            return True, TriggerReason.TIME_INTERVAL

        # 获取当前技术指标 (用于后续判断)
        try:
            prices, volumes = await self._fetch_recent_klines()
            current_indicators = self.indicators_calculator.calculate_all_indicators(
                prices, volumes
            )
        except Exception as e:
            self.logger.error(f"获取技术指标失败: {e}")
            return False, None

        # 触发条件2: 技术指标重大变化
        if self.last_indicators is not None:
            if self._has_significant_indicator_change(current_indicators):
                self.logger.info("技术指标重大变化触发")
                return True, TriggerReason.TECHNICAL_SIGNAL

        # 触发条件3: 市场异常波动 (1小时涨跌超过5%)
        if len(prices) >= 12:  # 至少12根5分钟K线
            hour_ago_price = prices[-12]
            price_change_pct = abs((current_price - hour_ago_price) / hour_ago_price)
            if price_change_pct > 0.05:  # 5%
                self.logger.warning(
                    f"市场异常波动触发: 1小时变化{price_change_pct*100:.2f}%"
                )
                return True, TriggerReason.MARKET_VOLATILITY

        # 保存当前指标用于下次对比
        self.last_indicators = current_indicators

        return False, None

    def _has_significant_indicator_change(self, current: Dict) -> bool:
        """
        检测技术指标是否有重大变化

        Args:
            current: 当前指标

        Returns:
            是否有重大变化
        """
        prev = self.last_indicators

        # MACD金叉/死叉
        if current['macd']['crossover'] in ['golden_cross', 'death_cross']:
            self.logger.info(f"MACD {current['macd']['crossover']}")
            return True

        # RSI跨越超买超卖阈值
        prev_rsi = prev['rsi']['value']
        curr_rsi = current['rsi']['value']
        if (prev_rsi < 30 and curr_rsi >= 30) or (prev_rsi > 70 and curr_rsi <= 70):
            self.logger.info(f"RSI跨越阈值: {prev_rsi:.1f} -> {curr_rsi:.1f}")
            return True

        # 布林带突破
        prev_bb_pos = prev['bollinger_bands']['position']
        curr_bb_pos = current['bollinger_bands']['position']
        if prev_bb_pos != curr_bb_pos and curr_bb_pos in ['above', 'below']:
            self.logger.info(f"布林带突破: {curr_bb_pos}")
            return True

        return False

    async def _fetch_recent_klines(self, limit: int = 100) -> Tuple[List[float], List[float]]:
        """
        获取最近的K线数据

        Args:
            limit: 数量

        Returns:
            (价格列表, 成交量列表)
        """
        try:
            # 使用5分钟K线
            klines = await self.trader.exchange.fetch_ohlcv(
                self.trader.symbol,
                timeframe='5m',
                limit=limit
            )

            if not klines or len(klines) < 50:
                raise ValueError(f"K线数据不足: {len(klines) if klines else 0}")

            # 提取收盘价和成交量
            prices = [float(k[4]) for k in klines]  # close price
            volumes = [float(k[5]) for k in klines]  # volume

            return prices, volumes

        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            raise

    def _check_daily_limit(self):
        """检查并重置每日调用计数"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.logger.info(
                f"新的一天开始,重置AI调用计数 | "
                f"昨日调用: {self.ai_call_count_today}次"
            )
            self.ai_call_count_today = 0
            self.last_reset_date = today

    async def analyze_and_suggest(self, trigger_reason: TriggerReason) -> Optional[Dict]:
        """
        执行AI分析并返回交易建议

        Args:
            trigger_reason: 触发原因

        Returns:
            AI建议字典或None
        """
        from src.strategies.ai_prompt import AIPromptBuilder

        self.logger.info(f"开始AI分析 | 触发原因: {trigger_reason.value}")

        try:
            # 收集数据
            analysis_data = await self._collect_analysis_data()

            # 构建提示词
            prompt = AIPromptBuilder.build_prompt(analysis_data)

            # 调用AI
            ai_response = await self._call_ai_model(prompt)

            if not ai_response:
                self.logger.error("AI调用失败")
                self.consecutive_failures += 1
                return None

            # 解析响应
            suggestion = AIPromptBuilder.parse_ai_response(ai_response)

            if not suggestion:
                self.logger.error("AI响应解析失败")
                self.consecutive_failures += 1
                return None

            # 验证建议
            is_valid, error_msg = AIPromptBuilder.validate_suggestion(
                suggestion,
                analysis_data['market_data']['current_price'],
                analysis_data['risk_metrics']['max_position_ratio']
            )

            if not is_valid:
                self.logger.warning(f"AI建议验证失败: {error_msg}")
                return None

            # 记录成功
            self.consecutive_failures = 0
            self.ai_call_count_today += 1
            self.last_trigger_time = time.time()

            # 保存到历史
            suggestion['timestamp'] = datetime.now().isoformat()
            suggestion['trigger_reason'] = trigger_reason.value
            self.ai_suggestions_history.append(suggestion)
            if len(self.ai_suggestions_history) > 100:
                self.ai_suggestions_history.pop(0)

            # 🆕 保存最新的AI决策详情（用于Web UI展示）
            self.last_ai_decision = {
                "suggestion": suggestion,
                "market_data": analysis_data.get("multi_timeframe_analysis", {}),
                "orderbook": analysis_data.get("orderbook_analysis", {}),
                "derivatives": analysis_data.get("derivatives_data", {}),
                "correlation": analysis_data.get("btc_correlation", {}),
                "timestamp": datetime.now().isoformat()
            }

            self.logger.info(
                f"AI分析完成 | "
                f"建议: {suggestion['action']} | "
                f"置信度: {suggestion['confidence']}% | "
                f"金额: {suggestion['suggested_amount_pct']}%"
            )

            return suggestion

        except Exception as e:
            self.logger.error(f"AI分析异常: {e}", exc_info=True)
            self.consecutive_failures += 1
            return None

    async def _collect_analysis_data(self) -> Dict:
        """
        收集AI分析所需的所有数据（增强版）

        新增数据维度：
        - 多时间周期分析
        - 订单簿深度
        - 衍生品数据（资金费率、持仓量）
        - BTC相关性
        """
        from src.strategies.ai_prompt import AIPromptBuilder

        # 获取K线数据 (当前使用5分钟作为基准)
        prices, volumes = await self._fetch_recent_klines()

        # 计算技术指标 (基于5分钟)
        indicators = self.indicators_calculator.calculate_all_indicators(prices, volumes)

        # 市场数据
        current_price = await self.trader._get_latest_price()
        ticker = await self.trader.exchange.fetch_ticker(self.trader.symbol)

        market_data = {
            'current_price': current_price,
            '24h_change': ticker.get('percentage', 0),
            '24h_volume': ticker.get('quoteVolume', 0),
            '24h_high': ticker.get('high', 0),
            '24h_low': ticker.get('low', 0)
        }

        # ============ 🆕 并行收集高级数据 ============
        self.logger.info("开始收集多维度市场数据...")

        # 记录整体数据收集开始时间
        collection_start_time = time.time()

        try:
            # 使用 asyncio.gather 并行收集所有高级数据
            # 为每个数据收集任务添加计时
            mtf_start = time.time()
            multi_timeframe_task = self.multi_timeframe_analyzer.analyze_timeframes(
                self.trader.exchange,
                self.trader.symbol,
                current_price
            )

            ob_start = time.time()
            orderbook_task = self.orderbook_analyzer.analyze_order_book(
                self.trader.exchange,
                self.trader.symbol,
                current_price
            )

            funding_start = time.time()
            funding_rate_task = self.derivatives_fetcher.fetch_funding_rate(
                self.trader.symbol
            )

            oi_start = time.time()
            open_interest_task = self.derivatives_fetcher.fetch_open_interest(
                self.trader.symbol
            )

            corr_start = time.time()
            btc_correlation_task = self.correlation_analyzer.analyze_btc_correlation(
                self.trader.exchange,
                self.trader.symbol,
                timeframe='1h',
                current_price=current_price
            )

            sentiment_task = self.sentiment_data.get_comprehensive_sentiment()

            # 并行执行所有任务
            (
                multi_timeframe_data,
                orderbook_data,
                funding_rate_data,
                open_interest_data,
                btc_correlation_data,
                sentiment
            ) = await asyncio.gather(
                multi_timeframe_task,
                orderbook_task,
                funding_rate_task,
                open_interest_task,
                btc_correlation_task,
                sentiment_task,
                return_exceptions=True  # 容错处理
            )

            # 记录各项数据收集性能
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics()
                    # 注意：由于并行执行，这里的时间测量不完全准确，但可以提供粗略估计
                    # 实际应该在每个分析器内部进行精确计时
                    total_duration = time.time() - collection_start_time
                    metrics.record_ai_data_collection(self.trader.symbol, 'all', total_duration)
                except Exception as me:
                    self.logger.warning(f"记录性能指标失败: {me}")

            # 容错处理：如果某个数据源失败，使用空数据
            if isinstance(multi_timeframe_data, Exception):
                self.logger.error(f"多时间周期分析失败: {multi_timeframe_data}")
                multi_timeframe_data = {}

            if isinstance(orderbook_data, Exception):
                self.logger.error(f"订单簿分析失败: {orderbook_data}")
                orderbook_data = {}

            if isinstance(funding_rate_data, Exception):
                self.logger.error(f"资金费率获取失败: {funding_rate_data}")
                funding_rate_data = {}

            if isinstance(open_interest_data, Exception):
                self.logger.error(f"持仓量获取失败: {open_interest_data}")
                open_interest_data = {}

            if isinstance(btc_correlation_data, Exception):
                self.logger.error(f"BTC相关性分析失败: {btc_correlation_data}")
                btc_correlation_data = {}

            if isinstance(sentiment, Exception):
                self.logger.error(f"市场情绪获取失败: {sentiment}")
                sentiment = {}

            self.logger.info("多维度市场数据收集完成")

        except Exception as e:
            self.logger.error(f"高级数据收集失败: {e}", exc_info=True)
            multi_timeframe_data = {}
            orderbook_data = {}
            funding_rate_data = {}
            open_interest_data = {}
            btc_correlation_data = {}
            sentiment = {}
        # ============================================

        # 持仓状态
        total_value = await self.trader._get_pair_specific_assets_value()
        balance = await self.trader.exchange.fetch_balance()
        funding_balance = await self.trader.exchange.fetch_funding_balance()

        base_amount = (
            float(balance.get('free', {}).get(self.trader.base_asset, 0)) +
            float(funding_balance.get(self.trader.base_asset, 0))
        )
        base_value = base_amount * current_price
        quote_value = (
            float(balance.get('free', {}).get(self.trader.quote_asset, 0)) +
            float(funding_balance.get(self.trader.quote_asset, 0))
        )

        position_ratio = base_value / total_value if total_value > 0 else 0

        # 计算盈亏
        initial_principal = getattr(settings, 'INITIAL_PRINCIPAL', 0)
        unrealized_pnl = total_value - initial_principal if initial_principal > 0 else 0
        pnl_pct = (unrealized_pnl / initial_principal * 100) if initial_principal > 0 else 0

        portfolio = {
            'total_value_usdt': total_value,
            'base_asset_value': base_value,
            'quote_asset_value': quote_value,
            'position_ratio': position_ratio,
            'unrealized_pnl': unrealized_pnl,
            'pnl_percentage': pnl_pct
        }

        # 网格状态
        grid_status = {
            'base_price': self.trader.base_price,
            'grid_size': self.trader.grid_size,
            'upper_band': self.trader._get_upper_band(),
            'lower_band': self.trader._get_lower_band(),
            'current_volatility': getattr(self.trader, 'last_volatility', 0),
            'next_buy_price': self.trader._get_lower_band(),
            'next_sell_price': self.trader._get_upper_band()
        }

        # 风险指标
        risk_metrics = {
            'max_position_ratio': settings.MAX_POSITION_RATIO,
            'min_position_ratio': settings.MIN_POSITION_RATIO,
            'current_risk_state': getattr(self.trader, 'current_risk_state', 'ALLOW_ALL'),
            'consecutive_losses': getattr(self.trader, 'consecutive_failures', 0),
            'max_drawdown': 'N/A'  # TODO: 实现最大回撤计算
        }

        # 最近交易
        recent_trades = []
        if hasattr(self.trader, 'order_tracker'):
            trades = self.trader.order_tracker.get_trade_history()
            recent_trades = [
                {
                    'time': datetime.fromtimestamp(t['timestamp']).strftime('%Y-%m-%d %H:%M'),
                    'side': t.get('side', 'N/A'),
                    'price': t.get('price', 0),
                    'amount': t.get('amount', 0),
                    'pnl': f"{t.get('profit', 0):.2f} USDT" if 'profit' in t else 'N/A'
                }
                for t in trades[-10:]
            ]

        return AIPromptBuilder.build_analysis_data(
            symbol=self.trader.symbol,
            market_data=market_data,
            technical_indicators=indicators,
            sentiment_data=sentiment,
            portfolio=portfolio,
            recent_trades=recent_trades,
            grid_status=grid_status,
            risk_metrics=risk_metrics,
            multi_timeframe=multi_timeframe_data,  # 🆕 多时间周期数据
            orderbook=orderbook_data,  # 🆕 订单簿深度数据
            derivatives={  # 🆕 衍生品数据
                'funding_rate': funding_rate_data,
                'open_interest': open_interest_data
            },
            correlation=btc_correlation_data  # 🆕 BTC相关性数据
        )

    async def _call_ai_model(self, prompt: str) -> Optional[str]:
        """
        调用AI模型

        Args:
            prompt: 提示词

        Returns:
            AI返回的文本
        """
        if self.ai_provider == AIProvider.OPENAI:
            return await self._call_openai(prompt)
        elif self.ai_provider == AIProvider.ANTHROPIC:
            return await self._call_anthropic(prompt)
        else:
            self.logger.error("不支持的AI提供商")
            return None

    async def _call_openai(self, prompt: str) -> Optional[str]:
        """调用OpenAI API"""
        start_time = time.time()
        try:
            response = await asyncio.to_thread(
                self.ai_client.chat.completions.create,
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": "You are a professional cryptocurrency trading analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            # 记录性能和token消耗
            latency = time.time() - start_time

            # 提取token使用情况
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            # 计算成本（以GPT-4为例，实际价格需要根据模型调整）
            # GPT-4-turbo: $10/1M prompt tokens, $30/1M completion tokens
            cost_usd = 0
            if 'gpt-4' in self.ai_model.lower():
                cost_usd = (prompt_tokens * 0.00001) + (completion_tokens * 0.00003)
            elif 'gpt-3.5' in self.ai_model.lower():
                # GPT-3.5-turbo: $0.5/1M prompt tokens, $1.5/1M completion tokens
                cost_usd = (prompt_tokens * 0.0000005) + (completion_tokens * 0.0000015)

            # 记录到Prometheus
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics()
                    metrics.record_ai_decision(
                        symbol=self.trader.symbol,
                        provider='openai',
                        status='success',
                        latency=latency,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        cost_usd=cost_usd
                    )
                except Exception as me:
                    self.logger.warning(f"记录AI指标失败: {me}")

            self.logger.info(
                f"OpenAI调用成功 | 耗时: {latency:.2f}s | "
                f"Tokens: {total_tokens} (prompt:{prompt_tokens}, completion:{completion_tokens}) | "
                f"成本: ${cost_usd:.6f}"
            )

            return response.choices[0].message.content

        except Exception as e:
            latency = time.time() - start_time
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics()
                    metrics.record_ai_decision(
                        symbol=self.trader.symbol,
                        provider='openai',
                        status='error',
                        latency=latency
                    )
                except Exception:
                    pass

            self.logger.error(f"OpenAI API调用失败: {e}")
            return None

    async def _call_anthropic(self, prompt: str) -> Optional[str]:
        """调用Anthropic API"""
        start_time = time.time()
        try:
            response = await asyncio.to_thread(
                self.ai_client.messages.create,
                model=self.ai_model,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # 记录性能和token消耗
            latency = time.time() - start_time

            # 提取token使用情况
            usage = response.usage
            prompt_tokens = usage.input_tokens if usage else 0
            completion_tokens = usage.output_tokens if usage else 0
            total_tokens = prompt_tokens + completion_tokens

            # 计算成本（Anthropic Claude价格）
            # Claude-3.5-sonnet: $3/1M input tokens, $15/1M output tokens
            cost_usd = 0
            if 'claude-3' in self.ai_model.lower() or 'claude-sonnet' in self.ai_model.lower():
                cost_usd = (prompt_tokens * 0.000003) + (completion_tokens * 0.000015)
            elif 'claude-opus' in self.ai_model.lower():
                # Claude-3-opus: $15/1M input tokens, $75/1M output tokens
                cost_usd = (prompt_tokens * 0.000015) + (completion_tokens * 0.000075)

            # 记录到Prometheus
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics()
                    metrics.record_ai_decision(
                        symbol=self.trader.symbol,
                        provider='anthropic',
                        status='success',
                        latency=latency,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        cost_usd=cost_usd
                    )
                except Exception as me:
                    self.logger.warning(f"记录AI指标失败: {me}")

            self.logger.info(
                f"Anthropic调用成功 | 耗时: {latency:.2f}s | "
                f"Tokens: {total_tokens} (input:{prompt_tokens}, output:{completion_tokens}) | "
                f"成本: ${cost_usd:.6f}"
            )

            return response.content[0].text

        except Exception as e:
            latency = time.time() - start_time
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics()
                    metrics.record_ai_decision(
                        symbol=self.trader.symbol,
                        provider='anthropic',
                        status='error',
                        latency=latency
                    )
                except Exception:
                    pass

            self.logger.error(f"Anthropic API调用失败: {e}")
            return None
