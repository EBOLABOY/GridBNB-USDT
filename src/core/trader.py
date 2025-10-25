from src.config.settings import TradingConfig, FLIP_THRESHOLD, settings
from src.core.exchange_client import ExchangeClient
from src.core.order_tracker import OrderTracker, OrderThrottler
from src.strategies.risk_manager import AdvancedRiskManager, RiskState
import logging
import asyncio
import numpy as np
from datetime import datetime
import time
import math
from src.utils.helpers import send_pushplus_message, format_trade_message
import json
import os
from src.services.monitor import TradingMonitor
# S1策略已移除: from src.strategies.position_controller_s1 import PositionControllerS1

# AI策略导入 (优雅降级)
try:
    from src.strategies.ai_strategy import AITradingStrategy
    AI_STRATEGY_AVAILABLE = True
except ImportError:
    AI_STRATEGY_AVAILABLE = False
    logging.warning("AI策略模块未安装或导入失败，AI辅助功能禁用")


class GridTrader:
    def __init__(self, exchange, config, symbol: str):
        """初始化网格交易器"""
        self.exchange = exchange
        self.config = config
        self.symbol = symbol  # 使用传入的symbol参数

        # 解析并存储基础和计价货币
        try:
            self.base_asset, self.quote_asset = self.symbol.split('/')
        except ValueError:
            raise ValueError(f"交易对格式不正确: {self.symbol}。应为 'BASE/QUOTE' 格式。")

        # 从结构化配置中获取交易对特定的初始值
        symbol_params = settings.INITIAL_PARAMS_JSON.get(self.symbol, {})

        # 优先使用交易对特定配置，否则使用全局默认值
        self.base_price = symbol_params.get('initial_base_price', 0.0)  # 默认为0，让initialize逻辑处理
        self.grid_size = symbol_params.get('initial_grid', settings.INITIAL_GRID)
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
        self.start_time = time.time()

        # EWMA波动率状态变量
        self.ewma_volatility = None  # EWMA波动率
        self.last_price = None  # 上一次价格，用于计算收益率
        self.ewma_initialized = False  # EWMA是否已初始化

        # 日志也带上交易对标识
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{self.symbol}]")

        self.symbol_info = None
        self.amount_precision = None  # 数量精度
        self.price_precision = None   # 价格精度
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
        # S1策略已移除: self.position_controller_s1 = PositionControllerS1(self)

        # 独立的监测状态变量，避免买入和卖出监测相互干扰
        self.is_monitoring_buy = False   # 是否在监测买入机会
        self.is_monitoring_sell = False  # 是否在监测卖出机会

        # 【新增】波动率平滑化相关变量
        self.volatility_history = []  # 用于存储最近的波动率值
        self.volatility_smoothing_window = 3  # 平滑窗口大小，取最近3次的平均值

        # 状态持久化相关 - 状态文件名与交易对挂钩
        state_filename = f"trader_state_{self.symbol.replace('/', '_')}.json"
        self.state_file_path = os.path.join(os.path.dirname(__file__), 'data', state_filename)

        # AI策略初始化 (如果启用)
        self.ai_strategy = None
        if settings.AI_ENABLED and AI_STRATEGY_AVAILABLE:
            try:
                self.ai_strategy = AITradingStrategy(self)
                self.logger.info("AI辅助策略已启用")
            except Exception as e:
                self.logger.error(f"AI策略初始化失败: {e}", exc_info=True)
                self.ai_strategy = None
        elif settings.AI_ENABLED and not AI_STRATEGY_AVAILABLE:
            self.logger.warning("AI_ENABLED=true 但AI策略模块不可用")

        # AI策略相关状态变量
        self.last_volatility = 0  # 用于AI策略

    def _save_state(self):
        """【重构后】以原子方式安全地保存当前核心策略状态到文件"""
        state = {
            'base_price': self.base_price,
            'grid_size': self.grid_size,
            'highest': self.highest,
            'lowest': self.lowest,
            'last_grid_adjust_time': self.last_grid_adjust_time,
            'last_trade_time': self.last_trade_time,
            'last_trade_price': self.last_trade_price,
            'timestamp': time.time(),
            # EWMA波动率状态
            'ewma_volatility': self.ewma_volatility,
            'last_price': self.last_price,
            'ewma_initialized': self.ewma_initialized,
            # 独立监测状态
            'is_monitoring_buy': self.is_monitoring_buy,
            'is_monitoring_sell': self.is_monitoring_sell,
            # 波动率平滑相关
            'volatility_history': self.volatility_history
        }

        temp_file_path = self.state_file_path + ".tmp"

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)

            # 1. 写入临时文件
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            # 2. 原子性地重命名临时文件为正式文件
            os.rename(temp_file_path, self.state_file_path)

            self.logger.info(f"核心状态已安全保存。基准价: {self.base_price:.2f}, 网格: {self.grid_size:.2f}%")

        except Exception as e:
            self.logger.error(f"保存核心状态失败: {e}")

        finally:
            # 3. 确保临时文件在任何情况下都被删除
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as e:
                    self.logger.error(f"删除临时状态文件失败: {e}")

    def _load_state(self):
        """从文件加载核心策略状态"""
        if not os.path.exists(self.state_file_path):
            self.logger.info("未找到状态文件，将使用默认配置启动。")
            return

        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # 加载并验证状态值
            saved_base_price = state.get('base_price')
            if saved_base_price and saved_base_price > 0:
                self.base_price = float(saved_base_price)

            saved_grid_size = state.get('grid_size')
            if saved_grid_size and saved_grid_size > 0:
                self.grid_size = float(saved_grid_size)

            self.highest = state.get('highest')  # 可以是 None
            self.lowest = state.get('lowest')    # 可以是 None

            saved_last_grid_adjust_time = state.get('last_grid_adjust_time')
            if saved_last_grid_adjust_time:
                self.last_grid_adjust_time = float(saved_last_grid_adjust_time)

            saved_last_trade_time = state.get('last_trade_time')
            if saved_last_trade_time:
                self.last_trade_time = float(saved_last_trade_time)

            saved_last_trade_price = state.get('last_trade_price')
            if saved_last_trade_price:
                self.last_trade_price = float(saved_last_trade_price)

            # 加载EWMA波动率状态
            saved_ewma_volatility = state.get('ewma_volatility')
            if saved_ewma_volatility is not None:
                self.ewma_volatility = float(saved_ewma_volatility)

            saved_last_price = state.get('last_price')
            if saved_last_price is not None:
                self.last_price = float(saved_last_price)

            saved_ewma_initialized = state.get('ewma_initialized')
            if saved_ewma_initialized is not None:
                self.ewma_initialized = bool(saved_ewma_initialized)

            # 加载独立监测状态
            saved_is_monitoring_buy = state.get('is_monitoring_buy')
            if saved_is_monitoring_buy is not None:
                self.is_monitoring_buy = bool(saved_is_monitoring_buy)

            saved_is_monitoring_sell = state.get('is_monitoring_sell')
            if saved_is_monitoring_sell is not None:
                self.is_monitoring_sell = bool(saved_is_monitoring_sell)

            # 加载波动率历史记录
            saved_volatility_history = state.get('volatility_history')
            if saved_volatility_history is not None and isinstance(saved_volatility_history, list):
                self.volatility_history = saved_volatility_history

            self.logger.info(
                f"成功从文件加载状态。基准价: {self.base_price:.2f}, 网格: {self.grid_size:.2f}%, "
                f"EWMA已初始化: {self.ewma_initialized}, 监测状态: 买入={self.is_monitoring_buy}, 卖出={self.is_monitoring_sell}, "
                f"波动率历史记录数: {len(self.volatility_history)}"
            )
        except Exception as e:
            self.logger.error(f"加载核心状态失败，将使用默认值: {e}")

    async def initialize(self):
        if self.initialized:
            return

        # 首先加载保存的状态
        self._load_state()

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

            self.symbol_info = self.exchange.exchange.market(self.symbol)

            # 从市场信息中获取精度
            if self.symbol_info and 'precision' in self.symbol_info:
                try:
                    amount_precision = self.symbol_info['precision'].get('amount')
                    price_precision = self.symbol_info['precision'].get('price')

                    self.amount_precision = int(float(amount_precision)) if amount_precision is not None else None
                    self.price_precision = int(float(price_precision)) if price_precision is not None else None
                    self.logger.info(f"交易对精度: 数量 {self.amount_precision}, 价格 {self.price_precision}")
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"精度转换失败: amount={amount_precision}, price={price_precision}, error={e}")
                    self.logger.warning("使用默认精度: 数量 6, 价格 2")
                    self.amount_precision = 6
                    self.price_precision = 2
            else:
                self.logger.warning("无法获取交易对精度信息，将使用默认值")
                # 使用动态默认精度，而不是硬编码BNB/USDT精度
                self.amount_precision = 6  # 通用默认精度
                self.price_precision = 2   # 通用默认精度

            # 设置基准价：优先使用加载的状态，然后是交易对特定配置，最后是实时价格
            if self.base_price is None or self.base_price == 0:
                # self.base_price 在 __init__ 中已经从 INITIAL_PARAMS_JSON 加载
                # 如果它仍然是0，说明配置中没指定，此时才获取实时价格
                self.logger.info(f"交易对 {self.symbol} 未在INITIAL_PARAMS_JSON中指定初始基准价")
                self.base_price = await self._get_latest_price()
                self.logger.info(f"使用实时价格作为基准价: {self.base_price}")
            else:
                self.logger.info(f"使用配置的基准价: {self.base_price}")

            if self.base_price is None:
                raise ValueError("无法获取当前价格")

            self.logger.info(f"初始化完成 | 交易对: {self.symbol} | 基准价: {self.base_price}")

            # 发送启动通知
            threshold = FLIP_THRESHOLD(self.grid_size)  # 计算实际阈值
            send_pushplus_message(
                f"网格交易启动成功\n"
                f"交易对: {self.symbol}\n"
                f"基准价: {self.base_price} {self.quote_asset}\n"
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
            ticker = await self.exchange.fetch_ticker(self.symbol)
            if ticker and 'last' in ticker:
                return ticker['last']
            self.logger.error("获取价格失败: 返回数据格式不正确")
            return self.base_price
        except Exception as e:
            self.logger.error(f"获取最新价格失败: {str(e)}")
            return self.base_price

    def update_config(self):
        """
        热重载配置参数（阶段4优化）

        支持动态更新的参数：
        - INITIAL_GRID: 初始网格大小
        - MIN_TRADE_AMOUNT: 最小交易金额
        - MAX_POSITION_RATIO: 最大仓位比例
        - MIN_POSITION_RATIO: 最小仓位比例

        注意：
        - 不更新 BINANCE_API_KEY/SECRET（需要重启）
        - 不更新 SYMBOLS（需要重启）
        - 不更新交易对特定的 initial_base_price（避免破坏策略连续性）
        """
        try:
            self.logger.info(f"开始更新配置: {self.symbol}")

            # 1. 重新创建 TradingConfig 实例（会自动从 settings 读取最新配置）
            from src.config.settings import TradingConfig, settings, SYMBOLS_LIST
            new_config = TradingConfig()

            # 2. 更新网格大小（如果配置了交易对特定值，则使用；否则使用全局默认值）
            symbol_params = settings.INITIAL_PARAMS_JSON.get(self.symbol, {})
            new_grid_size = symbol_params.get('initial_grid', settings.INITIAL_GRID)

            if new_grid_size != self.grid_size:
                self.logger.info(f"网格大小更新: {self.grid_size}% → {new_grid_size}%")
                self.grid_size = new_grid_size

            # 3. 更新风控参数
            if new_config.RISK_PARAMS['position_limit'] != self.config.RISK_PARAMS['position_limit']:
                self.logger.info(
                    f"仓位限制更新: {self.config.RISK_PARAMS['position_limit']} → "
                    f"{new_config.RISK_PARAMS['position_limit']}"
                )

            # 4. 更新网格参数
            if new_config.GRID_PARAMS != self.config.GRID_PARAMS:
                self.logger.info(f"网格参数已更新")
                self.logger.debug(f"旧参数: {self.config.GRID_PARAMS}")
                self.logger.debug(f"新参数: {new_config.GRID_PARAMS}")

            # 5. 替换 config 对象
            self.config = new_config

            # 6. 通知风险管理器重新评估
            if self.risk_manager:
                self.risk_manager.config = new_config

            self.logger.info(f"✅ 配置更新完成: {self.symbol}")

        except Exception as e:
            self.logger.error(f"配置更新失败: {e}", exc_info=True)

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
            latest_fills = await self.exchange.fetch_my_trades(self.symbol, limit=limit)
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
        initial_lower_band = self._get_lower_band()

        if current_price <= initial_lower_band:
            # --- START OF CORRECTION ---
            self.is_monitoring_buy = True

            old_lowest = self.lowest if self.lowest is not None else float('inf')

            # 正确的逻辑：self.lowest 只能减小，不能增加
            self.lowest = current_price if self.lowest is None else min(self.lowest, current_price)

            # 只有在最低价确实被刷新(降低)时，才打印日志
            if self.lowest < old_lowest:
                threshold = FLIP_THRESHOLD(self.grid_size)
                self.logger.info(
                    f"买入监测 | "
                    f"当前价: {current_price:.2f} | "
                    f"触发价: {initial_lower_band:.5f} | "
                    f"最低价: {self.lowest:.2f} (已更新) | "
                    f"反弹阈值: {threshold * 100:.2f}%"
                )
            # --- END OF CORRECTION ---

            # 触发买入的逻辑保持不变
            threshold = FLIP_THRESHOLD(self.grid_size)
            if self.lowest and current_price >= self.lowest * (1 + threshold):
                self.is_monitoring_buy = False # 准备交易，退出监测
                self.logger.info(
                    f"触发买入信号 | 当前价: {current_price:.2f} | 已反弹: {(current_price / self.lowest - 1) * 100:.2f}%")
                # 只返回价格条件是否满足，余额检查在execute_order中进行
                return True
        else:
            # 只有当价格回升，并且我们之前正处于"买入监测"状态时，才重置
            if self.is_monitoring_buy:
                self.logger.info(f"价格已回升至 {current_price:.2f}，高于下轨 {initial_lower_band:.2f}。重置买入监测状态。")
                self.is_monitoring_buy = False
                self._reset_extremes()

        return False

    async def _check_sell_signal(self):
        current_price = self.current_price
        initial_upper_band = self._get_upper_band()

        if current_price >= initial_upper_band:
            # --- START OF CORRECTION ---
            # 无论如何，先进入监测状态
            self.is_monitoring_sell = True

            # 使用一个临时变量来记录旧的最高价，方便对比
            old_highest = self.highest if self.highest is not None else 0.0

            # 正确的逻辑：self.highest 只能增加，不能减少
            self.highest = current_price if self.highest is None else max(self.highest, current_price)

            # 只有在最高价确实被刷新(提高)时，才打印日志
            if self.highest > old_highest:
                threshold = FLIP_THRESHOLD(self.grid_size)
                dynamic_trigger_price = self.highest * (1 - threshold)
                self.logger.info(
                    f"卖出监测 | "
                    f"当前价: {current_price:.2f} | "
                    f"触发价(动态): {dynamic_trigger_price:.5f} | "
                    f"最高价: {self.highest:.2f} (已更新)"
                )
            # --- END OF CORRECTION ---

            # 触发卖出的逻辑保持不变
            threshold = FLIP_THRESHOLD(self.grid_size)
            if self.highest and current_price <= self.highest * (1 - threshold):
                self.is_monitoring_sell = False  # 准备交易，退出监测
                self.logger.info(
                    f"触发卖出信号 | 当前价: {current_price:.2f} | 目标价: {self.highest * (1 - threshold):.5f} | 已下跌: {(1 - current_price / self.highest) * 100:.2f}%")
                # 只返回价格条件是否满足，余额检查在execute_order中进行
                return True
        else:
            # 只有当价格回落，并且我们之前正处于"卖出监测"状态时，才意味着本次机会结束，可以重置了
            if self.is_monitoring_sell:
                self.logger.info(f"价格已回落至 {current_price:.2f}，低于上轨 {initial_upper_band:.2f}。重置卖出监测状态。")
                self.is_monitoring_sell = False
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

            total_assets = await self._get_pair_specific_assets_value()

            # 目标金额严格等于总资产的10%
            amount = total_assets * 0.1

            # 只在金额变化超过1%时记录日志
            # 使用 max(..., 0.01) 避免除以零错误
            if not hasattr(self, f'{cache_key}_last') or \
                    abs(amount - getattr(self, f'{cache_key}_last', 0)) / max(getattr(self, f'{cache_key}_last', 0.01),
                                                                              0.01) > 0.01:
                self.logger.info(
                    f"目标订单金额计算 | "
                    f"交易对相关资产: {total_assets:.2f} {self.quote_asset} | "
                    f"计算金额 (10%): {amount:.2f} {self.quote_asset}"
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
        return balance.get('free', {}).get(currency, 0) * settings.SAFETY_MARGIN

    async def _calculate_dynamic_interval_seconds(self):
        """根据波动率动态计算网格调整的时间间隔（秒）"""
        try:
            volatility = await self._calculate_volatility()
            if volatility is None:  # Handle case where volatility calculation failed
                raise ValueError("波动率计算失败")  # Volatility calculation failed

            interval_rules = TradingConfig.DYNAMIC_INTERVAL_PARAMS['volatility_to_interval_hours']
            default_interval_hours = TradingConfig.DYNAMIC_INTERVAL_PARAMS['default_interval_hours']

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
            default_interval_hours = TradingConfig.DYNAMIC_INTERVAL_PARAMS.get('default_interval_hours', 1.0)
            return default_interval_hours * 3600

    async def main_loop(self):
        consecutive_errors = 0
        max_consecutive_errors = 5

        while True:
            try:
                # ------------------------------------------------------------------
                # 阶段一：初始化与状态更新
                # ------------------------------------------------------------------
                if not self.initialized:
                    await self.initialize()

                # 获取最新的价格，这是后续所有决策的基础
                current_price = await self._get_latest_price()
                if not current_price:
                    await asyncio.sleep(5)
                    continue
                self.current_price = current_price

                # ========== 新增：获取本轮循环的统一账户快照 ==========
                spot_balance = await self.exchange.fetch_balance()
                funding_balance = await self.exchange.fetch_funding_balance()
                # ========== 新增结束 ==========

                # --- 核心理念：网格策略独立运行，AI策略全局洞察并行决策 ---

                # ------------------------------------------------------------------
                # 阶段二：周期性维护模块 (始终运行，保证机器人认知更新)
                # ------------------------------------------------------------------

                # 1. 检查是否需要调整网格大小 (包含波动率计算)
                dynamic_interval_seconds = await self._calculate_dynamic_interval_seconds()
                if time.time() - self.last_grid_adjust_time > dynamic_interval_seconds:
                    self.logger.info(
                        f"维护时间到达，准备更新波动率并调整网格 (间隔: {dynamic_interval_seconds / 3600:.2f} 小时).")
                    # adjust_grid_size 内部会调用 _calculate_volatility
                    await self.adjust_grid_size()
                    self.last_grid_adjust_time = time.time() # 更新时间戳

                # ------------------------------------------------------------------
                # 阶段三：网格交易决策模块 (根据风控和市场信号执行)
                # ------------------------------------------------------------------

                # 1. 【核心】首先获取唯一的风控许可
                risk_state = await self.risk_manager.check_position_limits(spot_balance, funding_balance)

                # 2. 定义标志位，确保一轮循环只做一次主网格交易
                trade_executed_this_loop = False

                # 3. 卖出逻辑：只有在风控允许的情况下，才去检查信号
                if risk_state != RiskState.ALLOW_BUY_ONLY:
                    sell_signal = await self._check_signal_with_retry(
                        lambda: self._check_sell_signal(), "卖出检测")
                    if sell_signal:
                        if await self.execute_order('sell'):
                            trade_executed_this_loop = True

                # 4. 买入逻辑：如果没卖出，且风控允许，才去检查买入信号
                if not trade_executed_this_loop and risk_state != RiskState.ALLOW_SELL_ONLY:
                    buy_signal = await self._check_signal_with_retry(
                        lambda: self._check_buy_signal(), "买入检测")
                    if buy_signal:
                        if await self.execute_order('buy'):
                            trade_executed_this_loop = True

                # ------------------------------------------------------------------
                # 阶段四：AI策略独立决策 (与网格策略并行，全局洞察)
                # ------------------------------------------------------------------
                # AI策略作为"大脑"，了解网格运行状态，独立做出趋势判断和建议
                # 与网格策略不冲突，可以同时执行

                if self.ai_strategy:
                    try:
                        # 检查是否应该触发AI分析
                        should_trigger, trigger_reason = await self.ai_strategy.should_trigger(current_price)

                        if should_trigger:
                            self.logger.info(f"🤖 触发AI分析 | 原因: {trigger_reason.value}")

                            # 执行AI分析并获取建议
                            # AI可以看到完整的网格状态、持仓情况、交易历史
                            suggestion = await self.ai_strategy.analyze_and_suggest(trigger_reason)

                            if suggestion and suggestion['confidence'] >= settings.AI_CONFIDENCE_THRESHOLD:
                                action = suggestion['action']
                                confidence = suggestion['confidence']
                                amount_pct = suggestion['suggested_amount_pct']

                                self.logger.info(
                                    f"🤖 AI建议 | 操作: {action} | "
                                    f"置信度: {confidence}% | "
                                    f"金额比例: {amount_pct}% | "
                                    f"理由: {suggestion['reason']}"
                                )

                                # AI策略独立执行，不受网格交易影响
                                if action == 'buy':
                                    # AI建议买入 - 检查风控许可后执行
                                    if risk_state != RiskState.ALLOW_SELL_ONLY:
                                        await self._execute_ai_trade('buy', amount_pct, suggestion)
                                    else:
                                        self.logger.warning("🤖 AI建议买入，但当前风控状态不允许")

                                elif action == 'sell':
                                    # AI建议卖出 - 检查风控许可后执行
                                    if risk_state != RiskState.ALLOW_BUY_ONLY:
                                        await self._execute_ai_trade('sell', amount_pct, suggestion)
                                    else:
                                        self.logger.warning("🤖 AI建议卖出，但当前风控状态不允许")

                                else:  # hold
                                    self.logger.info(f"🤖 AI建议持仓观望 | 理由: {suggestion.get('reason', 'N/A')}")
                            else:
                                if suggestion:
                                    self.logger.info(
                                        f"🤖 AI建议置信度不足 ({suggestion['confidence']}% < {settings.AI_CONFIDENCE_THRESHOLD}%)，不执行"
                                    )
                    except Exception as e:
                        self.logger.error(f"🤖 AI策略执行异常: {e}", exc_info=True)
                        # AI异常不影响网格策略继续运行

                # --- 逻辑执行完毕 ---

                # 循环成功，重置错误计数器
                consecutive_errors = 0
                await asyncio.sleep(5)  # 主循环的固定休眠时间

            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"主循环发生错误 (第{consecutive_errors}次连续失败): {e}", exc_info=True)

                if consecutive_errors >= max_consecutive_errors:
                    fatal_msg = (
                        f"交易对[{self.symbol}]连续失败 {max_consecutive_errors} 次，任务已自动停止！\n"
                        f"最后一次错误: {str(e)}"
                    )
                    self.logger.critical(fatal_msg)
                    try:
                        send_pushplus_message(fatal_msg, f"!!!系统致命错误 - {self.symbol}!!!")
                    except Exception as notify_error:
                        self.logger.error(f"发送紧急通知失败: {notify_error}")
                    break # 退出循环，结束此交易对的任务

                await asyncio.sleep(30) # 发生错误后等待30秒重试

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
            required_quote = settings.MIN_TRADE_AMOUNT * 2  # 保持两倍最小交易额
            required_base = required_quote / current_price

            # 获取现货余额
            spot_quote = float(balance['free'].get(self.quote_asset, 0))
            spot_base = float(balance['free'].get(self.base_asset, 0))

            # 一次性检查和赎回所需资金
            transfers = []
            if spot_quote < required_quote:
                transfers.append({
                    'asset': self.quote_asset,
                    'amount': required_quote - spot_quote
                })
            if spot_base < required_base:
                transfers.append({
                    'asset': self.base_asset,
                    'amount': required_base - spot_base
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
            open_orders = await self.exchange.fetch_open_orders(self.symbol)
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

        # 保存状态
        self._save_state()

        # 5) 推送通知
        msg = format_trade_message(
            side='buy' if side == 'buy' else 'sell',
            symbol=self.symbol,
            price=order_price,
            amount=order_amount,
            total=order_price * order_amount,
            grid_size=self.grid_size,
            base_asset=self.base_asset,
            quote_asset=self.quote_asset,
            retry_count=(retry_count + 1, max_retries)
        )
        send_pushplus_message(msg, "交易成功通知")

        # 6) 将多余资金转入理财 (如果功能开启)
        if settings.ENABLE_SAVINGS_FUNCTION:
            await self._transfer_excess_funds()
        else:
            self.logger.info("理财功能已禁用，跳过资金转移。")

        return order_dict

    async def execute_order(self, side):
        """执行订单，带重试机制"""
        max_retries = 10  # 最大重试次数
        retry_count = 0
        check_interval = 3  # 下单后等待检查时间（秒）

        while retry_count < max_retries:
            try:
                # 获取最新订单簿数据
                order_book = await self.exchange.fetch_order_book(self.symbol, limit=5)
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
                amount_quote = await self._calculate_order_amount(side)
                amount = self._adjust_amount_precision(amount_quote / order_price)

                # 调整价格精度
                order_price = self._adjust_price_precision(order_price)

                # 检查余额是否足够 - 需要获取最新的余额信息
                spot_balance = await self.exchange.fetch_balance({'type': 'spot'})
                funding_balance = await self.exchange.fetch_funding_balance()

                if not await self._ensure_balance_for_trade(side, spot_balance, funding_balance):
                    self.logger.warning(f"{side}余额不足，第 {retry_count + 1} 次尝试中止")
                    return False

                # 为了日志记录，将字符串类型的 amount 临时转为浮点数
                log_display_amount = float(amount)
                self.logger.info(
                    f"尝试第 {retry_count + 1}/{max_retries} 次 {side} 单 | "
                    f"价格: {order_price} | "
                    f"金额: {amount_quote:.2f} {self.quote_asset} | "
                    f"数量: {log_display_amount:.8f} {self.base_asset}"
                )

                # 创建订单
                order = await self.exchange.create_order(
                    self.symbol,
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
                updated_order = await self.exchange.fetch_order(order_id, self.symbol)

                # 订单已成交
                if updated_order['status'] == 'closed':
                    self.logger.info(f"订单已成交 | ID: {order_id}")
                    return await self._handle_filled_order(
                        updated_order, side, retry_count, max_retries
                    )

                # 如果订单未成交，取消订单并重试
                self.logger.warning(f"订单未成交，尝试取消 | ID: {order_id} | 状态: {updated_order['status']}")
                try:
                    await self.exchange.cancel_order(order_id, self.symbol)
                    self.logger.info(f"订单已取消，准备重试 | ID: {order_id}")
                except Exception as e:
                    # 如果取消订单时出错，检查是否已成交
                    self.logger.warning(f"取消订单时出错: {str(e)}，再次检查订单状态")
                    try:
                        check_order = await self.exchange.fetch_order(order_id, self.symbol)
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
                        await self.exchange.cancel_order(order_id, self.symbol)
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
📊 交易对: {self.symbol}
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
📊 交易对: {self.symbol}
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
                available = float(balance['free'].get(self.quote_asset, 0))
                if available >= required:
                    return True
            else:
                available = float(balance['free'].get(self.base_asset, 0))
                if available >= amount:
                    return True

            self.logger.info(f"等待资金到账 ({i + 1}/{max_attempts})...")
            await asyncio.sleep(1)

        raise Exception("等待资金到账超时")

    async def _adjust_grid_after_trade(self):
        """根据市场波动动态调整网格大小"""
        trade_count = self.order_tracker.trade_count
        if trade_count % TradingConfig.GRID_PARAMS.get('adjust_interval', 5) == 0:
            volatility = await self._calculate_volatility()

            # 根据波动率调整
            high_threshold = TradingConfig.GRID_PARAMS.get('volatility_threshold', {}).get('high', 0.3)
            if volatility > high_threshold:
                new_size = min(
                    self.grid_size * 1.1,  # 扩大10%
                    TradingConfig.GRID_PARAMS['max']
                )
                action = "扩大"
            else:
                new_size = max(
                    self.grid_size * 0.9,  # 缩小10%
                    TradingConfig.GRID_PARAMS['min']
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
                grid_size=self.grid_size,
                base_asset=self.base_asset,
                quote_asset=self.quote_asset
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
            self.grid_size = TradingConfig.GRID_PARAMS.get('initial', settings.INITIAL_GRID)
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
                    order = await self.exchange.fetch_order(order_id, self.symbol, params)

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
                            f"{self.base_asset} {{'买入' if side == 'buy' else '卖出'}}单成交\\n"
                            f"价格: {order['price']} {self.quote_asset}"
                        )
                    elif order['status'] == 'open':
                        # 取消未成交订单
                        params = {
                            'timestamp': int(time.time() * 1000 + self.exchange.time_diff),
                            'recvWindow': 5000
                        }
                        await self.exchange.cancel_order(order_id, self.symbol, params)
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
        """根据【平滑后】的波动率和市场趋势调整网格大小"""
        try:
            # 1. 计算当前的瞬时波动率
            current_volatility = await self._calculate_volatility()
            if current_volatility is None:
                self.logger.warning("无法计算当前波动率，跳过网格调整。")
                return

            # 2. 更新波动率历史记录
            self.volatility_history.append(current_volatility)
            # 保持历史记录的长度不超过平滑窗口大小
            if len(self.volatility_history) > self.volatility_smoothing_window:
                self.volatility_history.pop(0)  # 移除最旧的记录

            # 3. 计算平滑后的波动率（移动平均值）
            # 只有当历史记录足够长时才开始计算，以保证平均值的有效性
            if len(self.volatility_history) < self.volatility_smoothing_window:
                self.logger.info(f"正在收集波动率数据 ({len(self.volatility_history)}/{self.volatility_smoothing_window})... 瞬时值: {current_volatility:.4f}")
                return  # 数据不足，暂时不调整

            smoothed_volatility = sum(self.volatility_history) / len(self.volatility_history)

            self.logger.info(f"波动率分析 | 瞬时值: {current_volatility:.4f} | 平滑后({self.volatility_smoothing_window}次平均): {smoothed_volatility:.4f}")

            # 4. 【关键】使用平滑后的波动率来决定网格大小
            volatility_for_decision = smoothed_volatility

            # ========== 使用连续函数计算新网格大小 ==========
            # 1. 从配置中获取连续调整的参数
            params = TradingConfig.GRID_CONTINUOUS_PARAMS
            base_grid = params['base_grid']
            center_volatility = params['center_volatility']
            sensitivity_k = params['sensitivity_k']

            # 2. 应用线性函数公式
            # 公式: 新网格 = 基础网格 + k * (当前平滑波动率 - 波动率中心点)
            new_grid = base_grid + sensitivity_k * (volatility_for_decision - center_volatility)

            self.logger.info(
                f"连续网格计算 | "
                f"波动率: {volatility_for_decision:.2%} | "
                f"计算公式: {base_grid:.2f}% + {sensitivity_k} * ({volatility_for_decision:.2%} - {center_volatility:.2%}) = {new_grid:.2f}%"
            )

            # 确保网格在允许范围内
            new_grid = max(min(new_grid, TradingConfig.GRID_PARAMS['max']), TradingConfig.GRID_PARAMS['min'])

            # 只有在变化大于0.01%时才更新，避免频繁的微小调整
            if abs(new_grid - self.grid_size) > 0.01:
                self.logger.info(
                    f"调整网格大小 | "
                    f"平滑波动率: {volatility_for_decision:.2%} | "  # 日志中体现是平滑值
                    f"原网格: {self.grid_size:.2f}% | "
                    f"新网格 (限定范围后): {new_grid:.2f}%"
                )
                self.grid_size = new_grid
                self.last_grid_adjust_time = time.time()  # 更新时间
                # 保存状态
                self._save_state()

        except Exception as e:
            self.logger.error(f"调整网格大小失败: {str(e)}")

    async def _calculate_volatility(self):
        """
        计算改进的混合波动率：7天4小时线传统波动率 + EWMA波动率
        使用4小时K线数据计算7天年化波动率，结合EWMA提供敏感性
        更短的时间窗口让机器人更敏感地响应短期市场变化
        """
        try:
            # 获取7天4小时K线数据 (7天 * 6根4小时K线 = 42根)
            klines = await self.exchange.fetch_ohlcv(
                self.symbol,
                timeframe='4h',  # 从'1d'改为'4h'
                limit=42         # 7天 * 6根4小时K线 = 42
            )

            if not klines or len(klines) < 2:
                self.logger.warning("K线数据不足，返回默认波动率")
                return 0.2  # 返回20%的默认波动率

            # 提取收盘价
            prices = [float(k[4]) for k in klines]
            current_price = prices[-1]

            # 计算7天传统波动率 (传递完整的klines数据以支持成交量加权)
            traditional_volatility = self._calculate_traditional_volatility(klines)

            # 计算EWMA波动率
            ewma_volatility = self._update_ewma_volatility(current_price)

            # 混合波动率：EWMA权重0.7，传统波动率权重0.3
            if ewma_volatility is not None:
                hybrid_volatility = (
                    settings.VOLATILITY_HYBRID_WEIGHT * ewma_volatility +
                    (1 - settings.VOLATILITY_HYBRID_WEIGHT) * traditional_volatility
                )
                self.logger.debug(
                    f"混合波动率计算 | 传统: {traditional_volatility:.4f} | "
                    f"EWMA: {ewma_volatility:.4f} | 混合: {hybrid_volatility:.4f}"
                )
            else:
                # EWMA未初始化时使用传统波动率
                hybrid_volatility = traditional_volatility
                self.logger.debug(f"使用传统波动率: {traditional_volatility:.4f}")

            return hybrid_volatility

        except Exception as e:
            self.logger.error(f"计算波动率失败: {str(e)}")
            return 0.2  # 返回默认波动率而不是0

    def _calculate_traditional_volatility(self, klines):
        """
        计算传统的7天年化波动率 (已优化：支持成交量加权)
        使用对数收益率的标准差，基于4小时数据
        """
        if len(klines) < 2:
            return 0.2

        # 提取收盘价和成交量
        prices = np.array([float(k[4]) for k in klines])
        volumes = np.array([float(k[5]) for k in klines])

        # 计算对数收益率
        # np.diff 会让序列长度减1，所以我们对应地处理成交量
        log_returns = np.diff(np.log(prices))

        # 如果不启用成交量加权，则执行原逻辑
        if not TradingConfig.ENABLE_VOLUME_WEIGHTING:
            volatility = np.std(log_returns) * np.sqrt(365 * 6)
            return volatility

        # --- 执行成交量加权逻辑 ---
        # 我们需要对应收益率的成交量，通常使用后一根K线的成交量
        relevant_volumes = volumes[1:]

        # 计算平均成交量，处理分母为0的情况
        average_volume = np.mean(relevant_volumes)
        if average_volume == 0:
            # 如果所有成交量都为0，则退回至不加权的计算
            volatility = np.std(log_returns) * np.sqrt(365 * 6)
            return volatility

        # 计算成交量因子 (权重)
        volume_factors = relevant_volumes / average_volume

        # 计算加权后的收益率
        weighted_log_returns = log_returns * volume_factors

        self.logger.debug(f"成交量加权计算 | 平均成交量: {average_volume:.2f} | 成交量权重范围: [{np.min(volume_factors):.2f}, {np.max(volume_factors):.2f}]")

        # 基于加权收益率计算年化波动率
        volatility = np.std(weighted_log_returns) * np.sqrt(365 * 6)

        return volatility

    def _update_ewma_volatility(self, current_price):
        """
        更新EWMA波动率
        使用RiskMetrics标准的λ=0.94
        """
        if self.last_price is None:
            # 首次调用，保存价格但不计算波动率
            self.last_price = current_price
            return None

        # 计算当期收益率的平方
        if self.last_price > 0:
            return_squared = (np.log(current_price / self.last_price)) ** 2
        else:
            return_squared = 0

        # 更新EWMA波动率
        lambda_factor = settings.VOLATILITY_EWMA_LAMBDA

        if not self.ewma_initialized:
            # 首次初始化：使用当期收益率平方作为初始值
            self.ewma_volatility = return_squared
            self.ewma_initialized = True
        else:
            # EWMA更新公式：σ²(t) = λ * σ²(t-1) + (1-λ) * r²(t)
            self.ewma_volatility = (
                lambda_factor * self.ewma_volatility +
                (1 - lambda_factor) * return_squared
            )

        # 更新上一次价格
        self.last_price = current_price

        # 返回年化波动率 (开平方并年化)
        return np.sqrt(self.ewma_volatility * 252)

    def _adjust_amount_precision(self, amount):
        """根据交易所精度动态调整数量"""
        if self.amount_precision is None:
            # 如果精度未初始化，使用默认值
            self.logger.warning("数量精度未初始化，使用默认值3")
            return float(f"{amount:.3f}")

        # 使用ccxt的精度调整方法
        try:
            return self.exchange.exchange.amount_to_precision(self.symbol, amount)
        except Exception as e:
            self.logger.error(f"精度调整失败: {e}, 使用默认精度")
            precision = int(self.amount_precision) if self.amount_precision is not None else 3
            return float(f"{amount:.{precision}f}")

    def _normalize_order_amount(self, amount: float, price: float) -> tuple[str | float, float, float] | None:
        """应用交易所限制并返回下单数量、浮点数量和名义金额"""
        if amount is None or price is None or price <= 0:
            return None

        try:
            normalized_amount = float(amount)
        except (TypeError, ValueError):
            return None

        if normalized_amount <= 0:
            return None

        limits = (self.symbol_info or {}).get('limits') or {}
        amount_limits = limits.get('amount') or {}
        cost_limits = limits.get('cost') or {}

        def _safe_float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        min_amount = _safe_float(amount_limits.get('min'))
        max_amount = _safe_float(amount_limits.get('max'))
        min_cost = _safe_float(cost_limits.get('min'))
        max_cost = _safe_float(cost_limits.get('max'))

        if min_amount is not None and normalized_amount < min_amount:
            normalized_amount = min_amount
        if min_cost is not None and min_cost > 0:
            min_amount_from_cost = min_cost / price
            if normalized_amount < min_amount_from_cost:
                normalized_amount = min_amount_from_cost

        if max_amount is not None and max_amount > 0 and normalized_amount > max_amount:
            normalized_amount = max_amount
        if max_cost is not None and max_cost > 0:
            max_amount_from_cost = max_cost / price
            if normalized_amount > max_amount_from_cost:
                normalized_amount = max_amount_from_cost

        precision_amount = self._adjust_amount_precision(normalized_amount)

        try:
            amount_float = float(precision_amount)
        except (TypeError, ValueError):
            return None

        if amount_float <= 0:
            return None

        if min_amount is not None and amount_float < min_amount:
            precision_amount = self._adjust_amount_precision(min_amount)
            try:
                amount_float = float(precision_amount)
            except (TypeError, ValueError):
                return None
            if amount_float < min_amount:
                return None

        if min_cost is not None and min_cost > 0 and amount_float * price < min_cost:
            target_amount = min_cost / price
            precision_amount = self._adjust_amount_precision(target_amount)
            try:
                amount_float = float(precision_amount)
            except (TypeError, ValueError):
                return None
            if amount_float * price < min_cost:
                return None

        if max_amount is not None and max_amount > 0 and amount_float > max_amount:
            precision_amount = self._adjust_amount_precision(max_amount)
            try:
                amount_float = float(precision_amount)
            except (TypeError, ValueError):
                return None
            if amount_float > max_amount:
                return None

        if max_cost is not None and max_cost > 0 and amount_float * price > max_cost:
            target_amount = max_cost / price
            precision_amount = self._adjust_amount_precision(target_amount)
            try:
                amount_float = float(precision_amount)
            except (TypeError, ValueError):
                return None
            if amount_float * price > max_cost:
                return None

        notional = amount_float * price
        return precision_amount, amount_float, notional

    def _adjust_price_precision(self, price):
        """根据交易所精度动态调整价格"""
        if self.price_precision is None:
            # 如果精度未初始化，使用默认值
            self.logger.warning("价格精度未初始化，使用默认值2")
            return float(f"{price:.2f}")

        # 使用ccxt的精度调整方法
        try:
            return self.exchange.exchange.price_to_precision(self.symbol, price)
        except Exception as e:
            self.logger.error(f"价格精度调整失败: {e}, 使用默认精度")
            precision = int(self.price_precision) if self.price_precision is not None else 2
            return float(f"{price:.{precision}f}")

    async def calculate_trade_amount(self, side, order_price):
        # 获取必要参数
        balance = await self.exchange.fetch_balance()
        total_assets = float(balance['total'][self.quote_asset]) + float(balance['total'].get(self.base_asset, 0)) * order_price

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
            total_assets * settings.RISK_FACTOR * volatility_factor * kelly_f * percentile_factor,
            total_assets * settings.MAX_POSITION_RATIO
        )

        # 应用最小/最大限制
        amount_quote = max(
            min(risk_adjusted_amount, TradingConfig.BASE_AMOUNT),
            settings.MIN_TRADE_AMOUNT
        )

        return amount_quote

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
            order_book = await self.exchange.fetch_order_book(self.symbol)
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
            ohlcv = await self.exchange.fetch_ohlcv(self.symbol, '4h', limit=42)  # 42根4小时K线 ≈ 7天
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
        total_assets = float(balance['total'][self.quote_asset]) + float(balance['total'].get(self.base_asset, 0)) * current_price

        # 获取当前订单需要的金额
        amount_quote = await self.calculate_trade_amount(side, current_price)

        # 考虑手续费和滑价
        required = amount_quote * 1.05  # 增加5%缓冲
        return min(required, settings.MAX_POSITION_RATIO * total_assets)

    async def _transfer_excess_funds(self):
        """将超出总资产16%目标的部分资金转回理财账户"""
        # 功能开关检查
        if not settings.ENABLE_SAVINGS_FUNCTION:
            return

        try:
            balance = await self.exchange.fetch_balance()
            current_price = await self._get_latest_price()
            total_assets = await self._get_pair_specific_assets_value()

            # 如果无法获取价格或总资产，则跳过
            if not current_price or current_price <= 0 or total_assets <= 0:
                self.logger.warning("无法获取价格或总资产，跳过资金转移检查")
                return

            # 计算目标保留金额 (总资产的16%)
            target_quote_hold = total_assets * 0.16
            target_base_hold_value = total_assets * 0.16
            target_base_hold_amount = target_base_hold_value / current_price

            # 获取当前现货可用余额
            spot_quote_balance = float(balance.get('free', {}).get(self.quote_asset, 0))
            spot_base_balance = float(balance.get('free', {}).get(self.base_asset, 0))

            self.logger.info(
                f"资金转移检查 | 总资产: {total_assets:.2f} {self.quote_asset} | "
                f"目标{self.quote_asset}持有: {target_quote_hold:.2f} | 现货{self.quote_asset}: {spot_quote_balance:.2f} | "
                f"目标{self.base_asset}持有(等值): {target_base_hold_value:.2f} {self.quote_asset} ({target_base_hold_amount:.4f} {self.base_asset}) | "
                f"现货{self.base_asset}: {spot_base_balance:.4f}"
            )

            transfer_executed = False  # 标记是否执行了划转

            # 处理计价货币：如果现货超出目标，转移多余部分
            if spot_quote_balance > target_quote_hold:
                transfer_amount = spot_quote_balance - target_quote_hold
                # 增加最小划转金额判断，避免无效操作
                # 将阈值提高到 1.0
                if transfer_amount > 1.0:
                    self.logger.info(f"转移多余{self.quote_asset}到理财: {transfer_amount:.2f}")
                    try:
                        await self.exchange.transfer_to_savings(self.quote_asset, transfer_amount)
                        transfer_executed = True
                    except Exception as transfer_e:
                        self.logger.error(f"转移{self.quote_asset}到理财失败: {str(transfer_e)}")
                else:
                    self.logger.info(f"{self.quote_asset}超出部分 ({transfer_amount:.2f}) 过小，不执行划转")

            # 处理基础货币：如果现货超出目标，转移多余部分
            if spot_base_balance > target_base_hold_amount:
                transfer_amount = spot_base_balance - target_base_hold_amount
                # 检查转移金额是否大于等于最小申购额
                min_transfer = settings.MIN_BNB_TRANSFER if self.base_asset == 'BNB' else 0.01
                if transfer_amount >= min_transfer:
                    self.logger.info(f"转移多余{self.base_asset}到理财: {transfer_amount:.4f}")
                    try:
                        await self.exchange.transfer_to_savings(self.base_asset, transfer_amount)
                        transfer_executed = True
                    except Exception as transfer_e:
                        self.logger.error(f"转移{self.base_asset}到理财失败: {str(transfer_e)}")
                else:
                    # 修改日志消息以反映新的阈值
                    self.logger.info(f"{self.base_asset}超出部分 ({transfer_amount:.4f}) 低于最小申购额 {min_transfer}，不执行划转")

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
            max_single_transfer = self.config.MAX_SINGLE_TRANSFER
            while required_with_buffer > 0:
                transfer_amount = min(required_with_buffer, max_single_transfer)
                await self.exchange.transfer_to_spot(self.quote_asset, transfer_amount)
                required_with_buffer -= transfer_amount
                self.logger.info(f"预划转完成: {transfer_amount} {self.quote_asset} | 剩余需划转: {required_with_buffer}")

            self.logger.info("资金预划转完成，等待10秒确保到账")
            await asyncio.sleep(10)  # 等待资金到账

        except Exception as e:
            self.logger.error(f"预划转失败: {str(e)}")
            raise

    def _calculate_dynamic_base(self, total_assets):
        """计算动态基础交易金额"""
        # 计算基于总资产百分比的交易金额范围
        min_amount = max(
            settings.MIN_TRADE_AMOUNT,  # 不低于最小交易金额
            total_assets * settings.MIN_POSITION_PERCENT  # 不低于总资产的5%
        )
        max_amount = total_assets * settings.MAX_POSITION_PERCENT  # 不超过总资产的15%

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
        # 功能开关检查
        if not settings.ENABLE_SAVINGS_FUNCTION:
            self.logger.info("理财功能已禁用，跳过初始资金检查与划转。")
            return

        try:
            # 获取现货和理财账户余额
            balance = await self.exchange.fetch_balance()
            funding_balance = await self.exchange.fetch_funding_balance()
            total_assets = await self._get_pair_specific_assets_value()
            current_price = await self._get_latest_price()

            # 计算目标持仓（总资产的16%）
            target_quote = total_assets * 0.16
            target_base = (total_assets * 0.16) / current_price

            # 获取现货余额
            quote_balance = float(balance['free'].get(self.quote_asset, 0))
            base_balance = float(balance['free'].get(self.base_asset, 0))

            # 计算总余额（现货+理财）
            total_quote = quote_balance + float(funding_balance.get(self.quote_asset, 0))
            total_base = base_balance + float(funding_balance.get(self.base_asset, 0))

            # 调整计价货币余额
            if quote_balance > target_quote:
                # 多余的申购到理财
                transfer_amount = quote_balance - target_quote
                self.logger.info(f"发现可划转{self.quote_asset}: {transfer_amount}")
                # --- 添加最小申购金额检查 (>= 1) ---
                if transfer_amount >= 1.0:
                    try:
                        await self.exchange.transfer_to_savings(self.quote_asset, transfer_amount)
                        self.logger.info(f"已将 {transfer_amount:.2f} {self.quote_asset} 申购到理财")
                    except Exception as e_savings_quote:
                        self.logger.error(f"申购{self.quote_asset}到理财失败: {str(e_savings_quote)}")
                else:
                    self.logger.info(f"可划转{self.quote_asset} ({transfer_amount:.2f}) 低于最小申购额 1.0，跳过申购")
            elif quote_balance < target_quote:
                # 不足的从理财赎回
                needed_amount = target_quote - quote_balance

                # --- 【新增】前置检查：确保理财账户里有该资产 ---
                funding_quote_balance = float(funding_balance.get(self.quote_asset, 0))
                if funding_quote_balance > 0:
                    # 实际能赎回的金额，不能超过理财账户里的余额
                    actual_transfer_amount = min(needed_amount, funding_quote_balance)
                    self.logger.info(f"理财账户有 {funding_quote_balance:.2f} {self.quote_asset}，尝试从理财赎回: {actual_transfer_amount:.2f}")
                    try:
                        # 确保赎回金额大于一个极小值，避免API报错
                        if actual_transfer_amount >= 0.01:
                            await self.exchange.transfer_to_spot(self.quote_asset, actual_transfer_amount)
                            self.logger.info(f"已成功从理财赎回 {actual_transfer_amount:.2f} {self.quote_asset}")
                        else:
                            self.logger.info(f"计算出的需赎回金额 ({actual_transfer_amount:.4f}) 过小，跳过。")
                    except Exception as e_spot_quote:
                        self.logger.error(f"从理财赎回{self.quote_asset}失败: {str(e_spot_quote)}")
                else:
                    # 如果理财里没有，就直接警告
                    self.logger.warning(f"现货{self.quote_asset}不足，且理财账户中没有{self.quote_asset}可供赎回。请手动补充底仓。")

            # 调整基础货币余额
            if base_balance > target_base:
                # 多余的申购到理财
                transfer_amount = base_balance - target_base
                self.logger.info(f"发现可划转{self.base_asset}: {transfer_amount}")
                # --- 添加最小申购金额检查 ---
                min_transfer = settings.MIN_BNB_TRANSFER if self.base_asset == 'BNB' else 0.01
                if transfer_amount >= min_transfer:
                    try:
                        await self.exchange.transfer_to_savings(self.base_asset, transfer_amount)
                        self.logger.info(f"已将 {transfer_amount:.4f} {self.base_asset} 申购到理财")
                    except Exception as e_savings:
                        self.logger.error(f"申购{self.base_asset}到理财失败: {str(e_savings)}")
                else:
                    self.logger.info(f"可划转{self.base_asset} ({transfer_amount:.4f}) 低于最小申购额 {min_transfer}，跳过申购")
            elif base_balance < target_base:
                # 不足的从理财赎回
                needed_amount = target_base - base_balance

                # --- 【新增】前置检查：确保理财账户里有该资产 ---
                funding_base_balance = float(funding_balance.get(self.base_asset, 0))
                if funding_base_balance > 0:
                    # 实际能赎回的金额，不能超过理财账户里的余额
                    actual_transfer_amount = min(needed_amount, funding_base_balance)
                    self.logger.info(f"理财账户有 {funding_base_balance:.4f} {self.base_asset}，尝试从理财赎回: {actual_transfer_amount:.4f}")
                    try:
                        # 确保赎回金额大于一个极小值，避免API报错
                        if actual_transfer_amount > 1e-8:
                            await self.exchange.transfer_to_spot(self.base_asset, actual_transfer_amount)
                            self.logger.info(f"已成功从理财赎回 {actual_transfer_amount:.4f} {self.base_asset}")
                        else:
                            self.logger.info(f"计算出的需赎回金额 ({actual_transfer_amount:.8f}) 过小，跳过。")
                    except Exception as e_spot:
                        self.logger.error(f"从理财赎回{self.base_asset}失败: {str(e_spot)}")
                else:
                    # 如果理财里没有，就直接警告
                    self.logger.warning(f"现货{self.base_asset}不足，且理财账户中没有{self.base_asset}可供赎回。请手动补充底仓。")

            self.logger.info(
                f"资金分配完成\n"
                f"{self.quote_asset}: {total_quote:.2f}\n"
                f"{self.base_asset}: {total_base:.4f}"
            )
        except Exception as e:
            self.logger.error(f"初始资金检查失败: {str(e)}")

    async def _get_pair_specific_assets_value(self):
        """
        获取当前交易对相关资产价值（以计价货币计算）- 用于交易决策

        此方法仅计算当前交易对（self.base_asset和self.quote_asset）的资产价值，
        用于该交易对的交易决策和风险控制，实现交易对之间的风险隔离。

        如需获取全账户总资产（用于报告），请使用 exchange.calculate_total_account_value() 方法。
        """
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

            # 分别获取现货和理财账户余额（使用动态资产名称）
            spot_base = float(balance.get('free', {}).get(self.base_asset, 0) or 0)
            spot_quote = float(balance.get('free', {}).get(self.quote_asset, 0) or 0)

            # 加上已冻结的余额
            spot_base += float(balance.get('used', {}).get(self.base_asset, 0) or 0)
            spot_quote += float(balance.get('used', {}).get(self.quote_asset, 0) or 0)

            # 加上理财账户余额
            fund_base = 0
            fund_quote = 0
            if funding_balance:
                fund_base = float(funding_balance.get(self.base_asset, 0) or 0)
                fund_quote = float(funding_balance.get(self.quote_asset, 0) or 0)

            # 分别计算现货和理财账户总值
            spot_value = spot_quote + (spot_base * current_price)
            fund_value = fund_quote + (fund_base * current_price)
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
                    f"【{self.symbol}】交易对资产: {total_assets:.2f} {self.quote_asset} | "
                    f"现货: {spot_value:.2f} {self.quote_asset} "
                    f"({self.base_asset}: {spot_base:.4f}, {self.quote_asset}: {spot_quote:.2f}) | "
                    f"理财: {fund_value:.2f} {self.quote_asset} "
                    f"({self.base_asset}: {fund_base:.4f}, {self.quote_asset}: {fund_quote:.2f})"
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
            base_balance = float(balance['total'].get(self.base_asset, 0))
            quote_balance = float(balance['total'].get(self.quote_asset, 0))
            current_price = await self._get_latest_price()

            self.total_assets = quote_balance + (base_balance * current_price)
            self.logger.info(f"更新总资产: {self.total_assets:.2f} {self.quote_asset}")

        except Exception as e:
            self.logger.error(f"更新总资产失败: {str(e)}")

    async def get_ma_data(self, short_period=20, long_period=50):
        """获取MA数据"""
        try:
            # 获取K线数据
            klines = await self.exchange.fetch_ohlcv(
                self.symbol,
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
                self.symbol,
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
                self.symbol,
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

    async def _ensure_sufficient_balance(self, side: str, price: float, amount: float) -> bool:
        """AI交易余额检查包装，复用标准资金校验流程"""
        try:
            if price is None or price <= 0:
                self.logger.error("价格无效，无法执行余额检查。")
                return False

            spot_balance = await self.exchange.fetch_balance({'type': 'spot'})
            funding_balance = await self.exchange.fetch_funding_balance()

            if side == 'buy':
                required_quote = float(price) * float(amount)
                return await self._ensure_balance_for_trade(
                    side='buy',
                    spot_balance=spot_balance,
                    funding_balance=funding_balance,
                    required_quote=required_quote
                )
            elif side == 'sell':
                required_base = float(amount)
                required_quote = float(price) * required_base
                return await self._ensure_balance_for_trade(
                    side='sell',
                    spot_balance=spot_balance,
                    funding_balance=funding_balance,
                    required_quote=required_quote,
                    required_base=required_base
                )
            else:
                self.logger.error(f"未知交易方向: {side}")
                return False
        except Exception as e:
            self.logger.error(f"AI余额检查失败({side}): {e}", exc_info=True)
            return False

    def _calculate_ema(self, data, period):
        """计算EMA"""
        if not data or len(data) == 0:
            return 0

        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price - ema) * multiplier + ema
        return ema

    async def _ensure_balance_for_trade(
        self,
        side: str,
        spot_balance: dict,
        funding_balance: dict,
        *,
        required_quote: float | None = None,
        required_base: float | None = None
    ) -> bool:
        """
        【重构后】统一检查买卖双方的余额，并在需要时从理财赎回。
        """
        try:
            # 1. 确定所需资产和数量
            amount_quote = required_quote if required_quote is not None else await self._calculate_order_amount(side)
            if side == 'buy':
                asset_needed = self.quote_asset
                required_amount = amount_quote
                spot_balance_asset = float(spot_balance.get('free', {}).get(self.quote_asset, 0) or 0)
            else: # side == 'sell'
                if required_base is not None:
                    required_amount = required_base
                else:
                    if not self.current_price or self.current_price <= 0:
                        self.logger.error(f"价格无效，无法计算卖出所需 {self.base_asset} 数量。")
                        return False
                    required_amount = amount_quote / self.current_price
                asset_needed = self.base_asset
                spot_balance_asset = float(spot_balance.get('free', {}).get(self.base_asset, 0) or 0)

            self.logger.info(f"{side}前余额检查 | 所需 {asset_needed}: {required_amount:.4f} | 现货可用: {spot_balance_asset:.4f}")

            # 2. 如果现货余额足够，直接成功返回
            if spot_balance_asset >= required_amount:
                return True

            # 3. 现货不足，检查理财功能是否开启
            if not settings.ENABLE_SAVINGS_FUNCTION:
                self.logger.error(f"资金不足 ({asset_needed})，且理财功能已禁用。")
                return False

            # 4. 尝试从理财赎回
            self.logger.info(f"现货 {asset_needed} 不足，尝试从理财赎回...")
            funding_balance_asset = float(funding_balance.get(asset_needed, 0) or 0)

            # 检查总余额是否足够
            if spot_balance_asset + funding_balance_asset < required_amount:
                msg = f"总资金不足警告 ({side}) | 所需 {asset_needed}: {required_amount:.4f} | 总计 (现货+理财): {spot_balance_asset + funding_balance_asset:.4f}"
                self.logger.error(msg)
                send_pushplus_message(msg, "总资金不足警告")
                return False

            # 计算需要赎回的金额 (增加5%缓冲)
            redeem_amount = (required_amount - spot_balance_asset) * 1.05
            # 确保赎回金额不超过理财账户的余额
            actual_redeem_amount = min(redeem_amount, funding_balance_asset)

            self.logger.info(f"从理财赎回 {actual_redeem_amount:.4f} {asset_needed}")
            await self.exchange.transfer_to_spot(asset_needed, actual_redeem_amount)
            await asyncio.sleep(5) # 等待资金到账

            # 5. 再次检查余额
            new_spot_balance = await self.exchange.fetch_balance({'type': 'spot'})
            new_spot_balance_asset = float(new_spot_balance.get('free', {}).get(asset_needed, 0) or 0)
            self.logger.info(f"赎回后余额检查 | 现货 {asset_needed}: {new_spot_balance_asset:.4f}")

            if new_spot_balance_asset >= required_amount:
                return True
            else:
                self.logger.error(f"赎回后资金仍不足 ({asset_needed})。")
                return False

        except Exception as e:
            self.logger.error(f"检查 {side} 余额失败: {e}", exc_info=True)
            send_pushplus_message(f"余额检查错误 ({side}): {e}", "系统错误")
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
                base_asset=self.base_asset,
                quote_asset=self.quote_asset,
                retry_count=retry_count
            )

            send_pushplus_message(message, "交易执行通知")

            return order
        except Exception as e:
            self.logger.error(f"执行交易失败: {str(e)}")
            raise

    async def _execute_ai_trade(self, side: str, amount_pct: float, suggestion: dict):
        """
        执行AI建议的交易

        Args:
            side: 'buy' 或 'sell'
            amount_pct: 资金比例百分比 (0-100)
            suggestion: AI建议字典
        """
        try:
            # 获取当前账户资产
            total_value = await self._get_pair_specific_assets_value()

            # 计算交易金额 (USDT)
            trade_amount_usdt = total_value * (amount_pct / 100)

            # 检查最小交易金额
            if trade_amount_usdt < settings.MIN_TRADE_AMOUNT:
                self.logger.warning(
                    f"AI建议交易金额过小 ({trade_amount_usdt:.2f} USDT < {settings.MIN_TRADE_AMOUNT} USDT)，跳过"
                )
                return False

            current_price = self.current_price
            if current_price is None or current_price <= 0:
                self.logger.error("当前价格无效，无法执行AI交易")
                return False

            normalized = self._normalize_order_amount(trade_amount_usdt / current_price, current_price)
            if not normalized:
                self.logger.warning("AI建议交易数量在精度调整后无效，跳过")
                return False

            amount_for_order, amount_float, actual_notional = normalized

            if amount_float <= 0:
                self.logger.warning("AI建议交易数量调整后为0，跳过")
                return False

            if side == 'buy':
                if not await self._ensure_sufficient_balance('buy', current_price, amount_float):
                    self.logger.warning("AI建议买入但余额不足")
                    return False
            else:  # sell
                if not await self._ensure_sufficient_balance('sell', current_price, amount_float):
                    self.logger.warning("AI建议卖出但余额不足")
                    return False

            trade_amount_usdt = actual_notional

            if trade_amount_usdt < settings.MIN_TRADE_AMOUNT:
                self.logger.warning(
                    f"AI建议交易金额经调整后过小 ({trade_amount_usdt:.2f} USDT < {settings.MIN_TRADE_AMOUNT} USDT)，跳过"
                )
                return False

            self.logger.info(
                f"执行AI建议交易 | "
                f"方向: {side} | "
                f"价格: {current_price:.4f} | "
                f"数量: {amount_float:.6f} | "
                f"金额: {trade_amount_usdt:.2f} USDT | "
                f"置信度: {suggestion['confidence']}%"
            )

            # 执行交易
            order = await self._execute_trade(side, current_price, amount_for_order)

            if order:
                # 记录AI交易
                self.order_tracker.add_order({
                    'timestamp': time.time(),
                    'side': side,
                    'price': current_price,
                    'amount': amount_float,
                    'type': 'ai_assisted',
                    'confidence': suggestion['confidence'],
                    'reason': suggestion['reason'],
                    'risk_level': suggestion.get('risk_level', 'unknown')
                })

                # 发送AI交易通知
                ai_message = (
                    f"🤖 AI辅助交易执行成功\n"
                    f"交易对: {self.symbol}\n"
                    f"操作: {side.upper()}\n"
                    f"价格: {current_price:.4f} {self.quote_asset}\n"
                    f"数量: {amount_float:.6f} {self.base_asset}\n"
                    f"金额: {trade_amount_usdt:.2f} {self.quote_asset}\n"
                    f"置信度: {suggestion['confidence']}%\n"
                    f"理由: {suggestion['reason']}\n"
                    f"风险等级: {suggestion.get('risk_level', 'N/A')}"
                )

                if suggestion.get('stop_loss'):
                    ai_message += f"\n止损价: {suggestion['stop_loss']:.4f}"
                if suggestion.get('take_profit'):
                    ai_message += f"\n止盈价: {suggestion['take_profit']:.4f}"

                send_pushplus_message(ai_message, "AI交易通知")

                self.logger.info(f"AI交易执行成功 | 订单ID: {order.get('id', 'N/A')}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"AI交易执行失败: {e}", exc_info=True)
            send_pushplus_message(
                f"AI交易执行失败\n"
                f"交易对: {self.symbol}\n"
                f"操作: {side}\n"
                f"错误: {str(e)}",
                "AI交易错误"
            )
            return False

