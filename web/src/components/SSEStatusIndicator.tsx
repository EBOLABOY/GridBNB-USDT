/**
 * SSE连接状态指示器组件
 */

import React from 'react';
import { Badge, Tooltip, Space } from 'antd';
import {
  WifiOutlined,
  LoadingOutlined,
  DisconnectOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { SSEStatus } from '@/hooks/useSSE';

interface SSEStatusIndicatorProps {
  status: SSEStatus;
  error?: string | null;
  reconnectCount?: number;
  showText?: boolean;
}

const SSEStatusIndicator: React.FC<SSEStatusIndicatorProps> = ({
  status,
  error,
  reconnectCount = 0,
  showText = true,
}) => {
  // 状态映射
  const statusConfig = {
    connecting: {
      status: 'processing' as const,
      text: reconnectCount > 0 ? `重连中 (${reconnectCount})` : '连接中',
      icon: <LoadingOutlined spin />,
      color: '#1890ff',
      tooltip: reconnectCount > 0 ? `正在尝试第 ${reconnectCount} 次重连` : '正在建立SSE连接',
    },
    connected: {
      status: 'success' as const,
      text: '实时',
      icon: <WifiOutlined />,
      color: '#52c41a',
      tooltip: 'SSE连接已建立，数据实时更新中',
    },
    disconnected: {
      status: 'default' as const,
      text: '离线',
      icon: <DisconnectOutlined />,
      color: '#999',
      tooltip: 'SSE连接已断开',
    },
    error: {
      status: 'error' as const,
      text: '错误',
      icon: <CloseCircleOutlined />,
      color: '#ff4d4f',
      tooltip: error || 'SSE连接错误',
    },
  };

  const config = statusConfig[status];

  if (showText) {
    return (
      <Tooltip title={config.tooltip}>
        <Space size={4}>
          <Badge status={config.status} />
          <span style={{ fontSize: 12, color: config.color }}>
            {config.text}
          </span>
        </Space>
      </Tooltip>
    );
  }

  return (
    <Tooltip title={config.tooltip}>
      <span style={{ color: config.color, fontSize: 16 }}>
        {config.icon}
      </span>
    </Tooltip>
  );
};

export default SSEStatusIndicator;
