"""
全局资金分配器集成示例

展示如何将GlobalFundAllocator集成到GridTrader和main.py中
"""

# ============================================================================
# 步骤1: 修改 src/main.py
# ============================================================================

import asyncio
from typing import Dict
from src.core.trader import GridTrader
from src.core.exchanges.factory import ExchangeFactory, ExchangeType
from src.strategies.global_allocator import GlobalFundAllocator
from src.config.settings import settings, SYMBOLS_LIST

async def main():
    """主函数 - 启动多交易对交易"""

    # 🆕 步骤1: 创建全局资金分配器
    allocator = GlobalFundAllocator(
        symbols=SYMBOLS_LIST,
        total_capital=settings.INITIAL_PRINCIPAL,
        strategy=getattr(settings, 'ALLOCATION_STRATEGY', 'equal'),
        max_global_usage=getattr(settings, 'GLOBAL_MAX_USAGE', 0.95)
    )

    # 创建交易所实例（全局共享）
    exchange = await ExchangeFactory.create(
        exchange_type=ExchangeType(settings.EXCHANGE),
        config={
            'apiKey': settings.BINANCE_API_KEY if settings.EXCHANGE == 'binance'
                     else settings.OKX_API_KEY,
            'secret': settings.BINANCE_API_SECRET if settings.EXCHANGE == 'binance'
                     else settings.OKX_API_SECRET,
            # ... 其他配置
        }
    )

    # 🆕 步骤2: 为每个交易对创建trader，并传入分配器
    traders: Dict[str, GridTrader] = {}
    tasks = []

    for symbol in SYMBOLS_LIST:
        trader = GridTrader(
            symbol=symbol,
            exchange=exchange,
            global_allocator=allocator  # 🆕 传入分配器
        )

        traders[symbol] = trader

        # 🆕 步骤3: 注册trader到分配器
        allocator.register_trader(symbol, trader)

        # 创建异步任务
        task = asyncio.create_task(
            run_trader_for_symbol(trader),
            name=f"trader_{symbol.replace('/', '_')}"
        )
        tasks.append(task)

    # 🆕 步骤4: 启动全局状态监控任务
    monitor_task = asyncio.create_task(
        periodic_global_status_logger(allocator),
        name="global_allocator_monitor"
    )
    tasks.append(monitor_task)

    # 等待所有任务
    await asyncio.gather(*tasks, return_exceptions=True)


async def periodic_global_status_logger(allocator: GlobalFundAllocator):
    """定期打印全局资金分配状态"""
    while True:
        try:
            await asyncio.sleep(300)  # 每5分钟

            # 打印状态
            summary = await allocator.get_global_status_summary()
            print(summary)

            # 动态重新平衡（如果启用）
            await allocator.rebalance_if_needed()

        except Exception as e:
            print(f"全局状态监控错误: {e}")


# ============================================================================
# 步骤2: 修改 src/core/trader.py
# ============================================================================

from typing import Optional
from src.strategies.global_allocator import GlobalFundAllocator

class GridTrader:
    """网格交易器"""

    def __init__(
        self,
        symbol: str,
        exchange,
        global_allocator: Optional[GlobalFundAllocator] = None  # 🆕 新增参数
    ):
        # ... 现有初始化代码 ...

        self.symbol = symbol
        self.exchange = exchange

        # 🆕 保存全局分配器引用
        self.global_allocator = global_allocator

        # 如果没有分配器，记录警告
        if not self.global_allocator:
            self.logger.warning(
                "未使用全局资金分配器，多交易对可能存在资金冲突！"
            )

    async def execute_order(self, side: Literal['buy', 'sell']):
        """
        执行订单

        🆕 集成全局资金检查
        """
        try:
            # ... 原有代码：计算订单金额 ...

            amount_usdt = await self._calculate_order_amount(side)

            # 🆕 步骤1: 全局资金检查
            if self.global_allocator:
                allowed, reason = await self.global_allocator.check_trade_allowed(
                    symbol=self.symbol,
                    required_amount=amount_usdt,
                    side=side
                )

                if not allowed:
                    self.logger.warning(
                        f"全局资金分配器拒绝交易 | "
                        f"{side} {self.symbol} | "
                        f"金额: {amount_usdt:.2f} USDT | "
                        f"原因: {reason}"
                    )
                    return False

            # ... 原有代码：执行订单 ...

            order = await self.exchange.create_order(
                self.symbol,
                'limit',
                side,
                amount,
                price
            )

            # ... 等待订单成交 ...

            # 🆕 步骤2: 交易成功后记录到分配器
            if self.global_allocator and order['status'] == 'closed':
                await self.global_allocator.record_trade(
                    symbol=self.symbol,
                    amount=amount_usdt,
                    side=side
                )

                self.logger.debug(
                    f"已记录交易到全局分配器 | "
                    f"{side} {amount_usdt:.2f} USDT"
                )

            return True

        except Exception as e:
            self.logger.error(f"执行订单失败: {e}")
            return False


