/**
 * 主布局组件 - 现代化设计
 */

import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Space, Typography, Button, theme, Badge } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  SettingOutlined,
  AppstoreOutlined,
  UserOutlined,
  LogoutOutlined,
  BulbOutlined,
  BulbFilled,
  FileTextOutlined,
  HistoryOutlined,
  BellOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useTheme } from '@/contexts/ThemeContext';
import { modernColors } from '@/config/theme';
import './BasicLayout.css';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;
const { useToken } = theme;

const BasicLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { theme: currentTheme, toggleTheme } = useTheme();
  const { token } = useToken();

  // 侧边栏菜单配置
  const menuItems: MenuProps['items'] = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/configs',
      icon: <SettingOutlined />,
      label: '配置管理',
    },
    {
      key: '/templates',
      icon: <AppstoreOutlined />,
      label: '策略模板',
    },
    {
      key: '/trades',
      icon: <HistoryOutlined />,
      label: '交易历史',
    },
    {
      key: '/logs',
      icon: <FileTextOutlined />,
      label: '日志查看',
    },
  ];

  // 用户下拉菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  // 处理菜单点击
  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key);
  };

  // 处理用户菜单点击
  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      navigate('/login');
    } else if (key === 'profile') {
      navigate('/profile');
    }
  };

  // 获取用户信息
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 - 浅色主题 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="light"
        width={240}
        style={{
          boxShadow: '2px 0 8px rgba(0,0,0,0.04)',
          position: 'relative',
          zIndex: 10,
        }}
      >
        {/* Logo区域 */}
        <div
          className="logo"
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? '0' : '0 24px',
            borderBottom: `1px solid ${modernColors.border}`,
            transition: 'all 0.2s',
          }}
        >
          <Text
            strong
            style={{
              color: modernColors.primary,
              fontSize: collapsed ? 18 : 20,
              fontWeight: 700,
              letterSpacing: collapsed ? 0 : '0.5px',
            }}
          >
            {collapsed ? '💹' : '💹 GridBNB'}
          </Text>
        </div>

        {/* 菜单 */}
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{
            border: 'none',
            paddingTop: 8,
          }}
        />
      </Sider>

      <Layout>
        {/* 顶部导航栏 */}
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${modernColors.border}`,
            boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
            height: 64,
          }}
        >
          {/* 左侧：折叠按钮 */}
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: 18,
              width: 40,
              height: 40,
            }}
          />

          {/* 右侧：操作区 */}
          <Space size={16}>
            {/* 通知 */}
            <Badge count={0} showZero={false}>
              <Button
                type="text"
                icon={<BellOutlined style={{ fontSize: 18 }} />}
                style={{ width: 40, height: 40 }}
              />
            </Badge>

            {/* 主题切换 */}
            <Button
              type="text"
              icon={currentTheme === 'dark' ? <BulbFilled style={{ fontSize: 18 }} /> : <BulbOutlined style={{ fontSize: 18 }} />}
              onClick={toggleTheme}
              title={currentTheme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
              style={{ width: 40, height: 40 }}
            />

            {/* 用户信息 */}
            <Dropdown
              menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
              placement="bottomRight"
              trigger={['click']}
            >
              <Space
                style={{
                  cursor: 'pointer',
                  padding: '4px 12px',
                  borderRadius: 8,
                  transition: 'all 0.2s',
                }}
                className="user-dropdown"
              >
                <Avatar
                  icon={<UserOutlined />}
                  style={{
                    background: modernColors.primary,
                  }}
                />
                <Text strong style={{ color: modernColors.textPrimary }}>
                  {user?.username || 'Admin'}
                </Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 主内容区 */}
        <Content
          style={{
            margin: '24px',
            padding: 0,
            minHeight: 280,
            background: 'transparent',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default BasicLayout;
