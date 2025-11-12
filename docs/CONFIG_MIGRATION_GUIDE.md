# GridBNB 配置管理系统迁移指南

> 版本：v3.2.0+
>
> 日期：2025-10-29

## 📋 概述

从 v3.2.0 版本开始，GridBNB 交易系统引入了**基于数据库的配置管理系统**，实现了配置的图形化管理、版本控制和导入/导出功能。

### 主要变化

| 项目 | 旧方式 | 新方式 |
|------|--------|--------|
| 配置存储 | 全部在 .env 文件 | API密钥在.env，其他配置在数据库 |
| 配置修改 | 手动编辑.env，重启应用 | Web界面修改，部分配置实时生效 |
| 配置备份 | 手动复制.env文件 | 自动版本历史 + 导出功能 |
| 配置模板 | 无 | 内置3种策略模板 |

### 配置加载优先级

```
1. API密钥配置  → 从 .env 文件读取（安全考虑）
2. 其他配置     → 数据库 > .env > 默认值
3. 缓存机制     → 启动时加载到内存，提供reload接口
```

---

## 🚀 快速开始

### 步骤1：初始化数据库

首次使用需要初始化数据库：

```bash
# 初始化数据库（创建表、默认用户、默认配置）
python scripts/init_database.py

# 如果需要重置数据库（⚠️ 会删除所有数据）
python scripts/init_database.py --reset
```

初始化完成后会创建：
- ✅ 所有数据库表
- ✅ 默认管理员账户（admin / admin123）
- ✅ 所有默认配置项（从 config_definitions.py）
- ✅ 3个系统预设模板（保守型/平衡型/激进型）

### 步骤2：配置 API 密钥

编辑 `.env` 文件，配置交易所API密钥：

```env
# 必需：Binance API密钥
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# 可选：OKX API密钥（如果使用OKX交易所）
OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_api_secret
OKX_PASSPHRASE=your_okx_passphrase

# 可选：测试网密钥
TESTNET_MODE=false
BINANCE_TESTNET_API_KEY=
BINANCE_TESTNET_API_SECRET=
```

**重要提示：**
- ✅ API密钥**仅存储在.env文件**中，不会写入数据库
- ✅ .env 文件应添加到 `.gitignore`，避免泄露
- ✅ 其他配置项（交易对、网格大小等）通过Web界面管理

### 步骤3：启动Web服务器

```bash
# 启动FastAPI服务器
python -m src.services.fastapi_server

# 服务将运行在 http://localhost:8000
```

### 步骤4：登录并修改密码

1. 访问 `http://localhost:8000`
2. 使用默认账户登录：
   - 用户名：`admin`
   - 密码：`admin123`
3. **立即修改默认密码**（安全要求）
4. 进入配置管理页面，调整交易策略

---

## 🔧 配置管理功能

### 1. Web界面管理配置

访问 `http://localhost:8000/configs`，可以：

- 📋 **查看配置列表**：按类型、状态筛选
- ✏️ **编辑配置**：实时修改配置值
- 🔄 **重新加载**：不重启系统即可应用部分配置
- 📊 **查看历史**：每次修改都有版本记录
- 📁 **配置分类**：
  - 交易所配置 (EXCHANGE)
  - 交易策略 (TRADING)
  - 风控配置 (RISK)
  - AI策略 (AI)
  - 通知配置 (NOTIFICATION)
  - 系统配置 (SYSTEM)

### 2. 配置导出

**API端点：** `GET /api/configs/export`

**参数：**
- `config_type`：可选，按类型导出（如：trading, risk）
- `include_sensitive`：是否包含敏感配置（默认：false）

**示例：**
```bash
# 导出所有配置
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/configs/export \
  -o gridbnb_config_backup.json

# 仅导出交易策略配置
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/configs/export?config_type=trading" \
  -o gridbnb_trading_config.json
```

**导出文件格式：**
```json
{
  "version": "3.2.0",
  "export_time": "2025-10-29T14:20:00",
  "exported_by": "admin",
  "total_configs": 45,
  "configs": {
    "SYMBOLS": {
      "value": "BNB/USDT,ETH/USDT",
      "type": "trading",
      "data_type": "string",
      "display_name": "交易对列表",
      "description": "要交易的币对，多个用逗号分隔",
      "requires_restart": true
    },
    "INITIAL_GRID": {
      "value": "2.0",
      "type": "trading",
      "data_type": "number",
      "display_name": "初始网格大小",
      "description": "初始网格大小（百分比）",
      "requires_restart": false
    }
    // ... 更多配置
  }
}
```

### 3. 配置导入

**API端点：** `POST /api/configs/import`

**参数：**
- `file`：JSON配置文件
- `overwrite`：是否覆盖已存在的配置（默认：false）
- `create_backup`：是否创建备份（默认：true）

**示例：**
```bash
# 导入配置（不覆盖已存在的）
curl -H "Authorization: Bearer <token>" \
  -F "file=@gridbnb_config_backup.json" \
  http://localhost:8000/api/configs/import

# 导入配置并覆盖已存在的
curl -H "Authorization: Bearer <token>" \
  -F "file=@gridbnb_config_backup.json" \
  "http://localhost:8000/api/configs/import?overwrite=true"
```

**导入结果：**
```json
{
  "message": "配置导入完成",
  "imported": 42,
  "skipped": 3,
  "failed": 0,
  "requires_restart": true,
  "details": [
    {
      "key": "INITIAL_GRID",
      "status": "updated",
      "requires_restart": false
    },
    {
      "key": "SYMBOLS",
      "status": "updated",
      "requires_restart": true
    }
    // ... 详细信息
  ]
}
```

