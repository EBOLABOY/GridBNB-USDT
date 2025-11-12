/**
 * 首页 - 交易系统运行监控（现代化数据大屏风格）
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Tag,
  Table,
  Typography,
  Space,
  Badge,
  Progress,
  Alert,
  Spin,
  message,
  Button,
  Tabs,
  Switch,
  Tooltip,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  TrophyOutlined,
  DollarOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  BarChartOutlined,
  PieChartOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import type { ColumnsType } from 'antd/es/table';
import {
  getDashboardStatus,
  type DashboardData,
  type SymbolStatus,
  type RecentTrade,
  type SystemInfo,
  type Performance,
} from '@/api/dashboard';
import { ProfitTrendChart, TradeVolumeChart, PositionPieChart } from '@/components/charts';
import { useSSE } from '@/hooks/useSSE';
import SSEStatusIndicator from '@/components/SSEStatusIndicator';
import GlassCard from '@/components/GlassCard';
import CountUp from '@/components/CountUp';
import { modernTheme } from '@/styles/modernTheme';
import { modernColors } from '@/config/theme';

const { Text } = Typography;

const Home: React.FC = () => {
  // 状态管理
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [symbolStatus, setSymbolStatus] = useState<SymbolStatus[]>([]);
  const [recentTrades, setRecentTrades] = useState<RecentTrade[]>([]);
  const [performance, setPerformance] = useState<Performance | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sseEnabled, setSseEnabled] = useState<boolean>(true);

  // 模拟历史数据（后续从后端API获取）
  const [profitHistory, setProfitHistory] = useState<Array<{ time: string; profit: number }>>([]);
  const [tradeVolumeData, setTradeVolumeData] = useState<Array<{ symbol: string; buyCount: number; sellCount: number }>>([]);
  const [positionData, setPositionData] = useState<Array<{ symbol: string; value: number }>>([]);

  // 获取仪表盘数据
  const fetchDashboardData = useCallback(async () => {
    try {
      setError(null);
      const response = await getDashboardStatus();

      if (response.success && response.data) {
        setDashboardData(response.data.dashboard);
        setSystemInfo(response.data.system);
        setSymbolStatus(response.data.symbols);
        setRecentTrades(response.data.recent_trades);
        setPerformance(response.data.performance);

        // 处理图表数据
        // 1. 生成盈亏趋势数据（模拟最近24小时数据）
        const now = Date.now();
        const mockProfitHistory = Array.from({ length: 24 }, (_, i) => {
          const hourAgo = 23 - i;
          const time = new Date(now - hourAgo * 3600 * 1000);
          const timeStr = `${time.getHours()}:00`;
          const profit = response.data.dashboard.total_profit * (1 - (hourAgo / 24) * 0.1);
          return { time: timeStr, profit: Math.max(profit, 0) };
        });
        setProfitHistory(mockProfitHistory.reverse());

        // 2. 生成交易量分布数据
        const volumeData = response.data.symbols.map(symbol => ({
          symbol: symbol.symbol,
          buyCount: Math.floor(Math.random() * 50) + 10,
          sellCount: Math.floor(Math.random() * 50) + 10,
        }));
        setTradeVolumeData(volumeData);

        // 3. 生成仓位分布数据
        const posData = response.data.symbols.map(symbol => ({
          symbol: symbol.symbol,
          value: symbol.currentPrice * symbol.position * 100, // 简化计算
        })).filter(item => item.value > 0);
        setPositionData(posData);
      } else {
        throw new Error(response.error || '获取数据失败');
      }
    } catch (err: any) {
      console.error('获取仪表盘数据失败:', err);
      setError(err.message || '获取数据失败，请检查后端服务是否正常运行');
      message.error('获取数据失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, []);

  // SSE连接 - 接收实时更新（增量更新优化）
  const { status: sseStatus, error: sseError, reconnectCount } = useSSE({
    url: '/api/sse/events',
    enabled: sseEnabled,
    onMessage: (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('SSE消息:', data);

        // 根据事件类型处理 - 使用增量更新策略
        if (data.type === 'dashboard_update' && data.payload) {
          // ✅ 增量更新：只更新变化的字段
          const { payload } = data;

          // 更新仪表盘核心数据
          if (payload.dashboard) {
            setDashboardData(prev => prev ? { ...prev, ...payload.dashboard } : payload.dashboard);
          }

          // 更新系统信息
          if (payload.system) {
            setSystemInfo(prev => prev ? { ...prev, ...payload.system } : payload.system);
          }

          // 更新交易对状态（部分更新）
          if (payload.symbols) {
            setSymbolStatus(prev => {
              if (!Array.isArray(payload.symbols)) return prev;

              // 如果是完整列表，直接替换
              if (payload.full_replace) {
                return payload.symbols;
              }

              // 增量更新：合并新数据
              const symbolMap = new Map(prev.map(s => [s.symbol, s]));
              payload.symbols.forEach((newSymbol: any) => {
                const existing = symbolMap.get(newSymbol.symbol);
                symbolMap.set(newSymbol.symbol, existing ? { ...existing, ...newSymbol } : newSymbol);
              });
              return Array.from(symbolMap.values());
            });
          }

          // 更新最近交易（追加新交易）
          if (payload.recent_trades) {
            setRecentTrades(prev => {
              const newTrades = Array.isArray(payload.recent_trades) ? payload.recent_trades : [];
              // 合并去重，保留最新的10条
              const allTrades = [...newTrades, ...prev];
              const uniqueTrades = Array.from(
                new Map(allTrades.map(t => [t.id, t])).values()
              );
              return uniqueTrades.slice(0, 10);
            });
          }

          // 更新性能指标
          if (payload.performance) {
            setPerformance(prev => prev ? { ...prev, ...payload.performance } : payload.performance);
          }

          console.log('✅ 增量更新完成');
        } else if (data.type === 'config_updated') {
          // 配置更新：提示用户并全量刷新
          message.info('系统配置已更新');
          fetchDashboardData();
        } else if (data.type === 'full_refresh') {
          // 服务端要求全量刷新
          console.log('⚠️ 服务端请求全量刷新');
          fetchDashboardData();
        }
      } catch (err) {
        console.error('解析SSE消息失败:', err);
      }
    },
    onError: (err) => {
      console.error('SSE错误:', err);
    },
    reconnectInterval: 3000,
    maxReconnectAttempts: 10,
  });

  // 初始加载和定时轮询（作为SSE的备份）
  useEffect(() => {
    // 立即获取数据
    fetchDashboardData();

    // 设置定时轮询（当SSE连接时，间隔更长；未连接时，间隔更短）
    const interval = setInterval(
      fetchDashboardData,
      sseStatus === 'connected' ? 60000 : 10000 // SSE连接时60秒，未连接时10秒
    );

    // 清理定时器
    return () => clearInterval(interval);
  }, [fetchDashboardData, sseStatus]);

  // 交易对状态表格列定义 - 现代化颜色
  const symbolColumns: ColumnsType<SymbolStatus> = [
    {
      title: '交易对',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text) => (
        <Text strong style={{ color: modernTheme.colors.textPrimary }}>{text}</Text>
      ),
    },
    {
      title: '当前价格',
      dataIndex: 'currentPrice',
      key: 'currentPrice',
      render: (price) => (
        <Text
          code
          style={{
            background: 'rgba(0, 212, 255, 0.1)',
            color: modernTheme.colors.primary,
            border: `1px solid ${modernTheme.colors.primary}33`,
          }}
        >
          ${price.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '24h涨跌',
      dataIndex: 'change24h',
      key: 'change24h',
      render: (change) => (
        <Text
          strong
          style={{
            color: change >= 0 ? modernTheme.colors.success : modernTheme.colors.danger,
          }}
        >
          {change >= 0 ? '+' : ''}{change.toFixed(2)}%
        </Text>
      ),
    },
    {
      title: '仓位',
      dataIndex: 'position',
      key: 'position',
      render: (position) => (
        <Progress
          percent={position * 100}
          size="small"
          strokeColor={{
            '0%': modernTheme.colors.secondary,
            '100%': modernTheme.colors.success,
          }}
          trailColor="rgba(255,255,255,0.1)"
          format={(percent) => `${percent?.toFixed(0)}%`}
        />
      ),
    },
    {
      title: '累计盈亏',
      dataIndex: 'profit',
      key: 'profit',
      render: (profit) => (
        <div style={{
          fontSize: 14,
          fontWeight: 'bold',
          color: profit >= 0 ? modernTheme.colors.success : modernTheme.colors.danger,
        }}>
          {profit >= 0 ? '+' : ''}{profit.toFixed(2)} USDT
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) =>
        status === 'active' ? (
          <Tag
            icon={<CheckCircleOutlined />}
            style={{
              background: `${modernTheme.colors.success}22`,
              border: `1px solid ${modernTheme.colors.success}`,
              color: modernTheme.colors.success,
            }}
          >
            运行中
          </Tag>
        ) : (
          <Tag
            icon={<CloseCircleOutlined />}
            style={{
              background: 'rgba(255,255,255,0.1)',
              border: '1px solid rgba(255,255,255,0.3)',
              color: modernTheme.colors.textSecondary,
            }}
          >
            已停止
          </Tag>
        ),
    },
    {
      title: '最近交易',
      dataIndex: 'lastTradeTime',
      key: 'lastTradeTime',
      render: (time) => (
        <Text style={{ color: modernTheme.colors.textSecondary }}>{time}</Text>
      ),
    },
  ];

  // 最近交易表格列定义 - 现代化颜色
  const tradeColumns: ColumnsType<RecentTrade> = [
    {
      title: '交易对',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text) => (
        <Text strong style={{ color: modernTheme.colors.textPrimary }}>{text}</Text>
      ),
    },
    {
      title: '方向',
      dataIndex: 'side',
      key: 'side',
      render: (side) => (
        <Tag
          style={{
            background: side === 'buy'
              ? `${modernTheme.colors.success}22`
              : `${modernTheme.colors.danger}22`,
            border: `1px solid ${side === 'buy' ? modernTheme.colors.success : modernTheme.colors.danger}`,
            color: side === 'buy' ? modernTheme.colors.success : modernTheme.colors.danger,
          }}
        >
          {side === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      render: (price) => (
        <Text style={{ color: modernTheme.colors.primary }}>
          ${price.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '数量',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount) => (
        <Text style={{ color: modernTheme.colors.textSecondary }}>
          {amount.toFixed(4)}
        </Text>
      ),
    },
    {
      title: '盈亏',
      dataIndex: 'profit',
      key: 'profit',
      render: (profit) => (
        <Text
          strong
          style={{
            color: profit >= 0 ? modernTheme.colors.success : modernTheme.colors.danger,
          }}
        >
          {profit >= 0 ? '+' : ''}{profit.toFixed(2)} USDT
        </Text>
      ),
    },
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      render: (time) => (
        <Text style={{ color: modernTheme.colors.textSecondary }}>{time}</Text>
      ),
    },
  ];

  // 加载中状态 - 现代化风格
  if (loading && !dashboardData) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '100px 0',
        background: modernTheme.gradients.card,
        borderRadius: modernTheme.borderRadius.lg,
      }}>
        <Spin size="large" tip="加载仪表盘数据中..." />
      </div>
    );
  }

  // 错误状态 - 现代化风格
  if (error && !dashboardData) {
    return (
      <GlassCard>
        <Alert
          message="数据加载失败"
          description={error}
          type="error"
          showIcon
          action={
            <Button
              size="small"
              type="primary"
              onClick={fetchDashboardData}
              style={{
                background: modernTheme.gradients.blue,
                border: 'none',
              }}
            >
              重试
            </Button>
          }
        />
      </GlassCard>
    );
  }

  // 没有数据 - 现代化风格
  if (!dashboardData) {
    return (
      <GlassCard>
        <Alert
          message="暂无数据"
          description="系统暂未返回任何数据，请稍后刷新"
          type="warning"
          showIcon
        />
      </GlassCard>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#F9FAFB',
      padding: '0',
    }}>
      {/* 顶部警告（如果系统有异常）*/}
      {dashboardData.system_status === 'error' && (
        <Alert
          message="系统异常"
          description="交易系统出现异常，请检查日志或联系管理员"
          type="error"
          showIcon
          closable
          style={{ marginBottom: 24 }}
        />
      )}

      {/* 网络错误警告 */}
      {error && (
        <Alert
          message="数据同步异常"
          description={error}
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 24 }}
          onClose={() => setError(null)}
        />
      )}

      {/* SSE状态和控制栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space
          split={<span style={{ color: '#d9d9d9' }}>|</span>}
          wrap
          style={{ width: '100%' }}
        >
          {/* SSE连接状态 */}
          <SSEStatusIndicator
            status={sseStatus}
            error={sseError}
            reconnectCount={reconnectCount}
            showText
          />

          {/* SSE开关 */}
          <Space size={4}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              实时推送:
            </Text>
            <Switch
              size="small"
              checked={sseEnabled}
              onChange={setSseEnabled}
            />
          </Space>

          {/* 手动刷新按钮 */}
          <Tooltip title="手动刷新数据">
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined spin={loading} />}
              onClick={fetchDashboardData}
              disabled={loading}
            >
              刷新
            </Button>
          </Tooltip>

          {/* 最后更新时间 */}
          {systemInfo && (
            <Space size={4}>
              <ClockCircleOutlined style={{ color: '#999', fontSize: 12 }} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {systemInfo.last_update ? new Date(systemInfo.last_update).toLocaleTimeString('zh-CN') : '--'}
              </Text>
            </Space>
          )}
        </Space>
      </Card>

      {/* 核心指标卡片 - 现代浅色风格，优化对比度 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={12} lg={6}>
          <Card
            style={{
              background: '#FFFFFF',
              borderRadius: 12,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
              border: '1px solid #F0F0F0',
            }}
            styles={{ body: { padding: '20px' } }}
          >
            <div>
              <div style={{
                fontSize: 13,
                color: '#6B7280',
                marginBottom: 12,
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                累计盈亏
              </div>
              <div style={{
                fontSize: 32,
                fontWeight: 700,
                color: dashboardData.total_profit >= 0 ? '#10B981' : '#EF4444',
                marginBottom: 12,
                lineHeight: 1.2,
              }}>
                <CountUp
                  end={dashboardData.total_profit}
                  decimals={2}
                  suffix=" USDT"
                />
              </div>
              <div style={{
                fontSize: 13,
                color: dashboardData.total_profit >= 0 ? '#10B981' : '#EF4444',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}>
                {dashboardData.total_profit >= 0 ? (
                  <><ArrowUpOutlined /> 盈利中</>
                ) : (
                  <><ArrowDownOutlined /> 亏损中</>
                )}
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={12} lg={6}>
          <Card
            style={{
              background: '#FFFFFF',
              borderRadius: 12,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
              border: '1px solid #F0F0F0',
            }}
            styles={{ body: { padding: '20px' } }}
          >
            <div>
              <div style={{
                fontSize: 13,
                color: '#6B7280',
                marginBottom: 12,
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                收益率
              </div>
              <div style={{
                fontSize: 32,
                fontWeight: 700,
                color: '#3B82F6',
                marginBottom: 12,
                lineHeight: 1.2,
              }}>
                <CountUp
                  end={dashboardData.profit_rate}
                  decimals={2}
                  suffix="%"
                />
              </div>
              <div style={{
                fontSize: 13,
                color: '#9CA3AF',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}>
                <TrophyOutlined /> 总收益
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={12} lg={6}>
          <Card
            style={{
              background: '#FFFFFF',
              borderRadius: 12,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
              border: '1px solid #F0F0F0',
            }}
            styles={{ body: { padding: '20px' } }}
          >
            <div>
              <div style={{
                fontSize: 13,
                color: '#6B7280',
                marginBottom: 12,
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                今日盈亏
              </div>
              <div style={{
                fontSize: 32,
                fontWeight: 700,
                color: dashboardData.today_profit >= 0 ? '#10B981' : '#EF4444',
                marginBottom: 12,
                lineHeight: 1.2,
              }}>
                <CountUp
                  end={dashboardData.today_profit}
                  decimals={2}
                  suffix=" USDT"
                />
              </div>
              <div style={{
                fontSize: 13,
                color: '#9CA3AF',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}>
                <DollarOutlined /> 24H
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={12} lg={6}>
          <Card
            style={{
              background: '#FFFFFF',
              borderRadius: 12,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
              border: '1px solid #F0F0F0',
            }}
            styles={{ body: { padding: '20px' } }}
          >
            <div>
              <div style={{
                fontSize: 13,
                color: '#6B7280',
                marginBottom: 12,
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                总交易次数
              </div>
              <div style={{
                fontSize: 32,
                fontWeight: 700,
                color: '#111827',
                marginBottom: 12,
                lineHeight: 1.2,
              }}>
                <CountUp
                  end={dashboardData.total_trades}
                  decimals={0}
                />
              </div>
              <div style={{
                fontSize: 13,
                color: '#9CA3AF',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}>
                <LineChartOutlined /> 累计
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 系统状态和活跃交易对 - 现代化风格 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <GlassCard hover style={{ height: '100%' }}>
            <div style={{
              fontSize: 16,
              fontWeight: 'bold',
              marginBottom: 16,
              color: modernTheme.colors.textPrimary,
              borderBottom: `2px solid ${modernTheme.colors.primary}`,
              paddingBottom: 8,
            }}>
              系统状态
            </div>
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={{ color: modernTheme.colors.textSecondary }}>运行状态:</Text>
                {systemInfo && systemInfo.status === 'running' ? (
                  <Tag
                    icon={<CheckCircleOutlined />}
                    color="success"
                    style={{
                      background: `${modernTheme.colors.success}22`,
                      border: `1px solid ${modernTheme.colors.success}`,
                      color: modernTheme.colors.success,
                    }}
                  >
                    运行中
                  </Tag>
                ) : systemInfo && systemInfo.status === 'stopped' ? (
                  <Tag icon={<CloseCircleOutlined />} color="default">
                    已停止
                  </Tag>
                ) : (
                  <Tag
                    icon={<CloseCircleOutlined />}
                    style={{
                      background: `${modernTheme.colors.danger}22`,
                      border: `1px solid ${modernTheme.colors.danger}`,
                      color: modernTheme.colors.danger,
                    }}
                  >
                    异常
                  </Tag>
                )}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text style={{ color: modernTheme.colors.textSecondary }}>活跃交易对:</Text>
                <Text strong style={{ color: modernTheme.colors.primary, fontSize: 18 }}>
                  {systemInfo?.active_symbols || 0}
                </Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text style={{ color: modernTheme.colors.textSecondary }}>运行时间:</Text>
                <Text style={{ color: modernTheme.colors.textPrimary }}>{systemInfo?.uptime || '--'}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text style={{ color: modernTheme.colors.textSecondary }}>最后更新:</Text>
                <Text style={{ color: modernTheme.colors.textSecondary }}>
                  <ClockCircleOutlined /> {systemInfo?.last_update || '--'}
                </Text>
              </div>
            </Space>
          </GlassCard>
        </Col>
        <Col xs={24} lg={12}>
          <GlassCard hover style={{ height: '100%' }}>
            <div style={{
              fontSize: 16,
              fontWeight: 'bold',
              marginBottom: 16,
              color: modernTheme.colors.textPrimary,
              borderBottom: `2px solid ${modernTheme.colors.secondary}`,
              paddingBottom: 8,
            }}>
              性能指标
            </div>
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text style={{ color: modernTheme.colors.textSecondary }}>CPU使用率:</Text>
                  <Text strong style={{ color: modernTheme.colors.primary }}>
                    {performance?.cpu_usage.toFixed(1) || 0}%
                  </Text>
                </div>
                <Progress
                  percent={performance?.cpu_usage || 0}
                  size="small"
                  strokeColor={{
                    '0%': modernTheme.colors.primary,
                    '100%': modernTheme.colors.primaryDark,
                  }}
                  trailColor="rgba(255,255,255,0.1)"
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text style={{ color: modernTheme.colors.textSecondary }}>内存使用:</Text>
                  <Text strong style={{ color: modernTheme.colors.secondary }}>
                    {performance?.memory_used || 0} / {performance?.memory_total || 0} MB
                  </Text>
                </div>
                <Progress
                  percent={performance?.memory_usage || 0}
                  size="small"
                  strokeColor={{
                    '0%': modernTheme.colors.secondary,
                    '100%': modernTheme.colors.success,
                  }}
                  trailColor="rgba(255,255,255,0.1)"
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text style={{ color: modernTheme.colors.textSecondary }}>API调用延迟:</Text>
                <Text strong style={{ color: modernTheme.colors.success }}>
                  <ThunderboltOutlined /> {performance?.api_latency || 0}ms
                </Text>
              </div>
            </Space>
          </GlassCard>
        </Col>
      </Row>

      {/* 📊 数据可视化图表 - 现代化风格 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <GlassCard>
            <div style={{
              fontSize: 16,
              fontWeight: 'bold',
              marginBottom: 16,
              color: modernTheme.colors.textPrimary,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <LineChartOutlined style={{ color: modernTheme.colors.primary }} />
              <span>数据可视化</span>
            </div>
            <Tabs
              defaultActiveKey="profit"
              items={[
                {
                  key: 'profit',
                  label: (
                    <span style={{ color: modernTheme.colors.textSecondary }}>
                      <LineChartOutlined />
                      盈亏趋势
                    </span>
                  ),
                  children: profitHistory.length > 0 ? (
                    <ProfitTrendChart data={profitHistory} height={300} />
                  ) : (
                    <div style={{ textAlign: 'center', padding: '50px 0', color: modernTheme.colors.textMuted }}>
                      暂无趋势数据
                    </div>
                  ),
                },
                {
                  key: 'volume',
                  label: (
                    <span style={{ color: modernTheme.colors.textSecondary }}>
                      <BarChartOutlined />
                      交易量分布
                    </span>
                  ),
                  children: tradeVolumeData.length > 0 ? (
                    <TradeVolumeChart data={tradeVolumeData} height={300} />
                  ) : (
                    <div style={{ textAlign: 'center', padding: '50px 0', color: modernTheme.colors.textMuted }}>
                      暂无交易量数据
                    </div>
                  ),
                },
                {
                  key: 'position',
                  label: (
                    <span style={{ color: modernTheme.colors.textSecondary }}>
                      <PieChartOutlined />
                      仓位分布
                    </span>
                  ),
                  children: positionData.length > 0 ? (
                    <PositionPieChart data={positionData} height={300} />
                  ) : (
                    <div style={{ textAlign: 'center', padding: '50px 0', color: modernTheme.colors.textMuted }}>
                      暂无仓位数据
                    </div>
                  ),
                },
              ]}
            />
          </GlassCard>
        </Col>
      </Row>

      {/* 交易对状态表格 - 现代化风格 */}
      <GlassCard style={{ marginBottom: 24 }}>
        <div style={{
          fontSize: 16,
          fontWeight: 'bold',
          marginBottom: 16,
          color: modernTheme.colors.textPrimary,
          borderBottom: `2px solid ${modernTheme.colors.primary}`,
          paddingBottom: 8,
        }}>
          交易对状态
        </div>
        <Table
          columns={symbolColumns}
          dataSource={symbolStatus}
          rowKey="symbol"
          pagination={false}
          size="small"
        />
      </GlassCard>

      {/* 最近交易记录 - 现代化风格 */}
      <GlassCard>
        <div style={{
          fontSize: 16,
          fontWeight: 'bold',
          marginBottom: 16,
          color: modernTheme.colors.textPrimary,
          borderBottom: `2px solid ${modernTheme.colors.secondary}`,
          paddingBottom: 8,
        }}>
          最近交易
        </div>
        <Table
          columns={tradeColumns}
          dataSource={recentTrades}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </GlassCard>
    </div>
  );
};

export default Home;
