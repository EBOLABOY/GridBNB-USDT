import ccxt.async_support as ccxt
import os
import logging
from config import SYMBOL, DEBUG_MODE, API_TIMEOUT, RECV_WINDOW
from datetime import datetime
import time
import asyncio

class ExchangeClient:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._verify_credentials()
        
        # 获取代理配置，如果环境变量中没有设置，则使用None
        proxy = os.getenv('HTTP_PROXY')
        
        # 先初始化交易所实例
        self.exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_API_SECRET'),
            'enableRateLimit': True,
            'timeout': 60000,  # 增加超时时间到60秒
            'options': {
                'defaultType': 'spot',
                'fetchMarkets': {
                    'spot': True,     # 启用现货市场
                    'margin': False,  # 明确禁用杠杆
                    'swap': False,   # 禁用合约
                    'future': False  # 禁用期货
                },
                'fetchCurrencies': False,
                'recvWindow': 5000,  # 固定接收窗口
                'adjustForTimeDifference': True,  # 启用时间调整
                'warnOnFetchOpenOrdersWithoutSymbol': False,
                'createMarketBuyOrderRequiresPrice': False
            },
            'aiohttp_proxy': proxy,  # 使用环境变量中的代理配置
            'verbose': DEBUG_MODE
        })
        if proxy:
            self.logger.info(f"使用代理: {proxy}")
        # 然后进行其他配置
        self.logger.setLevel(logging.INFO)
        self.logger.info("交易所客户端初始化完成")

        
        self.markets_loaded = False
        self.time_diff = 0
        self.balance_cache = {'timestamp': 0, 'data': None}
        self.funding_balance_cache = {'timestamp': 0, 'data': {}}
        self.cache_ttl = 30  # 缓存有效期（秒）
    
    def _verify_credentials(self):
        """验证API密钥是否存在"""
        required_env = ['BINANCE_API_KEY', 'BINANCE_API_SECRET']
        missing = [var for var in required_env if not os.getenv(var)]
        if missing:
            error_msg = f"缺少环境变量: {', '.join(missing)}"
            self.logger.critical(error_msg)
            raise EnvironmentError(error_msg)

    async def load_markets(self):
        try:
            # 先同步时间
            await self.sync_time()
            
            # 添加重试机制
            max_retries = 3
            for i in range(max_retries):
                try:
                    await self.exchange.load_markets()
                    self.markets_loaded = True
                    market = self.exchange.market(SYMBOL)
                    self.logger.info(f"市场数据加载成功 | 交易对: {SYMBOL}")
                    return True
                except Exception as e:
                    if i == max_retries - 1:
                        raise
                    self.logger.warning(f"加载市场数据失败，重试 {i+1}/{max_retries}")
                    await asyncio.sleep(2)
            
        except Exception as e:
            self.logger.error(f"加载市场数据失败: {str(e)}")
            self.markets_loaded = False
            raise

    async def fetch_ohlcv(self, symbol, timeframe='1h', limit=None):
        """获取K线数据"""
        try:
            params = {}
            if limit:
                params['limit'] = limit
            return await self.exchange.fetch_ohlcv(symbol, timeframe, params=params)
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {str(e)}")
            raise
    
    async def fetch_ticker(self, symbol):
        self.logger.debug(f"获取行情数据 {symbol}...")
        start = datetime.now()
        try:
            # 使用市场ID进行请求
            market = self.exchange.market(symbol)
            ticker = await self.exchange.fetch_ticker(market['id'])
            latency = (datetime.now() - start).total_seconds()
            self.logger.debug(f"获取行情成功 | 延迟: {latency:.3f}s | 最新价: {ticker['last']}")
            return ticker
        except Exception as e:
            self.logger.error(f"获取行情失败: {str(e)}")
            self.logger.debug(f"请求参数: symbol={symbol}")
            raise
    
    async def fetch_funding_balance(self):
        """获取理财账户余额"""
        now = time.time()
        
        # 如果缓存有效，直接返回缓存数据
        if now - self.funding_balance_cache['timestamp'] < self.cache_ttl:
            return self.funding_balance_cache['data']
        
        try:
            # 使用新的Simple Earn API
            result = await self.exchange.sapi_get_simple_earn_flexible_position()
            self.logger.debug(f"理财账户原始数据: {result}")
            balances = {}
            
            # 处理返回的数据结构
            data = result.get('rows', []) if isinstance(result, dict) else result
            
            for item in data:
                asset = item['asset']
                amount = float(item.get('totalAmount', 0) or item.get('amount', 0))
                balances[asset] = amount
            
            # 只在余额发生显著变化时打印日志
            if not self.funding_balance_cache.get('data'):
                self.logger.info(f"理财账户余额: {balances}")
            else:
                # 检查是否有显著变化（超过0.1%）
                old_balances = self.funding_balance_cache['data']
                significant_change = False
                for asset, amount in balances.items():
                    old_amount = old_balances.get(asset, 0)
                    if old_amount == 0:
                        if amount != 0:
                            significant_change = True
                            break
                    elif abs((amount - old_amount) / old_amount) > 0.001:  # 0.1%的变化
                        significant_change = True
                        break
                
                if significant_change:
                    self.logger.info(f"理财账户余额更新: {balances}")
            
            # 更新缓存
            self.funding_balance_cache = {
                'timestamp': now,
                'data': balances
            }
            
            return balances
        except Exception as e:
            self.logger.error(f"获取理财账户余额失败: {str(e)}")
            return {}

    async def fetch_balance(self, params=None):
        """获取账户余额（含缓存机制）"""
        now = time.time()
        if now - self.balance_cache['timestamp'] < self.cache_ttl:
            return self.balance_cache['data']
        
        try:
            params = params or {}
            params['timestamp'] = int(time.time() * 1000) + self.time_diff
            balance = await self.exchange.fetch_balance(params)
            
            # 获取理财账户余额
            funding_balance = await self.fetch_funding_balance()
            
            # 合并现货和理财余额
            for asset, amount in funding_balance.items():
                if asset not in balance['total']:
                    balance['total'][asset] = 0
                if asset not in balance['free']:
                    balance['free'][asset] = 0
                balance['total'][asset] += amount
            
            self.logger.debug(f"账户余额概要: {balance['total']}")
            self.balance_cache = {'timestamp': now, 'data': balance}
            return balance
        except Exception as e:
            self.logger.error(f"获取余额失败: {str(e)}")
            # 出错时不抛出异常，而是返回一个空的但结构完整的余额字典
            return {'free': {}, 'used': {}, 'total': {}}
    
    async def create_order(self, symbol, type, side, amount, price):
        try:
            # 在下单前重新同步时间
            await self.sync_time()
            # 添加时间戳到请求参数
            params = {
                'timestamp': int(time.time() * 1000 + self.time_diff),
                'recvWindow': 5000
            }
            return await self.exchange.create_order(symbol, type, side, amount, price, params)
        except Exception as e:
            self.logger.error(f"下单失败: {str(e)}")
            raise
    
    async def fetch_order(self, order_id, symbol, params=None):
        if params is None:
            params = {}
        params['timestamp'] = int(time.time() * 1000 + self.time_diff)
        params['recvWindow'] = 5000
        return await self.exchange.fetch_order(order_id, symbol, params)
    
    async def fetch_open_orders(self, symbol):
        """获取当前未成交订单"""
        return await self.exchange.fetch_open_orders(symbol)
    
    async def cancel_order(self, order_id, symbol, params=None):
        """取消指定订单"""
        if params is None:
            params = {}
        params['timestamp'] = int(time.time() * 1000 + self.time_diff)
        params['recvWindow'] = 5000
        return await self.exchange.cancel_order(order_id, symbol, params)
    
    async def close(self):
        """关闭交易所连接"""
        try:
            if self.exchange:
                await self.exchange.close()
                self.logger.info("交易所连接已安全关闭")
        except Exception as e:
            self.logger.error(f"关闭连接时发生错误: {str(e)}")

    async def sync_time(self):
        """同步交易所服务器时间"""
        try:
            server_time = await self.exchange.fetch_time()
            local_time = int(time.time() * 1000)
            self.time_diff = server_time - local_time
            self.logger.info(f"时间同步完成 | 时差: {self.time_diff}ms")
        except Exception as e:
            self.logger.error(f"时间同步失败: {str(e)}")

    async def fetch_order_book(self, symbol, limit=5):
        """获取订单簿数据"""
        try:
            market = self.exchange.market(symbol)
            return await self.exchange.fetch_order_book(market['id'], limit=limit)
        except Exception as e:
            self.logger.error(f"获取订单簿失败: {str(e)}")
            raise

    async def get_flexible_product_id(self, asset):
        """获取指定资产的活期理财产品ID"""
        try:
            params = {
                'asset': asset,
                'timestamp': int(time.time() * 1000 + self.time_diff),
                'current': 1,  # 当前页
                'size': 100,   # 每页数量
            }
            result = await self.exchange.sapi_get_simple_earn_flexible_list(params)
            products = result.get('rows', [])
            
            # 查找对应资产的活期理财产品
            for product in products:
                if product['asset'] == asset and product['status'] == 'PURCHASING':
                    self.logger.info(f"找到{asset}活期理财产品: {product['productId']}")
                    return product['productId']
            
            raise ValueError(f"未找到{asset}的可用活期理财产品")
        except Exception as e:
            self.logger.error(f"获取活期理财产品失败: {str(e)}")
            raise

    async def transfer_to_spot(self, asset, amount):
        """从活期理财赎回到现货账户"""
        try:
            # 获取产品ID
            product_id = await self.get_flexible_product_id(asset)
            
            # 格式化金额，确保精度正确
            if asset == 'USDT':
                formatted_amount = "{:.2f}".format(float(amount))
            elif asset == 'BNB':
                formatted_amount = "{:.8f}".format(float(amount))
            else:
                formatted_amount = str(amount)
            
            params = {
                'asset': asset,
                'amount': formatted_amount,
                'productId': product_id,
                'timestamp': int(time.time() * 1000 + self.time_diff),
                'redeemType': 'FAST'  # 快速赎回
            }
            self.logger.info(f"开始赎回: {formatted_amount} {asset} 到现货")
            result = await self.exchange.sapi_post_simple_earn_flexible_redeem(params)
            self.logger.info(f"划转成功: {result}")
            
            # 赎回后清除余额缓存，确保下次获取最新余额
            self.balance_cache = {'timestamp': 0, 'data': None}
            self.funding_balance_cache = {'timestamp': 0, 'data': {}}
            
            return result
        except Exception as e:
            self.logger.error(f"赎回失败: {str(e)}")
            raise

    async def transfer_to_savings(self, asset, amount):
        """从现货账户申购活期理财"""
        try:
            # 获取产品ID
            product_id = await self.get_flexible_product_id(asset)
            
            # 格式化金额，确保精度正确
            if asset == 'USDT':
                formatted_amount = "{:.2f}".format(float(amount))  # USDT保留2位小数
            elif asset == 'BNB':
                formatted_amount = "{:.8f}".format(float(amount))  # BNB保留8位小数
            else:
                formatted_amount = str(amount)
            
            params = {
                'asset': asset,
                'amount': formatted_amount,
                'productId': product_id,
                'timestamp': int(time.time() * 1000 + self.time_diff)
            }
            self.logger.info(f"开始申购: {formatted_amount} {asset} 到活期理财")
            result = await self.exchange.sapi_post_simple_earn_flexible_subscribe(params)
            self.logger.info(f"划转成功: {result}")
            
            # 申购后清除余额缓存，确保下次获取最新余额
            self.balance_cache = {'timestamp': 0, 'data': None}
            self.funding_balance_cache = {'timestamp': 0, 'data': {}}
            
            return result
        except Exception as e:
            self.logger.error(f"申购失败: {str(e)}")
            raise

    async def fetch_my_trades(self, symbol, limit=10):
        """获取指定交易对的最近成交记录"""
        self.logger.debug(f"获取最近 {limit} 条成交记录 for {symbol}...")
        if not self.markets_loaded:
            await self.load_markets()
        try:
            # 确保使用市场ID
            market = self.exchange.market(symbol)
            trades = await self.exchange.fetch_my_trades(market['id'], limit=limit)
            self.logger.info(f"成功获取 {len(trades)} 条最近成交记录 for {symbol}")
            return trades
        except Exception as e:
            self.logger.error(f"获取成交记录失败 for {symbol}: {str(e)}")
            # 返回空列表或根据需要处理错误
            return [] 