# 网格策略前端配置功能待实现清单

> **创建日期**: 2025-11-06
> **最后更新**: 2025-11-06
> **状态**: 进行中
> **前端实现覆盖率**: 38% (10/39 已实现，5/39 部分实现，24/39 未实现)

## 📋 概述

前端网格策略配置页面 (`web/src/pages/Template/GridConfig.tsx`) 已经实现了完整的用户界面，包含39个配置字段。本文档追踪这些配置项在后端的实现状态，按优先级规划实施计划。

## 📊 实现状态总览

| 类别 | 字段数 | 已实现 | 部分实现 | 未实现 | 覆盖率 |
|-----|--------|--------|---------|--------|--------|
| 交易对配置 | 2 | ✅ 2 | - | - | 100% |
| 核心交易逻辑 | 10 | - | 🟡 2 | ❌ 8 | 20% |
| 订单执行 | 5 | - | 🟡 1 | ❌ 4 | 20% |
| 数量/金额管理 | 7 | - | 🟡 2 | ❌ 5 | 29% |
| 仓位控制 | 2 | ✅ 2 | - | - | 100% |
| 波动率自适应 | 6 | ✅ 6 | - | - | 100% |
| 高级功能 | 7 | - | - | ❌ 7 | 0% |
| **总计** | **39** | **10** | **5** | **24** | **38%** |

---

## ✅ 已实现功能 (10/39)

### 1. 交易对配置 (2/2)

| 字段 | 后端实现 | 位置 | 说明 |
|-----|---------|------|------|
| base_currency | `SYMBOLS` | `settings.py:40` | 通过 `BNB/USDT` 格式解析 |
| quote_currency | `SYMBOLS` | `settings.py:40` | 通过 `BNB/USDT` 格式解析 |

### 2. 仓位控制 (2/2)

| 字段 | 后端实现 | 位置 | 说明 |
|-----|---------|------|------|
| max_position | `MAX_POSITION_RATIO` / `POSITION_LIMITS_JSON` | `settings.py:84,106` | 全局或交易对级别限制 |
| min_position | `MIN_POSITION_RATIO` / `POSITION_LIMITS_JSON` | `settings.py:87,106` | 全局或交易对级别限制 |

### 3. 波动率自适应 (6/6)

| 字段 | 后端实现 | 位置 | 说明 |
|-----|---------|------|------|
| enable_volatility_adjustment | `GRID_CONTINUOUS_PARAMS_JSON` | `settings.py:77` | 配置存在即启用 |
| base_grid | `GRID_CONTINUOUS_PARAMS_JSON.base_grid` | `settings.py:77, .env:238` | 基础网格大小 |
| center_volatility | `GRID_CONTINUOUS_PARAMS_JSON.center_volatility` | `settings.py:77, .env:238` | 中心波动率 |
| sensitivity_k | `GRID_CONTINUOUS_PARAMS_JSON.sensitivity_k` | `settings.py:77, .env:238` | 敏感度系数 |
| enable_dynamic_interval | `DYNAMIC_INTERVAL_PARAMS_JSON` | `settings.py:78, .env:244` | 动态交易间隔 |
| default_interval_hours | `DYNAMIC_INTERVAL_PARAMS_JSON.default_interval_hours` | `settings.py:78, .env:244` | 默认间隔 |
| enable_volume_weighting | `ENABLE_VOLUME_WEIGHTING` | `settings.py:79, .env:247` | 成交量加权 |

---

## 🟡 部分实现功能 (5/39)

### 1. 价格区间 (2/2 - 概念支持但无配置项)

| 字段 | 当前状态 | 说明 |
|-----|---------|------|
| price_min | ⚠️ 风控相关逻辑存在 | 有止损机制但无明确的价格区间配置 |
| price_max | ⚠️ 风控相关逻辑存在 | 有止盈机制但无明确的价格区间配置 |

**建议**:
- 添加 `GRID_PRICE_MIN` 和 `GRID_PRICE_MAX` 配置项
- 在 `risk_manager.py` 中实现价格区间检查
- 超出区间时暂停交易或发出警告

### 2. 订单类型 (1/5 - 代码支持但硬编码)

