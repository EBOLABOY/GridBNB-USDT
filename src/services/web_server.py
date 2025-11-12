from aiohttp import web
import os
from src.utils.helpers import LogConfig
import aiofiles
import logging
from datetime import datetime
import psutil
import time
import base64
from functools import wraps
from src.config.settings import settings
import src

# 导入Prometheus指标
try:
    from src.monitoring.metrics import get_metrics
    from prometheus_client import CONTENT_TYPE_LATEST
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logging.warning("Prometheus客户端未安装,/metrics端点将不可用")

AIO_PROMETHEUS_CONTENT_TYPE = 'text/plain; version=0.0.4'

def auth_required(func):
    """基础认证装饰器"""
    @wraps(func)
    async def wrapper(request):
        # 如果没有设置认证信息，则跳过认证
        if not settings.WEB_USER or not settings.WEB_PASSWORD:
            return await func(request)

        auth_header = request.headers.get('Authorization')

        if auth_header is None:
            return web.Response(
                status=401,
                headers={'WWW-Authenticate': 'Basic realm="GridBNB Trading Bot"'},
                text="需要认证"
            )

        try:
            auth_type, auth_token = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                raise ValueError("只支持Basic认证")

            decoded_token = base64.b64decode(auth_token).decode('utf-8')
            user, password = decoded_token.split(':', 1)

            if user == settings.WEB_USER and password == settings.WEB_PASSWORD:
                return await func(request)
        except Exception as e:
            logging.warning(f"认证失败: {e}")

        return web.Response(
            status=401,
            headers={'WWW-Authenticate': 'Basic realm="GridBNB Trading Bot"'},
            text="认证失败"
        )

    return wrapper

