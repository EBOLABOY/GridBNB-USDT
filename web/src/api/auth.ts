/**
 * 认证相关API
 */

import { request } from '@/utils/request';
import type { LoginRequest, LoginResponse, User } from '@/types';

// 用户登录
export const login = (data: LoginRequest): Promise<LoginResponse> => {
  return request.post('/api/auth/login', data);
};

// 用户注销
export const logout = (): Promise<any> => {
  return request.post('/api/auth/logout');
};

// 获取当前用户信息
export const getCurrentUser = (): Promise<User> => {
  return request.get('/api/auth/me');
};

// 验证token
export const verifyToken = (): Promise<{ valid: boolean }> => {
  return request.get('/api/auth/verify');
};

// 修改密码
export const changePassword = (data: {
  old_password: string;
  new_password: string;
}): Promise<{ message: string }> => {
  return request.post('/api/auth/change-password', data);
};
