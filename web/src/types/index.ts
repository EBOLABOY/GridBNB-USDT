/**
 * 通用类型定义
 */

// API响应结构
export interface ApiResponse<T = any> {
  success?: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 分页响应
export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// 用户信息
export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  login_count?: number;
}

// 登录请求
export interface LoginRequest {
  username: string;
  password: string;
}

// 登录响应
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// 配置类型 - 仅保留交易所、通知配置和AI配置
export const ConfigType = {
  EXCHANGE: 'exchange',
  NOTIFICATION: 'notification',
  AI: 'ai',
} as const;

export type ConfigType = typeof ConfigType[keyof typeof ConfigType];

// 配置状态
export const ConfigStatus = {
  DRAFT: 'draft',
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  ARCHIVED: 'archived',
} as const;

export type ConfigStatus = typeof ConfigStatus[keyof typeof ConfigStatus];

// 配置项
export interface Configuration {
  id: number;
  config_key: string;
  config_value: string;
  config_type: ConfigType;
  display_name: string;
  description?: string;
  data_type?: string;
  default_value?: string;
  validation_rules?: Record<string, any>;
  status: ConfigStatus;
  is_required?: boolean;
  is_sensitive?: boolean;
  requires_restart?: boolean;
  created_by?: number;
  updated_by?: number;
  created_at: string;
  updated_at: string;
}

// 配置历史
export interface ConfigurationHistory {
  id: number;
  config_id: number;
  old_value: string;
  new_value: string;
  change_reason?: string;
  version: number;
  changed_by: number;
  changed_at: string;
}

// 配置模板
export interface ConfigurationTemplate {
  id: number;
  template_name: string;
  template_type: string;
  display_name: string;
  description?: string;
  config_json: Record<string, any>;
  is_system: boolean;
  is_active: boolean;
  usage_count: number;
  created_by?: number;
  created_at: string;
  updated_at?: string;
}

// 路由菜单项
export interface MenuItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  path?: string;
  children?: MenuItem[];
}

// 网格策略状态
export const GridStrategyStatus = {
  ACTIVE: 'active',
  STOPPED: 'stopped',
  ERROR: 'error',
} as const;

export type GridStrategyStatus = typeof GridStrategyStatus[keyof typeof GridStrategyStatus];

// 网格策略
export interface GridStrategy {
  id: number;
  name: string;
  symbol: string;
  investment_amount: number;
  grid_count: number;
  price_min?: number;
  price_max?: number;
  price_range_auto?: boolean;
  min_profit_rate: number;
  take_profit_enabled?: boolean;
  take_profit_rate?: number;
  stop_loss_enabled?: boolean;
  stop_loss_rate?: number;
  dynamic_adjustment?: boolean;
  status: GridStrategyStatus;
  total_profit: number;
  today_profit: number;
  created_at: string;
  updated_at: string;
}