| 字段 | 当前状态 | 说明 |
|-----|---------|------|
| order_type | 🟡 **硬编码为 limit** | `exchange_client.py` 支持，但 `trader.py` 中固定使用限价单 |

**建议**: 在 `trader.py` 中添加市价单逻辑分支

### 3. 网格大小 (2/7 - 仅支持统一网格)

| 字段 | 当前状态 | 说明 |
|-----|---------|------|
| INITIAL_GRID | ✅ 已实现 | `settings.py:45` - 全局默认网格大小 |
| grid_type | ❌ 未实现 | 缺少按百分比 vs 按价差的区分 |

**建议**: 实现 `grid_type` 来支持两种模式

---

## ❌ 未实现功能 (24/39)

### 🔴 P0 - 核心功能（必须实现）

#### 1.1 触发条件核心逻辑 (6个字段)

| 字段 | 功能描述 | 实现难度 | 预计工作量 | 依赖 |
|-----|---------|---------|-----------|-----|
| **grid_type** | 按百分比 vs 按价差 | 🟡 中等 | 4h | 无 |
| **trigger_base_price_type** | 触发基准价类型（current/cost/avg_24h/manual） | 🟢 简单 | 2h | 无 |
| **trigger_base_price** | 手动触发基准价 | 🟢 简单 | 1h | trigger_base_price_type |
| **rise_sell_percent** | 上涨卖出百分比/价差 | 🟡 中等 | 3h | grid_type |
| **fall_buy_percent** | 下跌买入百分比/价差 | 🟡 中等 | 3h | grid_type |
| **enable_pullback_sell** | 启用回落卖出 | 🟡 中等 | 4h | rise_sell_percent |
| **pullback_sell_percent** | 回落卖出触发条件 | 🟡 中等 | 3h | enable_pullback_sell |
| **enable_rebound_buy** | 启用拐点买入 | 🟡 中等 | 4h | fall_buy_percent |
| **rebound_buy_percent** | 拐点买入触发条件 | 🟡 中等 | 3h | enable_rebound_buy |

**总工作量**: ~27小时

**实施计划**:
1. **阶段1**: 基础触发机制 (grid_type, rise_sell, fall_buy) - 10h
2. **阶段2**: 基准价选择 (trigger_base_price_*) - 3h
3. **阶段3**: 高级触发 (pullback, rebound) - 14h

**技术要点**:
```python
# 示例实现结构
class GridTriggerConfig:
    grid_type: Literal['percent', 'price']  # 百分比 or 价差
    trigger_base_price_type: Literal['current', 'cost', 'avg_24h', 'manual']
    trigger_base_price: Optional[float]

    rise_sell_percent: float  # grid_type='percent' 时为百分比
    fall_buy_percent: float   # grid_type='price' 时为价格差

    enable_pullback_sell: bool
    pullback_sell_percent: float
    enable_rebound_buy: bool
    rebound_buy_percent: float

# trader.py 中新增方法
async def calculate_trigger_levels(self):
    """计算触发价位"""
    base_price = await self.get_base_price()  # 根据 trigger_base_price_type

    if self.config.grid_type == 'percent':
        sell_trigger = base_price * (1 + self.config.rise_sell_percent / 100)
        buy_trigger = base_price * (1 - self.config.fall_buy_percent / 100)
    else:  # 'price'
        sell_trigger = base_price + self.config.rise_sell_percent
        buy_trigger = base_price - self.config.fall_buy_percent

    return sell_trigger, buy_trigger
```

#### 1.2 数量/金额管理 (5个字段)

| 字段 | 功能描述 | 实现难度 | 预计工作量 | 依赖 |
|-----|---------|---------|-----------|-----|
| **amount_mode** | 按百分比 vs 按金额(USDT) | 🟢 简单 | 2h | 无 |
| **grid_symmetric** | 对称 vs 不对称网格 | 🟡 中等 | 3h | 无 |
| **order_quantity** | 对称网格每笔委托数量 | 🟢 简单 | 2h | amount_mode |
| **buy_quantity** | 不对称网格买入数量 | 🟢 简单 | 1h | grid_symmetric |
| **sell_quantity** | 不对称网格卖出数量 | 🟢 简单 | 1h | grid_symmetric |

