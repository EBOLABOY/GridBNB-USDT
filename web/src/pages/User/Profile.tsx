/**
 * 用户信息页面
 */

import { useState, useEffect } from 'react';
import { Card, Descriptions, Button, Space, Tag, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { getCurrentUser } from '@/api/auth';
import ChangePasswordModal from '@/components/ChangePasswordModal';
import type { User } from '@/types';

const UserProfile = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);

  useEffect(() => {
    loadUserInfo();
  }, []);

  const loadUserInfo = async () => {
    setLoading(true);
    try {
      const data = await getCurrentUser();
      setUser(data);
      // 更新localStorage中的用户信息
      localStorage.setItem('user', JSON.stringify(data));
    } catch (error) {
      message.error('获取用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Card
        title={
          <Space>
            <UserOutlined />
            <span>个人信息</span>
          </Space>
        }
        loading={loading}
        extra={
          <Space>
            <Button
              type="primary"
              icon={<LockOutlined />}
              onClick={() => setPasswordModalOpen(true)}
            >
              修改密码
            </Button>
          </Space>
        }
      >
        <Descriptions bordered column={2}>
          <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
          <Descriptions.Item label="用户ID">{user?.id}</Descriptions.Item>
          <Descriptions.Item label="账户状态">
            <Tag color={user?.is_active ? 'success' : 'error'}>
              {user?.is_active ? '正常' : '已禁用'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="账户类型">
            <Tag color={user?.is_admin ? 'blue' : 'default'}>
              {user?.is_admin ? '管理员' : '普通用户'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="注册时间">
            {user?.created_at ? new Date(user.created_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="最后登录">
            {user?.last_login ? new Date(user.last_login).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="登录次数">{user?.login_count || 0}</Descriptions.Item>
        </Descriptions>
      </Card>

      <ChangePasswordModal
        open={passwordModalOpen}
        onCancel={() => setPasswordModalOpen(false)}
      />
    </div>
  );
};

export default UserProfile;
