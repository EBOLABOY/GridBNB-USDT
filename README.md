# BNB/USDT 自动化网格交易机器人

这是一个基于 Python 的自动化交易程序，专为币安 (Binance) 交易所的 BNB/USDT 交易对设计。该程序采用网格交易策略，旨在通过动态调整网格和仓位来捕捉市场波动，并内置风险管理机制。

## 核心功能

*   **自动化网格交易**: 针对 BNB/USDT 交易对执行网格买卖策略。
*   **动态网格调整**: 根据市场波动率自动调整网格大小 (`config.py` 中的 `GRID_PARAMS`)。
*   **风险管理**:
    *   最大回撤限制 (`MAX_DRAWDOWN`)
    *   每日亏损限制 (`DAILY_LOSS_LIMIT`)
    *   最大仓位比例限制 (`MAX_POSITION_RATIO`)
*   **Web 用户界面**: 提供一个简单的 Web 界面 (通过 `web_server.py`)，用于实时监控交易状态、账户信息、订单和调整配置。
*   **状态持久化**: 将交易状态保存到 `data/` 目录下的 JSON 文件中，以便重启后恢复。
*   **通知推送**: 可通过 PushPlus 发送重要事件和错误通知 (`PUSHPLUS_TOKEN`)。
*   **日志记录**: 详细的运行日志记录在 `trading_system.log` 文件中。

## 环境要求

*   Python 3.8+
*   依赖库见 `requirements.txt` 文件。
*   **最低服务器配置建议**：
    *   CPU：1核及以上（推荐2核）
    *   内存：512MB 及以上（推荐1GB或2GB）
    *   硬盘：500MB 可用空间
    *   操作系统：Windows、Linux 或 macOS
    *   网络：需能访问币安API和PushPlus（如启用通知）
    *   网络建议：建议选择日本等对币安延迟低的网络，避免香港和美国地区。

## 安装步骤

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/EBOLABOY/GridBNB-USDT
    cd GridBNB-USDT
    ```

2.  **创建并激活虚拟环境**:
    *   **Windows**:
        ```bash
        python -m venv .venv
        .\.venv\Scripts\activate
        ```
    *   **Linux / macOS**:
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```

3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

## 配置

1.  **创建 `.env` 文件**:
    在项目根目录下创建一个名为 `.env` 的文件。

2.  **配置环境变量**:
    在 `.env` 文件中添加以下必要的环境变量，并填入你的信息：
    ```dotenv
    # 币安 API (必须)
    BINANCE_API_KEY=YOUR_BINANCE_API_KEY
    BINANCE_API_SECRET=YOUR_BINANCE_API_SECRET

    # PushPlus Token (可选, 用于消息推送)
    PUSHPLUS_TOKEN=YOUR_PUSHPLUS_TOKEN

    # 初始设置 (可选, 影响首次运行和统计)
    # 如不设置，INITIAL_PRINCIPAL 和 INITIAL_BASE_PRICE 默认为 0
    INITIAL_PRINCIPAL=1000.0  # 你的初始总资产 (USDT)
    INITIAL_BASE_PRICE=600.0   # 你认为合适的初始基准价格 (用于首次启动确定方向)
    
    # 如果需要使用代理的话开启本配置，指向代理服务器端口，本地调测使用，实盘建议部署服务器上
    # HTTP_PROXY =  http://127.0.0.1:XXXXX
    ```
    *   **重要**: 确保你的币安 API Key 具有现货交易权限，但**不要**开启提现权限。

3.  **调整交易参数 (可选)**:
    你可以根据自己的策略需求修改 `config.py` 文件中的参数，例如：
    *   `SYMBOL`: 交易对 (默认为 'BNB/USDT')
    *   `INITIAL_GRID`: 初始网格大小 (%)
    *   `MIN_TRADE_AMOUNT`: 最小交易金额 (USDT)
    *   `MAX_POSITION_RATIO`, `MIN_POSITION_RATIO`: 最大/最小仓位比例
    *   风险参数 (`MAX_DRAWDOWN`, `DAILY_LOSS_LIMIT`)
    *   波动率与网格对应关系 (`GRID_PARAMS['volatility_threshold']`)

## 运行

在激活虚拟环境的项目根目录下运行主程序：

```bash
python main.py
```

程序启动后将开始连接交易所、初始化状态并执行交易逻辑。


## docker部署

部署前请先根据上文说明配置好 .env 文件的环境变量。

```bash
# 拉取代码
#（如已在上方步骤完成可跳过）
git clone https://github.com/EBOLABOY/GridBNB-USDT
cd GridBNB-USDT
# 部署镜像
docker-compose up -d
```

*如需自定义端口，请修改 docker-compose.yml 中的端口映射。*

## Web 界面

程序启动后，会自动运行一个 Web 服务器。你可以通过浏览器访问以下地址来监控和管理交易机器人：

`http://127.0.0.1:58080`

*注意: 端口号 (8080) 可能在 `web_server.py` 中定义，如果无法访问请检查该文件。*

Web 界面可以让你查看当前状态、账户余额、持仓、挂单、历史记录，并可能提供一些手动操作或配置调整的功能。

## 日志

程序的运行日志会输出到控制台，并同时记录在项目根目录下的 `trading_system.log` 文件中。

## 注意事项

*   **交易风险**: 所有交易决策均由程序自动执行，但市场存在固有风险。请务必了解策略原理和潜在风险，并自行承担交易结果。不建议在未充分理解和测试的情况下投入大量资金。
*   **API Key 安全**: 妥善保管你的 API Key 和 Secret，不要泄露给他人。
*   **配置合理性**: 确保 `config.py` 和 `.env` 中的配置符合你的预期和风险承受能力。

## 贡献

欢迎提交 Pull Requests 或 Issues 来改进项目。