**总工作量**: ~9小时

**实施计划**:
1. **阶段1**: 金额模式切换 (amount_mode, order_quantity) - 4h
2. **阶段2**: 不对称网格 (grid_symmetric, buy/sell_quantity) - 5h

**技术要点**:
```python
class GridQuantityConfig:
    amount_mode: Literal['percent', 'amount']  # 百分比 or 固定金额
    grid_symmetric: bool

    # 对称网格（单一数量）
    order_quantity: Optional[float]  # percent模式时为%, amount模式时为USDT

    # 不对称网格（分别设置）
    buy_quantity: Optional[float]
    sell_quantity: Optional[float]

# trader.py 中修改
async def _calculate_order_amount(self, side: str):
    """计算订单数量"""
    if self.config.amount_mode == 'percent':
        # 按百分比
        total_value = await self.get_total_value()
        if self.config.grid_symmetric:
            percent = self.config.order_quantity / 100
        else:
            percent = (self.config.buy_quantity if side == 'buy'
                      else self.config.sell_quantity) / 100
        return total_value * percent
    else:  # 'amount'
        # 按固定金额
        if self.config.grid_symmetric:
            return self.config.order_quantity
        else:
            return (self.config.buy_quantity if side == 'buy'
                   else self.config.sell_quantity)
```

#### 1.3 订单执行优化 (4个字段)

| 字段 | 功能描述 | 实现难度 | 预计工作量 | 依赖 |
|-----|---------|---------|-----------|-----|
| **buy_price_mode** | 买入参考价（bid1-5/ask1-5/trigger） | 🟡 中等 | 4h | 盘口数据获取 |
| **sell_price_mode** | 卖出参考价（bid1-5/ask1-5/trigger） | 🟡 中等 | 4h | 盘口数据获取 |
| **buy_price_offset** | 买入价格偏移 | 🟢 简单 | 1h | buy_price_mode |
| **sell_price_offset** | 卖出价格偏移 | 🟢 简单 | 1h | sell_price_mode |

**总工作量**: ~10小时

**实施计划**:
1. **阶段1**: 盘口数据获取 - 3h
2. **阶段2**: 价格档位选择 - 5h
3. **阶段3**: 价格偏移 - 2h

**技术要点**:
```python
class OrderPriceConfig:
    buy_price_mode: str  # 'bid1', 'bid2', ..., 'ask1', ..., 'trigger'
    sell_price_mode: str
    buy_price_offset: Optional[float]
    sell_price_offset: Optional[float]

# exchange_client.py 中新增
async def get_order_book_price(self, symbol: str, mode: str) -> float:
    """获取盘口价格"""
    orderbook = await self.exchange.fetch_order_book(symbol, limit=5)

    if mode.startswith('bid'):
        level = int(mode[3:])  # 'bid1' -> 1
        return orderbook['bids'][level - 1][0]
    elif mode.startswith('ask'):
        level = int(mode[3:])
        return orderbook['asks'][level - 1][0]
    else:  # 'trigger'
        return self.trigger_price

# trader.py 中使用
async def calculate_order_price(self, side: str) -> float:
    """计算委托价格"""
    mode = (self.config.buy_price_mode if side == 'buy'
           else self.config.sell_price_mode)

    base_price = await self.exchange_client.get_order_book_price(
        self.symbol, mode
    )

    offset = (self.config.buy_price_offset if side == 'buy'
             else self.config.sell_price_offset) or 0

    return base_price + offset
```

---

### 🟡 P1 - 重要功能（应该实现）

#### 2.1 高级风控 (2个字段)

| 字段 | 功能描述 | 实现难度 | 预计工作量 | 依赖 |
|-----|---------|---------|-----------|-----|
| **enable_floor_price** | 保底价触发 | 🟡 中等 | 3h | price_min |
| **enable_auto_close** | 清仓设置 | 🟡 中等 | 4h | 风控系统 |

**总工作量**: ~7小时

**实施计划**:
1. 在 `risk_manager.py` 中实现保底价检查
2. 添加自动清仓逻辑（触发条件可配置）

