# 策略改进路线图 (Strategy Improvements Roadmap)

> **文档版本**: v1.0.0
> **生成日期**: 2025-10-24
> **当前策略评分**: 8.2/10 ⭐⭐⭐⭐
> **目标评分**: 9.5/10 ⭐⭐⭐⭐⭐

---

## 📊 当前策略评估总结

### ✅ 核心优势

| 维度 | 评分 | 说明 |
|-----|------|------|
| **技术领先性** | 9/10 | EWMA+传统混合波动率、AI+网格双轨制、成交量加权 |
| **代码质量** | 9/10 | 100%类型注解、企业级架构、完善测试覆盖 |
| **风险意识** | 7/10 | 有仓位控制和AI过滤，但缺全局风控和止损 |
| **适应性** | 8/10 | 动态调整能力强，但单边市场应对不足 |

### ⚠️ 关键风险点

#### 🔴 高风险（需立即处理）

1. **多交易对无全局资金限制**
   - **问题**: 每个交易对独立使用90%仓位，可能导致资金冲突
   - **影响**: 交易失败、资金利用率低
   - **文件**: `src/strategies/risk_manager.py`

2. **缺少止损机制**
   - **问题**: 极端下跌时无保护措施，持续买入接刀子
   - **影响**: 可能导致重大亏损
   - **文件**: `src/core/trader.py`

3. **单边市场适应性差**
   - **问题**: 牛市中不断卖出，踏空主升浪
   - **影响**: 错失趋势收益
   - **文件**: `src/core/trader.py`

#### 🟡 中等风险（建议优化）

4. **AI与风控存在冲突**
   - **问题**: AI全局判断可能被局部风控规则否决
   - **影响**: 降低AI策略有效性
   - **文件**: `src/core/trader.py:728-739`

5. **波动率计算跳变**
   - **问题**: 网格大小可能突然跳变50%
   - **影响**: 交易策略不稳定
   - **文件**: `src/core/trader.py:1309-1357`

6. **理财与交易冲突**
   - **问题**: 赎回理财有延迟，可能错过最佳价格
   - **影响**: 交易执行效率降低
   - **文件**: `src/core/trader.py:802-839`

#### 🟢 低风险（可选优化）

7. **基准价从不调整**
   - **问题**: 市场中枢偏移后效率降低
   - **影响**: 网格运行效率下降
   - **配置**: `AUTO_ADJUST_BASE_PRICE: bool = False`

8. **缺少AI学习反馈**
   - **问题**: 无法评估AI建议的准确性
   - **影响**: 错失自我优化机会
   - **文件**: `src/strategies/ai_strategy.py`

---

## 🎯 实施路线图

### 阶段1: 风险修复 (P0优先级) ⏱️ 1-2周

#### 1.1 全局资金分配器 🔴

**目标**: 协调多交易对的资金使用，避免冲突

**新增文件**: `src/strategies/global_allocator.py`

**核心功能**:
```python
class GlobalFundAllocator:
    """全局资金分配器"""

    def __init__(self, symbols: List[str], total_capital: float):
        self.symbols = symbols
        self.total_capital = total_capital
        # 为每个交易对分配独立资金池
        self.allocation = {
            symbol: total_capital / len(symbols)
            for symbol in symbols
        }
        # 全局风控: 总仓位不超过95%
        self.max_global_usage = 0.95

    async def check_trade_allowed(
        self,
        symbol: str,
        amount: float
    ) -> bool:
        """检查交易是否会超出全局限制"""
        current_global_usage = await self._get_global_usage()

        if current_global_usage + (amount / self.total_capital) > self.max_global_usage:
            return False
        return True

    async def _get_global_usage(self) -> float:
        """计算全局资金使用率"""
        used_capital = 0
        for symbol, trader in self.traders.items():
            position_value = await trader._get_position_value()
            used_capital += position_value
        return used_capital / self.total_capital
```

**集成位置**: `src/main.py`
```python
# 在main()函数中创建全局分配器
allocator = GlobalFundAllocator(
    symbols=SYMBOLS_LIST,
    total_capital=settings.INITIAL_PRINCIPAL
)

# 每个trader初始化时传入
trader = GridTrader(
    symbol=symbol,
    exchange=exchange,
    global_allocator=allocator  # 新增参数
)
```

**配置项** (.env):
```bash
# 全局资金分配策略
GLOBAL_MAX_USAGE=0.95        # 全局最大资金使用率
ALLOCATION_STRATEGY=equal    # equal/weighted/dynamic
```

**预期效果**:
- ✅ 多交易对不会争抢资金
- ✅ 总仓位受控
- ✅ 资金利用率提升

---

