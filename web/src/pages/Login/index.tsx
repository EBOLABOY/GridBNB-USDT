/**
 * 登录页面 - Ant Design Pro 风格
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Form, Input, Button, Typography, message, Checkbox } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { login } from '@/api/auth';
import { modernColors } from '@/config/theme';
import type { LoginRequest } from '@/types';
import './Login.css';

const { Title, Text } = Typography;

const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = React.useState(false);

  // 获取重定向路径（如果有的话）
  const from = (location.state as any)?.from?.pathname || '/';

  const onFinish = async (values: LoginRequest) => {
    setLoading(true);
    try {
      const response = await login(values);

      // 保存token和用户信息
      localStorage.setItem('token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));

      message.success('登录成功！');

      // 跳转回原页面或首页
      navigate(from, { replace: true });
    } catch (error) {
      message.error('登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-content">
        {/* 左侧：品牌信息 */}
        <div className="login-left">
          <div className="login-brand">
            <div className="brand-logo">💹</div>
            <Title level={1} className="brand-title">GridBNB</Title>
            <Text className="brand-subtitle">企业级网格交易配置管理系统</Text>
          </div>
          <div className="login-description">
            <Text className="description-text">
              专业的交易配置管理平台，为您提供安全、高效、智能的交易解决方案
            </Text>
          </div>
        </div>

        {/* 右侧：登录表单 */}
        <div className="login-right">
          <div className="login-form-wrapper">
            <div className="login-header">
              <Title level={2} style={{ marginBottom: 8 }}>登录</Title>
              <Text type="secondary">欢迎登录 GridBNB 交易管理系统</Text>
            </div>

            <Form
              name="login"
              initialValues={{ username: 'admin', password: 'admin123', remember: true }}
              onFinish={onFinish}
              size="large"
              style={{ marginTop: 32 }}
            >
              <Form.Item
                name="username"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input
                  prefix={<UserOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                  placeholder="用户名"
                  autoComplete="username"
                />
              </Form.Item>

              <Form.Item
                name="password"
                rules={[{ required: true, message: '请输入密码' }]}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: 'rgba(0,0,0,.25)' }} />}
                  placeholder="密码"
                  autoComplete="current-password"
                />
              </Form.Item>

              <Form.Item>
                <Form.Item name="remember" valuePropName="checked" noStyle>
                  <Checkbox>自动登录</Checkbox>
                </Form.Item>
                <a style={{ float: 'right' }} href="#!">
                  忘记密码
                </a>
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  size="large"
                >
                  登录
                </Button>
              </Form.Item>
            </Form>

            <div className="login-other">
              <Text type="secondary" style={{ fontSize: 13 }}>
                默认账号：admin / admin123
              </Text>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