**技术要点**:
```python
class AdvancedRiskConfig:
    enable_floor_price: bool
    floor_price: Optional[float]  # 保底价
    floor_price_action: str  # 'stop' or 'alert'

    enable_auto_close: bool
    auto_close_conditions: Dict  # 清仓条件配置

# risk_manager.py 中
async def check_floor_price(self, current_price: float) -> bool:
    """检查是否触及保底价"""
    if not self.config.enable_floor_price:
        return False

    if current_price <= self.config.floor_price:
        if self.config.floor_price_action == 'stop':
            await self.emergency_stop()
        else:
            await self.send_alert("触及保底价")
        return True
    return False
```

---

### 🟢 P2 - 可选功能（增强体验）

#### 3.1 策略生命周期 (1个字段)

| 字段 | 功能描述 | 实现难度 | 预计工作量 | 依赖 |
|-----|---------|---------|-----------|-----|
| **expiry_days** | 策略有效期（天数，-1=永久） | 🟢 简单 | 2h | 无 |

**实施计划**:
- 在策略启动时记录开始时间
- 每次主循环检查是否过期
- 过期后自动停止策略

**技术要点**:
```python
class StrategyLifecycle:
    expiry_days: int  # -1 = 永久
    start_time: datetime

    def is_expired(self) -> bool:
        if self.expiry_days < 0:
            return False
        elapsed = (datetime.now() - self.start_time).days
        return elapsed >= self.expiry_days
```

#### 3.2 交易时段控制 (1个字段)

| 字段 | 功能描述 | 实现难度 | 预计工作量 | 依赖 |
|-----|---------|---------|-----------|-----|
| **enable_monitor_period** | 监控时段设置 | 🟡 中等 | 3h | 无 |

**实施计划**:
- 添加时段配置（如：只在工作日交易，或特定时间段）
- 在主循环中检查当前时段

**技术要点**:
```python
class TradingPeriodConfig:
    enable_monitor_period: bool
    trading_hours: List[Tuple[int, int]]  # [(9, 17), ...]
    trading_days: List[int]  # [1, 2, 3, 4, 5]  # 周一到周五
    timezone: str  # 'Asia/Shanghai'
```

#### 3.3 高级优化 (3个字段)

| 字段 | 功能描述 | 实现难度 | 预计工作量 | 依赖 |
|-----|---------|---------|-----------|-----|
| **enable_deviation_control** | 偏差控制 | 🔴 复杂 | 8h | 市场数据分析 |
| **enable_price_optimization** | 报价优化 | 🔴 复杂 | 10h | 盘口深度分析 |
| **enable_delay_confirm** | 延迟确认 | 🟡 中等 | 4h | 订单执行系统 |

**总工作量**: ~22小时

**说明**: 这些是高级算法优化功能，实现复杂度较高，建议放在最后实施。

---

## 🗓️ 实施路线图

### 第一阶段：核心交易逻辑 (预计 46 小时)

**目标**: 实现基本的网格策略配置功能

1. **Week 1** (16h):
   - ✅ 设计 `GridStrategyConfig` 数据模型
   - ✅ 实现 grid_type（按百分比/价差）
   - ✅ 实现触发基准价选择
   - ✅ 实现 rise_sell/fall_buy 基础逻辑

2. **Week 2** (14h):
   - ✅ 实现回落卖出逻辑
   - ✅ 实现拐点买入逻辑
   - ✅ 单元测试覆盖

3. **Week 3** (9h):
   - ✅ 实现金额模式切换
   - ✅ 实现对称/不对称网格

4. **Week 4** (10h):
   - ✅ 实现盘口价格档位
   - ✅ 实现价格偏移
   - ✅ 集成测试

**交付物**:
- `src/strategies/grid_strategy_config.py` - 配置模型
- `src/core/trader.py` - 更新交易逻辑
- `tests/unit/test_grid_strategy.py` - 单元测试
- 覆盖率目标: 70%

### 第二阶段：高级功能 (预计 20 小时)

**目标**: 实现风控和优化功能

1. **Week 5** (10h):
   - ✅ 实现价格区间限制
   - ✅ 实现保底价触发
   - ✅ 实现市价单支持

2. **Week 6** (10h):
   - ✅ 实现自动清仓
   - ✅ 实现策略有效期
   - ✅ 实现交易时段控制

