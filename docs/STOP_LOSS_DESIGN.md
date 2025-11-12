# 止损机制设计文档

> **创建日期**: 2025-10-24
> **版本**: v1.0.0
> **优先级**: 🔴 P0 (阶段1关键功能)

---

## 📋 目录

1. [背景与动机](#背景与动机)
2. [功能需求](#功能需求)
3. [技术设计](#技术设计)
4. [实现细节](#实现细节)
5. [配置说明](#配置说明)
6. [测试计划](#测试计划)

---

## 背景与动机

### 当前问题

网格交易策略在震荡市表现优秀，但在**单边急跌市**存在重大风险：

- ❌ **无止损保护**：价格持续下跌，账户持续加仓买入
- ❌ **浮亏扩大**：网格基准价不调整，亏损越来越大
- ❌ **资金占用**：大量资金被套，无法灵活应对

### 真实场景

**场景1：急跌市**
```
初始: 基准价 600 USDT, 持仓 10 BNB, 总资产 6000 USDT
Day 1: 价格跌至 540 (-10%) → 加仓买入
Day 2: 价格跌至 480 (-20%) → 继续加仓
Day 3: 价格跌至 420 (-30%) → 资金耗尽，浮亏 -40%
```

**改进后：启用止损**
```
初始: 基准价 600 USDT, 设置止损 -15%
Day 1: 价格跌至 510 (-15%) → 触发止损，平仓止损
结果: 及时止损，最大亏损控制在 -15%，保留 85% 资金
```

---

## 功能需求

### 核心功能

#### 1. 价格止损（Price Stop Loss）

**定义**：当前价格相对基准价下跌超过阈值时触发

**计算公式**：
```python
stop_loss_price = base_price * (1 - STOP_LOSS_PERCENTAGE / 100)
触发条件: current_price <= stop_loss_price
```

**示例**：
- 基准价：600 USDT
- 止损比例：15%
- 止损价：510 USDT
- 当价格 ≤ 510 时触发

---

#### 2. 回撤止损（Drawdown Stop Loss）

**定义**：从最高盈利回撤超过阈值时触发止盈

**计算公式**：
```python
max_profit = max(current_profit)  # 历史最高盈利
drawdown = (max_profit - current_profit) / max_profit
触发条件: drawdown >= TAKE_PROFIT_DRAWDOWN / 100
```

**示例**：
- 最高盈利：+200 USDT
- 回撤止盈：20%
- 当前盈利：+160 USDT
- 回撤比例：(200-160)/200 = 20%
- 触发止盈，锁定利润

---

#### 3. 紧急平仓（Emergency Liquidation）

**定义**：快速清空所有持仓，转为稳定币

**执行步骤**：
1. 取消所有挂单
2. 市价单卖出基础资产（如 BNB）
3. 转移计价货币到理财（如果启用）
4. 记录止损事件
5. 发送告警通知

**安全措施**：
- ✅ 使用市价单，确保快速成交
- ✅ 多次重试机制（最多5次）
- ✅ 失败时发送紧急通知
- ✅ 记录完整日志用于复盘

---

## 技术设计

### 类结构

```python
class StopLossManager:
    """止损管理器"""

    def __init__(self, trader: GridTrader):
        self.trader = trader
        self.max_profit = 0.0  # 历史最高盈利
        self.stop_loss_triggered = False

    async def check_stop_loss(self) -> tuple[bool, str]:
        """检查是否需要触发止损

        Returns:
            (是否触发, 触发原因)
        """

    async def emergency_liquidate(self, reason: str):
        """紧急平仓"""
```

### 状态机

```
正常运行 (NORMAL)
    ↓ (价格跌破止损线)
触发止损 (STOP_LOSS_TRIGGERED)
    ↓ (开始平仓)
平仓中 (LIQUIDATING)
    ↓ (平仓完成)
已止损 (STOPPED)
```

### 数据流

```
main_loop()
    → check_stop_loss()
        → 价格止损检查
        → 回撤止损检查
    → emergency_liquidate() (如果触发)
        → cancel_all_orders()
        → market_sell_all()
        → transfer_to_savings()
        → send_alert()
```

---

## 实现细节

### 1. 添加到 trader.py

#### 1.1 初始化

```python
class GridTrader:
    def __init__(self, ...):
        # ... 现有代码 ...

        # 🆕 止损相关状态
        self.max_profit = 0.0  # 历史最高盈利
        self.stop_loss_triggered = False  # 止损是否已触发
        self.stop_loss_price = None  # 止损价格
```

#### 1.2 核心方法

```python
async def _check_stop_loss(self) -> tuple[bool, str]:
    """检查止损条件

    Returns:
        (是否触发, 触发原因)
    """
    if not settings.ENABLE_STOP_LOSS:
        return False, ""

    if self.stop_loss_triggered:
        return False, "已触发过止损"

    current_price = self.current_price

    # 1. 价格止损检查
    if settings.STOP_LOSS_PERCENTAGE > 0:
        stop_loss_price = self.base_price * (1 - settings.STOP_LOSS_PERCENTAGE / 100)

        if current_price <= stop_loss_price:
            return True, f"价格止损: {current_price:.2f} <= {stop_loss_price:.2f} (-{settings.STOP_LOSS_PERCENTAGE}%)"

    # 2. 回撤止损检查
    if settings.TAKE_PROFIT_DRAWDOWN > 0:
        current_profit = await self._calculate_current_profit()

        # 更新最高盈利
        if current_profit > self.max_profit:
            self.max_profit = current_profit

        # 计算回撤
        if self.max_profit > 0:
            drawdown = (self.max_profit - current_profit) / self.max_profit

            if drawdown >= settings.TAKE_PROFIT_DRAWDOWN / 100:
                return True, f"回撤止盈: 从最高盈利 {self.max_profit:.2f} 回撤 {drawdown*100:.1f}%"

    return False, ""

async def _emergency_liquidate(self, reason: str):
    """紧急平仓"""
    self.logger.critical(f"🚨 触发止损: {reason}")
    self.stop_loss_triggered = True

    try:
        # 1. 取消所有挂单
        open_orders = await self.exchange.fetch_open_orders(self.symbol)
        for order in open_orders:
            try:
                await self.exchange.cancel_order(order['id'], self.symbol)
                self.logger.info(f"已取消订单: {order['id']}")
            except Exception as e:
                self.logger.error(f"取消订单失败: {e}")

        # 2. 市价单卖出所有基础资产
        balance = await self.exchange.fetch_balance({'type': 'spot'})
        base_balance = float(balance['free'].get(self.base_asset, 0))

        if base_balance > 0:
            # 调整精度
            base_balance = self._adjust_amount_precision(base_balance)

            self.logger.info(f"市价卖出 {base_balance} {self.base_asset}")

            order = await self.exchange.create_order(
                self.symbol,
                'market',
                'sell',
                base_balance
            )

            self.logger.info(f"止损卖单已成交: {order}")

        # 3. 转移资金到理财（如果启用）
        if settings.ENABLE_SAVINGS_FUNCTION:
            await asyncio.sleep(2)  # 等待订单结算
            await self._transfer_excess_funds()

        # 4. 发送告警通知
        alert_msg = f"""
🚨 止损告警 🚨
━━━━━━━━━━━━━━━━━━━━
交易对: {self.symbol}
触发原因: {reason}
当前价格: {self.current_price:.2f} {self.quote_asset}
基准价格: {self.base_price:.2f} {self.quote_asset}
已卖出: {base_balance:.4f} {self.base_asset}
━━━━━━━━━━━━━━━━━━━━
系统已停止该交易对的交易
"""
        send_pushplus_message(alert_msg, "🚨 止损告警")

        # 5. 记录止损事件
        self._save_state()

        self.logger.critical(f"止损完成，交易已停止")

    except Exception as e:
        self.logger.error(f"紧急平仓失败: {e}", exc_info=True)
        send_pushplus_message(
            f"紧急平仓失败: {e}\n请立即人工介入！",
            "🆘 紧急告警"
        )
        raise

async def _calculate_current_profit(self) -> float:
    """计算当前盈利（USDT）"""
    try:
        total_assets = await self._get_pair_specific_assets_value()
        initial_principal = settings.INITIAL_PRINCIPAL or 0

        if initial_principal > 0:
            profit = total_assets - initial_principal
        else:
            # 如果没设置初始本金，使用交易历史计算
            profit = sum(t.get('profit', 0) for t in self.order_tracker.trade_history)

        return profit
    except Exception as e:
        self.logger.error(f"计算盈利失败: {e}")
        return 0.0
```

#### 1.3 集成到 main_loop

```python
async def main_loop(self):
    while True:
        try:
            # ... 现有的初始化和价格获取 ...

            # 🆕 止损检查（在所有交易逻辑之前）
            if settings.ENABLE_STOP_LOSS:
                should_stop, reason = await self._check_stop_loss()

                if should_stop:
                    await self._emergency_liquidate(reason)
                    # 止损后停止该交易对的运行
                    break

            # ... 现有的交易逻辑 ...

        except Exception as e:
            # ... 现有的错误处理 ...
```

---

## 配置说明

### 环境变量（.env）

```bash
# ========== 止损配置 (Stop Loss Settings) ==========
# 是否启用止损机制 (true/false)
ENABLE_STOP_LOSS=true

# 价格止损比例 (%)
# 当价格相对基准价下跌超过此比例时触发止损
# 例如: 15.0 表示下跌15%止损
# 设为 0 则禁用价格止损
STOP_LOSS_PERCENTAGE=15.0

# 回撤止盈比例 (%)
# 当盈利从最高点回撤超过此比例时触发止盈
# 例如: 20.0 表示从最高盈利回撤20%就止盈
# 设为 0 则禁用回撤止盈
TAKE_PROFIT_DRAWDOWN=20.0
```

### Settings.py 配置

```python
class Settings(BaseSettings):
    # ... 现有配置 ...

    # 止损配置
    ENABLE_STOP_LOSS: bool = False  # 默认禁用，需要用户主动启用
    STOP_LOSS_PERCENTAGE: float = 15.0  # 价格止损比例
    TAKE_PROFIT_DRAWDOWN: float = 20.0  # 回撤止盈比例

    @field_validator('STOP_LOSS_PERCENTAGE')
    @classmethod
    def validate_stop_loss_percentage(cls, v):
        if v < 0 or v > 50:
            raise ValueError(f"STOP_LOSS_PERCENTAGE 必须在 0-50 之间，当前: {v}")
        if v > 0 and v < 5:
            logging.warning(f"STOP_LOSS_PERCENTAGE 设置过小 ({v}%)，可能频繁触发")
        return v

    @field_validator('TAKE_PROFIT_DRAWDOWN')
    @classmethod
    def validate_take_profit_drawdown(cls, v):
        if v < 0 or v > 100:
            raise ValueError(f"TAKE_PROFIT_DRAWDOWN 必须在 0-100 之间，当前: {v}")
        return v
```

---

## 测试计划

### 单元测试

```python
# tests/unit/test_stop_loss.py

class TestStopLoss:
    """止损机制单元测试"""

    def test_price_stop_loss_triggered(self):
        """测试价格止损触发"""

    def test_price_stop_loss_not_triggered(self):
        """测试价格止损不触发"""

    def test_drawdown_stop_triggered(self):
        """测试回撤止盈触发"""

    def test_drawdown_stop_not_triggered(self):
        """测试回撤止盈不触发"""

    def test_emergency_liquidate_success(self):
        """测试紧急平仓成功"""

    def test_emergency_liquidate_retry(self):
        """测试紧急平仓重试机制"""
```

### 集成测试场景

#### 场景1：急跌市止损

```python
# 模拟急跌市
初始状态:
- 基准价: 600 USDT
- 止损比例: 15%
- 止损价: 510 USDT

价格变化:
600 → 580 → 550 → 520 → 505 (触发止损)

预期结果:
✅ 在 505 USDT 触发止损
✅ 市价单卖出所有 BNB
✅ 发送止损通知
✅ 停止该交易对运行
```

#### 场景2：回撤止盈

```python
初始状态:
- 盈利: 0 USDT
- 回撤止盈: 20%

盈利变化:
0 → +50 → +100 → +150 → +120 (回撤 20%)

预期结果:
✅ 在 +120 USDT 触发止盈
✅ 锁定利润，平仓退出
```

---

## 风险与注意事项

### ⚠️ 风险

1. **市价单滑点**：极端行情下，市价单可能有较大滑点
2. **网络延迟**：止损信号到平仓完成有时间差
3. **误触发**：止损比例设置过小，可能频繁触发

### ✅ 缓解措施

1. **合理设置止损比例**：建议 10-20%
2. **测试环境验证**：先在测试环境充分测试
3. **监控告警**：止损触发时立即通知
4. **手动介入**：保留手动介入机制

---

## 实施检查清单

- [ ] 添加 `_check_stop_loss()` 方法
- [ ] 添加 `_emergency_liquidate()` 方法
- [ ] 添加 `_calculate_current_profit()` 方法
- [ ] 集成到 `main_loop()`
- [ ] 添加配置项到 `.env.example`
- [ ] 添加配置项到 `settings.py`
- [ ] 添加配置验证器
- [ ] 编写单元测试（至少6个）
- [ ] 更新 ROADMAP.md
- [ ] 更新 CLAUDE.md
- [ ] 在测试环境验证
- [ ] 文档完善

---

**文档版本**: v1.0.0
**最后更新**: 2025-10-24
**作者**: GridBNB-USDT Team
