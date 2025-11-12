# GridBNB 监控系统使用指南

> **版本**: 2.0.0
> **更新时间**: 2025-10-21
> **状态**: 生产就绪

---

## 📋 目录

1. [快速开始](#快速开始)
2. [监控架构](#监控架构)
3. [Prometheus指标说明](#prometheus指标说明)
4. [Grafana仪表盘](#grafana仪表盘)
5. [告警配置](#告警配置)
6. [故障排查](#故障排查)

---

## 🚀 快速开始

### 方式一: Docker Compose 启动 (推荐)

```bash
# 1. 进入项目目录
cd GridBNB-USDT/docker

# 2. 启动所有服务 (包括Prometheus和Grafana)
docker compose up -d

# 3. 验证服务状态
docker compose ps

# 应该看到以下服务都在运行:
# - gridbnb-bot (交易机器人)
# - prometheus (监控数据收集)
# - grafana (可视化)
# - nginx (反向代理)
```

### 方式二: 单独安装依赖

```bash
# 1. 安装Prometheus客户端
pip install prometheus-client

# 2. 启动应用
python src/main.py

# 3. 访问metrics端点
curl http://localhost:58181/metrics
```

### 访问地址

| 服务 | 地址 | 默认账号 |
|-----|------|---------|
| GridBNB Web界面 | http://localhost:80 | config/.env配置 |
| Prometheus | http://localhost:9090 | 无需认证 |
| Grafana | http://localhost:3000 | admin/admin |
| Metrics API | http://localhost:58181/metrics | 无需认证 |

---

## 🏗️ 监控架构

```
┌─────────────────┐
│  GridBNB Bot    │
│  (Port: 58181)  │
│                 │
│  /metrics       │◄──────┐
└─────────────────┘       │
                          │ 采集 (15s间隔)
                          │
                  ┌───────┴───────┐
                  │  Prometheus   │
                  │  (Port: 9090) │
                  │               │
                  │  - 数据存储   │
                  │  - 告警规则   │
                  └───────┬───────┘
                          │ 查询
                          │
                  ┌───────▼───────┐
                  │   Grafana     │
                  │  (Port: 3000) │
                  │               │
                  │  - 仪表盘     │
                  │  - 可视化     │
                  └───────────────┘
```

**数据流程**:
1. GridBNB Bot 收集实时交易数据
2. 通过`/metrics`端点暴露Prometheus格式指标
3. Prometheus每15秒采集一次数据
4. Grafana从Prometheus查询数据并可视化
5. 告警规则触发时发送通知

---

## 📊 Prometheus指标说明

### 1. 订单相关指标

#### `gridbnb_orders_total`
- **类型**: Counter
- **说明**: 订单总数
- **标签**: `symbol`, `side`, `status`
- **示例查询**:
  ```promql
  # 5分钟内的订单增量
  increase(gridbnb_orders_total[5m])

  # 按交易对统计订单数
  sum by(symbol) (gridbnb_orders_total)
  ```

#### `gridbnb_order_latency_seconds`
- **类型**: Histogram
- **说明**: 订单执行延迟(秒)
- **标签**: `symbol`, `side`
- **示例查询**:
  ```promql
  # P95延迟
  histogram_quantile(0.95, rate(gridbnb_order_latency_seconds_bucket[5m]))

  # 平均延迟
  rate(gridbnb_order_latency_seconds_sum[5m]) / rate(gridbnb_order_latency_seconds_count[5m])
  ```

#### `gridbnb_order_failures_total`
- **类型**: Counter
- **说明**: 订单失败次数
- **标签**: `symbol`, `side`, `error_type`
- **示例查询**:
  ```promql
  # 订单失败率
  rate(gridbnb_order_failures_total[5m]) / rate(gridbnb_orders_total[5m])
  ```

---

### 2. 账户余额指标

#### `gridbnb_usdt_balance`
- **类型**: Gauge
- **说明**: USDT余额
- **标签**: `account_type` (spot/savings)
- **示例查询**:
  ```promql
  # 现货账户USDT余额
  gridbnb_usdt_balance{account_type="spot"}

  # 总USDT余额
  sum(gridbnb_usdt_balance)
  ```

#### `gridbnb_total_account_value_usdt`
- **类型**: Gauge
- **说明**: 账户总价值(USDT)
- **示例查询**:
  ```promql
  # 账户总价值
  gridbnb_total_account_value_usdt

  # 1小时价值变化率
  (gridbnb_total_account_value_usdt - gridbnb_total_account_value_usdt offset 1h)
  / gridbnb_total_account_value_usdt offset 1h
  ```

---

### 3. 网格策略指标

#### `gridbnb_grid_size_percent`
- **类型**: Gauge
- **说明**: 当前网格大小(百分比)
- **标签**: `symbol`

#### `gridbnb_current_price`
- **类型**: Gauge
- **说明**: 当前市场价格
- **标签**: `symbol`

#### `gridbnb_grid_upper_band` / `gridbnb_grid_lower_band`
- **类型**: Gauge
- **说明**: 网格上轨/下轨价格
- **标签**: `symbol`

**示例查询**:
```promql
# 价格距离上轨的百分比
(gridbnb_grid_upper_band - gridbnb_current_price) / gridbnb_current_price * 100

# 价格距离下轨的百分比
(gridbnb_current_price - gridbnb_grid_lower_band) / gridbnb_current_price * 100
```

---

### 4. 收益指标

#### `gridbnb_total_profit_usdt`
- **类型**: Gauge
- **说明**: 总盈亏(USDT)
- **标签**: `symbol`

#### `gridbnb_profit_rate_percent`
- **类型**: Gauge
- **说明**: 盈亏率(百分比)
- **标签**: `symbol`

#### `gridbnb_trade_profit_usdt`
- **类型**: Histogram
- **说明**: 单笔交易盈亏分布
- **标签**: `symbol`

**示例查询**:
```promql
# 所有交易对总盈亏
sum(gridbnb_total_profit_usdt)

# 平均单笔盈亏
avg(gridbnb_trade_profit_usdt)
```

---

### 5. 风险管理指标

#### `gridbnb_position_ratio`
- **类型**: Gauge
- **说明**: 仓位比例 (基础货币价值 / 总价值)
- **标签**: `symbol`

#### `gridbnb_risk_state`
- **类型**: Gauge
- **说明**: 风险状态 (0=允许全部, 1=仅卖出, 2=仅买入)
- **标签**: `symbol`

#### `gridbnb_volatility`
- **类型**: Gauge
- **说明**: 52日年化波动率
- **标签**: `symbol`

---

### 6. 系统资源指标

#### `gridbnb_cpu_usage_percent`
- **类型**: Gauge
- **说明**: CPU使用率(%)

#### `gridbnb_memory_usage_percent`
- **类型**: Gauge
- **说明**: 内存使用率(%)

#### `gridbnb_disk_usage_percent`
- **类型**: Gauge
- **说明**: 磁盘使用率(%)

#### `gridbnb_uptime_seconds`
- **类型**: Gauge
- **说明**: 应用运行时间(秒)

---

## 📈 Grafana仪表盘

### 仪表盘布局

仪表盘分为以下几个区域:

#### 1. 顶部统计卡片
- **账户总价值**: 实时总资产(USDT)
- **总盈亏**: 累计盈亏金额
- **盈亏率**: 收益率百分比

#### 2. 价格与网格
- 实时价格曲线
- 网格上下轨
- 基准价格

#### 3. 仓位监控
- 各交易对仓位比例趋势
- 仓位比例范围提示

#### 4. 订单统计
- 买入/卖出订单数量(5分钟增量)
- 订单执行延迟(P95/P99)

#### 5. 系统资源
- CPU使用率仪表盘
- 内存使用率仪表盘
- 磁盘使用率仪表盘

### 使用技巧

**1. 时间范围选择**
- 默认: 最近6小时
- 可切换: 1h, 6h, 24h, 7d, 30d

**2. 自动刷新**
- 默认: 10秒刷新
- 建议生产环境: 15-30秒

**3. 变量过滤**
- 按交易对过滤 (TODO: 需配置模板变量)

---

## 🚨 告警配置

### 已配置告警规则

告警规则文件: `docker/prometheus/rules/trading_alerts.yml`

#### 1. 系统健康告警

**TradingBotDown** (严重)
- 触发条件: 服务停止超过1分钟
- 处理: 立即检查日志和重启服务

**HighCPUUsage** (警告)
- 触发条件: CPU使用率>80%持续5分钟
- 处理: 检查是否有异常进程

**HighMemoryUsage** (警告)
- 触发条件: 内存使用率>85%持续5分钟
- 处理: 检查内存泄漏

**LowDiskSpace** (严重)
- 触发条件: 磁盘使用率>90%
- 处理: 清理日志或扩容

#### 2. 交易相关告警

**HighOrderFailureRate** (警告)
- 触发条件: 订单失败率>10%持续3分钟
- 处理: 检查API连接和余额

**HighOrderLatency** (警告)
- 触发条件: P95延迟>5秒
- 处理: 检查网络和API状态

**HighAPIErrorRate** (警告)
- 触发条件: API错误率>5%
- 处理: 检查Binance API状态

#### 3. 风险管理告警

**HighPositionRatio** (警告)
- 触发条件: 仓位比例>95%持续5分钟
- 处理: 检查风控策略

**AccountValueDropping** (严重)
- 触发条件: 账户价值1小时内下降>10%
- 处理: 立即检查交易记录

**ContinuousLoss** (警告)
- 触发条件: 盈亏率<-5%持续1小时
- 处理: 评估策略有效性

### 自定义告警

在`docker/prometheus/rules/`目录创建新的YAML文件:

```yaml
groups:
  - name: custom_alerts
    interval: 1m
    rules:
      - alert: CustomAlert
        expr: your_promql_expression > threshold
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "告警摘要"
          description: "告警描述 {{ $value }}"
```

重启Prometheus生效:
```bash
docker compose restart prometheus
```

---

## 🔧 故障排查

### 问题1: /metrics端点返回503

**原因**: prometheus-client未安装

**解决**:
```bash
pip install prometheus-client
```

### 问题2: Prometheus无法采集数据

**检查步骤**:
1. 验证GridBNB服务运行: `docker compose ps`
2. 检查网络连通性: `docker exec gridbnb-prometheus ping gridbnb-bot`
3. 查看Prometheus日志: `docker compose logs prometheus`
4. 验证targets状态: http://localhost:9090/targets

### 问题3: Grafana无数据

**检查步骤**:
1. 验证Prometheus数据源配置
2. 检查Prometheus是否有数据: http://localhost:9090
3. 测试简单查询: `gridbnb_total_account_value_usdt`
4. 查看Grafana日志: `docker compose logs grafana`

### 问题4: 告警不触发

**检查步骤**:
1. 验证规则文件语法: `promtool check rules docker/prometheus/rules/*.yml`
2. 查看Prometheus规则状态: http://localhost:9090/rules
3. 确认告警条件是否真的触发
4. 检查Alertmanager配置(如已启用)

---

## 📚 参考资源

- [Prometheus查询语言PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana文档](https://grafana.com/docs/)
- [GridBNB项目README](../README.md)
- [第一周完成报告](./WEEK1_COMPLETION_REPORT.md)

---

**文档维护**: Claude AI
**最后更新**: 2025-10-21
**版本**: 1.0.0