class IPLogger:
    def __init__(self):
        self.ip_records = []  # 存储IP访问记录
        self.max_records = 100  # 最多保存100条记录
        self._log_cache = {'content': None, 'timestamp': 0}  # 添加日志缓存
        self._cache_ttl = 2  # 缓存有效期（秒）

    def add_record(self, ip, path):
        # 查找是否存在相同IP的记录
        for record in self.ip_records:
            if record['ip'] == ip:
                # 如果找到相同IP，只更新时间
                record['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                record['path'] = path  # 更新访问路径
                return
        
        # 如果是新IP，添加新记录
        record = {
            'ip': ip,
            'path': path,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.ip_records.append(record)
        
        # 如果超出最大记录数，删除最早的记录
        if len(self.ip_records) > self.max_records:
            self.ip_records.pop(0)

    def get_records(self):
        return self.ip_records

def get_system_stats():
    """获取系统资源使用情况"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_used = memory.used / (1024 * 1024 * 1024)  # 转换为GB
    memory_total = memory.total / (1024 * 1024 * 1024)
    return {
        'cpu_percent': cpu_percent,
        'memory_used': round(memory_used, 2),
        'memory_total': round(memory_total, 2),
        'memory_percent': memory.percent
    }

async def _read_log_content():
    """公共的日志读取函数"""
    log_path = os.path.join(LogConfig.LOG_DIR, 'trading_system.log')
    if not os.path.exists(log_path):
        return None
        
    async with aiofiles.open(log_path, mode='r', encoding='utf-8') as f:
        content = await f.read()
        
    # 将日志按行分割并倒序排列
    lines = content.strip().split('\n')
    lines.reverse()
    return '\n'.join(lines)

@auth_required
async def handle_log(request):
    try:
        # 记录IP访问
        ip = request.remote
        request.app['ip_logger'].add_record(ip, request.path)

        # 获取系统资源状态
        system_stats = get_system_stats()

        # 获取交易对列表，用于生成下拉菜单
        traders_dict = request.app['traders']
        symbols_list = list(traders_dict.keys())

        # 读取日志内容
        content = await _read_log_content()
        if content is None:
            return web.Response(text="日志文件不存在", status=404)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>多币种网格交易监控</title>
            <meta charset="utf-8">
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
            <style>
                .grid-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 1rem;
                    padding: 1rem;
                }}
                .card {{
                    background: white;
                    border-radius: 0.5rem;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    padding: 1rem;
                }}
                .status-value {{
                    font-size: 1.5rem;
                    font-weight: bold;
                    color: #2563eb;
                }}
                .profit {{ color: #10b981; }}
                .loss {{ color: #ef4444; }}
                .log-container {{
                    height: calc(100vh - 400px);
                    overflow-y: auto;
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 1rem;
                    border-radius: 0.5rem;
                }}
            </style>
        </head>
        <body class="bg-gray-100">
            <div class="container mx-auto px-4 py-8">
                <div class="flex justify-center items-center mb-8">
                    <h1 class="text-3xl font-bold text-gray-800">多币种网格交易监控</h1>
                    <!-- 新增交易对选择器 -->
                    <select id="symbol-selector" class="ml-4 p-2 border rounded-md bg-white">
                        <option value="">选择交易对...</option>
                    </select>
                </div>

                <!-- AI决策分析卡片 -->
                <div class="card mb-8" id="ai-decision-card" style="display: none;">
                    <h2 class="text-lg font-semibold mb-4">🤖 AI 决策分析 <span class="text-sm text-gray-500" id="ai-timestamp">--</span></h2>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <!-- AI建议 -->
                        <div class="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg">
                            <div class="text-sm font-semibold text-gray-700 mb-2">💡 AI建议</div>
                            <div class="text-2xl font-bold mb-1" id="ai-action">--</div>
                            <div class="flex justify-between text-sm">
                                <span class="text-gray-600">置信度:</span>
                                <span class="font-semibold" id="ai-confidence">--</span>
                            </div>
                            <div class="flex justify-between text-sm">
                                <span class="text-gray-600">风险等级:</span>
                                <span class="font-semibold" id="ai-risk-level">--</span>
                            </div>
                            <div class="mt-2 text-sm text-gray-700 italic" id="ai-reason">--</div>
                        </div>

                        <!-- 多时间周期 -->
                        <div class="p-4 bg-gradient-to-r from-green-50 to-teal-50 rounded-lg">
                            <div class="text-sm font-semibold text-gray-700 mb-2">📊 多时间周期</div>
                            <div class="space-y-1 text-sm">
                                <div class="flex justify-between">
                                    <span>日线趋势:</span>
                                    <span class="font-semibold" id="ai-daily-trend">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>4小时趋势:</span>
                                    <span class="font-semibold" id="ai-4h-trend">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>1小时趋势:</span>
                                    <span class="font-semibold" id="ai-1h-trend">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>趋势一致性:</span>
                                    <span class="font-semibold" id="ai-alignment">--</span>
                                </div>
                            </div>
                        </div>

                        <!-- BTC相关性 -->
                        <div class="p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg">
                            <div class="text-sm font-semibold text-gray-700 mb-2">₿ BTC相关性</div>
                            <div class="space-y-1 text-sm">
                                <div class="flex justify-between">
                                    <span>关联强度:</span>
                                    <span class="font-semibold" id="ai-btc-strength">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>关联系数:</span>
                                    <span class="font-semibold" id="ai-btc-corr">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>BTC趋势:</span>
                                    <span class="font-semibold" id="ai-btc-trend">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>BTC 24h变化:</span>
                                    <span class="font-semibold" id="ai-btc-change">--</span>
                                </div>
                            </div>
                        </div>

                        <!-- 订单簿 & 衍生品 -->
                        <div class="p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg">
                            <div class="text-sm font-semibold text-gray-700 mb-2">📖 市场深度 & 衍生品</div>
                            <div class="space-y-1 text-sm">
                                <div class="flex justify-between">
                                    <span>流动性信号:</span>
                                    <span class="font-semibold" id="ai-liquidity">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>买卖压力:</span>
                                    <span class="font-semibold" id="ai-imbalance">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>资金费率:</span>
                                    <span class="font-semibold" id="ai-funding">--</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>持仓量变化:</span>
                                    <span class="font-semibold" id="ai-oi-change">--</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 状态卡片 -->
                <div class="grid-container mb-8">
                    <div class="card">
                        <h2 class="text-lg font-semibold mb-4">基本信息 & S1</h2>
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span>交易对</span>
                                <span class="status-value" id="symbol-display">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span>基准价格</span>
                                <span class="status-value" id="base-price">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span id="current-price-label">当前价格</span>
                                <span class="status-value" id="current-price">--</span>
                            </div>
                            <div class="flex justify-between pt-2 border-t mt-2">
                                <span>52日最高价 (S1)</span>
                                <span class="status-value" id="s1-high">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span>52日最低价 (S1)</span>
                                <span class="status-value" id="s1-low">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span>当前仓位 (%)</span>
                                <span class="status-value" id="position-percentage">--</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2 class="text-lg font-semibold mb-4">网格参数</h2>
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span>网格大小</span>
                                <span class="status-value" id="grid-size">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span>当前上轨 (USDT)</span>
                                <span class="status-value" id="grid-upper-band">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span>当前下轨 (USDT)</span>
                                <span class="status-value" id="grid-lower-band">--</span>
                            </div>    
                            <div class="flex justify-between">
                                <span>触发阈值</span>
                                <span class="status-value" id="threshold">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span>目标委托金额</span>
                                <span class="status-value" id="target-order-amount">--</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2 class="text-lg font-semibold mb-4">资金状况</h2>
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span id="total-assets-label">总资产</span>
                                <span class="status-value" id="total-assets">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span id="quote-balance-label">计价货币余额</span>
                                <span class="status-value" id="quote-balance">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span id="base-balance-label">基础货币余额</span>
                                <span class="status-value" id="base-balance">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span id="total-profit-label">总盈亏</span>
                                <span class="status-value" id="total-profit">--</span>
                            </div>
                            <div class="flex justify-between">
                                <span>盈亏率(%)</span>
                                <span class="status-value" id="profit-rate">--</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 系统资源监控 -->
                <div class="card mb-8">
                    <h2 class="text-lg font-semibold mb-4">系统资源</h2>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="p-4 bg-gray-50 rounded-lg">
                            <div class="text-sm text-gray-600">CPU使用率</div>
                            <div class="text-2xl font-bold mt-1">{system_stats['cpu_percent']}%</div>
                        </div>
                        <div class="p-4 bg-gray-50 rounded-lg">
                            <div class="text-sm text-gray-600">内存使用</div>
                            <div class="text-2xl font-bold mt-1">{system_stats['memory_percent']}%</div>
                            <div class="text-sm text-gray-500">
                                {system_stats['memory_used']}GB / {system_stats['memory_total']}GB
                            </div>
                        </div>
                        <div class="p-4 bg-gray-50 rounded-lg col-span-2">
                            <div class="text-sm text-gray-600">系统运行时间</div>
                            <div class="text-xl font-bold mt-1" id="system-uptime">--</div>
                        </div>
                    </div>
                </div>

                <!-- 最近交易记录 -->
                <div class="card mt-4 mb-8">
                    <h2 class="text-lg font-semibold mb-4">最近交易</h2>
                    <div class="overflow-x-auto">
                        <table class="min-w-full">
                            <thead>
                                <tr class="border-b">
                                    <th class="text-left py-2">时间</th>
                                    <th class="text-left py-2">方向</th>
                                    <th class="text-left py-2">价格</th>
                                    <th class="text-left py-2">数量</th>
                                    <th class="text-left py-2">金额(USDT)</th>
                                </tr>
                            </thead>
                            <tbody id="trade-history">
                                <!-- 交易记录将通过JavaScript动态插入 -->
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- IP访问记录 -->
                <div class="card mb-8">
                    <h2 class="text-lg font-semibold mb-4">访问记录</h2>
                    <div class="overflow-x-auto">
                        <table class="min-w-full">
                            <thead>
                                <tr class="bg-gray-50">
                                    <th class="px-6 py-3 text-left">时间</th>
                                    <th class="px-6 py-3 text-left">IP地址</th>
                                    <th class="px-6 py-3 text-left">访问路径</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f'''
                                <tr class="border-b">
                                    <td class="px-6 py-4">{record["time"]}</td>
                                    <td class="px-6 py-4">{record["ip"]}</td>
                                    <td class="px-6 py-4">{record["path"]}</td>
                                </tr>
                                ''' for record in list(reversed(request.app['ip_logger'].get_records()))[:5]])}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 系统日志 -->
                <div class="card">
                    <h2 class="text-lg font-semibold mb-4">系统日志</h2>
                    <div class="log-container" id="log-content">
                        <pre>{content}</pre>
                    </div>
                </div>
            </div>

            <script>
                const symbolSelector = document.getElementById('symbol-selector');
                let currentSymbol = '';

                // 动态更新页面标题
                function updatePageTitle(symbol) {{
                    document.title = `监控 - ${{symbol}}`;
                }}

                // 更新AI决策数据
                async function updateAIDecision() {{
                    if (!currentSymbol) return;
                    try {{
                        const response = await fetch(`/api/ai-decision?symbol=${{currentSymbol}}`);
                        const data = await response.json();

                        if (data.error || !data.ai_enabled) {{
                            document.getElementById('ai-decision-card').style.display = 'none';
                            return;
                        }}

                        if (!data.has_decision) {{
                            document.getElementById('ai-decision-card').style.display = 'none';
                            return;
                        }}

                        // 显示AI决策卡片
                        document.getElementById('ai-decision-card').style.display = 'block';

                        // 更新时间戳
                        const timestamp = new Date(data.timestamp * 1000);
                        const now = new Date();
                        const minutesAgo = Math.floor((now - timestamp) / 60000);
                        document.getElementById('ai-timestamp').textContent = `(${{minutesAgo}}分钟前)`;

                        // 更新AI建议
                        const suggestion = data.suggestion;
                        const actionEl = document.getElementById('ai-action');
                        actionEl.textContent = suggestion.action === 'buy' ? '🔵 买入' :
                                                suggestion.action === 'sell' ? '🔴 卖出' : '⚪ 持有';
                        actionEl.style.color = suggestion.action === 'buy' ? '#10b981' :
                                                suggestion.action === 'sell' ? '#ef4444' : '#6b7280';

                        document.getElementById('ai-confidence').textContent = `${{(suggestion.confidence * 100).toFixed(0)}}%`;
                        document.getElementById('ai-risk-level').textContent = suggestion.risk_level || '--';
                        document.getElementById('ai-reason').textContent = suggestion.reason || '--';

                        // 更新多时间周期
                        const mtf = data.multi_timeframe;
                        document.getElementById('ai-daily-trend').textContent = mtf.daily_trend || '--';
                        document.getElementById('ai-4h-trend').textContent = mtf['4h_trend'] || '--';
                        document.getElementById('ai-1h-trend').textContent = mtf['1h_trend'] || '--';
                        document.getElementById('ai-alignment').textContent = mtf.alignment || '--';

                        // 更新BTC相关性
                        const btc = data.btc_correlation;
                        document.getElementById('ai-btc-strength').textContent = btc.strength || '--';
                        document.getElementById('ai-btc-corr').textContent = btc.coefficient ? btc.coefficient.toFixed(2) : '--';
                        document.getElementById('ai-btc-trend').textContent = btc.btc_trend || '--';
                        const btcChangeEl = document.getElementById('ai-btc-change');
                        const btcChange = btc.btc_change || 0;
                        btcChangeEl.textContent = `${{btcChange >= 0 ? '+' : ''}}${{btcChange.toFixed(2)}}%`;
                        btcChangeEl.style.color = btcChange >= 0 ? '#10b981' : '#ef4444';

                        // 更新订单簿和衍生品
                        const ob = data.orderbook;
                        const deriv = data.derivatives;
                        document.getElementById('ai-liquidity').textContent = ob.liquidity_signal || '--';

                        const imbalanceEl = document.getElementById('ai-imbalance');
                        const imbalance = ob.imbalance || 0;
                        imbalanceEl.textContent = imbalance > 0 ? '买方优势' : imbalance < 0 ? '卖方优势' : '均衡';
                        imbalanceEl.style.color = imbalance > 0 ? '#10b981' : imbalance < 0 ? '#ef4444' : '#6b7280';

                        document.getElementById('ai-funding').textContent = deriv.funding_rate || '--';
                        document.getElementById('ai-oi-change').textContent = deriv.oi_change || '--';

                        console.log('AI决策数据更新成功');
                    }} catch (error) {{
                        console.error('更新AI决策数据失败:', error);
                        document.getElementById('ai-decision-card').style.display = 'none';
                    }}
                }}

                // 更新整个页面的状态
                async function updateStatus() {{
                    if (!currentSymbol) return;
                    try {{
                        const response = await fetch(`/api/status?symbol=${{currentSymbol}}`);
                        const data = await response.json();

                        if (data.error) {{
                            console.error(`获取 ${{currentSymbol}} 状态失败:`, data.error);
                            return;
                        }}

                        // 更新页面标题
                        updatePageTitle(data.symbol || currentSymbol);
                        
                        // 更新基本信息
                        document.querySelector('#symbol-display').textContent = data.symbol || '--';
                        document.querySelector('#base-price').textContent =
                            data.base_price ? data.base_price.toFixed(2) + ' ' + (data.quote_asset || '') : '--';
                        document.querySelector('#current-price-label').textContent =
                            `当前价格 (${{data.quote_asset || ''}})`;
                        document.querySelector('#current-price').textContent =
                            data.current_price ? data.current_price.toFixed(2) : '--';
                        
                        // 更新 S1 信息和仓位
                        document.querySelector('#s1-high').textContent = 
                            data.s1_daily_high ? data.s1_daily_high.toFixed(2) : '--';
                        document.querySelector('#s1-low').textContent = 
                            data.s1_daily_low ? data.s1_daily_low.toFixed(2) : '--';
                        document.querySelector('#position-percentage').textContent = 
                            data.position_percentage != null ? data.position_percentage.toFixed(2) + '%' : '--';
                        
                        // 更新网格参数
                        document.querySelector('#grid-size').textContent = 
                            data.grid_size ? (data.grid_size * 100).toFixed(2) + '%' : '--';
                        document.querySelector('#threshold').textContent = 
                            data.threshold ? (data.threshold * 100).toFixed(2) + '%' : '--';

                        // ---> 新增：更新网格上下轨 <---
                        document.querySelector('#grid-upper-band').textContent =
                            data.grid_upper_band != null ? data.grid_upper_band.toFixed(2) : '--';
                        document.querySelector('#grid-lower-band').textContent =
                            data.grid_lower_band != null ? data.grid_lower_band.toFixed(2) : '--';
                        
                        // 更新资金状况标签和数据
                        document.querySelector('#total-assets-label').textContent =
                            `总资产(${{data.quote_asset || ''}})`;
                        document.querySelector('#total-assets').textContent =
                            data.total_assets ? data.total_assets.toFixed(2) + ' ' + (data.quote_asset || '') : '--';
                        document.querySelector('#quote-balance-label').textContent =
                            `${{data.quote_asset || '计价货币'}}余额`;
                        document.querySelector('#quote-balance').textContent =
                            data.quote_balance != null ? data.quote_balance.toFixed(2) : '--';
                        document.querySelector('#base-balance-label').textContent =
                            `${{data.base_asset || '基础货币'}}余额`;
                        document.querySelector('#base-balance').textContent =
                            data.base_balance != null ? data.base_balance.toFixed(4) : '--';
                        document.querySelector('#total-profit-label').textContent =
                            `总盈亏(${{data.quote_asset || ''}})`;

                        // 更新目标委托金额
                        document.querySelector('#target-order-amount').textContent =
                            data.target_order_amount ? data.target_order_amount.toFixed(2) + ' ' + (data.quote_asset || '') : '--';
                        
                        // 更新盈亏信息
                        const totalProfitElement = document.querySelector('#total-profit');
                        totalProfitElement.textContent = data.total_profit ? data.total_profit.toFixed(2) : '--';
                        totalProfitElement.className = `status-value ${{data.total_profit >= 0 ? 'profit' : 'loss'}}`;

                        const profitRateElement = document.querySelector('#profit-rate');
                        profitRateElement.textContent = data.profit_rate ? data.profit_rate.toFixed(2) + '%' : '--';
                        profitRateElement.className = `status-value ${{data.profit_rate >= 0 ? 'profit' : 'loss'}}`;
                        
                        // 更新交易历史
                        document.querySelector('#trade-history').innerHTML = data.trade_history.map(function(trade) {{ return ` 
                            <tr class="border-b">
                                <td class="py-2">${{trade.timestamp}}</td>
                                <td class="py-2 ${{trade.side === 'buy' ? 'text-green-500' : 'text-red-500'}}">
                                    ${{trade.side === 'buy' ? '买入' : '卖出'}}
                                </td>
                                <td class="py-2">${{parseFloat(trade.price).toFixed(2)}}</td>
                                <td class="py-2">${{parseFloat(trade.amount).toFixed(4)}}</td>
                                <td class="py-2">${{(parseFloat(trade.price) * parseFloat(trade.amount)).toFixed(2)}}</td>
                            </tr>
                        `; }}).join('');
                        

                        
                        // 更新系统运行时间
                        document.querySelector('#system-uptime').textContent = data.uptime;
                        
                        console.log(`状态更新成功: ${{currentSymbol}}`);
                    }} catch (error) {{
                        console.error(`更新 ${{currentSymbol}} 状态失败:`, error);
                    }}
                }}

                // 初始化函数
                async function initialize() {{
                    try {{
                        const response = await fetch('/api/symbols');
                        const data = await response.json();
                        const symbols = data.symbols || [];

                        if (symbols.length > 0) {{
                            // 填充下拉菜单
                            symbols.forEach(symbol => {{
                                const option = document.createElement('option');
                                option.value = symbol;
                                option.textContent = symbol;
                                symbolSelector.appendChild(option);
                            }});

                            // 设置初始选中的交易对
                            currentSymbol = symbols[0];
                            symbolSelector.value = currentSymbol;

                            // 首次加载数据
                            updateStatus();
                            updateAIDecision();

                            // 启动定时更新
                            setInterval(updateStatus, 5000); // 5秒更新一次
                            setInterval(updateAIDecision, 30000); // 30秒更新一次AI决策
                        }} else {{
                            document.body.innerHTML = '<h1 class="text-center text-2xl mt-12">没有正在运行的交易对。</h1>';
                        }}
                    }} catch(e) {{
                         console.error("初始化失败:", e);
                         document.body.innerHTML = '<h1 class="text-center text-2xl mt-12">无法连接到监控服务。</h1>';
                    }}
                }}

                // 监听下拉菜单的变化事件
                symbolSelector.addEventListener('change', (event) => {{
                    currentSymbol = event.target.value;
                    updateStatus(); // 立即更新
                    updateAIDecision(); // 立即更新AI决策
                }});

                // 页面加载时执行初始化
                document.addEventListener('DOMContentLoaded', initialize);
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    except Exception as e:
        return web.Response(text=f"Error: {str(e)}", status=500)

@auth_required
async def handle_status(request):
    """处理状态API请求"""
    try:
        traders = request.app['traders']

        # 从查询参数获取交易对，默认使用第一个
        symbol = request.query.get('symbol')
        if not symbol or symbol not in traders:
            symbol = list(traders.keys())[0]  # 默认使用第一个交易对

        trader = traders[symbol]
        # S1策略已移除: s1_controller = trader.position_controller_s1

        # 获取交易所数据
        balance = await trader.exchange.fetch_balance()
        current_price = await trader._get_latest_price() or 0 # 提供默认值以防失败

        # 获取理财账户余额
        funding_balance = await trader.exchange.fetch_funding_balance()
        
        # 获取网格参数
        grid_size = trader.grid_size
        grid_size_decimal = grid_size / 100 if grid_size else 0
        threshold = grid_size_decimal / 5
        
        # ---> 新增：计算网格上下轨 <---
        # 确保 trader.base_price 和 trader.grid_size 是有效的
        upper_band = None
        lower_band = None
        if trader.base_price is not None and trader.grid_size is not None:
             try:
                 # 调用 trader.py 中已有的方法
                 upper_band = trader._get_upper_band()
                 lower_band = trader._get_lower_band()
             except Exception as band_e:
                 logging.warning(f"计算网格上下轨失败: {band_e}")
        
        # 计算系统运行时间
        current_time = time.time()
        uptime_seconds = int(current_time - trader.start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"
        
        # 【双轨制资产计算 - 第一轨：全局报告】
        # 使用全局方法获取真正的账户总资产（包括所有币种），用于准确的盈亏报告
        global_total_assets = await trader.exchange.calculate_total_account_value()

        # 使用动态资产名称计算余额
        base_asset = trader.base_asset
        quote_asset = trader.quote_asset

        # 合并计算用于显示的各项余额
        spot_quote = float(balance.get('total', {}).get(quote_asset, 0))
        funding_quote = float(funding_balance.get(quote_asset, 0))
        display_quote_balance = spot_quote + funding_quote

        spot_base = float(balance.get('total', {}).get(base_asset, 0))
        funding_base = float(funding_balance.get(base_asset, 0))
        display_base_balance = spot_base + funding_base

        # 计算全局总盈亏和盈亏率（基于全账户资产）
        initial_principal = settings.INITIAL_PRINCIPAL
        total_profit = 0.0
        profit_rate = 0.0
        if initial_principal > 0:
            total_profit = global_total_assets - initial_principal
            profit_rate = (total_profit / initial_principal) * 100
        else:
            logging.warning("初始本金未设置或为0，无法计算盈亏率")
        
        # 获取最近交易信息
        last_trade_price = trader.last_trade_price
        last_trade_time = trader.last_trade_time
        last_trade_time_str = datetime.fromtimestamp(last_trade_time).strftime('%Y-%m-%d %H:%M:%S') if last_trade_time else '--'
        
        # 获取交易历史
        trade_history = []
        if hasattr(trader, 'order_tracker'):
            trades = trader.order_tracker.get_trade_history()
            trade_history = [{
                'timestamp': datetime.fromtimestamp(trade['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                'side': trade.get('side', '--'),
                'price': trade.get('price', 0),
                'amount': trade.get('amount', 0),
                'profit': trade.get('profit', 0)
            } for trade in trades[-10:]]  # 只取最近10笔交易
        
        # 【双轨制资产计算 - 第二轨：交易决策】
        # 计算目标委托金额 (交易对相关资产的10%)，这里会调用 _get_pair_specific_assets_value 方法
        # 确保交易决策只基于交易对相关资产，实现风险隔离
        target_order_amount = await trader._calculate_order_amount('buy') # buy/sell 结果一样
        
        # 获取账户快照用于仓位计算
        spot_balance = await trader.exchange.fetch_balance()
        funding_balance = await trader.exchange.fetch_funding_balance()

        # 获取仓位百分比 - 使用风控管理器的方法获取最准确的仓位比例
        position_ratio = await trader.risk_manager._get_position_ratio(spot_balance, funding_balance)
        position_percentage = position_ratio * 100

        # S1策略已移除: s1_high / s1_low 不再获取
        s1_high = None
        s1_low = None

        # 构建响应数据
        status = {
            "symbol": trader.symbol,  # 新增：交易对信息
            "base_asset": base_asset,  # 新增：基础货币名称
            "quote_asset": quote_asset,  # 新增：计价货币名称
            "base_price": trader.base_price,
            "current_price": current_price,
            "grid_size": grid_size_decimal,
            "threshold": threshold,
            "total_assets": global_total_assets,  # 使用全局总资产用于报告
            "quote_balance": display_quote_balance,  # 使用动态计价货币余额
            "base_balance": display_base_balance,    # 使用动态基础货币余额
            "target_order_amount": target_order_amount,
            "trade_history": trade_history or [],
            "last_trade_price": last_trade_price,
            "last_trade_time": last_trade_time,
            "last_trade_time_str": last_trade_time_str,
            "total_profit": total_profit,
            "profit_rate": profit_rate,
            "s1_daily_high": s1_high,
            "s1_daily_low": s1_low,
            "position_percentage": position_percentage,
            "grid_upper_band": upper_band,
            "grid_lower_band": lower_band,
            "uptime": uptime_str,
            "uptime_seconds": uptime_seconds
        }
        
        return web.json_response(status)
    except Exception as e:
        logging.error(f"获取状态数据失败: {str(e)}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)

@auth_required
async def handle_symbols(request):
    """获取所有可用的交易对"""
    try:
        traders = request.app['traders']
        symbols = list(traders.keys())
        return web.json_response({"symbols": symbols})
    except Exception as e:
        logging.error(f"获取交易对列表失败: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)


@auth_required
async def handle_ai_decision(request):
    """
    🆕 获取AI决策数据（用于Web UI可视化）

    返回最新的AI决策详情，包括多维度市场数据和AI建议
    """
    try:
        traders = request.app['traders']

        # 从查询参数获取交易对
        symbol = request.query.get('symbol')

        if not symbol:
            # 默认使用第一个交易对
            symbol = list(traders.keys())[0] if traders else None

        if not symbol or symbol not in traders:
            return web.json_response({
                "error": "Invalid symbol or no traders available"
            }, status=404)

        trader = traders[symbol]

        # 检查trader是否启用了AI策略
        if not hasattr(trader, 'ai_strategy') or trader.ai_strategy is None:
            return web.json_response({
                "ai_enabled": False,
                "message": "AI策略未启用"
            })

        # 获取最新的AI决策数据
        ai_strategy = trader.ai_strategy
        last_decision = getattr(ai_strategy, 'last_ai_decision', None)

        if not last_decision:
            return web.json_response({
                "ai_enabled": True,
                "has_decision": False,
                "message": "暂无AI决策数据"
            })

        # 提取关键数据用于展示
        suggestion = last_decision.get("suggestion", {})
        market_data = last_decision.get("market_data", {})
        orderbook = last_decision.get("orderbook", {})
        derivatives = last_decision.get("derivatives", {})
        correlation = last_decision.get("correlation", {})

        # 构建简化的展示数据
        response = {
            "ai_enabled": True,
            "has_decision": True,
            "timestamp": last_decision.get("timestamp"),
            "suggestion": {
                "action": suggestion.get("action"),
                "confidence": suggestion.get("confidence"),
                "reason": suggestion.get("reason"),
                "risk_level": suggestion.get("risk_level")
            },
            "multi_timeframe": {
                "alignment": market_data.get("alignment", "unknown"),
                "daily_trend": market_data.get("macro_daily", {}).get("trend", "unknown"),
                "4h_trend": market_data.get("medium_4h", {}).get("trend", "unknown"),
                "1h_trend": market_data.get("micro_1h", {}).get("trend", "unknown"),
                "overall_strength": market_data.get("overall_strength", 0),
                "recommendation": market_data.get("trading_recommendation", "")
            },
            "orderbook": {
                "liquidity_signal": orderbook.get("liquidity_signal", "unknown"),
                "imbalance": orderbook.get("imbalance", 0),
                "spread_percent": orderbook.get("spread_percent", 0),
                "resistance_walls_count": len(orderbook.get("resistance_walls", [])),
                "support_walls_count": len(orderbook.get("support_walls", [])),
                "insight": orderbook.get("trading_insight", "")
            },
            "derivatives": {
                "funding_rate": derivatives.get("funding_rate", {}).get("current_rate_display", "N/A"),
                "funding_sentiment": derivatives.get("funding_rate", {}).get("sentiment", "unknown"),
                "oi_change": derivatives.get("open_interest", {}).get("24h_change_display", "N/A"),
                "oi_signal": derivatives.get("open_interest", {}).get("signal", "unknown")
            },
            "btc_correlation": {
                "coefficient": correlation.get("correlation_coefficient", 0),
                "strength": correlation.get("correlation_strength", "unknown"),
                "btc_trend": correlation.get("btc_current_state", {}).get("short_term_trend", "unknown"),
                "btc_change": correlation.get("btc_current_state", {}).get("24h_change", 0),
                "warning": correlation.get("risk_warning"),
                "insight": correlation.get("trading_insight", "")
            }
        }

        return web.json_response(response)

    except Exception as e:
        logging.error(f"获取AI决策数据失败: {str(e)}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)


async def handle_metrics(request):
    """Prometheus指标端点(无需认证)"""
    if not METRICS_AVAILABLE:
        return web.Response(
            text="Prometheus metrics not available. Install prometheus-client package.",
            status=503
        )

    try:
        # 获取指标实例
        metrics = get_metrics()

        # 更新当前trader数据到指标
        traders = request.app.get('traders', {})
        for symbol, trader in traders.items():
            try:
                # 更新网格参数
                if hasattr(trader, 'base_price') and hasattr(trader, 'grid_size'):
                    current_price = getattr(trader, 'last_trade_price', None) or trader.base_price
                    upper = trader.base_price * (1 + trader.grid_size)
                    lower = trader.base_price * (1 - trader.grid_size)

                    metrics.update_grid_params(
                        symbol=symbol,
                        grid_size=trader.grid_size,
                        base_price=trader.base_price,
                        current_price=current_price,
                        upper_band=upper,
                        lower_band=lower
                    )

                # 更新收益
                if hasattr(trader, 'total_profit'):
                    metrics.update_profit(
                        symbol=symbol,
                        total_profit=trader.total_profit
                    )

            except Exception as e:
                logging.error(f"更新{symbol}指标失败: {e}")

        # 生成Prometheus格式的指标
        metrics_data = metrics.get_metrics()

        return web.Response(
            body=metrics_data,
            content_type=AIO_PROMETHEUS_CONTENT_TYPE
        )

    except Exception as e:
        logging.error(f"获取Prometheus指标失败: {str(e)}", exc_info=True)
        return web.Response(text=f"Error: {str(e)}", status=500)

async def start_web_server(traders):
    app = web.Application()
    # 添加中间件处理无效请求
    @web.middleware
    async def error_middleware(request, handler):
        try:
            return await handler(request)
        except web.HTTPException as ex:
            return web.json_response(
                {"error": str(ex)},
                status=ex.status,
                headers={'Access-Control-Allow-Origin': '*'}
            )
        except Exception as e:
            return web.json_response(
                {"error": "Internal Server Error"},
                status=500,
                headers={'Access-Control-Allow-Origin': '*'}
            )
    
    app.middlewares.append(error_middleware)
    app['traders'] = traders  # 存储所有trader实例
    app['ip_logger'] = IPLogger()
    
    # 禁用访问日志
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

    home_prefix = os.getenv('HOME_PREFIX', '')

    app.router.add_get('/' + home_prefix, handle_log)
    app.router.add_get('/api/logs', handle_log_content)
    app.router.add_get('/api/status', handle_status)
    app.router.add_get('/api/symbols', handle_symbols)
    app.router.add_get('/api/ai-decision', handle_ai_decision)  # 🆕 AI决策API
    app.router.add_get('/health', handle_health)  # 健康检查端点（无需认证）
    app.router.add_get('/api/health', handle_health)  # 备用路径
    app.router.add_get('/version', handle_version)  # 版本信息端点（无需认证）
    app.router.add_get('/api/version', handle_version)  # 备用路径
    app.router.add_get('/metrics', handle_metrics)  # Prometheus指标端点（无需认证）
    app.router.add_get('/api/metrics', handle_metrics)  # 备用路径
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 58181)
    await site.start()

    # 打印访问地址
    local_ip = "localhost"  # 或者使用实际IP
    logging.info(f"Web服务已启动:")
    logging.info(f"- 本地访问: http://{local_ip}:58181/{home_prefix}")
    logging.info(f"- 局域网访问: http://0.0.0.0:58181/{home_prefix}")

@auth_required
async def handle_log_content(request):
    """只返回日志内容的API端点"""
    try:
        content = await _read_log_content()
        if content is None:
            return web.Response(text="", status=404)

        return web.Response(text=content)
    except Exception as e:
        return web.Response(text="", status=500)

async def handle_health(request):
    """
    健康检查端点

    返回系统健康状态，用于监控和负载均衡
    """
    try:
        # 检查系统资源
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # 检查日志文件是否可访问
        log_accessible = os.path.exists(os.path.join(LogConfig.LOG_DIR, 'trading_system.log'))

        # 检查交易器状态
        app = request.app
        traders_healthy = len(app.get('traders', {})) > 0

        checks = {
            'log_file': log_accessible,
            'traders': traders_healthy,
            'cpu_ok': cpu_percent < 90,
            'memory_ok': memory.percent < 90,
            'disk_ok': disk.percent < 90
        }

        healthy = all(checks.values())
        status = 200 if healthy else 503

        return web.json_response({
            'status': 'healthy' if healthy else 'unhealthy',
            'checks': checks,
            'system': {
                'cpu_percent': round(cpu_percent, 2),
                'memory_percent': round(memory.percent, 2),
                'disk_percent': round(disk.percent, 2)
            },
            'timestamp': datetime.now().isoformat()
        }, status=status)
    except Exception as e:
        logging.error(f"健康检查失败: {e}")
        return web.json_response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)

async def handle_version(request):
    """
    版本信息端点

    返回应用程序版本和构建信息
    """
    try:
        # 获取 Git commit (如果可用)
        git_commit = 'unknown'
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                git_commit = result.stdout.strip()
        except:
            pass

        return web.json_response({
            'version': src.__version__,
            'author': src.__author__,
            'license': src.__license__,
            'description': src.__description__,
            'git_commit': git_commit,
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        })
    except Exception as e:
        logging.error(f"获取版本信息失败: {e}")
        return web.json_response({
            'version': 'unknown',
            'error': str(e)
        }, status=500) 