#### 1.2 止损机制 🔴

**目标**: 保护本金，防范极端风险

**修改文件**: `src/core/trader.py`

**新增方法**:
```python
async def _check_stop_loss(self) -> bool:
    """
    检查是否触发止损

    止损策略:
    1. 价格止损: 跌破基准价20%
    2. 回撤止损: 最大回撤超过25%
    3. 连续亏损止损: 连续失败5次
    """
    current_price = self.current_price

    # 止损1: 价格跌破基准价20%
    if current_price < self.base_price * 0.80:
        self.logger.critical(
            f"🛑 触发价格止损 | "
            f"当前价: {current_price} < "
            f"基准价80%: {self.base_price * 0.80}"
        )
        await self._emergency_liquidate("价格止损")
        return True

    # 止损2: 最大回撤超过25%
    total_value = await self._get_pair_specific_assets_value()
    if not hasattr(self, 'peak_value'):
        self.peak_value = total_value
    else:
        self.peak_value = max(self.peak_value, total_value)

    drawdown = (self.peak_value - total_value) / self.peak_value
    if drawdown > 0.25:
        self.logger.critical(
            f"🛑 触发回撤止损 | "
            f"最大回撤: {drawdown:.1%} | "
            f"峰值: {self.peak_value} → 当前: {total_value}"
        )
        await self._emergency_liquidate("回撤止损")
        return True

    # 止损3: 连续亏损5次
    if self.consecutive_failures >= 5:
        self.logger.critical(
            f"🛑 触发连续亏损止损 | "
            f"连续失败: {self.consecutive_failures}次"
        )
        # 冷静期60分钟
        self.cooldown_until = time.time() + 3600
        self.logger.warning("进入冷静期: 60分钟")
        return False  # 不清仓，只暂停

    return False

async def _emergency_liquidate(self, reason: str):
    """紧急清仓"""
    self.logger.critical(f"⚠️ 执行紧急清仓 | 原因: {reason}")

    try:
        # 1. 取消所有挂单
        open_orders = await self.exchange.fetch_open_orders(self.symbol)
        for order in open_orders:
            await self.exchange.cancel_order(order['id'], self.symbol)

        # 2. 卖出所有持仓
        balance = await self.exchange.fetch_balance()
        base_amount = float(balance['free'].get(self.base_asset, 0))

        if base_amount > 0:
            await self.exchange.create_market_order(
                self.symbol,
                'sell',
                base_amount
            )
            self.logger.info(f"已卖出全部持仓: {base_amount} {self.base_asset}")

        # 3. 发送通知
        send_pushplus_message(
            f"🚨 紧急清仓执行\n"
            f"交易对: {self.symbol}\n"
            f"原因: {reason}\n"
            f"清仓数量: {base_amount} {self.base_asset}\n"
            f"当前价格: {self.current_price}",
            "紧急止损通知"
        )

        # 4. 标记状态
        self.emergency_stopped = True

    except Exception as e:
        self.logger.error(f"紧急清仓失败: {e}", exc_info=True)
```

**集成到主循环** (src/core/trader.py:631-756):
```python
async def main_loop(self):
    while True:
        try:
            # ... 初始化代码 ...

            # 🆕 在所有交易逻辑前检查止损
            if await self._check_stop_loss():
                self.logger.critical("止损触发，退出交易循环")
                break

            # 🆕 检查冷静期
            if hasattr(self, 'cooldown_until') and time.time() < self.cooldown_until:
                remaining = (self.cooldown_until - time.time()) / 60
                self.logger.debug(f"冷静期中，剩余 {remaining:.1f} 分钟")
                await asyncio.sleep(60)
                continue

            # ... 原有交易逻辑 ...
```

**配置项** (.env):
```bash
# 止损配置
ENABLE_STOP_LOSS=true               # 是否启用止损
PRICE_STOP_LOSS_PCT=0.20            # 价格止损阈值 (20%)
DRAWDOWN_STOP_LOSS_PCT=0.25         # 回撤止损阈值 (25%)
CONSECUTIVE_LOSS_LIMIT=5            # 连续亏损次数限制
COOLDOWN_MINUTES=60                 # 冷静期时长(分钟)
```

**预期效果**:
- ✅ 极端下跌时自动保护
- ✅ 最大回撤可控
- ✅ 避免情绪化交易

---

#### 1.3 趋势识别模块 🔴

**目标**: 识别单边市场，避免踏空或接刀子

**新增文件**: `src/strategies/trend_detector.py`

