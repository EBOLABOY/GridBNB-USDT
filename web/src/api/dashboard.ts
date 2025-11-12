/**
 * 仪表盘相关API
 */

import { request } from '@/utils/request';

// 仪表盘数据类型
export interface DashboardData {
  total_profit: number;
  profit_rate: number;
  today_profit: number;
  total_trades: number;
  active_symbols: number;
  system_status: 'running' | 'stopped' | 'error';
}

export interface SystemInfo {
  status: string;
  active_symbols: number;
  uptime: string;
  last_update: string;
}

export interface SymbolStatus {
  symbol: string;
  currentPrice: number;
  change24h: number;
  position: number;
  profit: number;
  status: 'active' | 'inactive' | 'error';
  lastTradeTime: string;
}

export interface RecentTrade {
  id: number;
  symbol: string;
  side: 'buy' | 'sell' | 'unknown';
  price: number;
  amount: number;
  profit: number;
  time: string;
}

export interface Performance {
  cpu_usage: number;
  memory_usage: number;
  memory_total: number;
  memory_used: number;
  api_latency: number;
}

export interface DashboardStatusResponse {
  success: boolean;
  data: {
    dashboard: DashboardData;
    system: SystemInfo;
    symbols: SymbolStatus[];
    recent_trades: RecentTrade[];
    performance: Performance;
  };
  error?: string;
}

// 获取完整运行状态
export const getDashboardStatus = (): Promise<DashboardStatusResponse> => {
  return request.get('/api/dashboard/status');
};

// 获取快速统计（轻量级）
export const getQuickStats = (): Promise<{
  success: boolean;
  data: DashboardData;
  error?: string;
}> => {
  return request.get('/api/dashboard/quick-stats');
};
