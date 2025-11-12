# 多交易所支持 - 快速开始指南

## 🚀 5分钟快速上手

本指南帮助您快速开始使用企业级多交易所架构。

---

## 📋 前置条件

- ✅ Python 3.8+
- ✅ 已安装项目依赖 (`pip install -r requirements.txt`)
- ✅ 拥有交易所API密钥

---

## 🎯 步骤1：选择交易所

编辑 `.env` 文件，选择要使用的交易所：

### **使用币安 (Binance)**

```bash
EXCHANGE=binance
BINANCE_API_KEY="your_api_key"
BINANCE_API_SECRET="your_api_secret"
```

### **使用OKX**

```bash
EXCHANGE=okx
OKX_API_KEY="your_api_key"
OKX_API_SECRET="your_api_secret"
OKX_PASSPHRASE="your_passphrase"  # OKX特有
```

---

## 🎯 步骤2：验证配置

运行配置验证脚本：

```bash
python -c "
import asyncio
from src.core.exchange.validator import validate_and_create_exchange

async def test():
    exchange = await validate_and_create_exchange()
    print(f'✅ {exchange.exchange_type.value.upper()} 连接成功！')
    await exchange.close()

asyncio.run(test())
"
```

**预期输出**:

```
====================================================================
📋 交易所配置验证报告
====================================================================

🏦 交易所: BINANCE
💰 理财功能: 启用
📊 交易对: BNB/USDT,ETH/USDT

✅ 配置验证通过，没有发现问题

====================================================================
✅ 配置有效，可以启动交易系统
====================================================================

正在初始化币安交易所连接...
✅ 币安连接成功 | 账户资产: 5 种
✅ BINANCE 连接成功！
```

---

## 🎯 步骤3：运行交易系统

```bash
python src/main.py
```

就这么简单！系统会自动：
- ✅ 验证配置
- ✅ 创建交易所实例
- ✅ 初始化所有交易对
- ✅ 开始网格交易

---

## 🔄 切换交易所

想切换到OKX？只需3步：

### 1. 修改 `.env`

```bash
# 注释掉币安配置
# EXCHANGE=binance
# BINANCE_API_KEY="xxx"
# BINANCE_API_SECRET="yyy"

# 启用OKX配置
EXCHANGE=okx
OKX_API_KEY="your_okx_api_key"
OKX_API_SECRET="your_okx_api_secret"
OKX_PASSPHRASE="your_okx_passphrase"
```

### 2. 验证配置

```bash
python -c "
import asyncio
from src.core.exchange.validator import validate_and_create_exchange
asyncio.run(validate_and_create_exchange())
"
```

### 3. 重启系统

```bash
python src/main.py
```

**无需修改任何代码！** 🎉

---

## 📝 常用命令

### 查看支持的交易所

```bash
python -c "
from src.core.exchange import ExchangeFactory
print('支持的交易所:', ExchangeFactory.get_supported_exchanges())
"
```

输出:
```
支持的交易所: ['binance', 'okx']
```

### 测试连接

```bash
python -c "
import asyncio
from src.core.exchange import ExchangeFactory, ExchangeType

async def test():
    exchange = ExchangeFactory.create(
        ExchangeType.BINANCE,
        api_key='your_key',
        api_secret='your_secret'
    )
    await exchange.initialize()

    ticker = await exchange.fetch_ticker('BTC/USDT')
    print(f'BTC价格: {ticker[\"last\"]}')

    await exchange.close()

asyncio.run(test())
"
```

### 检查健康状态

```bash
python -c "
import asyncio
from src.core.exchange.validator import validate_and_create_exchange

async def check():
    exchange = await validate_and_create_exchange()
    is_healthy, message = await exchange.health_check()
    print(f'健康状态: {\"✅ 健康\" if is_healthy else \"❌ 异常\"}')
    print(f'详情: {message}')
    await exchange.close()

asyncio.run(check())
"
```

---

## 🧪 测试示例

运行完整的使用示例：

```bash
python examples/multi_exchange_usage.py
```