**核心算法**:
```python
from typing import List, Literal
import numpy as np
from dataclasses import dataclass

@dataclass
class TrendSignal:
    """趋势信号"""
    trend: Literal['strong_up', 'strong_down', 'ranging']
    confidence: float  # 0-1
    reason: str

class TrendDetector:
    """趋势检测器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def detect_trend(
        self,
        prices: List[float],
        volumes: List[float] = None
    ) -> TrendSignal:
        """
        综合检测市场趋势

        方法:
        1. 均线系统 (EMA20/EMA50)
        2. 价格动量 (连续5根K线方向)
        3. 价格位置 (30日高低点分位)
        4. 成交量确认 (可选)
        """
        if len(prices) < 50:
            return TrendSignal('ranging', 0.5, '数据不足')

        # 方法1: 均线系统
        ema_20 = np.mean(prices[-20:])
        ema_50 = np.mean(prices[-50:])
        ema_deviation = (ema_20 - ema_50) / ema_50

        # 方法2: 价格动量
        recent_5 = prices[-5:]
        is_consecutive_up = all(
            recent_5[i] > recent_5[i-1]
            for i in range(1, 5)
        )
        is_consecutive_down = all(
            recent_5[i] < recent_5[i-1]
            for i in range(1, 5)
        )

        # 方法3: 价格位置
        recent_30 = prices[-30:]
        recent_high = max(recent_30)
        recent_low = min(recent_30)
        current = prices[-1]

        if recent_high == recent_low:
            position = 0.5
        else:
            position = (current - recent_low) / (recent_high - recent_low)

        # 方法4: 成交量确认 (可选)
        volume_confirmed = True
        if volumes and len(volumes) >= 20:
            avg_volume = np.mean(volumes[-20:])
            recent_volume = np.mean(volumes[-5:])
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            volume_confirmed = volume_ratio > 1.2  # 放量

        # 综合判断
        reasons = []
        confidence = 0.0

        # 强势上涨判断
        if (ema_deviation > 0.05 and          # EMA20高出5%
            is_consecutive_up and              # 连续上涨
            position > 0.75 and                # 处于高位
            volume_confirmed):                 # 放量确认

            confidence = min(0.9, 0.6 + abs(ema_deviation) * 2)
            reasons.append(f"EMA20高出EMA50 {ema_deviation:.1%}")
            reasons.append(f"连续5日上涨")
            reasons.append(f"价格位于30日高位({position:.1%})")
            if volumes:
                reasons.append("放量上涨")

            return TrendSignal(
                'strong_up',
                confidence,
                ' | '.join(reasons)
            )

        # 强势下跌判断
        elif (ema_deviation < -0.05 and       # EMA20低于5%
              is_consecutive_down and          # 连续下跌
              position < 0.25 and              # 处于低位
              volume_confirmed):               # 放量确认

            confidence = min(0.9, 0.6 + abs(ema_deviation) * 2)
            reasons.append(f"EMA20低于EMA50 {ema_deviation:.1%}")
            reasons.append(f"连续5日下跌")
            reasons.append(f"价格位于30日低位({position:.1%})")
            if volumes:
                reasons.append("放量下跌")

            return TrendSignal(
                'strong_down',
                confidence,
                ' | '.join(reasons)
            )

        # 震荡市
        else:
            confidence = 1.0 - abs(ema_deviation) * 5  # 偏离越小，震荡越确定
            confidence = max(0.5, min(0.95, confidence))
            reasons.append(f"EMA偏离度小({ema_deviation:.1%})")
            reasons.append(f"无明显趋势特征")

            return TrendSignal(
                'ranging',
                confidence,
                ' | '.join(reasons)
            )
```

**集成到GridTrader** (src/core/trader.py):
```python
from src.strategies.trend_detector import TrendDetector, TrendSignal

class GridTrader:
    def __init__(self, ...):
        # ... 现有初始化 ...
        self.trend_detector = TrendDetector()
        self.current_trend: TrendSignal = None

    async def main_loop(self):
        while True:
            try:
                # ... 价格更新 ...

                # 🆕 每分钟检测一次趋势
                if not hasattr(self, 'last_trend_check') or \
                   time.time() - self.last_trend_check > 60:

                    recent_klines = await self.exchange.fetch_ohlcv(
                        self.symbol,
                        timeframe='1h',
                        limit=100
                    )
                    prices = [k[4] for k in recent_klines]
                    volumes = [k[5] for k in recent_klines]

                    self.current_trend = await self.trend_detector.detect_trend(
                        prices, volumes
                    )

                    self.last_trend_check = time.time()

                    if self.current_trend.confidence > 0.7:
                        self.logger.info(
                            f"📈 趋势检测 | "
                            f"类型: {self.current_trend.trend} | "
                            f"置信度: {self.current_trend.confidence:.1%} | "
                            f"原因: {self.current_trend.reason}"
                        )

                # 🆕 根据趋势调整交易策略
                risk_state = await self.risk_manager.check_position_limits(
                    spot_balance,
                    funding_balance
                )

                # 趋势覆盖风控
                if self.current_trend and self.current_trend.confidence > 0.7:
                    if self.current_trend.trend == 'strong_up':
                        # 强势上涨: 只买入，暂停卖出
                        if risk_state == RiskState.ALLOW_ALL:
                            risk_state = RiskState.ALLOW_BUY_ONLY
                            self.logger.info("💡 强势上涨，暂停网格卖出")

                    elif self.current_trend.trend == 'strong_down':
                        # 强势下跌: 只卖出，暂停买入
                        if risk_state == RiskState.ALLOW_ALL:
                            risk_state = RiskState.ALLOW_SELL_ONLY
                            self.logger.info("💡 强势下跌，暂停网格买入")

                # ... 原有交易逻辑，使用调整后的risk_state ...
```