**交付物**:
- `src/strategies/risk_manager.py` - 更新风控逻辑
- 覆盖率目标: 80%

### 第三阶段：高级优化（可选）

**目标**: 实现算法优化功能

- 偏差控制
- 报价优化
- 延迟确认

**预计**: 20-30小时

---

## 📦 数据模型设计

### 建议的配置结构

```python
# src/strategies/grid_strategy_config.py

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Dict, List
from datetime import datetime

class GridStrategyConfig(BaseModel):
    """网格策略完整配置"""

    # ========== 基础信息 ==========
    strategy_id: Optional[int] = None
    strategy_name: str
    symbol: str  # 'BNB/USDT'
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # ========== 触发条件 ==========
    grid_type: Literal['percent', 'price'] = 'percent'
    trigger_base_price_type: Literal['current', 'cost', 'avg_24h', 'manual'] = 'current'
    trigger_base_price: Optional[float] = None

    # 价格区间
    price_min: Optional[float] = None
    price_max: Optional[float] = None

    # 基础触发条件
    rise_sell_percent: float = 1.0  # 百分比或价差，取决于 grid_type
    fall_buy_percent: float = 1.0

    # 高级触发条件
    enable_pullback_sell: bool = False
    pullback_sell_percent: float = 0.5
    enable_rebound_buy: bool = False
    rebound_buy_percent: float = 0.5

    # ========== 订单设置 ==========
    order_type: Literal['limit', 'market'] = 'limit'

    # 限价单价格设置
    buy_price_mode: str = 'bid1'  # bid1-5, ask1-5, trigger
    sell_price_mode: str = 'ask1'
    buy_price_offset: Optional[float] = None
    sell_price_offset: Optional[float] = None

    # ========== 数量设置 ==========
    amount_mode: Literal['percent', 'amount'] = 'percent'
    grid_symmetric: bool = True

    # 对称网格
    order_quantity: Optional[float] = None

    # 不对称网格
    buy_quantity: Optional[float] = None
    sell_quantity: Optional[float] = None

    # ========== 仓位控制 ==========
    max_position: float = 100  # 百分比
    min_position: Optional[float] = None

    # ========== 波动率自适应 ==========
    enable_volatility_adjustment: bool = False
    base_grid: float = 2.5
    center_volatility: float = 0.25
    sensitivity_k: float = 10.0

    enable_dynamic_interval: bool = False
    default_interval_hours: float = 1.0

    enable_volume_weighting: bool = True

    # ========== 生命周期 ==========
    expiry_days: int = -1  # -1 = 永久

    # ========== 高级功能 ==========
    enable_monitor_period: bool = False
    trading_hours: Optional[List[tuple]] = None
    trading_days: Optional[List[int]] = None

    enable_deviation_control: bool = False
    enable_price_optimization: bool = False
    enable_delay_confirm: bool = False

    enable_floor_price: bool = False
    floor_price: Optional[float] = None

    enable_auto_close: bool = False
    auto_close_conditions: Optional[Dict] = None

    # ========== 验证器 ==========
    @validator('trigger_base_price')
    def validate_trigger_price(cls, v, values):
        if values.get('trigger_base_price_type') == 'manual' and v is None:
            raise ValueError("手动模式必须设置触发基准价")
        return v

    @validator('buy_quantity', 'sell_quantity')
    def validate_asymmetric_quantities(cls, v, values):
        if not values.get('grid_symmetric') and v is None:
            raise ValueError("不对称网格必须设置买入和卖出数量")
        return v

    @validator('price_max')
    def validate_price_range(cls, v, values):
        price_min = values.get('price_min')
        if price_min and v and v <= price_min:
            raise ValueError("price_max 必须大于 price_min")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_name": "BNB保守型网格",
                "symbol": "BNB/USDT",
                "grid_type": "percent",
                "trigger_base_price_type": "current",
                "rise_sell_percent": 1.0,
                "fall_buy_percent": 1.0,
                "order_type": "limit",
                "amount_mode": "percent",
                "grid_symmetric": True,
                "order_quantity": 10.0,
                "max_position": 80,
                "min_position": 20
            }
        }
```

### 配置存储方案

