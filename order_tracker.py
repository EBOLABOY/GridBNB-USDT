import time
from datetime import datetime
import logging
import os
import json

class OrderThrottler:
    def __init__(self, limit=10, interval=60):
        self.order_timestamps = []
        self.limit = limit
        self.interval = interval
    
    def check_rate(self):
        current_time = time.time()
        self.order_timestamps = [t for t in self.order_timestamps if current_time - t < self.interval]
        if len(self.order_timestamps) >= self.limit:
            return False
        self.order_timestamps.append(current_time)
        return True

class OrderTracker:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.history_file = os.path.join(self.data_dir, 'trade_history.json')
        self.backup_file = os.path.join(self.data_dir, 'trade_history.backup.json')
        self.archive_dir = os.path.join(self.data_dir, 'archives')
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir)
        self.max_archive_months = 12
        self.order_states = {}
        self.trade_count = 0
        self.orders = {}
        self.trade_history = []
        self.load_trade_history()
        self.clean_old_archives()
    
    def log_order(self, order):
        self.order_states[order['id']] = {
            'created': datetime.now(),
            'status': 'open'
        } 

    def add_order(self, order):
        """添加新订单到跟踪器"""
        try:
            order_id = order['id']
            self.orders[order_id] = {
                'order': order,
                'created_at': datetime.now(),
                'status': order['status'],
                'profit': 0
            }
            self.trade_count += 1
            self.logger.info(f"订单已添加到跟踪器 | ID: {order_id} | 状态: {order['status']}")
        except Exception as e:
            self.logger.error(f"添加订单失败: {str(e)}")
            raise

    def reset(self):
        self.trade_count = 0
        self.orders.clear()
        self.logger.info("订单跟踪器已重置") 

    def get_trade_history(self):
        """获取交易历史"""
        return self.trade_history

    def load_trade_history(self):
        """从文件加载历史交易记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.trade_history = json.load(f)
                self.logger.info(f"加载了 {len(self.trade_history)} 条历史交易记录")
        except Exception as e:
            self.logger.error(f"加载历史交易记录失败: {str(e)}")

    def save_trade_history(self):
        """将当前交易历史保存到文件"""
        try:
            # 先备份当前文件
            self.backup_history()
            # 保存当前记录
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.trade_history, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已将 {len(self.trade_history)} 条交易记录保存到 {self.history_file}")
        except Exception as e:
            self.logger.error(f"保存交易记录失败: {str(e)}")

    def backup_history(self):
        """备份交易历史"""
        try:
            if os.path.exists(self.history_file):
                import shutil
                shutil.copy2(self.history_file, self.backup_file)
                self.logger.info("交易历史备份成功")
        except Exception as e:
            self.logger.error(f"备份交易历史失败: {str(e)}")

    def add_trade(self, trade):
        """添加交易记录（自动去重）"""
        # -------- NEW: 去重 ----------
        if any(t['order_id'] == trade.get('order_id') for t in self.trade_history):
            self.logger.debug(f"重复 order_id {trade.get('order_id')} 已忽略")
            return
        # -----------------------------

        # 验证必要字段
        required_fields = ['timestamp', 'side', 'price', 'amount', 'order_id']
        for field in required_fields:
            if field not in trade:
                self.logger.error(f"交易记录缺少必要字段: {field}")
                return

        # 验证数据类型
        try:
            trade['timestamp'] = float(trade['timestamp'])
            trade['price'] = float(trade['price'])
            trade['amount'] = float(trade['amount'])
        except (ValueError, TypeError) as e:
            self.logger.error(f"交易记录数据类型错误: {str(e)}")
            return

        self.logger.info(f"添加交易记录: {trade}")
        self.trade_history.append(trade)
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
        try:
            # 先备份当前文件
            self.backup_history()
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.trade_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存交易记录失败: {str(e)}")

    def update_order(self, order_id, status, profit=0):
        if order_id in self.orders:
            self.orders[order_id]['status'] = status
            self.orders[order_id]['profit'] = profit
            if status == 'closed':
                # 更新订单状态为已关闭
                self.logger.info(f"订单已关闭 | ID: {order_id} | 利润: {profit}")

    def get_statistics(self):
        """获取交易统计信息"""
        try:
            if not self.trade_history:
                return {
                    'total_trades': 0,
                    'win_rate': 0,
                    'total_profit': 0,
                    'avg_profit': 0,
                    'max_profit': 0,
                    'max_loss': 0,
                    'profit_factor': 0,
                    'consecutive_wins': 0,
                    'consecutive_losses': 0
                }
            
            total_trades = len(self.trade_history)
            winning_trades = len([t for t in self.trade_history if t['profit'] > 0])
            total_profit = sum(t['profit'] for t in self.trade_history)
            profits = [t['profit'] for t in self.trade_history]
            
            # 计算最大连续盈利和亏损
            current_streak = 1
            max_win_streak = 0
            max_loss_streak = 0
            
            for i in range(1, len(profits)):
                if (profits[i] > 0 and profits[i-1] > 0) or (profits[i] < 0 and profits[i-1] < 0):
                    current_streak += 1
                else:
                    if profits[i-1] > 0:
                        max_win_streak = max(max_win_streak, current_streak)
                    else:
                        max_loss_streak = max(max_loss_streak, current_streak)
                    current_streak = 1
            
            return {
                'total_trades': total_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'total_profit': total_profit,
                'avg_profit': total_profit / total_trades if total_trades > 0 else 0,
                'max_profit': max(profits) if profits else 0,
                'max_loss': min(profits) if profits else 0,
                'profit_factor': sum(p for p in profits if p > 0) / abs(sum(p for p in profits if p < 0)) if sum(p for p in profits if p < 0) != 0 else 0,
                'consecutive_wins': max_win_streak,
                'consecutive_losses': max_loss_streak
            }
        except Exception as e:
            self.logger.error(f"计算统计信息失败: {str(e)}")
            return None

    def archive_old_trades(self):
        """归档旧的交易记录"""
        try:
            if len(self.trade_history) <= 100:
                return
            
            # 获取当前月份作为归档文件名
            current_month = datetime.now().strftime('%Y%m')
            archive_file = os.path.join(self.archive_dir, f'trades_{current_month}.json')
            
            # 将旧记录移动到归档
            old_trades = self.trade_history[:-100]
            
            # 如果归档文件存在，先读取并合并
            if os.path.exists(archive_file):
                with open(archive_file, 'r', encoding='utf-8') as f:
                    archived_trades = json.load(f)
                    old_trades = archived_trades + old_trades
            
            # 保存归档
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(old_trades, f, ensure_ascii=False, indent=2)
            
            # 更新当前交易历史
            self.trade_history = self.trade_history[-100:]
            self.logger.info(f"已归档 {len(old_trades)} 条交易记录到 {archive_file}")
        except Exception as e:
            self.logger.error(f"归档交易记录失败: {str(e)}")

    def clean_old_archives(self):
        """清理过期的归档文件"""
        try:
            archive_files = [f for f in os.listdir(self.archive_dir) if f.startswith('trades_')]
            archive_files.sort(reverse=True)  # 按时间倒序排列
            
            # 保留最近12个月的归档
            if len(archive_files) > self.max_archive_months:
                for old_file in archive_files[self.max_archive_months:]:
                    file_path = os.path.join(self.archive_dir, old_file)
                    os.remove(file_path)
                    self.logger.info(f"已删除过期归档: {old_file}")
        except Exception as e:
            self.logger.error(f"清理归档失败: {str(e)}")

    def analyze_trades(self, days=30):
        """分析最近交易表现"""
        try:
            if not self.trade_history:
                return None
            
            # 计算时间范围
            now = time.time()
            start_time = now - (days * 24 * 3600)
            
            # 筛选时间范围内的交易
            recent_trades = [t for t in self.trade_history if t['timestamp'] > start_time]
            
            if not recent_trades:
                return None
            
            # 按天统计
            daily_stats = {}
            for trade in recent_trades:
                trade_date = datetime.fromtimestamp(trade['timestamp']).strftime('%Y-%m-%d')
                if trade_date not in daily_stats:
                    daily_stats[trade_date] = {
                        'trades': 0,
                        'profit': 0,
                        'volume': 0
                    }
                daily_stats[trade_date]['trades'] += 1
                daily_stats[trade_date]['profit'] += trade['profit']
                daily_stats[trade_date]['volume'] += trade['price'] * trade['amount']
            
            return {
                'period': f'最近{days}天',
                'total_days': len(daily_stats),
                'active_days': len([d for d in daily_stats.values() if d['trades'] > 0]),
                'daily_stats': daily_stats,
                'avg_daily_trades': sum(d['trades'] for d in daily_stats.values()) / len(daily_stats),
                'avg_daily_profit': sum(d['profit'] for d in daily_stats.values()) / len(daily_stats),
                'best_day': max(daily_stats.items(), key=lambda x: x[1]['profit']) if daily_stats else None,
                'worst_day': min(daily_stats.items(), key=lambda x: x[1]['profit']) if daily_stats else None
            }
        except Exception as e:
            self.logger.error(f"分析交易失败: {str(e)}")
            return None

    def export_trades(self, format='csv'):
        """导出交易记录"""
        try:
            if not self.trade_history:
                return False
            
            export_dir = os.path.join(self.data_dir, 'exports')
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if format == 'csv':
                export_file = os.path.join(export_dir, f'trades_export_{timestamp}.csv')
                import csv
                with open(export_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['timestamp', 'side', 'price', 'amount', 'profit', 'order_id'])
                    writer.writeheader()
                    for trade in self.trade_history:
                        writer.writerow(trade)
            else:
                export_file = os.path.join(export_dir, f'trades_export_{timestamp}.json')
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(self.trade_history, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"交易记录已导出到: {export_file}")
            return True
        except Exception as e:
            self.logger.error(f"导出交易记录失败: {str(e)}")
            return False