**配置项** (.env):
```bash
# 趋势识别配置
ENABLE_TREND_DETECTION=true          # 是否启用趋势识别
TREND_CONFIDENCE_THRESHOLD=0.70      # 趋势置信度阈值
TREND_CHECK_INTERVAL=60              # 趋势检测间隔(秒)
TREND_OVERRIDE_RISK=true             # 趋势是否覆盖风控
```

**预期效果**:
- ✅ 单边上涨时持仓不卖
- ✅ 单边下跌时及时止损
- ✅ 震荡市正常网格
- ✅ 提升整体收益

---

### 阶段2: 性能优化 (P1优先级) ⏱️ 2-3周

#### 2.1 波动率计算平滑 🟡

**目标**: 减少噪音，避免网格大小跳变

**修改文件**: `src/core/trader.py:1309-1357`

**改进方案**:
```python
async def _calculate_volatility(self):
    """
    计算混合波动率并平滑处理

    改进:
    1. 使用5期移动平均平滑
    2. 异常值检测与过滤
    3. 失败时使用缓存值而非固定值
    """
    try:
        # ... 现有计算逻辑 ...
        hybrid_volatility = ...

        # 🆕 异常值检测
        if hybrid_volatility > 1.0:  # 100%以上可能异常
            self.logger.warning(
                f"检测到异常波动率: {hybrid_volatility:.2%}，使用缓存值"
            )
            if hasattr(self, 'last_valid_volatility'):
                return self.last_valid_volatility
            else:
                return 0.20  # 默认值

        # 🆕 保存到历史
        if not hasattr(self, 'volatility_history'):
            self.volatility_history = []

        self.volatility_history.append(hybrid_volatility)
        if len(self.volatility_history) > 10:
            self.volatility_history.pop(0)

        # 🆕 5期移动平均平滑
        if len(self.volatility_history) >= 5:
            smoothed_volatility = np.mean(self.volatility_history[-5:])
        else:
            smoothed_volatility = hybrid_volatility

        # 保存有效值
        self.last_valid_volatility = smoothed_volatility

        self.logger.debug(
            f"波动率计算 | "
            f"原始: {hybrid_volatility:.4f} | "
            f"平滑后: {smoothed_volatility:.4f} | "
            f"历史数: {len(self.volatility_history)}"
        )

        return smoothed_volatility

    except Exception as e:
        self.logger.error(f"计算波动率失败: {e}")

        # 🆕 改进: 使用缓存值而非固定值
        if hasattr(self, 'last_valid_volatility'):
            self.logger.warning(
                f"使用上次波动率: {self.last_valid_volatility:.4f}"
            )
            return self.last_valid_volatility
        else:
            return 0.20  # 最终降级值
```

**配置项**:
```bash
# 波动率平滑配置
VOLATILITY_SMOOTH_WINDOW=5           # 平滑窗口大小
VOLATILITY_MAX_THRESHOLD=1.0         # 异常值上限(100%)
VOLATILITY_MIN_THRESHOLD=0.01        # 异常值下限(1%)
```

---

#### 2.2 AI优先级提升 🟡

**目标**: 让高置信度AI建议可以覆盖常规风控

**修改文件**: `src/core/trader.py:714-747`