### 4. 重新加载配置

**API端点：** `POST /api/configs/reload`

在修改配置后，调用此接口可以立即应用更改（无需重启系统）：

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/configs/reload
```

**注意：**
- ✅ 标记为 `requires_restart=false` 的配置会立即生效
- ⚠️ 标记为 `requires_restart=true` 的配置仍需重启系统才能生效

---

## 📌 配置项说明

### 哪些配置需要重启？

| 配置项 | 需要重启 | 原因 |
|--------|----------|------|
| EXCHANGE | ✅ 是 | 交易所客户端初始化 |
| TESTNET_MODE | ✅ 是 | 测试网/实盘切换 |
| SYMBOLS | ✅ 是 | 交易对初始化 |
| AI_ENABLED | ✅ 是 | AI模块初始化 |
| INITIAL_GRID | ❌ 否 | 动态网格参数 |
| MIN_TRADE_AMOUNT | ❌ 否 | 交易金额限制 |
| ENABLE_STOP_LOSS | ❌ 否 | 风控开关 |
| TREND_DETECTION | ❌ 否 | 趋势识别开关 |

### 敏感配置

以下配置被标记为敏感，在Web界面中默认隐藏：

- `TELEGRAM_BOT_TOKEN`
- `PUSHPLUS_TOKEN`
- `WEBHOOK_URL`

**注意：**
- API密钥（BINANCE_API_KEY等）不存储在数据库中，仅从.env读取
- 敏感配置导出时默认不包含，需明确设置 `include_sensitive=true`

---

## 🔄 从旧版本迁移

如果您从旧版本（v3.1.x或更早）升级，请按以下步骤操作：

### 迁移步骤

1. **备份现有.env文件**
   ```bash
   cp .env .env.backup
   ```

2. **初始化数据库**
   ```bash
   python scripts/init_database.py
   ```

3. **保留API密钥在.env中**

   编辑 `.env`，只保留以下配置：
   ```env
   # API密钥（必须保留）
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   OKX_API_KEY=...
   OKX_API_SECRET=...
   OKX_PASSPHRASE=...

   # Web认证（可选，如果需要）
   WEB_USER=admin
   WEB_PASSWORD=your_password
   ```

4. **在Web界面配置其他参数**

   登录Web界面 (`http://localhost:8000`)，在配置管理页面设置：
   - 交易对 (SYMBOLS)
   - 初始网格 (INITIAL_GRID)
   - 风控参数 (MAX_POSITION_RATIO等)
   - 其他策略参数

5. **测试配置**

   启动系统前，建议：
   - 先使用测试网模式 (`TESTNET_MODE=true`)
   - 验证配置是否正确加载
   - 确认策略参数符合预期

---

## 🛠️ 开发者指南

### 在代码中使用ConfigLoader

```python
from src.config.loader import config_loader

# 获取配置值
initial_grid = config_loader.get('INITIAL_GRID')  # 返回: 2.0 (float)
symbols = config_loader.get('SYMBOLS')  # 返回: "BNB/USDT" (str)
enable_stop_loss = config_loader.get('ENABLE_STOP_LOSS')  # 返回: False (bool)

# 获取JSON配置
grid_params = config_loader.get('GRID_PARAMS_JSON')  # 返回: dict

# 获取所有配置
all_configs = config_loader.get_all(include_api_keys=False)

# 重新加载配置
config_loader.reload()
```

### 添加新配置项

1. 在 `src/config/config_definitions.py` 中添加配置定义：
   ```python
   {
       "config_key": "MY_NEW_CONFIG",
       "display_name": "我的新配置",
       "description": "配置说明",
       "config_type": ConfigTypeEnum.TRADING,
       "data_type": "number",
       "default_value": "100",
       "validation_rules": {
           "type": "float",
           "min": 0,
           "max": 1000
       },
       "is_required": False,
       "is_sensitive": False,
       "requires_restart": False,
   }
   ```

2. 重新初始化数据库（或手动在Web界面创建）

3. 在代码中使用：
   ```python
   my_config = config_loader.get('MY_NEW_CONFIG')
   ```

---

## ❓ 常见问题

### Q1: 修改配置后需要重启吗？

**A:** 取决于配置项的 `requires_restart` 字段：
- `requires_restart=false`：调用 `/api/configs/reload` 即可生效
- `requires_restart=true`：需要重启交易系统

### Q2: API密钥如何管理？

**A:** API密钥**不存入数据库**，仅保存在 `.env` 文件中：
- ✅ 更安全（不会通过API泄露）
- ✅ 符合最佳实践
- ✅ 便于生产环境部署

### Q3: 如何备份配置？

**A:** 有两种方式：
1. **Web导出**：访问配置页面，点击"导出配置"
2. **API导出**：`curl http://localhost:8000/api/configs/export -o backup.json`

### Q4: 配置导入失败怎么办？

**A:** 检查以下几点：
1. JSON格式是否正确
2. 配置键是否存在于数据库中
3. 如果是新配置，先在 `config_definitions.py` 中定义

### Q5: 如何查看配置历史？

**A:** 每次修改配置都会自动创建历史记录：
- 访问 `http://localhost:8000/configs/<config_id>/history`
- 可以查看所有历史版本
- 支持版本对比和回滚

---

## 📚 相关文档

- [项目README](../README.md)
- [API文档](http://localhost:8000/docs)
- [配置定义](../src/config/config_definitions.py)
- [FastAPI迁移指南](./FASTAPI_MIGRATION.md)

---

## 🙋 技术支持

如有问题，请提交Issue：https://github.com/your-repo/issues