# ============================================================================
# 步骤3: 添加配置项到 .env
# ============================================================================

"""
在 .env 文件中添加以下配置:

# ============================================================================
# 全局资金分配配置
# ============================================================================

# 总本金（USDT）- 用于计算全局分配
INITIAL_PRINCIPAL=1000.0

# 资金分配策略
# - equal: 平均分配（默认）
# - weighted: 按权重分配
# - dynamic: 动态分配（根据表现调整）
ALLOCATION_STRATEGY=equal

# 全局最大资金使用率（0-1之间）
GLOBAL_MAX_USAGE=0.95

# 权重配置（仅当ALLOCATION_STRATEGY=weighted时使用，JSON格式）
ALLOCATION_WEIGHTS={"BNB/USDT": 1.5, "ETH/USDT": 1.0, "BTC/USDT": 1.0}

# 动态重新平衡间隔（秒）
REBALANCE_INTERVAL=3600
"""


# ============================================================================
# 步骤4: 更新 src/config/settings.py
# ============================================================================

class Settings(BaseSettings):
    """应用程序设置类"""

    # ... 现有配置 ...

    # 🆕 全局资金分配配置
    ALLOCATION_STRATEGY: str = "equal"
    GLOBAL_MAX_USAGE: float = 0.95
    ALLOCATION_WEIGHTS: Dict[str, float] = {}
    REBALANCE_INTERVAL: int = 3600

    @field_validator('ALLOCATION_WEIGHTS', mode='before')
    @classmethod
    def parse_allocation_weights(cls, value):
        """解析权重配置JSON"""
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("ALLOCATION_WEIGHTS格式无效")
        return value if value else {}

    @field_validator('GLOBAL_MAX_USAGE')
    @classmethod
    def validate_global_max_usage(cls, v):
        """验证全局使用率"""
        if v < 0.5 or v > 1.0:
            raise ValueError(f"GLOBAL_MAX_USAGE必须在0.5-1.0之间，当前: {v}")
        return v

    @field_validator('ALLOCATION_STRATEGY')
    @classmethod
    def validate_allocation_strategy(cls, v):
        """验证分配策略"""
        valid = ['equal', 'weighted', 'dynamic']
        if v not in valid:
            raise ValueError(f"ALLOCATION_STRATEGY必须是{valid}之一，当前: {v}")
        return v


# ============================================================================
# 使用示例
# ============================================================================

"""
示例1: 平均分配（默认）

配置 .env:
    SYMBOLS=BNB/USDT,ETH/USDT,BTC/USDT
    INITIAL_PRINCIPAL=1200.0
    ALLOCATION_STRATEGY=equal
    GLOBAL_MAX_USAGE=0.95

结果:
    BNB/USDT: 400 USDT (33.3%)
    ETH/USDT: 400 USDT (33.3%)
    BTC/USDT: 400 USDT (33.3%)
    全局限额: 1140 USDT (95%)

每个交易对最多使用400 USDT，所有交易对合计不超过1140 USDT
"""

"""
示例2: 权重分配

配置 .env:
    SYMBOLS=BNB/USDT,ETH/USDT,BTC/USDT
    INITIAL_PRINCIPAL=1000.0
    ALLOCATION_STRATEGY=weighted
    ALLOCATION_WEIGHTS={"BNB/USDT": 2.0, "ETH/USDT": 1.5, "BTC/USDT": 1.0}

结果:
    总权重 = 2.0 + 1.5 + 1.0 = 4.5

    BNB/USDT: 444 USDT (2.0/4.5 = 44.4%)
    ETH/USDT: 333 USDT (1.5/4.5 = 33.3%)
    BTC/USDT: 222 USDT (1.0/4.5 = 22.2%)

BNB分配最多资金，因为权重最高
"""

"""
示例3: 动态分配

配置 .env:
    SYMBOLS=BNB/USDT,ETH/USDT
    INITIAL_PRINCIPAL=1000.0
    ALLOCATION_STRATEGY=dynamic
    REBALANCE_INTERVAL=3600

工作原理:
1. 初始平均分配: 各500 USDT
2. 运行1小时后，系统评估表现:
   - BNB/USDT: 盈利 +50 USDT (评分 1.5)
   - ETH/USDT: 亏损 -10 USDT (评分 0.8)
3. 重新分配:
   总评分 = 1.5 + 0.8 = 2.3
   - BNB/USDT: 652 USDT (1.5/2.3 = 65.2%)
   - ETH/USDT: 348 USDT (0.8/2.3 = 34.8%)

表现好的交易对获得更多资金！
"""