**改进逻辑**:
```python
if self.ai_strategy:
    suggestion = await self.ai_strategy.analyze_and_suggest(trigger_reason)

    if suggestion and suggestion['confidence'] >= settings.AI_CONFIDENCE_THRESHOLD:
        action = suggestion['action']
        confidence = suggestion['confidence']
        amount_pct = suggestion['suggested_amount_pct']

        # 🆕 AI优先级分级
        if confidence >= 85:
            # 高置信度: 覆盖常规风控
            self.logger.warning(
                f"🤖 AI高置信度({confidence}%) - 覆盖常规风控"
            )

            if action == 'buy':
                await self._execute_ai_trade('buy', amount_pct, suggestion)
            elif action == 'sell':
                await self._execute_ai_trade('sell', amount_pct, suggestion)

        elif confidence >= settings.AI_CONFIDENCE_THRESHOLD:
            # 中置信度: 受风控限制
            if action == 'buy':
                if risk_state != RiskState.ALLOW_SELL_ONLY:
                    await self._execute_ai_trade('buy', amount_pct, suggestion)
                else:
                    self.logger.warning(
                        f"🤖 AI建议买入(置信度{confidence}%)，"
                        f"但风控禁止: {risk_state}"
                    )

            elif action == 'sell':
                if risk_state != RiskState.ALLOW_BUY_ONLY:
                    await self._execute_ai_trade('sell', amount_pct, suggestion)
                else:
                    self.logger.warning(
                        f"🤖 AI建议卖出(置信度{confidence}%)，"
                        f"但风控禁止: {risk_state}"
                    )
```

**配置项**:
```bash
# AI优先级配置
AI_HIGH_CONFIDENCE_THRESHOLD=85      # 高置信度阈值
AI_CAN_OVERRIDE_RISK=true            # 是否允许覆盖风控
AI_OVERRIDE_MAX_AMOUNT_PCT=20        # 覆盖时最大金额比例(%)
```

---

#### 2.3 连续网格函数 🟡

**目标**: 使用已有的连续函数替代阶跃函数

**修改文件**: `src/core/trader.py:1266-1307`

**实现**:
```python
async def adjust_grid_size(self):
    """
    动态调整网格大小

    改进: 使用连续函数替代阶跃映射
    """
    try:
        volatility = await self._calculate_volatility()
        if volatility is None:
            return

        self.last_volatility = volatility

        # 🆕 使用连续函数
        params = TradingConfig.GRID_CONTINUOUS_PARAMS

        base_grid = params['base_grid']          # 2.5%
        center_vol = params['center_volatility'] # 0.20 (20%)
        sensitivity = params['sensitivity_k']    # 8.0

        # 连续函数: grid = base + k * (vol - center)
        new_grid = base_grid + sensitivity * (volatility - center_vol)

        # 限制在合理范围
        new_grid = np.clip(
            new_grid,
            TradingConfig.GRID_PARAMS['min'],  # 1.0%
            TradingConfig.GRID_PARAMS['max']   # 4.0%
        )

        # 🆕 只有变化超过0.1%才调整（减少频繁调整）
        if abs(new_grid - self.grid_size) < 0.001:
            self.logger.debug(
                f"网格大小变化小于0.1%，跳过调整 | "
                f"当前: {self.grid_size:.2f}% | 计算: {new_grid:.2f}%"
            )
            return

        old_grid = self.grid_size
        self.grid_size = new_grid
        self.last_grid_adjust_time = time.time()

        self.logger.info(
            f"网格动态调整 | "
            f"{old_grid:.2f}% → {new_grid:.2f}% | "
            f"波动率: {volatility:.2%} | "
            f"算法: 连续函数"
        )

        self._save_state()

    except Exception as e:
        self.logger.error(f"调整网格大小失败: {e}")
```

**配置项** (已存在于settings.py):
```bash
# 连续网格参数 (JSON格式)
GRID_CONTINUOUS_PARAMS_JSON={
  "base_grid": 2.5,           # 中心网格
  "center_volatility": 0.20,  # 中心波动率
  "sensitivity_k": 8.0        # 灵敏度系数
}
```

---

### 阶段3: 增强功能 (P2优先级) ⏱️ 3-4周

#### 3.1 基准价自动调整 🟢

**目标**: 长期运行时自动调整基准价，适应市场中枢变化

**修改文件**: `src/core/trader.py`