**选项1: 数据库表** (推荐)
```sql
CREATE TABLE grid_strategies (
    id INTEGER PRIMARY KEY,
    strategy_name VARCHAR(255) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    config_json TEXT NOT NULL,  -- 存储完整的 GridStrategyConfig JSON
    status VARCHAR(20) DEFAULT 'draft',  -- draft/active/stopped
    created_by INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

**选项2: JSON文件**
```
config/strategies/
  ├── BNB-USDT-conservative.json
  ├── ETH-USDT-aggressive.json
  └── ...
```

---

## 🧪 测试策略

### 单元测试覆盖

```python
# tests/unit/test_grid_strategy_config.py

def test_grid_type_percent_calculation():
    """测试百分比模式的触发价计算"""
    config = GridStrategyConfig(
        symbol="BNB/USDT",
        grid_type="percent",
        trigger_base_price_type="manual",
        trigger_base_price=600.0,
        rise_sell_percent=1.0,
        fall_buy_percent=1.0
    )

    sell_trigger = 600 * 1.01  # 606
    buy_trigger = 600 * 0.99   # 594

    assert sell_trigger == 606
    assert buy_trigger == 594

def test_grid_type_price_calculation():
    """测试价差模式的触发价计算"""
    config = GridStrategyConfig(
        symbol="BNB/USDT",
        grid_type="price",
        trigger_base_price_type="manual",
        trigger_base_price=600.0,
        rise_sell_percent=10.0,  # 价差10 USDT
        fall_buy_percent=10.0
    )

    sell_trigger = 600 + 10  # 610
    buy_trigger = 600 - 10   # 590

    assert sell_trigger == 610
    assert buy_trigger == 590

def test_asymmetric_grid_quantities():
    """测试不对称网格数量配置"""
    config = GridStrategyConfig(
        symbol="BNB/USDT",
        grid_symmetric=False,
        buy_quantity=100.0,  # 买入100 USDT
        sell_quantity=150.0   # 卖出150 USDT
    )

    assert config.buy_quantity == 100.0
    assert config.sell_quantity == 150.0

# 更多测试用例...
```

### 集成测试

```python
# tests/integration/test_grid_strategy_workflow.py

async def test_complete_grid_trading_workflow():
    """测试完整的网格交易流程"""
    # 1. 创建配置
    config = GridStrategyConfig(...)

    # 2. 初始化交易器
    trader = GridTrader(exchange, config, symbol)
    await trader.initialize()

    # 3. 模拟价格变动，触发交易
    await simulate_price_movement(...)

    # 4. 验证订单创建
    assert len(trader.active_orders) > 0

    # 5. 验证仓位管理
    position = await trader.get_position_ratio()
    assert config.min_position <= position <= config.max_position
```

---

## 📝 API 接口设计

### RESTful API 端点

```python
# src/api/routes/grid_strategy_routes.py

from fastapi import APIRouter, Depends, HTTPException
from src.strategies.grid_strategy_config import GridStrategyConfig
from src.database.models import User

router = APIRouter(prefix="/api/grid-strategies", tags=["grid-strategies"])

@router.post("/", response_model=GridStrategyResponse)
async def create_grid_strategy(
    config: GridStrategyConfig,
    current_user: User = Depends(get_current_user)
):
    """创建新的网格策略配置"""
    # 1. 验证配置
    config.validate()

    # 2. 保存到数据库
    strategy = await save_strategy(config, current_user.id)

    # 3. 返回结果
    return GridStrategyResponse(
        id=strategy.id,
        message="网格策略创建成功",
        config=config
    )

@router.get("/{strategy_id}")
async def get_grid_strategy(strategy_id: int):
    """获取策略配置详情"""
    strategy = await load_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    return strategy

@router.put("/{strategy_id}")
async def update_grid_strategy(
    strategy_id: int,
    config: GridStrategyConfig
):
    """更新策略配置"""
    await update_strategy(strategy_id, config)
    return {"message": "更新成功"}

@router.post("/{strategy_id}/start")
async def start_grid_strategy(strategy_id: int):
    """启动策略"""
    await start_strategy(strategy_id)
    return {"message": "策略已启动"}

@router.post("/{strategy_id}/stop")
async def stop_grid_strategy(strategy_id: int):
    """停止策略"""
    await stop_strategy(strategy_id)
    return {"message": "策略已停止"}
