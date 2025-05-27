from config import TradingConfig, FLIP_THRESHOLD, SAFETY_MARGIN, COOLDOWN
from exchange_client import ExchangeClient
from order_tracker import OrderTracker, OrderThrottler
from risk_manager import AdvancedRiskManager
import logging
import asyncio
import numpy as np
from datetime import datetime
import time
import math
from helpers import send_pushplus_message, format_trade_message
import json
from monitor import TradingMonitor
from position_controller_s1 import PositionControllerS1


class GridTrader:
    def __init__(self, exchange, config):
        """初始化网格交易器"""
        self.exchange = exchange
        self.config = config
        self.symbol = config.SYMBOL
        self.base_price = config.INITIAL_BASE_PRICE
        self.grid_size = config.INITIAL_GRID
        self.initialized = False
        self.highest = None
        self.lowest = None
        self.current_price = None
        self.active_orders = {'buy': None, 'sell': None}
        self.order_tracker = OrderTracker()
        self.risk_manager = AdvancedRiskManager(self)
        self.total_assets = 0
        self.last_trade_time = None
        self.last_trade_price = None
        self.price_history = []
        self.last_grid_adjust_time = time.time()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.symbol_info = None
        self.monitored_orders = []
        self.pending_orders = {}
        self.order_timestamps = {}
        self.throttler = OrderThrottler(limit=10, interval=60)
        self.last_price_check = 0  # 新增价格检查时间戳
        self.ORDER_TIMEOUT = 10  # 订单超时时间（秒）
        self.MIN_TRADE_INTERVAL = 30  # 两次交易之间的最小间隔（秒）
        self.grid_params = {
            'base_size': 2.0,  # 基础网格大小
            'min_size': 1.0,  # 最小网格
            'max_size': 4.0,  # 最大网格
            'adjust_step': 0.2  # 调整步长
        }
        self.volatility_window = 24  # 波动率计算周期（小时）
        self.monitor = TradingMonitor(self)  # 初始化monitor
        self.balance_check_interval = 60  # 每60秒检查一次余额
        self.last_balance_check = 0
        self.funding_balance_cache = {
            'timestamp': 0,
            'data': {}
        }
        self.funding_cache_ttl = 60  # 理财余额缓存60秒
        self.position_controller_s1 = PositionControllerS1(self)
        self.buying_or_selling = False  # 不在等待买入或卖出

    async def initialize(self):
        if self.initialized:
            return

        self.logger.info("正在加载市场数据...")
        try:
            # 确保市场数据加载成功
            retry_count = 0
            while not self.exchange.markets_loaded and retry_count < 3:
                try:
                    await self.exchange.load_markets()
                    await asyncio.sleep(1)
                except Exception as e:
                    self.logger.warning(f"加载市场数据失败: {str(e)}")
                    retry_count += 1
                    if retry_count >= 3:
                        raise
                    await asyncio.sleep(2)

            # 检查现货账户资金并划转
            await self._check_and_transfer_initial_funds()

            self.symbol_info = self.exchange.exchange.market(self.config.SYMBOL)

            # 优先使用.env配置的基准价
            if self.config.INITIAL_BASE_PRICE > 0:
                self.base_price = self.config.INITIAL_BASE_PRICE
                self.logger.info(f"使用预设基准价: {self.base_price}")
            else:
                self.base_price = await self._get_latest_price()
                self.logger.info(f"使用实时基准价: {self.base_price}")

            if self.base_price is None:
                raise ValueError("无法获取当前价格")

            self.logger.info(f"初始化完成 | 交易对: {self.config.SYMBOL} | 基准价: {self.base_price}")

            # 发送启动通知
            threshold = FLIP_THRESHOLD(self.grid_size)  # 计算实际阈值
            send_pushplus_message(
                f"网格交易启动成功\n"
                f"交易对: {self.config.SYMBOL}\n"
                f"基准价: {self.base_price} USDT\n"
                f"网格大小: {self.grid_size}%\n"
                f"触发阈值: {threshold * 100}% (网格大小的1/5)"
            )

            # 添加市场价对比
            market_price = await self._get_latest_price()
            price_diff = (market_price - self.base_price) / self.base_price * 100
            self.logger.info(
                f"市场当前价: {market_price:.4f} | "
                f"价差: {price_diff:+.2f}%"
            )

            # 启动时合并最近成交，不覆盖本地历史
            await self._sync_recent_trades(limit=50)
            self.initialized = True
        except Exception as e:
            self.initialized = False
            self.logger.error(f"初始化失败: {str(e)}")
            # 发送错误通知
            send_pushplus_message(
                f"网格交易启动失败\n"
                f"错误信息: {str(e)}",
                "错误通知"
            )
            raise

    async def _get_latest_price(self):
        try:
            ticker = await self.exchange.fetch_ticker(self.config.SYMBOL)
            if ticker and 'last' in ticker:
                return ticker['last']
            self.logger.error("获取价格失败: 返回数据格式不正确")
            return self.base_price
        except Exception as e:
            self.logger.error(f"获取最新价格失败: {str(e)}")
            return self.base_price

    def _get_upper_band(self):
        return self.base_price * (1 + self.grid_size / 100)

    def _get_lower_band(self):
        return self.base_price * (1 - self.grid_size / 100)

    def _reset_extremes(self):
        """
        清空上一轮监测记录的最高价 / 最低价，防止残留值
        引发虚假“反弹/回撤”判定
        """
        if self.highest is not None or self.lowest is not None:
            self.logger.debug(
                f"复位 high/low 变量 | highest={self.highest} lowest={self.lowest}"
            )
        self.highest = None
        self.lowest = None

    async def _sync_recent_trades(self, limit: int = 50):
        """
        启动同步：
        1) 把交易所最近 N 条 fill 聚合为整单；
        2) cost < MIN_TRADE_AMOUNT 的跳过；
        3) 用聚合结果覆盖本地同 id 旧记录，然后保存。
        """
        try:
            latest_fills = await self.exchange.fetch_my_trades(self.config.SYMBOL, limit=limit)
            if not latest_fills:
                self.logger.info("启动同步：未获取到任何成交记录")
                return

            # ---------- 聚合 ----------
            aggregated: dict[str, dict] = {}
            for tr in latest_fills:
                oid = tr.get('order') or tr.get('orderId')
                if not oid:  # 无 orderId 的利息 / 返佣跳过
                    continue
                price = float(tr.get('price', 0))
                amount = float(tr.get('amount', 0))
                cost = float(tr.get('cost') or price * amount)

                entry = aggregated.setdefault(
                    oid,
                    {'timestamp': tr['timestamp'] / 1000,
                     'side': tr['side'],
                     'amount': 0.0,
                     'cost': 0.0}
                )
                entry['amount'] += amount
                entry['cost'] += cost
                entry['timestamp'] = min(entry['timestamp'], tr['timestamp'] / 1000)

            # ---------- 本地字典 ----------
            local = {t['order_id']: t for t in self.order_tracker.trade_history}

            # ---------- 覆盖写入 ----------
            for oid, info in aggregated.items():
                avg_price = info['cost'] / info['amount']
                local[oid] = {  # 直接覆盖或新增
                    'timestamp': info['timestamp'],
                    'side': info['side'],
                    'price': avg_price,
                    'amount': info['amount'],
                    'order_id': oid,
                    'profit': 0
                }

            # ---------- 保存 ----------
            merged = sorted(local.values(), key=lambda x: x['timestamp'])
            self.order_tracker.trade_history = merged
            self.order_tracker.save_trade_history()
            self.logger.info(f"启动同步：本地历史共 {len(merged)} 条记录")

        except Exception as e:
            self.logger.error(f"同步最近成交失败: {e}")

    async def _check_buy_signal(self):
        current_price = self.current_price
        if current_price <= self._get_lower_band():
            self.buying_or_selling = True  # 进入买入或卖出监测
            # 记录最低价
            new_lowest = current_price if self.lowest is None else min(self.lowest, current_price)
            # 只在最低价更新时打印日志
            if new_lowest != self.lowest:
                self.lowest = new_lowest
                self.logger.info(
                    f"买入监测 | "
                    f"当前价: {current_price:.2f} | "
                    f"触发价: {self._get_lower_band():.5f} | "
                    f"最低价: {self.lowest:.2f} | "
                    f"网格下限: {self._get_lower_band():.2f} | "
                    f"反弹阈值: {FLIP_THRESHOLD(self.grid_size) * 100:.2f}%"
                )
            threshold = FLIP_THRESHOLD(self.grid_size)
            # 从最低价反弹指定比例时触发买入
            if self.lowest and current_price >= self.lowest * (1 + threshold):
                self.buying_or_selling = False  # 不在买入或卖出
                self.logger.info(
                    f"触发买入信号 | 当前价: {current_price:.2f} | 已反弹: {(current_price / self.lowest - 1) * 100:.2f}%")
                # 检查买入余额是否充足
                if not await self.check_buy_balance(current_price):
                    return False
                return True
        else:
            self.buying_or_selling = False  # 退出买入或卖出监测
            self._reset_extremes()  # NEW
        return False

    async def _check_sell_signal(self):
        current_price = self.current_price
        initial_upper_band = self._get_upper_band()  # 初始上轨价格

        if current_price >= initial_upper_band:
            self.buying_or_selling = True  # 进入买入或卖出监测
            # 记录最高价
            new_highest = current_price if self.highest is None else max(self.highest, current_price)
            threshold = FLIP_THRESHOLD(self.grid_size)

            # 计算动态触发价格 (基于最高价的回调阈值)
            dynamic_trigger_price = new_highest * (1 - threshold) if new_highest is not None else initial_upper_band

            # 只在最高价更新时打印日志
            if new_highest != self.highest:
                self.highest = new_highest
                # 重新计算动态触发价，基于更新后的最高价
                dynamic_trigger_price = self.highest * (1 - threshold)

                self.logger.info(
                    f"卖出监测 | "
                    f"当前价: {current_price:.2f} | "
                    f"触发价(动态): {dynamic_trigger_price:.5f} | "
                    f"最高价: {self.highest:.2f}"
                )

            # 从最高价下跌指定比例时触发卖出
            if self.highest and current_price <= self.highest * (1 - threshold):
                self.buying_or_selling = False  # 不在买入或卖出
                self.logger.info(
                    f"触发卖出信号 | 当前价: {current_price:.2f} | 目标价: {self.highest * (1 - threshold):.5f} | 已下跌: {(1 - current_price / self.highest) * 100:.2f}%")
                # 检查卖出余额是否充足
                if not await self.check_sell_balance():
                    return False
                return True
        else:
            self.buying_or_selling = False
            self._reset_extremes()
        return False

    async def _calculate_order_amount(self, order_type):
        """计算目标订单金额 (总资产的10%)\n"""
        try:
            current_time = time.time()

            # 使用缓存避免频繁计算和日志输出
            cache_key = f'order_amount_target'  # 使用不同的缓存键
            if hasattr(self, cache_key) and \
                    current_time - getattr(self, f'{cache_key}_time') < 60:  # 1分钟缓存
                return getattr(self, cache_key)

            total_assets = await self._get_total_assets()

            # 目标金额严格等于总资产的10%
            amount = total_assets * 0.1

            # 只在金额变化超过1%时记录日志
            # 使用 max(..., 0.01) 避免除以零错误
            if not hasattr(self, f'{cache_key}_last') or \
                    abs(amount - getattr(self, f'{cache_key}_last', 0)) / max(getattr(self, f'{cache_key}_last', 0.01),
                                                                              0.01) > 0.01:
                self.logger.info(
                    f"目标订单金额计算 | "
                    f"总资产: {total_assets:.2f} USDT | "
                    f"计算金额 (10%): {amount:.2f} USDT"
                )
                setattr(self, f'{cache_key}_last', amount)

            # 更新缓存
            setattr(self, cache_key, amount)
            setattr(self, f'{cache_key}_time', current_time)

            return amount

        except Exception as e:
            self.logger.error(f"计算目标订单金额失败: {str(e)}")
            # 返回一个合理的默认值或上次缓存值，避免返回0导致后续计算错误
            return getattr(self, cache_key, 0)  # 如果缓存存在则返回缓存，否则返回0

    async def get_available_balance(self, currency):
        balance = await self.exchange.fetch_balance({'type': 'spot'})
        return balance.get('free', {}).get(currency, 0) * SAFETY_MARGIN

    async def _calculate_dynamic_interval_seconds(self):
        """根据波动率动态计算网格调整的时间间隔（秒）"""
        try:
            volatility = await self._calculate_volatility()
            if volatility is None:  # Handle case where volatility calculation failed
                raise ValueError("波动率计算失败")  # Volatility calculation failed

            interval_rules = self.config.DYNAMIC_INTERVAL_PARAMS['volatility_to_interval_hours']
            default_interval_hours = self.config.DYNAMIC_INTERVAL_PARAMS['default_interval_hours']

            matched_interval_hours = default_interval_hours  # Start with default

            for rule in interval_rules:
                vol_range = rule['range']
                # Check if volatility falls within the defined range [min, max)
                if vol_range[0] <= volatility < vol_range[1]:
                    matched_interval_hours = rule['interval_hours']
                    self.logger.debug(
                        f"动态间隔匹配: 波动率 {volatility:.4f} 在范围 {vol_range}, 间隔 {matched_interval_hours} 小时")  # Dynamic interval match
                    break  # Stop after first match

            interval_seconds = matched_interval_hours * 3600
            # Add a minimum interval safety check
            min_interval_seconds = 5 * 60  # Example: minimum 5 minutes
            final_interval_seconds = max(interval_seconds, min_interval_seconds)

            self.logger.debug(
                f"计算出的动态调整间隔: {final_interval_seconds:.0f} 秒 ({final_interval_seconds / 3600:.2f} 小时)")  # Calculated dynamic adjustment interval
            return final_interval_seconds

        except Exception as e:
            self.logger.error(
                f"计算动态调整间隔失败: {e}, 使用默认间隔。")  # Failed to calculate dynamic interval, using default.
            # Fallback to default interval from config
            default_interval_hours = self.config.DYNAMIC_INTERVAL_PARAMS.get('default_interval_hours', 1.0)
            return default_interval_hours * 3600

    async def main_loop(self):
        while True:
            try:
                if not self.initialized:
                    await self.initialize()
                    await self.position_controller_s1.update_daily_s1_levels()

                # 保留S1水平更新
                await self.position_controller_s1.update_daily_s1_levels()

                # 获取当前价格
                current_price = await self._get_latest_price()
                if not current_price:
                    await asyncio.sleep(5)
                    continue
                self.current_price = current_price

                # 优先检查买入卖出信号，不执行风控检查
                # 添加重试机制确保买入卖出检测正常运行
                sell_signal = await self._check_signal_with_retry(self._check_sell_signal, "卖出检测")
                if sell_signal:
                    await self.execute_order('sell')
                else:
                    buy_signal = await self._check_signal_with_retry(self._check_buy_signal, "买入检测")
                    if buy_signal:
                        await self.execute_order('buy')
                    else:
                        # 只有在没有交易信号时才执行其他操作

                        # 执行风控检查
                        if await self.risk_manager.multi_layer_check():
                            await asyncio.sleep(5)
                            continue

                        # 执行S1策略
                        await self.position_controller_s1.check_and_execute()

                        # 如果时间到了并且不在买入或卖出调整网格大小
                        dynamic_interval_seconds = await self._calculate_dynamic_interval_seconds()
                        if time.time() - self.last_grid_adjust_time > dynamic_interval_seconds and not self.buying_or_selling:
                            self.logger.info(
                                f"时间到了，准备调整网格大小 (间隔: {dynamic_interval_seconds / 3600} 小时).")
                            await self.adjust_grid_size()
                            self.last_grid_adjust_time = time.time()

                await asyncio.sleep(5)

            except Exception as e:
                self.logger.error(f"Main loop error: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def _check_signal_with_retry(self, check_func, check_name, max_retries=3, retry_delay=2):
        """带重试机制的信号检测函数
        
        Args:
            check_func: 要执行的检测函数 (_check_buy_signal 或 _check_sell_signal)
            check_name: 检测名称，用于日志
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            
        Returns:
            bool: 检测结果
        """
        retries = 0
        while retries <= max_retries:
            try:
                return await check_func()
            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    self.logger.warning(f"{check_name}出错，{retry_delay}秒后进行第{retries}次重试: {str(e)}")
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.error(f"{check_name}失败，达到最大重试次数({max_retries}次): {str(e)}")
                    return False
        return False

    async def _ensure_trading_funds(self):
        """确保现货账户有足够的交易资金"""
        try:
            balance = await self.exchange.fetch_balance()
            current_price = self.current_price

            # 计算所需资金
            required_usdt = self.config.MIN_TRADE_AMOUNT * 2  # 保持两倍最小交易额
            required_bnb = required_usdt / current_price

            # 获取现货余额
            spot_usdt = float(balance['free'].get('USDT', 0))
            spot_bnb = float(balance['free'].get('BNB', 0))

            # 一次性检查和赎回所需资金
            transfers = []
            if spot_usdt < required_usdt:
                transfers.append({
                    'asset': 'USDT',
                    'amount': required_usdt - spot_usdt
                })
            if spot_bnb < required_bnb:
                transfers.append({
                    'asset': 'BNB',
                    'amount': required_bnb - spot_bnb
                })

            # 如果需要赎回，一次性执行所有赎回操作
            if transfers:
                self.logger.info("开始资金赎回操作...")
                for transfer in transfers:
                    self.logger.info(f"从理财赎回 {transfer['amount']:.8f} {transfer['asset']}")
                    await self.exchange.transfer_to_spot(transfer['asset'], transfer['amount'])
                self.logger.info("资金赎回完成")
                # 等待资金到账
                await asyncio.sleep(2)
        except Exception as e:
            self.logger.error(f"资金检查和划转失败: {str(e)}")

    async def emergency_stop(self):
        try:
            open_orders = await self.exchange.fetch_open_orders(self.config.SYMBOL)
            for order in open_orders:
                await self.exchange.cancel_order(order['id'])
            send_pushplus_message("程序紧急停止", "系统通知")
            self.logger.critical("所有交易已停止，进入复盘程序")
        except Exception as e:
            self.logger.error(f"紧急停止失败: {str(e)}")
            send_pushplus_message(f"程序异常停止: {str(e)}", "错误通知")
        finally:
            await self.exchange.close()
            exit()

    async def _get_position_ratio(self):
        """获取当前仓位占总资产比例"""
        try:
            usdt_balance = await self.get_available_balance('USDT')
            position_value = await self.risk_manager._get_position_value()
            total_assets = position_value + usdt_balance
            if total_assets == 0:
                return 0
            return position_value / total_assets
        except Exception as e:
            self.logger.error(f"获取仓位比例失败: {str(e)}")
            return 0

    async def _handle_filled_order(
            self,
            order_dict: dict,
            side: str,
            retry_count: int,
            max_retries: int
    ):
        """
        对已成交订单进行统一后续处理：更新基准价、复位 high/low、
        记录交易、推送通知、资金转移。
        """
        order_price = float(order_dict['price'])
        order_amount = float(order_dict['filled'])
        order_id = order_dict['id']

        # 1) 更新基准价并复位最高/最低
        self.base_price = order_price
        self._reset_extremes()

        # 2) 清除活跃订单
        self.active_orders[side] = None

        # 3) 记录交易
        trade_info = {
            'timestamp': time.time(),
            'side': side,
            'price': order_price,
            'amount': order_amount,
            'order_id': order_id
        }
        self.order_tracker.add_trade(trade_info)

        # 4) 更新时间戳 / 总资产
        self.last_trade_time = time.time()
        self.last_trade_price = order_price
        await self._update_total_assets()
        self.logger.info(f"基准价已更新: {self.base_price}")

        # 5) 推送通知
        msg = format_trade_message(
            side='buy' if side == 'buy' else 'sell',
            symbol=self.config.SYMBOL,
            price=order_price,
            amount=order_amount,
            total=order_price * order_amount,
            grid_size=self.grid_size,
            retry_count=(retry_count + 1, max_retries)
        )
        send_pushplus_message(msg, "交易成功通知")

        # 6) 将多余资金转入理财
        await self._transfer_excess_funds()

        return order_dict

    async def execute_order(self, side):
        """执行订单，带重试机制"""
        max_retries = 10  # 最大重试次数
        retry_count = 0
        check_interval = 3  # 下单后等待检查时间（秒）

        while retry_count < max_retries:
            try:
                # 获取最新订单簿数据
                order_book = await self.exchange.fetch_order_book(self.config.SYMBOL, limit=5)
                if not order_book or not order_book.get('asks') or not order_book.get('bids'):
                    self.logger.error("获取订单簿数据失败或数据不完整")
                    retry_count += 1
                    await asyncio.sleep(3)
                    continue

                # 使用买1/卖1价格
                if side == 'buy':
                    order_price = order_book['asks'][0][0]  # 卖1价买入
                else:
                    order_price = order_book['bids'][0][0]  # 买1价卖出

                # 计算交易数量
                amount_usdt = await self._calculate_order_amount(side)
                amount = self._adjust_amount_precision(amount_usdt / order_price)

                # 检查余额是否足够
                if side == 'buy':
                    if not await self.check_buy_balance(order_price):
                        self.logger.warning(f"买入余额不足，第 {retry_count + 1} 次尝试中止")
                        return False
                else:
                    if not await self.check_sell_balance():
                        self.logger.warning(f"卖出余额不足，第 {retry_count + 1} 次尝试中止")
                        return False

                self.logger.info(
                    f"尝试第 {retry_count + 1}/{max_retries} 次 {side} 单 | "
                    f"价格: {order_price} | "
                    f"金额: {amount_usdt:.2f} USDT | "
                    f"数量: {amount:.8f} BNB"
                )

                # 创建订单
                order = await self.exchange.create_order(
                    self.config.SYMBOL,
                    'limit',
                    side,
                    amount,
                    order_price
                )

                # 更新活跃订单状态
                order_id = order['id']
                self.active_orders[side] = order_id
                self.order_tracker.add_order(order)

                # 等待指定时间后检查订单状态
                self.logger.info(f"订单已提交，等待 {check_interval} 秒后检查状态")
                await asyncio.sleep(check_interval)

                # 检查订单状态
                updated_order = await self.exchange.fetch_order(order_id, self.config.SYMBOL)

                # 订单已成交
                if updated_order['status'] == 'closed':
                    self.logger.info(f"订单已成交 | ID: {order_id}")
                    return await self._handle_filled_order(
                        updated_order, side, retry_count, max_retries
                    )

                # 如果订单未成交，取消订单并重试
                self.logger.warning(f"订单未成交，尝试取消 | ID: {order_id} | 状态: {updated_order['status']}")
                try:
                    await self.exchange.cancel_order(order_id, self.config.SYMBOL)
                    self.logger.info(f"订单已取消，准备重试 | ID: {order_id}")
                except Exception as e:
                    # 如果取消订单时出错，检查是否已成交
                    self.logger.warning(f"取消订单时出错: {str(e)}，再次检查订单状态")
                    try:
                        check_order = await self.exchange.fetch_order(order_id, self.config.SYMBOL)
                        if check_order['status'] == 'closed':
                            self.logger.info(f"订单已经成交 | ID: {order_id}")
                            return await self._handle_filled_order(
                                check_order, side, retry_count, max_retries
                            )

                    except Exception as check_e:
                        self.logger.error(f"检查订单状态失败: {str(check_e)}")

                # 清除活跃订单状态
                self.active_orders[side] = None

                # 增加重试计数
                retry_count += 1

                # 如果还有重试次数，等待一秒后继续
                if retry_count < max_retries:
                    self.logger.info(f"等待1秒后进行第 {retry_count + 1} 次尝试")
                    await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"执行{side}单失败: {str(e)}")

                # 尝试清理可能存在的订单
                if 'order_id' in locals() and self.active_orders.get(side) == order_id:
                    try:
                        await self.exchange.cancel_order(order_id, self.config.SYMBOL)
                        self.logger.info(f"已取消错误订单 | ID: {order_id}")
                    except Exception as cancel_e:
                        self.logger.error(f"取消错误订单失败: {str(cancel_e)}")
                    finally:
                        self.active_orders[side] = None

                # 增加重试计数
                retry_count += 1

                # 如果是关键错误，停止重试
                if "资金不足" in str(e) or "Insufficient" in str(e):
                    self.logger.error("资金不足，停止重试")
                    # 发送错误通知
                    error_message = f"""❌ 交易失败
━━━━━━━━━━━━━━━━━━━━
🔍 类型: {side} 失败
📊 交易对: {self.config.SYMBOL}
⚠️ 错误: 资金不足
"""
                    send_pushplus_message(error_message, "交易错误通知")
                    return False

                # 如果还有重试次数，稍等后继续
                if retry_count < max_retries:
                    self.logger.info(f"等待2秒后进行第 {retry_count + 1} 次尝试")
                    await asyncio.sleep(2)

        # 达到最大重试次数后仍未成功
        if retry_count >= max_retries:
            self.logger.error(f"{side}单执行失败，达到最大重试次数: {max_retries}")
            error_message = f"""❌ 交易失败
━━━━━━━━━━━━━━━━━━━━
🔍 类型: {side} 失败
📊 交易对: {self.config.SYMBOL}
⚠️ 错误: 达到最大重试次数 {max_retries} 次
"""
            send_pushplus_message(error_message, "交易错误通知")

        return False

    async def _wait_for_balance(self, side, amount, price):
        """等待直到有足够的余额可用"""
        max_attempts = 10
        for i in range(max_attempts):
            balance = await self.exchange.fetch_balance()
            if side == 'buy':
                required = amount * price
                available = float(balance['free'].get('USDT', 0))
                if available >= required:
                    return True
            else:
                available = float(balance['free'].get('BNB', 0))
                if available >= amount:
                    return True

            self.logger.info(f"等待资金到账 ({i + 1}/{max_attempts})...")
            await asyncio.sleep(1)

        raise Exception("等待资金到账超时")

    async def _adjust_grid_after_trade(self):
        """根据市场波动动态调整网格大小"""
        trade_count = self.order_tracker.trade_count
        if trade_count % self.config.GRID_PARAMS['adjust_interval'] == 0:
            volatility = await self._calculate_volatility()

            # 根据波动率调整
            if volatility > self.config.GRID_PARAMS['volatility_threshold']['high']:
                new_size = min(
                    self.grid_size * 1.1,  # 扩大10%
                    self.config.GRID_PARAMS['max']
                )
                action = "扩大"
            else:
                new_size = max(
                    self.grid_size * 0.9,  # 缩小10%
                    self.config.GRID_PARAMS['min']
                )
                action = "缩小"

            # 建议改进：添加趋势判断
            price_trend = self._get_price_trend()  # 获取价格趋势（1小时）
            if price_trend > 0:  # 上涨趋势
                new_size *= 1.05  # 额外增加5%
            elif price_trend < 0:  # 下跌趋势
                new_size *= 0.95  # 额外减少5%

            self.grid_size = new_size
            self.logger.info(
                f"动态调整网格 | 操作: {action} | "
                f"波动率: {volatility:.2%} | "
                f"新尺寸: {self.grid_size:.2f}%"
            )

    def _log_order(self, order):
        """记录订单信息"""
        try:
            side = order['side']
            price = float(order['price'])
            amount = float(order['amount'])
            total = price * amount

            # 计算利润
            profit = 0
            if side == 'sell':
                # 卖出时计算利润 = 卖出价格 - 基准价格
                profit = (price - self.base_price) * amount
            elif side == 'buy':
                # 买入时利润为0
                profit = 0

            # 只在这里添加交易记录
            self.order_tracker.add_trade({
                'timestamp': time.time(),
                'side': side,
                'price': price,
                'amount': amount,
                'profit': profit,
                'order_id': order['id']
            })

            # 发送通知
            message = format_trade_message(
                side=side,
                symbol=self.symbol,
                price=price,
                amount=amount,
                total=total,
                grid_size=self.grid_size
            )
            send_pushplus_message(message, "交易执行通知")
        except Exception as e:
            self.logger.error(f"记录订单失败: {str(e)}")

    async def _reinitialize(self):
        """系统重新初始化"""
        try:
            # 关闭现有连接
            await self.exchange.close()

            # 重置关键状态
            self.exchange = ExchangeClient()
            self.order_tracker.reset()
            self.base_price = None
            self.highest = None
            self.lowest = None
            self.grid_size = self.config.GRID_PARAMS['initial']
            self.last_trade = 0
            self.initialized = False  # 确保重置初始化状态

            # 等待新的交易所客户端就绪
            await asyncio.sleep(2)

            self.logger.info("系统重新初始化完成")
        except Exception as e:
            self.logger.critical(f"重新初始化失败: {str(e)}")
            raise

    async def _check_and_cancel_timeout_orders(self):
        """检查并取消超时订单"""
        current_time = time.time()
        for order_id, timestamp in list(self.order_timestamps.items()):
            if current_time - timestamp > self.ORDER_TIMEOUT:
                try:
                    params = {
                        'timestamp': int(time.time() * 1000 + self.exchange.time_diff),
                        'recvWindow': 5000
                    }
                    order = await self.exchange.fetch_order(order_id, self.config.SYMBOL, params)

                    if order['status'] == 'closed':
                        old_base_price = self.base_price
                        self.base_price = order['price']
                        await self._adjust_grid_after_trade()
                        # 更新最后成交信息
                        self.last_trade_price = order['price']
                        self.last_trade_time = current_time
                        self.logger.info(
                            f"订单已成交 | ID: {order_id} | 价格: {order['price']} | 基准价从 {old_base_price} 更新为 {self.base_price}")
                        # 清除活跃订单标记
                        for side, active_id in self.active_orders.items():
                            if active_id == order_id:
                                self.active_orders[side] = None
                        # 发送成交通知
                        send_pushplus_message(
                            f"BNB {{'买入' if side == 'buy' else '卖出'}}单成交\\n"
                            f"价格: {order['price']} USDT"
                        )
                    elif order['status'] == 'open':
                        # 取消未成交订单
                        params = {
                            'timestamp': int(time.time() * 1000 + self.exchange.time_diff),
                            'recvWindow': 5000
                        }
                        await self.exchange.cancel_order(order_id, self.config.SYMBOL, params)
                        self.logger.info(f"取消超时订单 | ID: {order_id}")
                        # 清除活跃订单标记
                        for side, active_id in self.active_orders.items():
                            if active_id == order_id:
                                self.active_orders[side] = None

                    # 清理订单记录
                    self.pending_orders.pop(order_id, None)
                    self.order_timestamps.pop(order_id, None)
                except Exception as e:
                    self.logger.error(f"检查订单状态失败: {str(e)} | 订单ID: {order_id}")
                    # 如果是时间同步错误，等待一秒后继续
                    if "Timestamp for this request" in str(e):
                        await asyncio.sleep(1)
                        continue

    async def adjust_grid_size(self):
        """根据波动率和市场趋势调整网格大小"""
        try:
            volatility = await self._calculate_volatility()
            self.logger.info(f"当前波动率: {volatility:.4f}")

            # 根据波动率获取基础网格大小
            base_grid = None
            for range_config in self.config.GRID_PARAMS['volatility_threshold']['ranges']:
                if range_config['range'][0] <= volatility < range_config['range'][1]:
                    base_grid = range_config['grid']
                    break

            # 如果没有匹配到波动率范围，使用默认网格
            if base_grid is None:
                base_grid = self.config.INITIAL_GRID

            # 删除趋势调整逻辑
            new_grid = base_grid

            # 确保网格在允许范围内
            new_grid = max(min(new_grid, self.config.GRID_PARAMS['max']), self.config.GRID_PARAMS['min'])

            if new_grid != self.grid_size:
                self.logger.info(
                    f"调整网格大小 | "
                    f"波动率: {volatility:.2%} | "
                    f"原网格: {self.grid_size:.2f}% | "
                    f"新网格: {new_grid:.2f}%"
                )
                self.grid_size = new_grid

        except Exception as e:
            self.logger.error(f"调整网格大小失败: {str(e)}")

    async def _calculate_volatility(self):
        """计算价格波动率"""
        try:
            # 获取24小时K线数据
            klines = await self.exchange.fetch_ohlcv(
                self.config.SYMBOL,
                timeframe='1h',
                limit=self.config.VOLATILITY_WINDOW
            )

            if not klines:
                return 0

            # 计算收益率
            prices = [float(k[4]) for k in klines]  # 收盘价
            returns = np.diff(np.log(prices))

            # 计算波动率（标准差）并年化
            volatility = np.std(returns) * np.sqrt(24 * 365)  # 年化波动率
            return volatility

        except Exception as e:
            self.logger.error(f"计算波动率失败: {str(e)}")
            return 0

    def _adjust_amount_precision(self, amount):
        """根据交易所精度调整数量"""
        precision = 3  # BNB的数量精度是3位小数

        formatted_amount = f"{amount:.3f}"
        return float(formatted_amount)

    async def calculate_trade_amount(self, side, order_price):
        # 获取必要参数
        balance = await self.exchange.fetch_balance()
        total_assets = float(balance['total']['USDT']) + float(balance['total'].get('BNB', 0)) * order_price

        # 计算波动率调整因子
        volatility = await self._calculate_volatility()
        volatility_factor = 1 / (1 + volatility * 10)  # 波动越大，交易量越小

        # 计算凯利仓位
        win_rate = await self.calculate_win_rate()
        payoff_ratio = await self.calculate_payoff_ratio()

        # 安全版凯利公式计算
        kelly_f = max(0.0, (win_rate * payoff_ratio - (1 - win_rate)) / payoff_ratio)  # 确保非负
        kelly_f = min(kelly_f, 0.3)  # 最大不超过30%仓位

        # 获取价格分位因子
        price_percentile = await self._get_price_percentile()
        if side == 'buy':
            percentile_factor = 1 + (1 - price_percentile) * 0.5  # 价格越低，买入越多
        else:
            percentile_factor = 1 + price_percentile * 0.5  # 价格越高，卖出越多

        # 动态计算交易金额
        risk_adjusted_amount = min(
            total_assets * self.config.RISK_FACTOR * volatility_factor * kelly_f * percentile_factor,
            total_assets * self.config.MAX_POSITION_RATIO
        )

        # 应用最小/最大限制
        amount_usdt = max(
            min(risk_adjusted_amount, self.config.BASE_AMOUNT),
            self.config.MIN_TRADE_AMOUNT
        )

        return amount_usdt

    async def calculate_win_rate(self):
        """计算胜率"""
        try:
            trades = self.order_tracker.get_trade_history()
            if not trades:
                return 0

            # 计算盈利交易数量
            winning_trades = [t for t in trades if t['profit'] > 0]
            win_rate = len(winning_trades) / len(trades)

            return win_rate
        except Exception as e:
            self.logger.error(f"计算胜率失败: {str(e)}")
            return 0

    async def calculate_payoff_ratio(self):
        """计算盈亏比"""
        trades = self.order_tracker.get_trade_history()
        if len(trades) < 10:
            return 1.0

        avg_win = np.mean([t['profit'] for t in trades if t['profit'] > 0])
        avg_loss = np.mean([abs(t['profit']) for t in trades if t['profit'] < 0])
        return avg_win / avg_loss if avg_loss != 0 else 1.0

    async def save_trade_stats(self):
        """保存交易统计数据"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'grid_size': self.grid_size,
            'position_size': self.current_position,
            'volatility': await self._calculate_volatility(),
            'win_rate': await self.calculate_win_rate(),
            'payoff_ratio': await self.calculate_payoff_ratio()
        }
        with open('trade_stats.json', 'a') as f:
            f.write(json.dumps(stats) + '\n')

    async def _get_order_price(self, side):
        """获取订单价格"""
        try:
            order_book = await self.exchange.fetch_order_book(self.config.SYMBOL)
            ask_price = order_book['asks'][0][0]  # 卖一价
            bid_price = order_book['bids'][0][0]  # 买一价

            if side == 'buy':
                order_price = ask_price  # 直接用卖一价
            else:
                order_price = bid_price  # 直接用买一价

            order_price = round(order_price, 2)

            self.logger.info(
                f"订单定价 | 方向: {side} | "
                f"订单价: {order_price}"
            )

            return order_price
        except Exception as e:
            self.logger.error(f"获取订单价格失败: {str(e)}")
            raise

    async def _get_price_percentile(self, period='7d'):
        """获取当前价格在历史中的分位位置"""
        try:
            # 获取过去7天价格数据（使用4小时K线）
            ohlcv = await self.exchange.fetch_ohlcv(self.config.SYMBOL, '4h', limit=42)  # 42根4小时K线 ≈ 7天
            closes = [candle[4] for candle in ohlcv]
            current_price = await self._get_latest_price()

            # 计算分位值
            sorted_prices = sorted(closes)
            lower = sorted_prices[int(len(sorted_prices) * 0.25)]  # 25%分位
            upper = sorted_prices[int(len(sorted_prices) * 0.75)]  # 75%分位

            # 添加数据有效性检查
            if len(sorted_prices) < 10:  # 当数据不足时使用更宽松的判断
                self.logger.warning("历史数据不足，使用简化分位计算")
                mid_price = (sorted_prices[0] + sorted_prices[-1]) / 2
                return 0.5 if current_price >= mid_price else 0.0

            # 计算当前价格位置
            if current_price <= lower:
                return 0.0  # 处于低位
            elif current_price >= upper:
                return 1.0  # 处于高位
            else:
                return (current_price - lower) / (upper - lower)

        except Exception as e:
            self.logger.error(f"获取价格分位失败: {str(e)}")
            return 0.5  # 默认中间位置

    async def _calculate_required_funds(self, side):
        """计算需要划转的资金量"""
        current_price = await self._get_latest_price()
        balance = await self.exchange.fetch_balance()
        total_assets = float(balance['total']['USDT']) + float(balance['total'].get('BNB', 0)) * current_price

        # 获取当前订单需要的金额
        amount_usdt = await self.calculate_trade_amount(side, current_price)

        # 考虑手续费和滑价
        required = amount_usdt * 1.05  # 增加5%缓冲
        return min(required, self.config.MAX_POSITION_RATIO * total_assets)

    async def _transfer_excess_funds(self):
        """将超出总资产16%目标的部分资金转回理财账户"""
        try:
            balance = await self.exchange.fetch_balance()
            current_price = await self._get_latest_price()
            total_assets = await self._get_total_assets()

            # 如果无法获取价格或总资产，则跳过
            if not current_price or current_price <= 0 or total_assets <= 0:
                self.logger.warning("无法获取价格或总资产，跳过资金转移检查")
                return

            # 计算目标保留金额 (总资产的16%)
            target_usdt_hold = total_assets * 0.16
            target_bnb_hold_value = total_assets * 0.16
            target_bnb_hold_amount = target_bnb_hold_value / current_price

            # 获取当前现货可用余额
            spot_usdt_balance = float(balance.get('free', {}).get('USDT', 0))
            spot_bnb_balance = float(balance.get('free', {}).get('BNB', 0))

            self.logger.info(
                f"资金转移检查 | 总资产: {total_assets:.2f} USDT | "
                f"目标USDT持有: {target_usdt_hold:.2f} | 现货USDT: {spot_usdt_balance:.2f} | "
                f"目标BNB持有(等值): {target_bnb_hold_value:.2f} USDT ({target_bnb_hold_amount:.4f} BNB) | "
                f"现货BNB: {spot_bnb_balance:.4f}"
            )

            transfer_executed = False  # 标记是否执行了划转

            # 处理USDT：如果现货超出目标，转移多余部分
            if spot_usdt_balance > target_usdt_hold:
                transfer_amount = spot_usdt_balance - target_usdt_hold
                # 增加最小划转金额判断，避免无效操作
                # 将阈值提高到 1.0 USDT
                if transfer_amount > 1.0:
                    self.logger.info(f"转移多余USDT到理财: {transfer_amount:.2f}")
                    try:
                        await self.exchange.transfer_to_savings('USDT', transfer_amount)
                        transfer_executed = True
                    except Exception as transfer_e:
                        self.logger.error(f"转移USDT到理财失败: {str(transfer_e)}")
                else:
                    self.logger.info(f"USDT超出部分 ({transfer_amount:.2f}) 过小，不执行划转")

            # 处理BNB：如果现货超出目标，转移多余部分
            if spot_bnb_balance > target_bnb_hold_amount:
                transfer_amount = spot_bnb_balance - target_bnb_hold_amount
                # 检查转移金额是否大于等于 0.01 BNB
                if transfer_amount >= 0.01:
                    self.logger.info(f"转移多余BNB到理财: {transfer_amount:.4f}")
                    try:
                        await self.exchange.transfer_to_savings('BNB', transfer_amount)
                        transfer_executed = True
                    except Exception as transfer_e:
                        self.logger.error(f"转移BNB到理财失败: {str(transfer_e)}")
                else:
                    # 修改日志消息以反映新的阈值
                    self.logger.info(f"BNB超出部分 ({transfer_amount:.4f}) 低于最小申购额 0.01 BNB，不执行划转")

            if transfer_executed:
                self.logger.info("多余资金已尝试转移到理财账户")
            else:
                self.logger.info("无需转移资金到理财账户")

        except Exception as e:
            self.logger.error(f"转移多余资金检查失败: {str(e)}")

    async def _check_flip_signal(self):
        """检查是否需要翻转交易方向"""
        try:
            current_price = self.current_price
            price_diff = abs(current_price - self.base_price)
            flip_threshold = self.base_price * FLIP_THRESHOLD(self.grid_size)

            if price_diff >= flip_threshold:
                # 智能预划转资金
                await self._pre_transfer_funds(current_price)
                self.logger.info(f"价格偏离阈值 | 当前价: {current_price} | 基准价: {self.base_price}")
                return True
        except Exception as e:
            self.logger.error(f"翻转信号检查失败: {str(e)}")
            return False

    async def _pre_transfer_funds(self, current_price):
        """智能预划转资金"""
        try:
            # 根据预期方向计算需求
            expected_side = 'buy' if current_price > self.base_price else 'sell'
            required = await self._calculate_required_funds(expected_side)

            # 添加20%缓冲
            required_with_buffer = required * 1.2

            # 分批次划转（应对大额划转限制）
            max_single_transfer = 5000  # 假设单次最大划转5000 USDT
            while required_with_buffer > 0:
                transfer_amount = min(required_with_buffer, max_single_transfer)
                await self.exchange.transfer_to_spot('USDT', transfer_amount)
                required_with_buffer -= transfer_amount
                self.logger.info(f"预划转完成: {transfer_amount} USDT | 剩余需划转: {required_with_buffer}")

            self.logger.info("资金预划转完成，等待10秒确保到账")
            await asyncio.sleep(10)  # 等待资金到账

        except Exception as e:
            self.logger.error(f"预划转失败: {str(e)}")
            raise

    def _calculate_dynamic_base(self, total_assets):
        """计算动态基础交易金额"""
        # 计算基于总资产百分比的交易金额范围
        min_amount = max(
            self.config.MIN_TRADE_AMOUNT,  # 不低于20 USDT
            total_assets * self.config.MIN_POSITION_PERCENT  # 不低于总资产的5%
        )
        max_amount = total_assets * self.config.MAX_POSITION_PERCENT  # 不超过总资产的15%

        # 计算目标交易金额（总资产的10%）
        target_amount = total_assets * 0.1

        # 确保交易金额在允许范围内
        return max(
            min_amount,
            min(
                target_amount,
                max_amount
            )
        )

    async def _check_and_transfer_initial_funds(self):
        """检查并划转初始资金"""
        try:
            # 获取现货和理财账户余额
            balance = await self.exchange.fetch_balance()
            funding_balance = await self.exchange.fetch_funding_balance()
            total_assets = await self._get_total_assets()
            current_price = await self._get_latest_price()

            # 计算目标持仓（总资产的16%）
            target_usdt = total_assets * 0.16
            target_bnb = (total_assets * 0.16) / current_price

            # 获取现货余额
            usdt_balance = float(balance['free'].get('USDT', 0))
            bnb_balance = float(balance['free'].get('BNB', 0))

            # 计算总余额（现货+理财）
            total_usdt = usdt_balance + float(funding_balance.get('USDT', 0))
            total_bnb = bnb_balance + float(funding_balance.get('BNB', 0))

            # 调整USDT余额
            if usdt_balance > target_usdt:
                # 多余的申购到理财
                transfer_amount = usdt_balance - target_usdt
                self.logger.info(f"发现可划转USDT: {transfer_amount}")
                # --- 添加最小申购金额检查 (>= 1 USDT) ---
                if transfer_amount >= 1.0:
                    try:
                        await self.exchange.transfer_to_savings('USDT', transfer_amount)
                        self.logger.info(f"已将 {transfer_amount:.2f} USDT 申购到理财")
                    except Exception as e_savings_usdt:
                        self.logger.error(f"申购USDT到理财失败: {str(e_savings_usdt)}")
                else:
                    self.logger.info(f"可划转USDT ({transfer_amount:.2f}) 低于最小申购额 1.0 USDT，跳过申购")
            elif usdt_balance < target_usdt:
                # 不足的从理财赎回
                transfer_amount = target_usdt - usdt_balance
                self.logger.info(f"从理财赎回USDT: {transfer_amount}")
                # 同样，赎回USDT也可能需要最小金额检查，如果遇到错误需添加
                try:
                    await self.exchange.transfer_to_spot('USDT', transfer_amount)
                    self.logger.info(f"已从理财赎回 {transfer_amount:.2f} USDT")
                except Exception as e_spot_usdt:
                    self.logger.error(f"从理财赎回USDT失败: {str(e_spot_usdt)}")

            # 调整BNB余额
            if bnb_balance > target_bnb:
                # 多余的申购到理财
                transfer_amount = bnb_balance - target_bnb
                self.logger.info(f"发现可划转BNB: {transfer_amount}")
                # --- 添加最小申购金额检查 ---
                if transfer_amount >= 0.01:
                    try:
                        await self.exchange.transfer_to_savings('BNB', transfer_amount)
                        self.logger.info(f"已将 {transfer_amount:.4f} BNB 申购到理财")
                    except Exception as e_savings:
                        self.logger.error(f"申购BNB到理财失败: {str(e_savings)}")
                else:
                    self.logger.info(f"可划转BNB ({transfer_amount:.4f}) 低于最小申购额 0.01 BNB，跳过申购")
            elif bnb_balance < target_bnb:
                # 不足的从理财赎回
                transfer_amount = target_bnb - bnb_balance
                self.logger.info(f"从理财赎回BNB: {transfer_amount}")
                # 赎回操作通常有不同的最低限额，或者限额较低，这里暂时不加检查
                # 如果赎回也遇到 -6005，需要在这里也加上对应的赎回最小额检查
                try:
                    await self.exchange.transfer_to_spot('BNB', transfer_amount)
                    self.logger.info(f"已从理财赎回 {transfer_amount:.4f} BNB")
                except Exception as e_spot:
                    self.logger.error(f"从理财赎回BNB失败: {str(e_spot)}")

            self.logger.info(
                f"资金分配完成\n"
                f"USDT: {total_usdt:.2f}\n"
                f"BNB: {total_bnb:.4f}"
            )
        except Exception as e:
            self.logger.error(f"初始资金检查失败: {str(e)}")

    async def _get_total_assets(self):
        """获取总资产价值（USDT）"""
        try:
            # 使用缓存避免频繁请求
            current_time = time.time()
            if hasattr(self, '_assets_cache') and \
                    current_time - self._assets_cache['time'] < 60:  # 1分钟缓存
                return self._assets_cache['value']

            # 设置一个默认返回值，以防发生异常
            default_total = self._assets_cache['value'] if hasattr(self, '_assets_cache') else 0

            balance = await self.exchange.fetch_balance()
            funding_balance = await self.exchange.fetch_funding_balance()
            current_price = await self._get_latest_price()

            # 防御性检查：确保返回的价格是有效的
            if not current_price or current_price <= 0:
                self.logger.error("获取价格失败，无法计算总资产")
                return default_total

            # 防御性检查：确保balance包含必要的键
            if not balance:
                self.logger.error("获取余额失败，返回默认总资产")
                return default_total

            # 分别获取现货和理财账户余额（使用安全的get方法）
            spot_bnb = float(balance.get('free', {}).get('BNB', 0) or 0)
            spot_usdt = float(balance.get('free', {}).get('USDT', 0) or 0)

            # 加上已冻结的余额
            spot_bnb += float(balance.get('used', {}).get('BNB', 0) or 0)
            spot_usdt += float(balance.get('used', {}).get('USDT', 0) or 0)

            # 加上理财账户余额
            fund_bnb = 0
            fund_usdt = 0
            if funding_balance:
                fund_bnb = float(funding_balance.get('BNB', 0) or 0)
                fund_usdt = float(funding_balance.get('USDT', 0) or 0)

            # 分别计算现货和理财账户总值
            spot_value = spot_usdt + (spot_bnb * current_price)
            fund_value = fund_usdt + (fund_bnb * current_price)
            total_assets = spot_value + fund_value

            # 更新缓存
            self._assets_cache = {
                'time': current_time,
                'value': total_assets
            }

            # 只在资产变化超过1%时才记录日志
            if not hasattr(self, '_last_logged_assets') or \
                    abs(total_assets - self._last_logged_assets) / max(self._last_logged_assets, 0.01) > 0.01:
                self.logger.info(
                    f"总资产: {total_assets:.2f} USDT | "
                    f"现货: {spot_value:.2f} USDT "
                    f"(BNB: {spot_bnb:.4f}, USDT: {spot_usdt:.2f}) | "
                    f"理财: {fund_value:.2f} USDT "
                    f"(BNB: {fund_bnb:.4f}, USDT: {fund_usdt:.2f})"
                )
                self._last_logged_assets = total_assets

            return total_assets

        except Exception as e:
            self.logger.error(f"计算总资产失败: {str(e)}")
            return self._assets_cache['value'] if hasattr(self, '_assets_cache') else 0

    async def _update_total_assets(self):
        """更新总资产信息"""
        try:
            balance = await self.exchange.fetch_balance()
            funding_balance = await self.exchange.fetch_funding_balance()

            # 计算总资产
            bnb_balance = float(balance['total'].get('BNB', 0))
            usdt_balance = float(balance['total'].get('USDT', 0))
            current_price = await self._get_latest_price()

            self.total_assets = usdt_balance + (bnb_balance * current_price)
            self.logger.info(f"更新总资产: {self.total_assets:.2f} USDT")

        except Exception as e:
            self.logger.error(f"更新总资产失败: {str(e)}")

    async def get_ma_data(self, short_period=20, long_period=50):
        """获取MA数据"""
        try:
            # 获取K线数据
            klines = await self.exchange.fetch_ohlcv(
                self.config.SYMBOL,
                timeframe='1h',
                limit=long_period + 10  # 多获取一些数据以确保计算准确
            )

            if not klines:
                return None, None

            # 提取收盘价
            closes = [float(x[4]) for x in klines]

            # 计算短期和长期MA
            short_ma = sum(closes[-short_period:]) / short_period
            long_ma = sum(closes[-long_period:]) / long_period

            return short_ma, long_ma

        except Exception as e:
            self.logger.error(f"获取MA数据失败: {str(e)}")
            return None, None

    async def get_macd_data(self):
        """获取MACD数据"""
        try:
            # 获取K线数据
            klines = await self.exchange.fetch_ohlcv(
                self.config.SYMBOL,
                timeframe='1h',
                limit=100  # MACD需要更多数据来计算
            )

            if not klines:
                return None, None

            # 提取收盘价
            closes = [float(x[4]) for x in klines]

            # 计算EMA12和EMA26
            ema12 = self._calculate_ema(closes, 12)
            ema26 = self._calculate_ema(closes, 26)

            # 计算MACD线
            macd_line = ema12 - ema26

            # 计算信号线（MACD的9日EMA）
            signal_line = self._calculate_ema([macd_line], 9)

            return macd_line, signal_line

        except Exception as e:
            self.logger.error(f"获取MACD数据失败: {str(e)}")
            return None, None

    async def get_adx_data(self, period=14):
        """获取ADX数据"""
        try:
            # 获取K线数据
            klines = await self.exchange.fetch_ohlcv(
                self.config.SYMBOL,
                timeframe='1h',
                limit=period + 10
            )

            if not klines:
                return None

            # 提取高低收价格
            highs = [float(x[2]) for x in klines]
            lows = [float(x[3]) for x in klines]
            closes = [float(x[4]) for x in klines]

            # 计算TR和DM
            tr = []  # True Range
            plus_dm = []  # +DM
            minus_dm = []  # -DM

            for i in range(1, len(klines)):
                tr.append(max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1])
                ))

                plus_dm.append(max(0, highs[i] - highs[i - 1]))
                minus_dm.append(max(0, lows[i - 1] - lows[i]))

            # 计算ADX
            atr = sum(tr[-period:]) / period
            plus_di = (sum(plus_dm[-period:]) / period) / atr * 100
            minus_di = (sum(minus_dm[-period:]) / period) / atr * 100
            dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
            adx = sum([dx]) / period  # 简化版ADX计算

            return adx

        except Exception as e:
            self.logger.error(f"获取ADX数据失败: {str(e)}")
            return None

    def _calculate_ema(self, data, period):
        """计算EMA"""
        if not data or len(data) == 0:
            return 0

        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price - ema) * multiplier + ema
        return ema

    async def check_buy_balance(self, current_price):
        """检查买入前的余额，如果不够则从理财赎回"""
        try:
            # 计算所需买入资金
            amount_usdt = await self._calculate_order_amount('buy')

            # 获取现货余额
            spot_balance = await self.exchange.fetch_balance({'type': 'spot'})

            # 防御性检查：确保返回的余额是有效的
            if not spot_balance or 'free' not in spot_balance:
                self.logger.error("获取现货余额失败，返回无效数据")
                return False

            spot_usdt = float(spot_balance.get('free', {}).get('USDT', 0) or 0)

            self.logger.info(f"买入前余额检查 | 所需USDT: {amount_usdt:.2f} | 现货USDT: {spot_usdt:.2f}")

            # 如果现货余额足够，直接返回成功
            if spot_usdt >= amount_usdt:
                return True

            # 现货不足，尝试从理财赎回
            self.logger.info(f"现货USDT不足，尝试从理财赎回...")
            funding_balance = await self.exchange.fetch_funding_balance()
            funding_usdt = float(funding_balance.get('USDT', 0) or 0)

            # 检查总余额是否足够
            if spot_usdt + funding_usdt < amount_usdt:
                # 总资金不足，发送通知
                error_msg = f"资金不足通知\\n交易类型: 买入\\n所需USDT: {amount_usdt:.2f}\\n" \
                            f"现货余额: {spot_usdt:.2f}\\n理财余额: {funding_usdt:.2f}\\n" \
                            f"缺口: {amount_usdt - (spot_usdt + funding_usdt):.2f}"
                self.logger.error(f"买入资金不足: 现货+理财总额不足以执行交易")
                send_pushplus_message(error_msg, "资金不足警告")
                return False

            # 计算需要赎回的金额（增加5%缓冲）
            needed_amount = (amount_usdt - spot_usdt) * 1.05

            # 从理财赎回
            self.logger.info(f"从理财赎回 {needed_amount:.2f} USDT")
            await self.exchange.transfer_to_spot('USDT', needed_amount)

            # 等待资金到账
            await asyncio.sleep(5)

            # 再次检查余额
            new_balance = await self.exchange.fetch_balance({'type': 'spot'})

            # 防御性检查：确保返回的余额是有效的
            if not new_balance or 'free' not in new_balance:
                self.logger.error("赎回后获取现货余额失败，返回无效数据")
                return False

            new_usdt = float(new_balance.get('free', {}).get('USDT', 0) or 0)

            self.logger.info(f"赎回后余额检查 | 现货USDT: {new_usdt:.2f}")

            if new_usdt >= amount_usdt:
                return True
            else:
                error_msg = f"资金赎回后仍不足\\n交易类型: 买入\\n所需USDT: {amount_usdt:.2f}\\n现货余额: {new_usdt:.2f}"
                self.logger.error(error_msg)
                send_pushplus_message(error_msg, "资金不足警告")
                return False

        except Exception as e:
            self.logger.error(f"检查买入余额失败: {str(e)}")
            send_pushplus_message(f"余额检查错误\\n交易类型: 买入\\n错误信息: {str(e)}", "系统错误")
            return False

    async def check_sell_balance(self):
        """检查卖出前的余额，如果不够则从理财赎回"""
        try:
            # 获取现货余额
            spot_balance = await self.exchange.fetch_balance({'type': 'spot'})

            # 防御性检查：确保返回的余额是有效的
            if not spot_balance or 'free' not in spot_balance:
                self.logger.error("获取现货余额失败，返回无效数据")
                return False

            spot_bnb = float(spot_balance.get('free', {}).get('BNB', 0) or 0)

            # 计算所需数量
            amount_usdt = await self._calculate_order_amount('sell')

            # 确保当前价格有效
            if not self.current_price or self.current_price <= 0:
                self.logger.error("当前价格无效，无法计算BNB需求量")
                return False

            bnb_needed = amount_usdt / self.current_price

            self.logger.info(f"卖出前余额检查 | 所需BNB: {bnb_needed:.8f} | 现货BNB: {spot_bnb:.8f}")

            # 如果现货余额足够，直接返回成功
            if spot_bnb >= bnb_needed:
                return True

            # 现货不足，尝试从理财赎回
            self.logger.info(f"现货BNB不足，尝试从理财赎回...")
            funding_balance = await self.exchange.fetch_funding_balance()
            funding_bnb = float(funding_balance.get('BNB', 0) or 0)

            # 检查总余额是否足够
            if spot_bnb + funding_bnb < bnb_needed:
                # 总资金不足，发送通知
                error_msg = f"资金不足通知\\n交易类型: 卖出\\n所需BNB: {bnb_needed:.8f}\\n" \
                            f"现货余额: {spot_bnb:.8f}\\n理财余额: {funding_bnb:.8f}\\n" \
                            f"缺口: {bnb_needed - (spot_bnb + funding_bnb):.8f}"
                self.logger.error(f"卖出资金不足: 现货+理财总额不足以执行交易")
                send_pushplus_message(error_msg, "资金不足警告")
                return False

            # 计算需要赎回的金额（增加5%缓冲）
            needed_amount = (bnb_needed - spot_bnb) * 1.05

            # 从理财赎回
            self.logger.info(f"从理财赎回 {needed_amount:.8f} BNB")
            await self.exchange.transfer_to_spot('BNB', needed_amount)

            # 等待资金到账
            await asyncio.sleep(5)

            # 再次检查余额
            new_balance = await self.exchange.fetch_balance({'type': 'spot'})

            # 防御性检查：确保返回的余额是有效的
            if not new_balance or 'free' not in new_balance:
                self.logger.error("赎回后获取现货余额失败，返回无效数据")
                return False

            new_bnb = float(new_balance.get('free', {}).get('BNB', 0) or 0)

            self.logger.info(f"赎回后余额检查 | 现货BNB: {new_bnb:.8f}")

            if new_bnb >= bnb_needed:
                return True
            else:
                error_msg = f"资金赎回后仍不足\\n交易类型: 卖出\\n所需BNB: {bnb_needed:.8f}\\n现货余额: {new_bnb:.8f}"
                self.logger.error(error_msg)
                send_pushplus_message(error_msg, "资金不足警告")
                return False

        except Exception as e:
            self.logger.error(f"检查卖出余额失败: {str(e)}")
            send_pushplus_message(f"余额检查错误\\n交易类型: 卖出\\n错误信息: {str(e)}", "系统错误")
            return False

    async def _execute_trade(self, side, price, amount, retry_count=None):
        """执行交易并发送通知"""
        try:
            order = await self.exchange.create_order(
                self.symbol,
                'market',
                side,
                amount,
                price
            )

            # 计算交易总额
            total = float(amount) * float(price)

            # 使用新的格式化函数发送通知
            message = format_trade_message(
                side=side,
                symbol=self.symbol,
                price=float(price),
                amount=float(amount),
                total=total,
                grid_size=self.grid_size,
                retry_count=retry_count
            )

            send_pushplus_message(message, "交易执行通知")

            return order
        except Exception as e:
            self.logger.error(f"执行交易失败: {str(e)}")
            raise