**新增方法**:
```python
async def _auto_adjust_base_price(self):
    """
    自动调整基准价

    触发条件:
    1. 每24小时评估一次
    2. 偏离超过30%

    调整策略:
    70%当前价 + 30%旧基准价（平滑调整）
    """
    if not settings.AUTO_ADJUST_BASE_PRICE:
        return

    current_time = time.time()

    # 每24小时检查一次
    if not hasattr(self, 'last_base_adjust_time'):
        self.last_base_adjust_time = current_time
        return

    if current_time - self.last_base_adjust_time < 86400:  # 24小时
        return

    current_price = self.current_price
    deviation = abs(current_price - self.base_price) / self.base_price

    # 偏离超过30%才调整
    if deviation > 0.30:
        old_base = self.base_price

        # 平滑调整: 70%新 + 30%旧
        new_base = 0.7 * current_price + 0.3 * old_base

        self.base_price = new_base
        self.last_base_adjust_time = current_time

        self.logger.warning(
            f"📊 基准价自动调整 | "
            f"旧: {old_base:.2f} → 新: {new_base:.2f} | "
            f"市场价: {current_price:.2f} | "
            f"偏离: {deviation:.1%}"
        )

        # 保存状态
        self._save_state()

        # 发送通知
        send_pushplus_message(
            f"基准价已自动调整\n\n"
            f"交易对: {self.symbol}\n"
            f"旧基准价: {old_base:.2f}\n"
            f"新基准价: {new_base:.2f}\n"
            f"当前市场价: {current_price:.2f}\n"
            f"偏离度: {deviation:.1%}",
            "策略参数调整通知"
        )

    self.last_base_adjust_time = current_time
```

**集成位置** (在main_loop中):
```python
# 在维护模块中添加
if time.time() - self.last_grid_adjust_time > dynamic_interval_seconds:
    await self.adjust_grid_size()
    await self._auto_adjust_base_price()  # 🆕 同时检查基准价
    self.last_grid_adjust_time = time.time()
```

**配置项**:
```bash
# 基准价自动调整
AUTO_ADJUST_BASE_PRICE=true          # 是否启用
BASE_PRICE_ADJUST_INTERVAL=86400     # 检查间隔(秒, 24小时)
BASE_PRICE_DEVIATION_THRESHOLD=0.30  # 偏离阈值(30%)
BASE_PRICE_ADJUST_WEIGHT=0.70        # 新价权重(70%)
```

---

#### 3.2 AI学习反馈系统 🟢

**目标**: 追踪AI建议的准确性，自动优化参数

**新增文件**: `src/strategies/ai_feedback.py`

