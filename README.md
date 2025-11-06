# GridBNB 多交易所自动化网格交易机器人

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Exchanges](https://img.shields.io/badge/Exchanges-Binance%20%7C%20OKX-green.svg)](https://www.binance.com/)
[![Version](https://img.shields.io/badge/Version-v3.2.0-brightgreen.svg)](https://github.com/EBOLABOY/GridBNB-USDT/releases)

一个基于 Python 的**企业级**自动化交易程序，支持 **Binance (币安)** 和 **OKX (欧易)** 等多个交易所。采用先进的网格交易策略，结合动态波动率分析和多层风险管理，旨在稳定捕捉市场波动收益。

## 🎉 最新更新 (v3.2.0 - 2025-10-28)

### 🧪 测试网/模拟盘支持 (新增)
- ✅ **Binance 测试网**: 支持 Binance 官方测试网环境，使用测试币无风险测试
- ✅ **OKX 模拟盘**: 支持 OKX Demo Trading 模拟交易
- ✅ **一键切换**: 通过 `TESTNET_MODE=true` 轻松切换到测试环境
- ✅ **完全隔离**: 测试网与实盘环境完全独立，保证资金安全
- ✅ **新手友好**: 在测试网中学习和验证策略，零风险
- 📖 **详细文档**: [CLAUDE.md - 测试网使用指南](docs/CLAUDE.md#-测试网模拟盘使用指南)

### 💰 智能配置优化
- ✅ **INITIAL_PRINCIPAL 自动检测**: 设置为0时自动检测账户总资产，无需手动配置
- ✅ **LOG_LEVEL 字符串支持**: 支持 `LOG_LEVEL=INFO` 等直观的字符串配置
- ✅ **配置合并优化**: 修复 DYNAMIC_INTERVAL_PARAMS 配置合并逻辑
- ✅ **更友好的错误提示**: 增强配置验证和错误信息

---

## 🎉 历史更新 (v3.1.0 - 2025-10-24)

### 🛡️ 止损机制 (新增)
- ✅ **价格止损**: 当价格跌破基准价特定比例时自动平仓
- ✅ **回撤止盈**: 从最高盈利回撤超过阈值时锁定利润
- ✅ **紧急平仓**: 市价单快速清仓，5次重试确保成功
- ✅ **17个单元测试**: 完整的测试覆盖
- ✅ **配置简单**: `.env` 文件中一键启用/禁用

### 🏦 企业级多交易所架构
- ✅ **Binance & OKX 完整支持**: 现货交易 + 理财功能
- ✅ **1230+ 行企业级代码**: 抽象工厂 + 适配器模式
- ✅ **100% 类型注解**: 完整的类型安全保障
- ✅ **15+ 单元测试**: 核心功能测试覆盖
- ✅ **即插即用**: 修改配置即可切换交易所

### 🤖 AI 辅助策略增强
- ✅ **OpenAI 自定义 Base URL**: 支持国内中转服务
- ✅ **多模型支持**: GPT-4 / Claude 智能分析
- ✅ **技术指标综合分析**: RSI, MACD, 布林带等
- ✅ **市场情绪监测**: Fear & Greed Index

📖 **详细文档**:
- [止损机制设计](docs/STOP_LOSS_DESIGN.md)
- [多交易所架构设计](docs/architecture/multi-exchange-design.md)
- [多交易所快速开始](docs/architecture/QUICK_START.md)
- [AI策略使用指南](docs/AI_STRATEGY_GUIDE.md)

---

## ✨ 核心特性

### 🏦 企业级多交易所支持

- ✅ **Binance (币安)**: 完整支持现货交易和简单储蓄
- ✅ **OKX (欧易)**: 完整支持现货交易和余币宝
- ✅ **即插即用**: 修改配置即可切换交易所，无需修改代码
- ✅ **统一接口**: 所有交易所使用相同的API接口
- ✅ **易于扩展**: 插件化架构，可轻松添加新交易所
- 📖 **详细文档**:
  - [多交易所快速开始](docs/architecture/QUICK_START.md)
  - [多交易所架构设计](docs/architecture/multi-exchange-design.md)

### 🚀 多币种并发交易
- ✅ **任意交易对支持**: BNB/USDT, ETH/USDT, BTC/USDT 等所有现货交易对
- ✅ **并发执行**: 多个交易对同时独立运行，互不干扰
- ✅ **动态配置**: 每个交易对可设置独立的初始价格和网格参数
- ✅ **资源共享**: 单例模式管理连接，避免 API 限流

### 📊 智能网格策略
- ✅ **7日4小时线波动率**: 基于4小时K线数据的敏感波动率计算
- ✅ **EWMA混合算法**: 70% EWMA + 30% 传统波动率，平衡稳定性与敏感性
- ✅ **动态网格调整**: 根据实时波动率自动调整网格大小 (1.0% - 4.0%)
- ✅ **连续函数计算**: 平滑的网格大小调整，避免阶跃变化
- ✅ **波动率平滑**: 移动平均平滑，减少噪音干扰

### 🤖 AI辅助交易策略 (可选)
- ✅ **多模型支持**: 集成OpenAI (GPT-4, GPT-3.5) 和 Anthropic (Claude)
- ✅ **技术指标分析**: RSI, MACD, 布林带, EMA, 成交量等综合分析
- ✅ **市场情绪监测**: 实时获取Fear & Greed Index市场情绪指标
- ✅ **智能触发机制**: 基于技术信号变化、时间间隔、市场波动自动触发
- ✅ **成本控制**: 每日调用限制、置信度阈值、金额比例控制
- ✅ **风险协同**: 与现有风控系统无缝集成，确保交易安全
- ✅ **自定义OpenAI Base URL**: 支持国内中转服务
- 📖 **详细文档**: [AI策略使用指南](docs/AI_STRATEGY_GUIDE.md)

### 🛡️ 多层风险管理
- ✅ **止损机制**: 价格止损和回撤止盈双重保护，最大限度降低极端行情风险
  - 价格止损：当价格相对基准价下跌超过设定比例时触发（默认15%）
  - 回撤止盈：当盈利从最高点回撤超过设定比例时锁定利润（默认20%）
  - 紧急平仓：自动市价单清仓，5次重试机制确保执行成功
  - 📖 **详细文档**: [止损机制设计](docs/STOP_LOSS_DESIGN.md)
- ✅ **仓位限制**: 可配置的最大/最小仓位比例控制
- ✅ **连续失败保护**: 最大重试次数限制，防止僵尸进程
- ✅ **实时监控**: 风险状态实时评估和告警
- ✅ **紧急停止**: 异常情况下的自动停止机制
- ✅ **理财功能开关**: 可选禁用理财功能，适合子账户用户

### 🌐 企业级部署
- ✅ **Docker 容器化**: 完整的 Docker Compose 部署方案
- ✅ **Nginx 反向代理**: 高性能 Web 服务和负载均衡
- ✅ **健康检查**: 自动监控和故障恢复
- ✅ **数据持久化**: 完整的状态保存和恢复机制
- ✅ **一键更新**: 便捷的更新脚本

### 📱 现代化 Web 界面
- ✅ **实时监控**: 交易状态、收益统计、风险指标
- ✅ **多币种视图**: 支持多交易对的统一监控界面
- ✅ **基础认证**: 可选的用户名密码保护
- ✅ **响应式设计**: 支持桌面和移动设备访问

### 📊 企业级监控系统
- ✅ **Prometheus指标**: 42个核心指标实时采集
- ✅ **Grafana仪表盘**: 专业的数据可视化界面
- ✅ **智能告警**: 多级别告警规则自动监控
- ✅ **性能监控**: CPU、内存、磁盘使用率实时跟踪
- ✅ **交易分析**: 订单延迟、成功率、盈亏趋势分析

---

## 🏗️ 企业级架构设计

### 设计模式应用
- ✅ **抽象工厂模式**: 统一的交易所创建接口
- ✅ **策略模式**: 不同交易所的策略实现
- ✅ **适配器模式**: 统一的业务接口
- ✅ **单例模式**: 全局唯一的交易所实例

### 代码质量
- ✅ **1230+ 行企业级代码**: 核心多交易所架构
- ✅ **100% 类型注解覆盖**: 完整的类型安全
- ✅ **完整的文档字符串**: 每个类和方法都有详细说明
- ✅ **15+ 单元测试**: 完整的测试覆盖
- ✅ **配置验证**: 启动前配置检查
- ✅ **健康检查**: 运行时健康监控

---

## 📋 系统要求

### 基础环境
- **Python**: 3.8+ (推荐 3.10+)
- **Docker**: 20.10+ (可选，推荐用于生产部署)
- **内存**: 最低 512MB，推荐 1GB+
- **存储**: 500MB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **CPU**: 1核心及以上
- **内存**: 512MB+ RAM
- **网络**: 亚洲地区服务器 (日本、新加坡等)
- **操作系统**: Ubuntu 20.04+, Windows 10+, macOS 10.15+

---

## 🚀 快速开始

### 方法一：Docker 部署 (推荐)

1. **克隆项目**
   ```bash
   git clone https://github.com/EBOLABOY/GridBNB-USDT.git
   cd GridBNB-USDT
   ```

2. **配置环境变量**
   ```bash
   # 复制配置文件模板
   cp config/.env.example config/.env

   # 编辑 config/.env 文件
   # 选择交易所: EXCHANGE=binance 或 EXCHANGE=okx
   # 填入对应的 API 密钥
   ```

3. **启动服务**
   ```bash
   # Windows 用户
   start-with-nginx.bat

   # Linux/Mac 用户
   chmod +x start-with-nginx.sh
   ./start-with-nginx.sh
   ```

4. **访问 Web 界面**
   - 打开浏览器访问: http://localhost

### 方法二：Python 直接运行

1. **克隆并安装**
   ```bash
   git clone https://github.com/EBOLABOY/GridBNB-USDT.git
   cd GridBNB-USDT

   # 创建虚拟环境
   python -m venv .venv

   # 激活虚拟环境
   # Windows:
   .\.venv\Scripts\activate
   # Linux/Mac:
   source .venv/bin/activate

   # 安装依赖
   pip install -r requirements.txt
   ```

2. **配置和运行**
   ```bash
   # 配置 config/.env 文件
   cp config/.env.example config/.env
   # 编辑 config/.env 文件，填入 API 密钥

   # 运行程序
   python src/main.py
   ```

---

## 🏦 多交易所配置

### 使用 Binance (币安)

```bash
# .env 配置
EXCHANGE=binance
BINANCE_API_KEY="your_binance_api_key"
BINANCE_API_SECRET="your_binance_api_secret"
```

### 使用 OKX (欧易)

```bash
# .env 配置
EXCHANGE=okx
OKX_API_KEY="your_okx_api_key"
OKX_API_SECRET="your_okx_api_secret"
OKX_PASSPHRASE="your_okx_passphrase"  # OKX特有参数
```

### 快速切换

**无需修改代码，只需更改配置！**

```bash
# 从 Binance 切换到 OKX
# 1. 修改 .env 中的 EXCHANGE=okx
# 2. 填写 OKX API 配置
# 3. 重启程序
```

📖 **详细指南**:
- [多交易所快速开始](docs/architecture/QUICK_START.md)
- [多交易所架构设计](docs/architecture/multi-exchange-design.md)
- [迁移指南](docs/MIGRATION_GUIDE.md)

---

## 📁 项目结构

```
GridBNB-USDT/
├── src/                        # 源代码目录
│   ├── main.py                 # 应用入口
│   ├── core/                   # 核心模块
│   │   ├── trader.py           # 网格交易器
│   │   ├── exchanges/          # 🆕 多交易所架构
│   │   │   ├── base.py         #     抽象基类和接口
│   │   │   ├── factory.py      #     工厂模式实现
│   │   │   ├── binance.py      #     Binance适配器
│   │   │   ├── okx.py          #     OKX适配器
│   │   │   └── utils.py        #     工具函数
│   │   └── order_tracker.py    # 订单跟踪
│   ├── strategies/             # 策略模块
│   │   ├── ai_strategy.py      # 🆕 AI辅助策略
│   │   └── risk_manager.py     # 风险管理
│   ├── services/               # 服务模块
│   │   ├── monitor.py          # 交易监控
│   │   └── web_server.py       # Web服务
│   └── config/                 # 配置模块
│       └── settings.py         # 配置管理
├── tests/                      # 测试目录
│   └── unit/                   # 单元测试
│       ├── test_exchange_factory.py    # 🆕 交易所工厂测试 (15+测试)
│       ├── test_exchange_adapters.py   # 🆕 交易所适配器测试
│       ├── test_trader.py              # 交易器核心逻辑测试
│       ├── test_config.py              # 配置验证测试
│       ├── test_risk_manager.py        # 风险管理测试
│       ├── test_ai_strategy.py         # 🆕 AI策略测试
│       └── test_web_auth.py            # Web认证测试
├── docs/                       # 文档目录
│   ├── architecture/           # 🆕 架构文档
│   │   ├── multi-exchange-design.md  # 🆕 多交易所架构设计
│   │   └── QUICK_START.md            # 🆕 快速开始指南
│   ├── CLAUDE.md               # AI 上下文文档（完整技术文档）
│   ├── MIGRATION_GUIDE.md      # 迁移指南
│   ├── AI_STRATEGY_GUIDE.md    # AI策略使用指南
│   ├── MONITORING_GUIDE.md     # 监控系统指南
│   └── CODE_QUALITY.md         # 代码质量规范
├── examples/                   # 🆕 示例代码
│   └── multi_exchange_usage.py # 多交易所使用示例
├── docker/                     # Docker配置
│   ├── Dockerfile
│   └── docker-compose.yml
└── config/                     # 配置文件
│   ├── .env.example            # 环境变量配置模板
    ├── .pre-commit-config.yaml # Pre-commit钩子配置
    └── pytest.ini              # Pytest配置
```

---

## ⚙️ 配置说明

### 核心配置 (.env 文件)

```bash
# ========== 交易所选择 ==========
# 选择要使用的交易所: binance / okx
EXCHANGE=binance

# ========== 测试网/模拟盘配置 🆕 ==========
# 是否使用测试网（true=模拟盘测试, false=实盘交易）
# 测试网使用测试币，不会影响真实资金，适合调试和学习
TESTNET_MODE=false

# ========== Binance API ==========
# 如果使用币安交易所，必填
BINANCE_API_KEY="your_binance_api_key_here"
BINANCE_API_SECRET="your_binance_api_secret_here"

# Binance 测试网 API（可选，仅在 TESTNET_MODE=true 时使用）🆕
# 测试网申请地址: https://testnet.binance.vision/
# BINANCE_TESTNET_API_KEY="your_testnet_api_key_here"
# BINANCE_TESTNET_API_SECRET="your_testnet_api_secret_here"

# ========== OKX API ==========
# 如果使用OKX交易所，必填
# OKX requires all three parameters
OKX_API_KEY="your_okx_api_key_here"
OKX_API_SECRET="your_okx_api_secret_here"
OKX_PASSPHRASE="your_okx_passphrase_here"

# OKX 测试网 API（可选，仅在 TESTNET_MODE=true 时使用）🆕
# OKX Demo环境需要单独申请API密钥
# 申请地址: https://www.okx.com/account/my-api (选择"Demo Trading"模式)
# OKX_TESTNET_API_KEY="your_okx_demo_api_key_here"
# OKX_TESTNET_API_SECRET="your_okx_demo_api_secret_here"
# OKX_TESTNET_PASSPHRASE="your_okx_demo_passphrase_here"

# ========== 策略核心配置 ==========
# 要运行的交易对列表，用英文逗号分隔
# 例如: "BNB/USDT,ETH/USDT,BTC/USDT"
SYMBOLS="BNB/USDT,ETH/USDT"

# 按交易对设置初始参数 (JSON格式)
# 为每个交易对设置 "initial_base_price" 和 "initial_grid"
# 如果某个交易对在此处未定义，程序将自动使用当前市价作为基准价，并使用下面的全局INITIAL_GRID
INITIAL_PARAMS_JSON='{"BNB/USDT": {"initial_base_price": 600.0, "initial_grid": 2.0}, "ETH/USDT": {"initial_base_price": 3000.0, "initial_grid": 2.5}, "BTC/USDT": {"initial_base_price": 45000.0, "initial_grid": 1.5}}'

# 全局默认初始网格大小 (%)
# 仅当上面的INITIAL_PARAMS_JSON中未指定某个交易对的网格时使用
INITIAL_GRID=2.0

# 最小交易金额 (USDT)，请确保大于交易所对该交易对的最小名义价值要求 (通常是10 USDT)
MIN_TRADE_AMOUNT=20.0

# ========== 初始状态设置 ==========
# 🆕 初始本金（用于计算总盈亏和盈亏率，单位: USDT）
# 设置为0或不设置时，系统会在启动时自动检测账户总资产
# 建议：首次运行设置为0自动检测，之后可固定为启动时的总资产以便准确计算盈亏
INITIAL_PRINCIPAL=0

# ========== 日志配置 🆕 ==========
# 日志级别（可选值: DEBUG, INFO, WARNING, ERROR, CRITICAL）
# 支持字符串或对应的整数值（10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL）
# 建议生产环境使用 INFO，调试时使用 DEBUG
LOG_LEVEL=INFO

# ========== 可选配置 ==========
# AI策略配置
ENABLE_AI_STRATEGY=false
AI_PROVIDER=openai  # openai 或 claude
OPENAI_API_KEY="your_openai_key"
OPENAI_BASE_URL="https://api.openai.com/v1"  # 支持自定义中转服务
ANTHROPIC_API_KEY="your_anthropic_key"

# PushPlus 通知 Token，用于发送交易通知或警报
PUSHPLUS_TOKEN="your_pushplus_token_here"

# 是否启用自动申购/赎回理财功能 (true/false)
# Binance: 简单储蓄 | OKX: 余币宝
# 对于使用子账户API的用户，或不希望使用理财功能的用户，请设置为 false
ENABLE_SAVINGS_FUNCTION=true

# Web UI 访问认证。如果留空，Web界面将无需密码即可访问。
WEB_USER="admin"
WEB_PASSWORD="YourSecurePasswordHere"

# 代理设置 (如果需要通过代理连接交易所)
# 例如: HTTP_PROXY="http://127.0.0.1:7890"
HTTP_PROXY=
```

### 重要安全提示

⚠️ **API 密钥安全**:
- ✅ 确保 API Key 只有**现货交易**权限
- ✅ **禁用提现权限**
- ✅ 不要在公共场所或代码中暴露密钥
- ✅ 定期更换 API 密钥
- ✅ OKX用户：妥善保管 **Passphrase**

### 理财功能配置

**启用理财功能 (默认)**:
```bash
ENABLE_SAVINGS_FUNCTION=true
```
- ✅ Binance: 自动申购/赎回简单储蓄
- ✅ OKX: 自动申购/赎回余币宝
- ✅ 最大化资金利用效率

**禁用理财功能**:
```bash
ENABLE_SAVINGS_FUNCTION=false
```
- ✅ 所有资金保留在现货账户
- ✅ 适合子账户用户或保守用户

---

## 🌐 Web 监控界面

### 访问地址
- **Docker 部署**: http://localhost
- **直接运行**: http://localhost:58181

### 功能特性
- 📊 **实时监控**: 交易状态、收益统计、持仓分析
- 📈 **多币种视图**: 支持多交易对统一监控
- 📱 **响应式设计**: 支持手机和平板访问
- 🔐 **安全认证**: 可选的用户名密码保护

---

## 🔄 更新和维护

### 一键更新 (Ubuntu/Linux)

```bash
cd GridBNB-USDT
chmod +x update.sh
./update.sh
```

### 手动更新

```bash
git pull origin main
docker compose up -d --build
docker compose ps
```

---

## 📊 监控和日志

### 日志文件
- **应用日志**: `logs/trading_system.log`
- **Docker 日志**: `docker compose logs -f`

### 监控命令
```bash
# 查看服务状态
docker compose ps

# 查看实时日志
docker compose logs -f gridbnb-bot

# 查看系统资源
docker stats
```

---

## 🔧 故障排除

### 常见问题

1. **配置验证失败**
   ```bash
   # 运行配置验证
   python -c "
   import asyncio
   from src.core.exchange.validator import validate_and_create_exchange
   asyncio.run(validate_and_create_exchange())
   "
   ```

2. **OKX连接失败**
   - 检查是否提供了 `OKX_PASSPHRASE`
   - 验证 API 权限设置
   - 确认 API 密钥格式正确

3. **理财功能报错**
   - 检查 API 是否有理财权限
   - 子账户用户设置 `ENABLE_SAVINGS_FUNCTION=false`

4. **Docker 相关**
   ```bash
   docker --version
   docker compose version
   docker compose restart
   docker compose logs gridbnb-bot
   ```

### 获取帮助

- 📖 **文档中心**: [docs/](docs/)
  - [AI 上下文文档](docs/CLAUDE.md) - 完整的项目技术文档
  - [多交易所快速开始](docs/architecture/QUICK_START.md)
  - [多交易所架构设计](docs/architecture/multi-exchange-design.md)
  - [迁移指南](docs/MIGRATION_GUIDE.md)
  - [AI策略使用指南](docs/AI_STRATEGY_GUIDE.md)
- 🐛 **问题反馈**: [GitHub Issues](https://github.com/EBOLABOY/GridBNB-USDT/issues)
- 💬 **社区讨论**: [Telegram群组](https://t.me/+b9fKO9kEOkg2ZjI1)

---

## ⚠️ 风险提示

- **投资风险**: 数字货币交易存在高风险，可能导致本金损失
- **策略风险**: 网格策略在单边行情中可能表现不佳
- **技术风险**: 程序可能存在 bug，建议小额测试
- **市场风险**: 极端市场条件下可能出现意外损失

**请在充分理解风险的前提下使用本程序，投资有风险，入市需谨慎！**

---

## 👨‍💻 开发者指南

### 代码质量工具

**已配置的工具**:
- ✅ **Black**: 代码自动格式化
- ✅ **isort**: 导入语句自动排序
- ✅ **Flake8**: 代码风格检查
- ✅ **mypy**: 静态类型检查
- ✅ **Bandit**: 安全漏洞扫描
- ✅ **Pre-commit**: Git 提交前自动检查

**快速开始**:
```bash
pip install -r requirements-dev.txt
pre-commit install
pre-commit run --all-files
```

### 添加新交易所

只需 3 步：

1. **创建适配器类**
   ```python
   class BybitAdapter(BaseExchangeAdapter):
       # 实现抽象方法...
   ```

2. **注册到工厂**
   ```python
   ExchangeFactory.register_adapter(ExchangeType.BYBIT, BybitAdapter)
   ```

3. **完成！**无需修改其他代码

📖 详见: [多交易所架构设计](docs/architecture/multi-exchange-design.md)

---

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 安装开发工具 (`pip install -r requirements-dev.txt`)
4. 编写代码并确保通过所有检查
5. 提交更改 (`git commit -m 'feat: Add AmazingFeature'`)
6. 推送到分支 (`git push origin feature/AmazingFeature`)
7. 开启 Pull Request

**代码质量要求**:
- ✅ 通过 Black 格式化
- ✅ 通过 Flake8 检查
- ✅ 添加类型注解
- ✅ 包含单元测试
- ✅ 更新相关文档

---

## 🙏 致谢

- [CCXT](https://github.com/ccxt/ccxt) - 统一交易所 API 库
- [Docker](https://www.docker.com/) - 容器化部署
- [Nginx](https://nginx.org/) - 高性能 Web 服务器

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

<div align="center">

### 🤝 联系与交流

遇到问题或有任何想法？通过以下方式加入我们的社区！

<p>
  <a href="https://t.me/+b9fKO9kEOkg2ZjI1"><img alt="Telegram" src="https://img.shields.io/badge/Telegram-群组交流-28A8EA?style=flat-square&logo=telegram"></a>
  <a href="https://github.com/EBOLABOY/GridBNB-USDT/issues"><img alt="Issues" src="https://img.shields.io/github/issues/EBOLABOY/GridBNB-USDT?style=flat-square&logo=github&label=Issues"></a>
</p>

**⭐ 如果这个项目对您有帮助，请给个 Star！⭐**

[![Powered by DartNode](https://dartnode.com/branding/DN-Open-Source-sm.png)](https://dartnode.com "Powered by DartNode - Free VPS for Open Source")

</div>
