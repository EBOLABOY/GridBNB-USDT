/**
 * 配置列表页面 - 简化版（适合小白用户）
 */

import React, { useRef, useState } from 'react';
import { Button, Space, Tag, Modal, message, Card, Typography, Alert } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { useNavigate } from 'react-router-dom';
import {
  getConfigs,
  deleteConfig,
  updateConfig,
} from '@/api/config';
import type { Configuration } from '@/types';
import { ConfigType, ConfigStatus } from '@/types';

const { confirm } = Modal;
const { Title, Paragraph } = Typography;

// 配置类型映射 - 简化版
const CONFIG_TYPE_MAP: Record<string, { text: string; color: string; icon: string }> = {
  [ConfigType.EXCHANGE]: { text: '交易所', color: '#3B82F6', icon: '🏦' },
  [ConfigType.NOTIFICATION]: { text: '通知', color: '#10B981', icon: '🔔' },
  [ConfigType.AI]: { text: 'AI配置', color: '#8B5CF6', icon: '🤖' },
  // 兼容旧数据
  trading: { text: '交易（旧）', color: '#F59E0B', icon: '⚠️' },
};

const ConfigList: React.FC = () => {
  const navigate = useNavigate();
  const actionRef = useRef<ActionType>(null);
  const [showSensitive, setShowSensitive] = useState<Record<number, boolean>>({});

  // 表格列定义
  const columns: ProColumns<Configuration>[] = [
    {
      title: '配置名称',
      dataIndex: 'display_name',
      width: 250,
      ellipsis: true,
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500, color: '#111827', fontSize: 14 }}>
            {record.display_name}
          </div>
        </div>
      ),
    },
    {
      title: '配置值',
      dataIndex: 'config_value',
      width: 300,
      search: false,
      ellipsis: true,
      render: (_, record) => {
        const isSensitive = record.is_sensitive;
        const isShown = showSensitive[record.id];

        if (isSensitive && !isShown) {
          return (
            <Space>
              <span style={{ fontFamily: 'monospace', color: '#6B7280' }}>••••••••</span>
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => setShowSensitive({ ...showSensitive, [record.id]: true })}
              >
                显示
              </Button>
            </Space>
          );
        }

        return (
          <Space>
            <span style={{ fontFamily: 'monospace', fontSize: 13 }}>
              {record.config_value.length > 50
                ? `${record.config_value.substring(0, 50)}...`
                : record.config_value}
            </span>
            {isSensitive && (
              <Button
                type="link"
                size="small"
                icon={<EyeInvisibleOutlined />}
                onClick={() => setShowSensitive({ ...showSensitive, [record.id]: false })}
              >
                隐藏
              </Button>
            )}
          </Space>
        );
      },
    },
    {
      title: '类型',
      dataIndex: 'config_type',
      width: 100,
      valueType: 'select',
      valueEnum: Object.fromEntries(
        Object.entries(CONFIG_TYPE_MAP).map(([key, value]) => [
          key,
          { text: value.text },
        ])
      ),
      render: (_, record) => {
        const typeInfo = CONFIG_TYPE_MAP[record.config_type] || {
          text: record.config_type,
          color: '#9CA3AF',
          icon: '⚙️'
        };

        // 检查是否是不支持的旧类型
        const isLegacyType = !Object.values(ConfigType).includes(record.config_type as any);

        return (
          <Tag
            color={isLegacyType ? '#FEF3C7' : typeInfo.color}
            style={isLegacyType ? {
              borderColor: '#F59E0B',
              color: '#92400E',
            } : undefined}
          >
            <span style={{ marginRight: 4 }}>{typeInfo.icon}</span>
            {typeInfo.text}
            {isLegacyType && (
              <Tooltip title="这是旧版本的配置，建议删除">
                <ExclamationCircleOutlined style={{ marginLeft: 4, fontSize: 12 }} />
              </Tooltip>
            )}
          </Tag>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        [ConfigStatus.ACTIVE]: { text: '已启用', status: 'Success' },
        [ConfigStatus.INACTIVE]: { text: '已停用', status: 'Default' },
      },
      render: (_, record) => {
        const isActive = record.status === ConfigStatus.ACTIVE;
        return (
          <Tag color={isActive ? 'success' : 'default'}>
            {isActive ? '✓ 已启用' : '已停用'}
          </Tag>
        );
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => {
        // 检查是否是不支持的旧类型
        const isLegacyType = !Object.values(ConfigType).includes(record.config_type as any);

        return [
          <Button
            key="edit"
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/configs/${record.id}`)}
            disabled={isLegacyType} // 旧类型不允许编辑
          >
            编辑
          </Button>,
          record.status === ConfigStatus.ACTIVE ? (
            <Button
              key="inactive"
              type="link"
              size="small"
              icon={<CloseCircleOutlined />}
              onClick={() => handleToggleStatus(record, ConfigStatus.INACTIVE)}
              style={{ color: '#F59E0B' }}
            >
              停用
            </Button>
          ) : (
            <Button
              key="active"
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleToggleStatus(record, ConfigStatus.ACTIVE)}
              style={{ color: '#10B981' }}
            >
              启用
            </Button>
          ),
          <Button
            key="delete"
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            {isLegacyType ? '立即删除' : '删除'}
          </Button>,
        ];
      },
    },
  ];

  // 切换配置状态
  const handleToggleStatus = async (record: Configuration, newStatus: string) => {
    try {
      await updateConfig(record.id, { status: newStatus as any });
      message.success(newStatus === ConfigStatus.ACTIVE ? '已启用配置' : '已停用配置');
      actionRef.current?.reload();
    } catch (error) {
      message.error('操作失败');
    }
  };

  // 删除配置
  const handleDelete = (record: Configuration) => {
    // 检查是否是不支持的旧类型
    const isLegacyType = !Object.values(ConfigType).includes(record.config_type as any);

    confirm({
      title: isLegacyType ? '删除旧版配置' : '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          {isLegacyType ? (
            <>
              <p style={{ color: '#F59E0B', fontWeight: 500 }}>
                这是旧版本遗留的配置，当前系统已不再支持
              </p>
              <p style={{ color: '#6B7280', fontSize: 14, marginTop: 8 }}>
                配置名称: {record.display_name}
              </p>
              <p style={{ color: '#6B7280', fontSize: 14 }}>
                类型: {record.config_type} (已废弃)
              </p>
              <p style={{ color: '#10B981', fontSize: 13, marginTop: 12 }}>
                ✓ 建议删除此配置以保持系统整洁
              </p>
            </>
          ) : (
            <>
              <p>确定要删除这个配置吗？</p>
              <p style={{ color: '#6B7280', fontSize: 14, marginTop: 8 }}>
                {record.display_name}
              </p>
              <p style={{ color: '#EF4444', fontSize: 12, marginTop: 12 }}>
                ⚠️ 删除后无法恢复，请谨慎操作！
              </p>
            </>
          )}
        </div>
      ),
      okText: isLegacyType ? '删除旧配置' : '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteConfig(record.id);
          message.success(isLegacyType ? '旧配置已删除' : '删除成功');
          actionRef.current?.reload();
        } catch (error: any) {
          console.error('删除配置失败:', error);
          const errorMsg = error?.response?.data?.detail || error?.message || '删除失败';
          message.error(`删除失败: ${errorMsg}`);
        }
      },
    });
  };

  // 请求数据
  const request = async (params: any) => {
    try {
      const response = await getConfigs({
        page: params.current,
        page_size: params.pageSize,
        search: params.keyword,
        type: params.config_type,
        status: params.status,
      });

      return {
        data: response.items,
        success: true,
        total: response.total,
      };
    } catch (error) {
      message.error('数据加载失败');
      return {
        data: [],
        success: false,
        total: 0,
      };
    }
  };

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ marginBottom: 8, color: '#111827' }}>
          系统配置
        </Title>
        <Paragraph style={{ fontSize: 15, color: '#6B7280', marginBottom: 0 }}>
          在这里可以管理交易所连接、消息通知、AI配置等基础设置
        </Paragraph>
      </div>

      {/* 新增配置提示卡片 */}
      <div
        style={{
          marginBottom: 24,
          borderRadius: 12,
          background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
          border: 'none',
          cursor: 'pointer',
          boxShadow: '0 4px 16px rgba(59, 130, 246, 0.4)',
          padding: '24px 28px',
          transition: 'all 0.3s ease',
        }}
        onClick={() => navigate('/configs/new')}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = '0 8px 24px rgba(59, 130, 246, 0.5)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = '0 4px 16px rgba(59, 130, 246, 0.4)';
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: 'rgba(255, 255, 255, 0.2)',
                backdropFilter: 'blur(10px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
              }}
            >
              <PlusOutlined style={{ fontSize: 28, color: '#FFFFFF', fontWeight: 'bold' }} />
            </div>
            <div>
              <div style={{
                fontSize: 20,
                fontWeight: 800,
                color: '#FFFFFF',
                marginBottom: 8,
                textShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
                letterSpacing: '0.5px',
              }}>
                添加新配置
              </div>
              <div style={{
                fontSize: 16,
                color: '#FFFFFF',
                fontWeight: 600,
                textShadow: '0 1px 3px rgba(0, 0, 0, 0.2)',
                opacity: 1,
              }}>
                点击这里配置交易所、通知方式或AI
              </div>
            </div>
          </div>
          <Button
            size="large"
            icon={<PlusOutlined />}
            style={{
              background: '#FFFFFF',
              borderColor: '#FFFFFF',
              color: '#2563EB',
              height: 48,
              fontSize: 16,
              fontWeight: 700,
              padding: '0 32px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#F0F9FF';
              e.currentTarget.style.transform = 'scale(1.02)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#FFFFFF';
              e.currentTarget.style.transform = 'scale(1)';
            }}
          >
            立即添加
          </Button>
        </div>
      </div>

      {/* 配置列表表格 */}
      <ProTable<Configuration>
        columns={columns}
        actionRef={actionRef}
        request={request}
        rowKey="id"
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          pageSizeOptions: ['10', '20', '50'],
        }}
        dateFormatter="string"
        toolBarRender={false}
        cardProps={{
          style: {
            borderRadius: 12,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
          },
        }}
        options={{
          reload: true,
          density: false,
          setting: false,
        }}
      />
    </div>
  );
};

export default ConfigList;