这会演示：
- ✅ 如何创建交易所实例
- ✅ 如何进行功能检测
- ✅ 如何处理错误
- ✅ 如何调整精度
- ✅ 更多高级用法...

---

## ⚙️ 高级配置

### 禁用理财功能

如果不需要理财功能（适合子账户用户）：

```bash
ENABLE_SAVINGS_FUNCTION=false
```

### 配置多个交易对

```bash
SYMBOLS="BNB/USDT,ETH/USDT,BTC/USDT"
```

### 设置初始参数

```bash
INITIAL_PARAMS_JSON='{
  "BNB/USDT": {"initial_base_price": 600.0, "initial_grid": 2.0},
  "ETH/USDT": {"initial_base_price": 3000.0, "initial_grid": 2.5}
}'
```

---

## 🐛 故障排除

### 问题1: "不支持的交易所"

**原因**: `EXCHANGE` 配置错误

**解决**:
```bash
# 检查拼写
EXCHANGE=binance  # ✅ 正确
EXCHANGE=Binance  # ❌ 错误（大小写敏感）
EXCHANGE=bnb      # ❌ 错误（不存在）
```

### 问题2: "缺少 API 密钥"

**原因**: API密钥配置缺失或格式错误

**解决**:
```bash
# 确保格式正确
BINANCE_API_KEY="your_key_here"    # ✅ 有引号
BINANCE_API_KEY=your_key_here      # ❌ 可能有空格问题
```

### 问题3: OKX "缺少 passphrase"

**原因**: OKX需要额外的passphrase参数

**解决**:
```bash
OKX_PASSPHRASE="your_passphrase"  # ✅ 必须提供
```

### 问题4: 理财功能报错

**原因**:
- API权限不足
- 交易所不支持
- 子账户限制

**解决**:
```bash
# 禁用理财功能
ENABLE_SAVINGS_FUNCTION=false
```

---

## 📚 下一步

### 深入学习

- 📖 [架构设计文档](MULTI_EXCHANGE_ARCHITECTURE.md)
- 📖 [迁移指南](MIGRATION_GUIDE.md)
- 📖 [完整示例](../examples/multi_exchange_usage.py)

### 添加新交易所

参考 [架构设计文档 - 扩展机制](MULTI_EXCHANGE_ARCHITECTURE.md#扩展机制)

### 运行测试

```bash
# 运行单元测试
pytest tests/unit/test_exchange_adapters.py -v

# 运行集成测试（需要真实API密钥）
pytest tests/unit/test_exchange_adapters.py -m integration -v
```

---

## 💡 提示和技巧

### 1. 使用配置验证器

**推荐**:
```python
from src.core.exchange.validator import validate_and_create_exchange
exchange = await validate_and_create_exchange()
```

**好处**:
- ✅ 自动验证配置
- ✅ 详细的错误提示
- ✅ 健康检查

### 2. 单例模式

交易所实例是单例的，可以安全共享：

```python
# 第一次创建
exchange1 = ExchangeFactory.create(...)

# 第二次获取（返回同一实例）
exchange2 = ExchangeFactory.get_instance(...)

assert exchange1 is exchange2  # True
```

### 3. 功能检测

不同交易所支持的功能不同，使用功能检测：

```python
if exchange.capabilities.supports(ExchangeFeature.FUNDING_ACCOUNT):
    # 使用理财功能
    await exchange.fetch_funding_balance()
else:
    # 优雅降级
    logger.warning("理财功能不可用")
```

---

## 🆘 获取帮助

- 🐛 **问题反馈**: [GitHub Issues](https://github.com/EBOLABOY/GridBNB-USDT/issues)
- 💬 **社区讨论**: [Telegram群组](https://t.me/+b9fKO9kEOkg2ZjI1)
- 📖 **详细文档**: [docs/](./docs/)

---

## ✅ 完成！

恭喜！您已经掌握了多交易所架构的基本使用。

**接下来**:
- 🚀 启动交易系统
- 📊 监控交易状态
- 💰 享受自动化收益

---

**祝交易顺利！** 🎉
