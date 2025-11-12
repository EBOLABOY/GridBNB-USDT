/**
 * 日志相关API
 */

import { request } from '@/utils/request';

// 日志条目类型
export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  event?: string;
  extra?: Record<string, any>;
}

// 日志列表响应
export interface LogsResponse {
  total: number;
  logs: LogEntry[];
  page: number;
  page_size: number;
}

// 日志文件信息
export interface LogFile {
  name: string;
  size: number;
  modified: string;
}

// 获取日志列表
export const getLogs = (params: {
  level?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
  log_file?: string;
}): Promise<{ success: boolean; data: LogsResponse; error?: string }> => {
  return request.get('/api/logs/list', { params });
};

// 获取日志文件列表
export const getLogFiles = (): Promise<{
  success: boolean;
  data: { files: LogFile[] };
  error?: string;
}> => {
  return request.get('/api/logs/files');
};
