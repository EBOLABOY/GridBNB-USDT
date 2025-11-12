# 多交易所支持 - 快速开始

本指南帮助您快速上手使用多交易所架构。

## 📋 目录
- [环境配置](#环境配置)
- [基础使用](#基础使用)
- [交易所切换](#交易所切换)
- [高级用法](#高级用法)
- [常见问题](#常见问题)

---

## 环境配置

### 1. 安装依赖

```bash
pip install ccxt pydantic python-dotenv
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# === 交易所选择 ===
EXCHANGE_NAME=binance  # 可选: binance, okx

# === Binance 配置 ===
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# === OKX 配置 ===
OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_api_secret
OKX_PASSPHRASE=your_okx_passphrase

# === 功能开关 ===
ENABLE_SAVINGS_FUNCTION=true

# === 其他配置 ===
HTTP_PROXY=  # 可选，代理设置
```

---

## 基础使用

### 使用Binance

```python
import asyncio
from src.core.exchanges import get_exchange_factory, ExchangeConfig
from src.config.settings import settings

async def main():
    # 1. 获取工厂
    factory = get_exchange_factory()

    # 2. 创建配置
    config = ExchangeConfig(
        exchange_name='binance',
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET,
        enable_savings=True
    )

    # 3. 创建交易所实例
    exchange = factory.create('binance', config)

    try:
        # 4. 使用交易所
        await exchange.load_markets()
        ticker = await exchange.fetch_ticker('BNB/USDT')
        print(f"BNB价格: {ticker['last']}")

    finally:
        await exchange.close()

asyncio.run(main())
```

### 使用OKX

```python
config = ExchangeConfig(
    exchange_name='okx',
    api_key=settings.OKX_API_KEY,
    api_secret=settings.OKX_API_SECRET,
    passphrase=settings.OKX_PASSPHRASE,  # OKX必需
    enable_savings=True
)

exchange = factory.create('okx', config)
```

---

## 交易所切换

### 方法1：修改配置文件

修改 `.env` 文件：

```bash
EXCHANGE_NAME=okx  # 从binance切换到okx
```

然后重启程序。

### 方法2：代码动态切换

```python
def create_exchange_by_name(name: str):
    """根据名称创建交易所"""
    factory = get_exchange_factory()

    if name == 'binance':
        config = ExchangeConfig(
            exchange_name='binance',
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET
        )
    elif name == 'okx':
        config = ExchangeConfig(
            exchange_name='okx',
            api_key=settings.OKX_API_KEY,
            api_secret=settings.OKX_API_SECRET,
            passphrase=settings.OKX_PASSPHRASE
        )
    else:
        raise ValueError(f"不支持的交易所: {name}")

    return factory.create(name, config)

# 使用
binance = create_exchange_by_name('binance')
okx = create_exchange_by_name('okx')
```

---

## 高级用法

### 1. 检查交易所能力

```python
from src.core.exchanges.base import ExchangeCapabilities

# 检查是否支持理财功能
if exchange.supports(ExchangeCapabilities.SAVINGS):
    balance = await exchange.fetch_funding_balance()
    print(f"理财余额: {balance}")
else:
    print("该交易所不支持理财功能")
```

### 2. 多交易所并行运行

```python
import asyncio

async def run_multiple_exchanges():
    factory = get_exchange_factory()

    # 创建多个交易所
    binance = factory.create('binance', binance_config)
    okx = factory.create('okx', okx_config)

    # 并行获取行情
    binance_ticker, okx_ticker = await asyncio.gather(
        binance.fetch_ticker('BNB/USDT'),
        okx.fetch_ticker('BNB/USDT')
    )

    print(f"Binance: {binance_ticker['last']}")
    print(f"OKX: {okx_ticker['last']}")
```

### 3. 自定义交易所配置

```python
config = ExchangeConfig(
    exchange_name='binance',
    api_key='...',
    api_secret='...',
    timeout=30000,           # 自定义超时
    enable_rate_limit=True,  # 启用限流
    proxy='http://localhost:1080',  # 使用代理
    verbose=True,            # 开启调试日志
    custom_options={         # 自定义选项
        'defaultType': 'spot',
        'recvWindow': 10000
    }
)
```

---

## 常见问题

### Q1: 如何添加新的交易所？

**A**: 创建新的交易所类并注册：

```python
from src.core.exchanges.base import BaseExchange, ISavingsFeature

class BybitExchange(BaseExchange, ISavingsFeature):
    def _create_ccxt_instance(self):
        return ccxt.bybit({...})

    # 实现其他方法...

# 注册
factory = get_exchange_factory()
factory.register('bybit', BybitExchange)
```

### Q2: 如何处理交易所特定功能？

**A**: 使用特性检查或isinstance：

```python
# 方法1: 使用能力检查
if exchange.supports(ExchangeCapabilities.SAVINGS):
    await exchange.transfer_to_savings('USDT', 100)

# 方法2: 使用isinstance
from src.core.exchanges import ISavingsFeature

if isinstance(exchange, ISavingsFeature):
    await exchange.transfer_to_savings('USDT', 100)
```

### Q3: 如何调试交易所API错误？

**A**: 启用详细日志：

```python
# 方法1: 配置中启用
config = ExchangeConfig(
    ...,
    verbose=True  # 显示详细请求/响应
)

# 方法2: 设置日志级别
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Q4: 如何测试不同交易所？

**A**: 使用测试模式或Mock：

```python
# 使用Mock交易所
from tests.unit.test_exchange_factory import MockExchange

factory = get_exchange_factory()
factory.register('mock', MockExchange)

config = ExchangeConfig(
    exchange_name='mock',
    api_key='test',
    api_secret='test'
)

exchange = factory.create('mock', config)
```

### Q5: 如何从旧架构迁移？

**A**: 参考迁移指南：

1. 阶段1：创建新架构代码（不影响现有系统）
2. 阶段2：使用适配器包装旧客户端
3. 阶段3：逐步替换旧代码
4. 阶段4：完全切换到新架构
5. 阶段5：清理旧代码

详细步骤见 `docs/architecture/multi-exchange-design.md`

---

## 下一步

- 阅读完整架构文档: `docs/architecture/multi-exchange-design.md`
- 查看迁移示例: `examples/multi_exchange_migration.py`
- 运行测试: `pytest tests/unit/test_exchange_factory.py -v`

---

**需要帮助？** 请查看文档或提交Issue。