```python
import time
import logging
from typing import Dict, List, Literal
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass
class AIDecision:
    """AI决策记录"""
    timestamp: float
    suggestion: Dict
    tracked_price: float
    execution_status: Literal['executed', 'rejected', 'failed']
    rejection_reason: str = ""

    # 结果评估 (1小时后)
    result_price: float = None
    result_evaluated: bool = False
    is_correct: bool = None
    profit: float = None

class AIFeedbackTracker:
    """AI反馈追踪器"""

    def __init__(self, trader):
        self.trader = trader
        self.logger = logging.getLogger(self.__class__.__name__)
        self.decisions: List[AIDecision] = []
        self.history_file = Path(f"data/ai_feedback_{trader.symbol.replace('/', '_')}.json")

        # 加载历史记录
        self._load_history()

    def record_suggestion(
        self,
        suggestion: Dict,
        executed: bool,
        rejection_reason: str = ""
    ):
        """记录AI建议"""
        decision = AIDecision(
            timestamp=time.time(),
            suggestion=suggestion.copy(),
            tracked_price=self.trader.current_price,
            execution_status='executed' if executed else 'rejected',
            rejection_reason=rejection_reason
        )

        self.decisions.append(decision)
        self._save_history()

        self.logger.debug(
            f"AI建议已记录 | "
            f"操作: {suggestion['action']} | "
            f"执行: {executed}"
        )

    async def evaluate_past_decisions(self):
        """
        评估历史决策

        规则:
        - 1小时后评估
        - buy建议: 价格上涨>2% = 正确
        - sell建议: 价格下跌>2% = 正确
        - hold建议: 价格波动<3% = 正确
        """
        current_time = time.time()
        current_price = self.trader.current_price

        evaluated_count = 0

        for decision in self.decisions:
            # 跳过已评估或太新的决策
            if decision.result_evaluated or \
               current_time - decision.timestamp < 3600:
                continue

            # 记录结果价格
            decision.result_price = current_price

            # 评估准确性
            action = decision.suggestion['action']
            tracked_price = decision.tracked_price
            price_change = (current_price - tracked_price) / tracked_price

            if action == 'buy':
                # 买入建议: 涨了>2%为正确
                decision.is_correct = price_change > 0.02
                decision.profit = price_change * 100  # 百分比收益

            elif action == 'sell':
                # 卖出建议: 跌了>2%为正确
                decision.is_correct = price_change < -0.02
                decision.profit = -price_change * 100  # 避免损失

            elif action == 'hold':
                # 持仓建议: 波动<3%为正确
                decision.is_correct = abs(price_change) < 0.03
                decision.profit = 0

            decision.result_evaluated = True
            evaluated_count += 1

        if evaluated_count > 0:
            self._save_history()

            # 计算统计数据
            stats = self.get_statistics()

            self.logger.info(
                f"AI决策评估完成 | "
                f"本次评估: {evaluated_count}个 | "
                f"总准确率: {stats['accuracy']:.1%} | "
                f"样本数: {stats['total_evaluated']}"
            )

            # 动态调整置信度阈值
            self._adjust_confidence_threshold(stats)

    def get_statistics(self) -> Dict:
        """获取统计数据"""
        evaluated = [d for d in self.decisions if d.result_evaluated]

        if not evaluated:
            return {
                'total_evaluated': 0,
                'accuracy': 0.0,
                'correct_count': 0,
                'by_action': {}
            }

        correct_count = sum(1 for d in evaluated if d.is_correct)
        accuracy = correct_count / len(evaluated)

        # 按操作类型统计
        by_action = {}
        for action in ['buy', 'sell', 'hold']:
            action_decisions = [d for d in evaluated if d.suggestion['action'] == action]
            if action_decisions:
                action_correct = sum(1 for d in action_decisions if d.is_correct)
                by_action[action] = {
                    'count': len(action_decisions),
                    'correct': action_correct,
                    'accuracy': action_correct / len(action_decisions)
                }

        return {
            'total_evaluated': len(evaluated),
            'accuracy': accuracy,
            'correct_count': correct_count,
            'by_action': by_action
        }

    def _adjust_confidence_threshold(self, stats: Dict):
        """根据准确率动态调整置信度阈值"""
        if stats['total_evaluated'] < 10:
            return  # 样本太少，不调整

        accuracy = stats['accuracy']
        current_threshold = settings.AI_CONFIDENCE_THRESHOLD

        # 准确率>70%: 降低阈值，更信任AI
        if accuracy > 0.70 and current_threshold > 60:
            new_threshold = max(60, current_threshold - 5)
            self.logger.info(
                f"AI准确率高({accuracy:.1%})，降低置信度阈值: "
                f"{current_threshold}% → {new_threshold}%"
            )
            settings.AI_CONFIDENCE_THRESHOLD = new_threshold

        # 准确率<50%: 提高阈值，减少信任
        elif accuracy < 0.50 and current_threshold < 85:
            new_threshold = min(85, current_threshold + 5)
            self.logger.warning(
                f"AI准确率低({accuracy:.1%})，提高置信度阈值: "
                f"{current_threshold}% → {new_threshold}%"
            )
            settings.AI_CONFIDENCE_THRESHOLD = new_threshold

    def _save_history(self):
        """保存历史记录"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            # 只保存最近500条
            recent = self.decisions[-500:]

            data = [asdict(d) for d in recent]

            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(f"保存AI反馈历史失败: {e}")

    def _load_history(self):
        """加载历史记录"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)

                self.decisions = [AIDecision(**d) for d in data]

                self.logger.info(
                    f"已加载AI反馈历史: {len(self.decisions)}条"
                )

        except Exception as e:
            self.logger.error(f"加载AI反馈历史失败: {e}")
            self.decisions = []
```

**集成到trader** (src/core/trader.py):
```python
from src.strategies.ai_feedback import AIFeedbackTracker

class GridTrader:
    def __init__(self, ...):
        # ...
        if self.ai_strategy:
            self.ai_feedback = AIFeedbackTracker(self)

    async def main_loop(self):
        while True:
            # ... AI策略部分 ...

            if self.ai_strategy:
                suggestion = await self.ai_strategy.analyze_and_suggest(trigger_reason)

                if suggestion:
                    executed = False
                    rejection_reason = ""

                    if suggestion['confidence'] >= settings.AI_CONFIDENCE_THRESHOLD:
                        # 尝试执行
                        if action in ['buy', 'sell']:
                            result = await self._execute_ai_trade(...)
                            executed = result
                            if not result:
                                rejection_reason = "执行失败"
                    else:
                        rejection_reason = f"置信度不足({suggestion['confidence']}%)"

                    # 🆕 记录建议
                    self.ai_feedback.record_suggestion(
                        suggestion,
                        executed,
                        rejection_reason
                    )

                # 🆕 每小时评估一次
                if time.time() - getattr(self, 'last_ai_eval', 0) > 3600:
                    await self.ai_feedback.evaluate_past_decisions()
                    self.last_ai_eval = time.time()
```

**配置项**:
```bash
# AI学习反馈配置
ENABLE_AI_FEEDBACK=true              # 是否启用反馈学习
AI_FEEDBACK_EVAL_INTERVAL=3600       # 评估间隔(秒)
AI_AUTO_ADJUST_THRESHOLD=true        # 是否自动调整阈值
AI_MIN_THRESHOLD=60                  # 最低置信度阈值
AI_MAX_THRESHOLD=85                  # 最高置信度阈值
```

