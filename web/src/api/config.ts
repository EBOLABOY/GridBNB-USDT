/**
 * 配置管理相关API
 */

import { request } from '@/utils/request';
import type {
  Configuration,
  ConfigurationHistory,
  ConfigurationTemplate,
  PaginatedResponse,
} from '@/types';

// 获取配置列表
export const getConfigs = (params?: {
  page?: number;
  page_size?: number;
  search?: string;
  type?: string;
  status?: string;
}): Promise<PaginatedResponse<Configuration>> => {
  return request.get('/api/configs', { params });
};

// 获取单个配置
export const getConfig = (id: number): Promise<Configuration> => {
  return request.get(`/api/configs/${id}`);
};

// 创建配置
export const createConfig = (data: Partial<Configuration>): Promise<Configuration> => {
  return request.post('/api/configs', data);
};

// 更新配置
export const updateConfig = (id: number, data: Partial<Configuration>): Promise<Configuration> => {
  return request.put(`/api/configs/${id}`, data);
};

// 删除配置
export const deleteConfig = (id: number): Promise<{ message: string }> => {
  return request.delete(`/api/configs/${id}`);
};

// 批量更新配置
export const batchUpdateConfigs = (data: { updates: Array<{ id: number; config_value: string }> }): Promise<{
  updated: number;
  message: string;
}> => {
  return request.post('/api/configs/batch-update', data);
};

// 获取配置历史
export const getConfigHistory = (id: number, params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ConfigurationHistory>> => {
  return request.get(`/api/configs/${id}/history`, { params });
};

// 回滚配置
export const rollbackConfig = (id: number, version: number): Promise<Configuration> => {
  return request.post(`/api/configs/${id}/rollback`, { version });
};

// 获取配置模板列表
export const getTemplates = (params?: {
  type?: string;
  is_system?: boolean;
}): Promise<{ total: number; items: ConfigurationTemplate[] }> => {
  return request.get('/api/templates', { params });
};

// 获取单个模板
export const getTemplate = (id: number): Promise<ConfigurationTemplate> => {
  return request.get(`/api/templates/${id}`);
};

// 应用模板
export const applyTemplate = (id: number): Promise<{
  applied: number;
  template_name: string;
  message: string;
}> => {
  return request.post(`/api/templates/${id}/apply`);
};

// 重新加载配置
export const reloadConfigs = (): Promise<{
  message: string;
  cache_size: number;
  warning?: string;
}> => {
  return request.post('/api/configs/reload');
};

// 导出配置
export const exportConfigs = (params?: {
  config_type?: string;
  include_sensitive?: boolean;
}): Promise<Blob> => {
  return request.get('/api/configs/export', {
    params,
    responseType: 'blob',
  });
};

// 导入配置
export const importConfigs = (
  file: File,
  params?: {
    overwrite?: boolean;
    create_backup?: boolean;
  }
): Promise<{
  message: string;
  imported: number;
  skipped: number;
  failed: number;
  requires_restart: boolean;
  details: Array<{
    key: string;
    status: string;
    reason?: string;
    error?: string;
    requires_restart?: boolean;
  }>;
}> => {
  const formData = new FormData();
  formData.append('file', file);

  return request.post('/api/configs/import', formData, {
    params,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

// 配置定义类型
export interface ConfigDefinition {
  config_key: string;
  display_name: string;
  description: string;
  config_type: string;
  data_type: 'string' | 'number' | 'boolean' | 'json';
  default_value: string;
  validation_rules: {
    required?: boolean;
    optional?: boolean;
    type?: string;
    min?: number;
    max?: number;
    pattern?: string;
    enum?: string[];
  };
  is_required: boolean;
  is_sensitive: boolean;
  requires_restart: boolean;
}

// 获取配置定义列表
export const getConfigDefinitions = (params?: {
  config_type?: string;
  config_key?: string;
}): Promise<ConfigDefinition[]> => {
  return request.get('/api/config-definitions', { params });
};

// 获取单个配置定义
export const getConfigDefinition = (config_key: string): Promise<ConfigDefinition> => {
  return request.get('/api/config-definitions', { params: { config_key } });
};
