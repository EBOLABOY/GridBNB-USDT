/**
 * 策略模板列表页面 - 统一管理网格策略和AI策略
 */

import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Space, Tag, Modal, message, Tooltip, Typography, Dropdown } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  DownOutlined,
} from '@ant-design/icons';
import { ProTable, type ProColumns, type ActionType } from '@ant-design/pro-components';

const { Text } = Typography;
const { confirm } = Modal;

// 策略类型
type StrategyType = 'grid' | 'ai';

// 策略接口
interface Strategy {
  id: number | string;
  name: string;
  type: StrategyType;
  type_name: string;
  symbol?: string;
  investment_amount?: number;
  status: 'active' | 'stopped' | 'error';
  total_profit: number;
  today_profit: number;
  created_at: string;
  updated_at: string;
  // 网格特有字段
  grid_count?: number;
  price_min?: number;
  price_max?: number;
  // AI特有字段
  ai_model?: string;
  prompt_preview?: string;
}

const TemplateList: React.FC = () => {
  const navigate = useNavigate();
  const actionRef = useRef<ActionType>();
  const [loading, setLoading] = useState(false);
  const [hasAIStrategy, setHasAIStrategy] = useState(false);

  // 获取策略列表
  const fetchStrategies = async () => {
    setLoading(true);
    try {
      // TODO: 替换为真实API调用
      // const response = await getStrategies();
      // setHasAIStrategy(response.data.some((s: Strategy) => s.type === 'ai'));
      // return {
      //   data: response.data,
      //   success: true,
      //   total: response.total,
      // };

      // 暂时返回空数据
      return {
        data: [],
        success: true,
        total: 0,
      };
    } catch (error) {
      message.error('获取策略列表失败');
      return {
        data: [],
        success: false,
        total: 0,
      };
    } finally {
      setLoading(false);
    }
  };

  // 启动策略
  const handleStart = (record: Strategy) => {
    confirm({
      title: '启动策略',
      icon: <PlayCircleOutlined />,
      content: `确定要启动策略 "${record.name}" 吗？`,
      okText: '启动',
      cancelText: '取消',
      onOk: async () => {
        try {
          // TODO: 调用API启动策略
          message.success('策略已启动');
          actionRef.current?.reload();
        } catch (error) {
          message.error('启动失败');
        }
      },
    });
  };

  // 停止策略
  const handleStop = (record: Strategy) => {
    confirm({
      title: '停止策略',
      icon: <PauseCircleOutlined />,
      content: `确定要停止策略 "${record.name}" 吗？`,
      okText: '停止',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          // TODO: 调用API停止策略
          message.success('策略已停止');
          actionRef.current?.reload();
        } catch (error) {
          message.error('停止失败');
        }
      },
    });
  };

  // 删除策略（仅网格策略可删除）
  const handleDelete = (record: Strategy) => {
    confirm({
      title: '删除策略',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>确定要删除策略 <strong>"{record.name}"</strong> 吗？</p>
          <p style={{ color: '#EF4444' }}>⚠️ 删除后将无法恢复，请确保已清空所有仓位！</p>
        </div>
      ),
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          // TODO: 调用API删除策略
          message.success('策略已删除');
          actionRef.current?.reload();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  // 编辑策略
  const handleEdit = (record: Strategy) => {
    if (record.type === 'grid') {
      navigate(`/templates/grid/${record.id}`);
    } else {
      navigate(`/templates/ai/${record.id}`);
    }
  };

  // 表格列定义
  const columns: ProColumns<Strategy>[] = [
    {
      title: '策略名称',
      dataIndex: 'name',
      width: 180,
      render: (text, record) => (
        <Space direction="vertical" size={2}>
          <Text strong style={{ color: '#111827' }}>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            ID: {record.id}
          </Text>
        </Space>
      ),
    },
    {
      title: '策略类型',
      dataIndex: 'type',
      width: 120,
      filters: [
        { text: '网格策略', value: 'grid' },
        { text: 'AI策略', value: 'ai' },
      ],
      onFilter: (value, record) => record.type === value,
      render: (_, record) => {
        if (record.type === 'grid') {
          return (
            <Tag style={{
              background: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid #3B82F6',
              color: '#3B82F6',
              fontSize: 13,
            }}>
              📊 网格策略
            </Tag>
          );
        } else {
          return (
            <Tag style={{
              background: 'rgba(139, 92, 246, 0.1)',
              border: '1px solid #8B5CF6',
              color: '#8B5CF6',
              fontSize: 13,
            }}>
              🤖 AI策略
            </Tag>
          );
        }
      },
    },
    {
      title: '交易对',
      dataIndex: 'symbol',
      width: 120,
      render: (text) => (
        <Tag style={{
          background: 'rgba(0, 0, 0, 0.02)',
          border: '1px solid #D1D5DB',
          color: '#111827',
          fontSize: 13,
        }}>
          {text}
        </Tag>
      ),
    },
    {
      title: '投资金额',
      dataIndex: 'investment_amount',
      width: 130,
      search: false,
      sorter: (a, b) => (a.investment_amount || 0) - (b.investment_amount || 0),
      render: (amount) => (
        <Text style={{ color: '#3B82F6', fontWeight: 500, fontSize: 14 }}>
          ${Number(amount).toLocaleString()}
        </Text>
      ),
    },
    {
      title: '策略参数',
      width: 200,
      search: false,
      render: (_, record) => {
        if (record.type === 'grid') {
          return (
            <Space direction="vertical" size={2}>
              <Text style={{ fontSize: 13, color: '#6B7280' }}>
                网格数: <span style={{ color: '#111827', fontWeight: 500 }}>{record.grid_count}</span>
              </Text>
              <Text style={{ fontSize: 13, color: '#6B7280' }}>
                区间: ${record.price_min} - ${record.price_max}
              </Text>
            </Space>
          );
        } else {
          return (
            <Space direction="vertical" size={2}>
              <Text style={{ fontSize: 13, color: '#6B7280' }}>
                模型: <span style={{ color: '#8B5CF6', fontWeight: 500 }}>{record.ai_model}</span>
              </Text>
              <Text
                ellipsis
                style={{ fontSize: 12, color: '#9CA3AF', maxWidth: 180 }}
                title={record.prompt_preview}
              >
                {record.prompt_preview}
              </Text>
            </Space>
          );
        }
      },
    },
    {
      title: '累计盈亏',
      dataIndex: 'total_profit',
      width: 130,
      search: false,
      sorter: (a, b) => a.total_profit - b.total_profit,
      render: (profit) => (
        <Text strong style={{
          color: Number(profit) >= 0 ? '#10B981' : '#EF4444',
          fontSize: 14,
        }}>
          {Number(profit) >= 0 ? '+' : ''}{Number(profit).toFixed(2)} USDT
        </Text>
      ),
    },
    {
      title: '今日盈亏',
      dataIndex: 'today_profit',
      width: 130,
      search: false,
      sorter: (a, b) => a.today_profit - b.today_profit,
      render: (profit) => (
        <Text style={{
          color: Number(profit) >= 0 ? '#10B981' : '#EF4444',
          fontWeight: 500,
          fontSize: 14,
        }}>
          {Number(profit) >= 0 ? '+' : ''}{Number(profit).toFixed(2)} USDT
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      filters: [
        { text: '运行中', value: 'active' },
        { text: '已停止', value: 'stopped' },
        { text: '异常', value: 'error' },
      ],
      onFilter: (value, record) => record.status === value,
      render: (_, record) => {
        if (record.status === 'active') {
          return (
            <Tag
              icon={<CheckCircleOutlined />}
              style={{
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid #10B981',
                color: '#10B981',
              }}
            >
              运行中
            </Tag>
          );
        } else if (record.status === 'stopped') {
          return (
            <Tag
              icon={<CloseCircleOutlined />}
              style={{
                background: 'rgba(156, 163, 175, 0.1)',
                border: '1px solid #9CA3AF',
                color: '#9CA3AF',
              }}
            >
              已停止
            </Tag>
          );
        } else {
          return (
            <Tag
              icon={<ExclamationCircleOutlined />}
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid #EF4444',
                color: '#EF4444',
              }}
            >
              异常
            </Tag>
          );
        }
      },
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 160,
      search: false,
      sorter: (a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      render: (text) => <Text style={{ fontSize: 13, color: '#6B7280' }}>{text}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      search: false,
      render: (_, record) => (
        <Space size={4}>
          {record.status === 'stopped' ? (
            <Tooltip title="启动">
              <Button
                type="link"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStart(record)}
                style={{ color: '#10B981' }}
              >
                启动
              </Button>
            </Tooltip>
          ) : (
            <Tooltip title="停止">
              <Button
                type="link"
                size="small"
                icon={<PauseCircleOutlined />}
                onClick={() => handleStop(record)}
                style={{ color: '#F59E0B' }}
              >
                停止
              </Button>
            </Tooltip>
          )}
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              style={{ color: '#3B82F6' }}
            >
              编辑
            </Button>
          </Tooltip>
          {record.type === 'grid' && (
            <Tooltip title="删除">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record)}
              >
                删除
              </Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ background: 'transparent' }}>
      <ProTable<Strategy>
        columns={columns}
        actionRef={actionRef}
        request={fetchStrategies}
        rowKey="id"
        loading={loading}
        search={{
          labelWidth: 'auto',
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        dateFormatter="string"
        headerTitle={
          <Space align="center">
            <span style={{ fontSize: 16, fontWeight: 600, color: '#111827' }}>
              策略模板管理
            </span>
            <Text type="secondary" style={{ fontSize: 14 }}>
              管理您的网格策略和AI策略
            </Text>
          </Space>
        }
        toolBarRender={() => [
          <Dropdown
            key="create"
            menu={{
              items: [
                {
                  key: 'grid',
                  label: '新增网格策略',
                  icon: <span style={{ fontSize: 16 }}>📊</span>,
                  onClick: () => navigate('/templates/grid/new'),
                },
                {
                  key: 'ai',
                  label: '配置AI策略',
                  icon: <span style={{ fontSize: 16 }}>🤖</span>,
                  onClick: () => navigate('/templates/ai/new'),
                  disabled: hasAIStrategy, // 已有AI策略时禁用
                },
              ],
            }}
          >
            <Button type="primary" icon={<PlusOutlined />}>
              新增策略 <DownOutlined />
            </Button>
          </Dropdown>,
        ]}
        style={{
          background: '#FFFFFF',
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
        }}
      />
    </div>
  );
};

export default TemplateList;
