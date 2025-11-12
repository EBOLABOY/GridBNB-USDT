"""
Prometheus 指标收集器

为GridBNB交易系统提供Prometheus格式的指标收集和导出功能
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
import time
import psutil
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TradingMetrics:
    """交易系统指标收集器"""

    def __init__(self):
        """初始化所有Prometheus指标"""

        # === 系统信息 ===
        self.system_info = Info('gridbnb_system', 'System information')
        self.system_info.info({
            'version': '2.0.0',
            'python_version': '3.13',
            'application': 'GridBNB-USDT'
        })

        # === 订单相关指标 ===
        # 订单总数(按交易对和方向分类)
        self.orders_total = Counter(
            'gridbnb_orders_total',
            'Total number of orders',
            ['symbol', 'side', 'status']
        )

        # 订单执行延迟
        self.order_latency = Histogram(
            'gridbnb_order_latency_seconds',
            'Order execution latency in seconds',
            ['symbol', 'side'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
        )

        # 订单失败次数
        self.order_failures = Counter(
            'gridbnb_order_failures_total',
            'Total number of failed orders',
            ['symbol', 'side', 'error_type']
        )

        # === 账户余额指标 ===
        # USDT余额
        self.usdt_balance = Gauge(
            'gridbnb_usdt_balance',
            'USDT balance',
            ['account_type']  # spot, savings
        )

        # 基础货币余额(BNB, ETH等)
        self.base_balance = Gauge(
            'gridbnb_base_balance',
            'Base currency balance',
            ['symbol', 'currency']
        )

        # 账户总价值(USDT)
        self.total_account_value = Gauge(
            'gridbnb_total_account_value_usdt',
            'Total account value in USDT'
        )

        # === 网格策略指标 ===
        # 当前网格大小
        self.grid_size = Gauge(
            'gridbnb_grid_size_percent',
            'Current grid size in percentage',
            ['symbol']
        )

        # 网格上轨价格
        self.grid_upper_band = Gauge(
            'gridbnb_grid_upper_band',
            'Grid upper band price',
            ['symbol']
        )

        # 网格下轨价格
        self.grid_lower_band = Gauge(
            'gridbnb_grid_lower_band',
            'Grid lower band price',
            ['symbol']
        )

        # 基准价格
        self.base_price = Gauge(
            'gridbnb_base_price',
            'Grid base price',
            ['symbol']
        )

        # 当前市场价格
        self.current_price = Gauge(
            'gridbnb_current_price',
            'Current market price',
            ['symbol']
        )

        # === 收益指标 ===
        # 总盈亏(USDT)
        self.total_profit = Gauge(
            'gridbnb_total_profit_usdt',
            'Total profit in USDT',
            ['symbol']
        )

        # 盈亏率(%)
        self.profit_rate = Gauge(
            'gridbnb_profit_rate_percent',
            'Profit rate in percentage',
            ['symbol']
        )

        # 单笔交易盈亏
        self.trade_profit = Histogram(
            'gridbnb_trade_profit_usdt',
            'Individual trade profit in USDT',
            ['symbol'],
            buckets=(-10, -5, -1, 0, 1, 5, 10, 20, 50, 100)
        )

        # === 风险管理指标 ===
        # 仓位比例
        self.position_ratio = Gauge(
            'gridbnb_position_ratio',
            'Position ratio (base value / total value)',
            ['symbol']
        )

        # 风险状态
        self.risk_state = Gauge(
            'gridbnb_risk_state',
            'Risk state (0=ALLOW_ALL, 1=ALLOW_SELL_ONLY, 2=ALLOW_BUY_ONLY)',
            ['symbol']
        )

        # === 波动率指标 ===
        # 52日年化波动率
        self.volatility = Gauge(
            'gridbnb_volatility',
            'Annualized volatility (52-day)',
            ['symbol']
        )

        # === API调用指标 ===
        # API调用总数
        self.api_calls_total = Counter(
            'gridbnb_api_calls_total',
            'Total number of API calls',
            ['method', 'status']
        )

        # API调用延迟
        self.api_latency = Histogram(
            'gridbnb_api_latency_seconds',
            'API call latency in seconds',
            ['method'],
            buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0)
        )

        # API错误计数
        self.api_errors = Counter(
            'gridbnb_api_errors_total',
            'Total number of API errors',
            ['method', 'error_type']
        )

        # === 系统资源指标 ===
        # CPU使用率
        self.cpu_usage = Gauge(
            'gridbnb_cpu_usage_percent',
            'CPU usage percentage'
        )

        # 内存使用率
        self.memory_usage = Gauge(
            'gridbnb_memory_usage_percent',
            'Memory usage percentage'
        )

        # 磁盘使用率
        self.disk_usage = Gauge(
            'gridbnb_disk_usage_percent',
            'Disk usage percentage'
        )

        # 运行时间
        self.uptime_seconds = Gauge(
            'gridbnb_uptime_seconds',
            'Application uptime in seconds'
        )

        # === AI策略指标 ===
        # AI数据收集耗时
        self.ai_data_collection_duration = Histogram(
            'gridbnb_ai_data_collection_seconds',
            'AI market data collection duration in seconds',
            ['symbol', 'data_type'],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0)
        )

        # AI决策调用次数
        self.ai_decisions_total = Counter(
            'gridbnb_ai_decisions_total',
            'Total number of AI decision calls',
            ['symbol', 'provider', 'status']
        )

        # AI决策延迟
        self.ai_decision_latency = Histogram(
            'gridbnb_ai_decision_latency_seconds',
            'AI decision API call latency in seconds',
            ['symbol', 'provider'],
            buckets=(1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
        )

        # AI Token消耗
        self.ai_tokens_used = Counter(
            'gridbnb_ai_tokens_total',
            'Total AI tokens consumed',
            ['symbol', 'provider', 'token_type']  # token_type: prompt, completion, total
        )

        # AI Token消耗成本（美元）
        self.ai_cost_usd = Counter(
            'gridbnb_ai_cost_usd_total',
            'Total AI API cost in USD',
            ['symbol', 'provider']
        )

        # AI决策置信度
        self.ai_confidence = Gauge(
            'gridbnb_ai_confidence',
            'Latest AI decision confidence score',
            ['symbol', 'action']  # action: buy, sell, hold
        )

        # 启动时间戳
        self.start_time = time.time()

        logger.info("Prometheus指标收集器已初始化")

    def record_order(self, symbol: str, side: str, status: str, latency: float = None):
        """记录订单执行"""
        self.orders_total.labels(symbol=symbol, side=side, status=status).inc()

        if latency is not None:
            self.order_latency.labels(symbol=symbol, side=side).observe(latency)

    def record_order_failure(self, symbol: str, side: str, error_type: str):
        """记录订单失败"""
        self.order_failures.labels(symbol=symbol, side=side, error_type=error_type).inc()

    def update_balances(self, usdt_spot: float = None, usdt_savings: float = None,
                       base_balances: Dict[str, float] = None):
        """更新余额指标"""
        if usdt_spot is not None:
            self.usdt_balance.labels(account_type='spot').set(usdt_spot)

        if usdt_savings is not None:
            self.usdt_balance.labels(account_type='savings').set(usdt_savings)

        if base_balances:
            for symbol, balance in base_balances.items():
                currency = symbol.split('/')[0]  # BNB/USDT -> BNB
                self.base_balance.labels(symbol=symbol, currency=currency).set(balance)

    def update_grid_params(self, symbol: str, grid_size: float = None, base_price: float = None,
                          current_price: float = None, upper_band: float = None,
                          lower_band: float = None):
        """更新网格参数"""
        if grid_size is not None:
            self.grid_size.labels(symbol=symbol).set(grid_size * 100)  # 转换为百分比

        if base_price is not None:
            self.base_price.labels(symbol=symbol).set(base_price)

        if current_price is not None:
            self.current_price.labels(symbol=symbol).set(current_price)

        if upper_band is not None:
            self.grid_upper_band.labels(symbol=symbol).set(upper_band)

        if lower_band is not None:
            self.grid_lower_band.labels(symbol=symbol).set(lower_band)

    def update_profit(self, symbol: str, total_profit: float = None, profit_rate: float = None,
                     trade_profit: float = None):
        """更新收益指标"""
        if total_profit is not None:
            self.total_profit.labels(symbol=symbol).set(total_profit)

        if profit_rate is not None:
            self.profit_rate.labels(symbol=symbol).set(profit_rate * 100)  # 转换为百分比

        if trade_profit is not None:
            self.trade_profit.labels(symbol=symbol).observe(trade_profit)

    def update_risk_metrics(self, symbol: str, position_ratio: float = None, risk_state: int = None):
        """更新风险指标"""
        if position_ratio is not None:
            self.position_ratio.labels(symbol=symbol).set(position_ratio)

        if risk_state is not None:
            self.risk_state.labels(symbol=symbol).set(risk_state)

    def update_volatility(self, symbol: str, volatility: float):
        """更新波动率"""
        self.volatility.labels(symbol=symbol).set(volatility)

    def record_api_call(self, method: str, status: str, latency: float = None):
        """记录API调用"""
        self.api_calls_total.labels(method=method, status=status).inc()

        if latency is not None:
            self.api_latency.labels(method=method).observe(latency)

    def record_api_error(self, method: str, error_type: str):
        """记录API错误"""
        self.api_errors.labels(method=method, error_type=error_type).inc()

    def update_system_metrics(self):
        """更新系统资源指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_usage.set(cpu_percent)

            # 内存使用率
            memory = psutil.virtual_memory()
            self.memory_usage.set(memory.percent)

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            self.disk_usage.set(disk.percent)

            # 运行时间
            uptime = time.time() - self.start_time
            self.uptime_seconds.set(uptime)

        except Exception as e:
            logger.error(f"更新系统指标失败: {e}")

    def set_total_account_value(self, value: float):
        """设置账户总价值"""
        self.total_account_value.set(value)

    def record_ai_data_collection(self, symbol: str, data_type: str, duration: float):
        """
        记录AI数据收集性能

        Args:
            symbol: 交易对
            data_type: 数据类型（multi_timeframe, orderbook, derivatives, correlation, all）
            duration: 耗时（秒）
        """
        self.ai_data_collection_duration.labels(symbol=symbol, data_type=data_type).observe(duration)

    def record_ai_decision(self, symbol: str, provider: str, status: str, latency: float = None,
                          prompt_tokens: int = None, completion_tokens: int = None,
                          total_tokens: int = None, cost_usd: float = None,
                          confidence: float = None, action: str = None):
        """
        记录AI决策调用

        Args:
            symbol: 交易对
            provider: AI提供商（openai, anthropic等）
            status: 状态（success, error）
            latency: API调用延迟（秒）
            prompt_tokens: prompt token数量
            completion_tokens: completion token数量
            total_tokens: 总token数量
            cost_usd: 成本（美元）
            confidence: 决策置信度
            action: 决策动作（buy, sell, hold）
        """
        # 记录调用次数
        self.ai_decisions_total.labels(symbol=symbol, provider=provider, status=status).inc()

        # 记录延迟
        if latency is not None:
            self.ai_decision_latency.labels(symbol=symbol, provider=provider).observe(latency)

        # 记录token消耗
        if prompt_tokens is not None:
            self.ai_tokens_used.labels(symbol=symbol, provider=provider, token_type='prompt').inc(prompt_tokens)
        if completion_tokens is not None:
            self.ai_tokens_used.labels(symbol=symbol, provider=provider, token_type='completion').inc(completion_tokens)
        if total_tokens is not None:
            self.ai_tokens_used.labels(symbol=symbol, provider=provider, token_type='total').inc(total_tokens)

        # 记录成本
        if cost_usd is not None:
            self.ai_cost_usd.labels(symbol=symbol, provider=provider).inc(cost_usd)

        # 记录置信度
        if confidence is not None and action is not None:
            self.ai_confidence.labels(symbol=symbol, action=action).set(confidence)

    def get_metrics(self) -> bytes:
        """获取Prometheus格式的指标数据"""
        # 更新系统指标
        self.update_system_metrics()

        # 生成Prometheus格式的数据
        return generate_latest()


# 全局指标实例
_metrics: Optional[TradingMetrics] = None


def get_metrics() -> TradingMetrics:
    """获取全局指标实例"""
    global _metrics
    if _metrics is None:
        _metrics = TradingMetrics()
    return _metrics


def reset_metrics():
    """重置指标(用于测试)"""
    global _metrics
    _metrics = None
