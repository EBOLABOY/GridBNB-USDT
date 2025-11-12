/**
 * 交易历史相关API
 */

import { request } from '@/utils/request';

// 交易记录类型
export interface TradeRecord {
  id: number;
  symbol: string;
  side: string;
  price: number;
  amount: number;
  total: number;
  profit: number;
  fee: number;
  timestamp: string;
  order_id?: string;
  notes?: string;
}

// 交易统计类型
export interface TradeSummary {
  total_count: number;
  buy_count: number;
  sell_count: number;
  total_profit: number;
  total_fee: number;
  total_volume: number;
  win_rate: number;
  avg_profit: number;
}

// 交易历史响应
export interface TradesResponse {
  total: number;
  trades: TradeRecord[];
  page: number;
  page_size: number;
  summary: TradeSummary;
}

// 交易对信息
export interface TradeSymbol {
  symbol: string;
  trade_count: number;
}

// 日统计
export interface DailyStat {
  date: string;
  count: number;
  profit: number;
  volume: number;
}

// 获取交易历史列表
export const getTrades = (params: {
  symbol?: string;
  side?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}): Promise<{ success: boolean; data: TradesResponse; error?: string }> => {
  return request.get('/api/trades/list', { params });
};

// 获取有交易记录的交易对
export const getTradeSymbols = (): Promise<{
  success: boolean;
  symbols: TradeSymbol[];
  error?: string;
}> => {
  return request.get('/api/trades/symbols');
};

// 获取交易统计
export const getTradeStatistics = (params: {
  symbol?: string;
  period?: string;
}): Promise<{
  success: boolean;
  summary: TradeSummary;
  daily_stats: DailyStat[];
  error?: string;
}> => {
  return request.get('/api/trades/statistics', { params });
};