```

---

## 📚 文档和示例

### 配置示例

#### 示例1: 保守型BNB网格

```json
{
  "strategy_name": "BNB保守型网格",
  "symbol": "BNB/USDT",
  "grid_type": "percent",
  "trigger_base_price_type": "current",
  "rise_sell_percent": 1.5,
  "fall_buy_percent": 1.5,
  "order_type": "limit",
  "buy_price_mode": "bid1",
  "sell_price_mode": "ask1",
  "amount_mode": "percent",
  "grid_symmetric": true,
  "order_quantity": 10.0,
  "max_position": 80,
  "min_position": 20,
  "enable_volatility_adjustment": true,
  "base_grid": 2.5,
  "expiry_days": -1
}
```

#### 示例2: 激进型ETH网格（不对称）

```json
{
  "strategy_name": "ETH激进型不对称网格",
  "symbol": "ETH/USDT",
  "grid_type": "price",
  "trigger_base_price_type": "manual",
  "trigger_base_price": 3000.0,
  "price_min": 2800.0,
  "price_max": 3200.0,
  "rise_sell_percent": 50.0,
  "fall_buy_percent": 50.0,
  "enable_pullback_sell": true,
  "pullback_sell_percent": 20.0,
  "order_type": "limit",
  "amount_mode": "amount",
  "grid_symmetric": false,
  "buy_quantity": 100.0,
  "sell_quantity": 150.0,
  "max_position": 95,
  "min_position": 5,
  "expiry_days": 30
}
```

---

## 🚀 快速开始

### 1. 前端提交配置

```typescript
// web/src/pages/Template/GridConfig.tsx
const handleSave = async () => {
  const values = await form.validateFields();

  const config = {
    strategy_name: `${values.base_currency}${values.quote_currency}网格策略`,
    symbol: `${values.base_currency}/${values.quote_currency}`,
    grid_type: values.grid_type,
    trigger_base_price_type: values.trigger_base_price_type,
    trigger_base_price: values.trigger_base_price,
    price_min: values.price_min,
    price_max: values.price_max,
    rise_sell_percent: values.rise_sell_percent,
    fall_buy_percent: values.fall_buy_percent,
    // ... 所有其他字段
  };

  await api.post('/api/grid-strategies', config);
};
```

### 2. 后端接收和验证

```python
# src/api/routes/grid_strategy_routes.py
@router.post("/")
async def create_grid_strategy(config: GridStrategyConfig):
    # Pydantic 自动验证
    strategy_id = await db.save_grid_strategy(config)
    return {"id": strategy_id, "message": "创建成功"}
```

### 3. 启动策略

```python
# src/core/trader.py
async def start_with_config(config: GridStrategyConfig):
    trader = GridTrader(exchange, config, config.symbol)
    await trader.initialize()
    await trader.main_loop()
```

---

## 📞 联系和反馈

如有问题或建议，请：
- 提交 Issue: https://github.com/your-repo/issues
- 查看文档: docs/GRID_STRATEGY_GUIDE.md
- 技术讨论: #grid-strategy 频道

---

## 📌 附录

### A. 术语表

| 术语 | 英文 | 说明 |
|-----|------|------|
| 网格策略 | Grid Strategy | 在价格区间内按固定间隔买卖的交易策略 |
| 触发基准价 | Trigger Base Price | 计算买卖触发价的基准价格 |
| 回落卖出 | Pullback Sell | 价格上涨后回落时卖出 |
| 拐点买入 | Rebound Buy | 价格下跌后反弹时买入 |
| 对称网格 | Symmetric Grid | 买入和卖出使用相同的数量 |
| 盘口价格 | Order Book Price | 交易所买卖盘中的价格档位 |

### B. 参考资料

- [Grid Trading Strategy Guide](https://www.binance.com/en/support/faq/grid-trading)
- [Ccxt Order Book Documentation](https://docs.ccxt.com/#/README?id=order-book-structure)
- [Pydantic Validation](https://docs.pydantic.dev/latest/concepts/validators/)

---

**最后更新**: 2025-11-06
**维护者**: AI Assistant
**版本**: v1.0