**预期效果**:
- ✅ 追踪AI决策结果
- ✅ 自动优化置信度阈值
- ✅ 提供准确率报告
- ✅ 持续改进AI效果

---

## 📈 预期收益提升

| 市场类型 | 当前预期收益 | 改进后预期收益 | 提升幅度 |
|---------|-------------|---------------|---------|
| 震荡市 (±10%) | +8-12% 月化 | +10-15% 月化 | +20% |
| 缓涨市 (+30%/年) | +10-15% 年化 | +25-35% 年化 | +100% |
| 急涨市 (+50%/年) | +5-10% 年化 | +35-45% 年化 | +300% |
| 缓跌市 (-20%/年) | -5~+5% | +5-10% 年化 | 大幅改善 |
| 急跌市 (-40%/年) | -15~-25% | -5~0% | 止损保护 |

**整体年化收益预期**:
- 当前: 15-25% (震荡市为主)
- 改进后: 25-40% (适应多种市场)

---

## 🔄 持续改进机制

### 每周评估指标

1. **交易效率**
   - 网格成交频率
   - 平均持仓时间
   - 资金利用率

2. **风险控制**
   - 最大回撤
   - 胜率 / 盈亏比
   - 止损触发次数

3. **AI表现**
   - 建议准确率
   - 执行成功率
   - 置信度校准

### 月度优化任务

1. **参数调优**
   - 波动率权重
   - 网格大小范围
   - AI触发阈值

2. **策略迭代**
   - 趋势识别算法
   - 止损逻辑
   - 仓位管理

3. **性能提升**
   - 缓存优化
   - 并发改进
   - 日志优化

---

## 📝 实施检查清单

### 阶段1 (P0 - 必须完成)

- [ ] 全局资金分配器
  - [ ] 创建 `src/strategies/global_allocator.py`
  - [ ] 修改 `src/main.py` 集成
  - [ ] 添加配置项到 `.env`
  - [ ] 编写单元测试
  - [ ] 文档更新

- [ ] 止损机制
  - [ ] 添加 `_check_stop_loss()` 方法
  - [ ] 添加 `_emergency_liquidate()` 方法
  - [ ] 集成到 `main_loop()`
  - [ ] 添加配置项
  - [ ] 测试极端场景

- [ ] 趋势识别模块
  - [ ] 创建 `src/strategies/trend_detector.py`
  - [ ] 集成到 `GridTrader`
  - [ ] 添加配置项
  - [ ] 回测验证
  - [ ] 文档说明

### 阶段2 (P1 - 建议完成)

- [ ] 波动率平滑
  - [ ] 修改 `_calculate_volatility()`
  - [ ] 添加异常检测
  - [ ] 测试平滑效果

- [ ] AI优先级提升
  - [ ] 修改AI执行逻辑
  - [ ] 添加分级机制
  - [ ] 验证覆盖效果

- [ ] 连续网格函数
  - [ ] 修改 `adjust_grid_size()`
  - [ ] 使用连续函数
  - [ ] 测试平滑度

### 阶段3 (P2 - 可选完成)

- [ ] 基准价自动调整
  - [ ] 添加 `_auto_adjust_base_price()`
  - [ ] 集成到主循环
  - [ ] 长期测试

- [ ] AI学习反馈
  - [ ] 创建 `src/strategies/ai_feedback.py`
  - [ ] 集成追踪逻辑
  - [ ] 实现自动优化

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. **Fork 本仓库**
2. **创建特性分支**
   ```bash
   git checkout -b feature/stop-loss-mechanism
   ```
3. **实现功能**
   - 遵循现有代码风格
   - 添加类型注解
   - 编写单元测试
4. **提交更改**
   ```bash
   git commit -m "feat: 添加止损机制"
   ```
5. **推送并创建 Pull Request**

### 代码质量要求

- ✅ 通过 Black 格式化
- ✅ 通过 Flake8 检查
- ✅ 100% 类型注解
- ✅ 单元测试覆盖
- ✅ 更新相关文档

---

## 📞 联系方式

- **GitHub Issues**: [提交问题](https://github.com/EBOLABOY/GridBNB-USDT/issues)
- **Telegram 群组**: [加入讨论](https://t.me/+b9fKO9kEOkg2ZjI1)
- **邮箱**: [技术支持](mailto:support@example.com)

---

## 📄 许可证

本文档和相关代码采用 MIT 许可证 - 查看 [LICENSE](../LICENSE) 文件了解详情。

---

**最后更新**: 2025-10-24
**维护者**: GridBNB-USDT 开发团队
**文档版本**: v1.0.0
