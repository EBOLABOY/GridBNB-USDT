/**
 * 交易历史页面
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Select,
  DatePicker,
  Space,
  Tag,
  Button,
  Tooltip,
  message,
  Statistic,
  Row,
  Col,
  Modal,
  Descriptions,
  Badge,
} from 'antd';
import {
  HistoryOutlined,
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  FilterOutlined,
  ClearOutlined,
  EyeOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { Dayjs } from 'dayjs';
import {
  getTrades,
  getTradeSymbols,
  type TradeRecord,
  type TradeSummary,
  type TradeSymbol,
} from '@/api/trades';

const { Option } = Select;
const { RangePicker } = DatePicker;

const Trades: React.FC = () => {
  // 状态管理
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [symbols, setSymbols] = useState<TradeSymbol[]>([]);
  const [summary, setSummary] = useState<TradeSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);

  // 筛选条件
  const [selectedSymbol, setSelectedSymbol] = useState<string | undefined>(undefined);
  const [selectedSide, setSelectedSide] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);

  // 详情弹窗
  const [detailVisible, setDetailVisible] = useState<boolean>(false);
  const [selectedTrade, setSelectedTrade] = useState<TradeRecord | null>(null);

  // 获取交易对列表
  const fetchSymbols = async () => {
    try {
      const response = await getTradeSymbols();
      if (response.success) {
        setSymbols(response.symbols || []);
      }
    } catch (err) {
      console.error('获取交易对列表失败:', err);
    }
  };

  // 获取交易记录
  const fetchTrades = async () => {
    try {
      setLoading(true);

      const response = await getTrades({
        symbol: selectedSymbol,
        side: selectedSide,
        start_time: dateRange[0] ? dateRange[0].toISOString() : undefined,
        end_time: dateRange[1] ? dateRange[1].toISOString() : undefined,
        page: page,
        page_size: pageSize,
      });

      if (response.success && response.data) {
        setTrades(response.data.trades);
        setTotal(response.data.total);
        setSummary(response.data.summary);
      } else {
        throw new Error(response.error || '获取交易历史失败');
      }
    } catch (err: any) {
      console.error('获取交易历史失败:', err);
      message.error('获取交易历史失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    fetchSymbols();
  }, []);

  // 交易数据变化时加载
  useEffect(() => {
    fetchTrades();
  }, [selectedSymbol, selectedSide, dateRange, page, pageSize]);

  // 交易方向标签 - 使用浅色主题
  const renderSideTag = (side: string) => {
    const sideUpper = side.toUpperCase();
    if (sideUpper === 'BUY') {
      return (
        <Tag color="#10B981" icon={<RiseOutlined />}>
          买入
        </Tag>
      );
    } else if (sideUpper === 'SELL') {
      return (
        <Tag color="#EF4444" icon={<FallOutlined />}>
          卖出
        </Tag>
      );
    } else {
      return <Tag color="#9CA3AF">{side}</Tag>;
    }
  };

  // 表格列定义
  const columns: ColumnsType<TradeRecord> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (timestamp: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')}
        </span>
      ),
    },
    {
      title: '交易对',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 120,
      render: (symbol: string) => <Tag color="#3B82F6">{symbol}</Tag>,
    },
    {
      title: '方向',
      dataIndex: 'side',
      key: 'side',
      width: 100,
      render: renderSideTag,
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      width: 120,
      align: 'right',
      render: (price: number) => (
        <span style={{ fontFamily: 'monospace' }}>${price.toFixed(2)}</span>
      ),
    },
    {
      title: '数量',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      align: 'right',
      render: (amount: number) => (
        <span style={{ fontFamily: 'monospace' }}>{amount.toFixed(4)}</span>
      ),
    },
    {
      title: '成交额',
      dataIndex: 'total',
      key: 'total',
      width: 120,
      align: 'right',
      render: (total: number) => (
        <span style={{ fontFamily: 'monospace' }}>${total.toFixed(2)}</span>
      ),
    },
    {
      title: '盈亏',
      dataIndex: 'profit',
      key: 'profit',
      width: 120,
      align: 'right',
      render: (profit: number) => (
        <Statistic
          value={profit}
          precision={2}
          prefix={profit >= 0 ? '+' : ''}
          suffix="USDT"
          valueStyle={{
            fontSize: 14,
            color: profit >= 0 ? '#3f8600' : '#cf1322',
          }}
        />
      ),
    },
    {
      title: '手续费',
      dataIndex: 'fee',
      key: 'fee',
      width: 100,
      align: 'right',
      render: (fee: number) => (
        <span style={{ fontFamily: 'monospace', color: '#999' }}>
          {fee.toFixed(2)}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => {
            setSelectedTrade(record);
            setDetailVisible(true);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  // 清空筛选
  const handleClearFilters = () => {
    setSelectedSymbol(undefined);
    setSelectedSide(undefined);
    setDateRange([null, null]);
    setPage(1);
  };

  // 导出CSV
  const handleExport = () => {
    try {
      // CSV表头
      const headers = ['时间', '交易对', '方向', '价格', '数量', '成交额', '盈亏', '手续费', '订单ID'];

      // CSV数据行
      const rows = trades.map((trade) => [
        dayjs(trade.timestamp).format('YYYY-MM-DD HH:mm:ss'),
        trade.symbol,
        trade.side,
        trade.price.toFixed(2),
        trade.amount.toFixed(4),
        trade.total.toFixed(2),
        trade.profit.toFixed(2),
        trade.fee.toFixed(2),
        trade.order_id || '',
      ]);

      // 构建CSV内容
      const csvContent = [
        headers.join(','),
        ...rows.map((row) => row.join(',')),
      ].join('\n');

      // 添加BOM以支持中文
      const BOM = '\uFEFF';
      const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `trades_${Date.now()}.csv`;
      link.click();
      URL.revokeObjectURL(url);

      message.success('交易记录导出成功');
    } catch (err) {
      message.error('导出失败');
    }
  };

  return (
    <div>
      {/* 统计卡片 */}
      {summary && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总交易次数"
                value={summary.total_count}
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="总盈亏"
                value={summary.total_profit}
                precision={2}
                suffix="USDT"
                valueStyle={{
                  color: summary.total_profit >= 0 ? '#3f8600' : '#cf1322',
                }}
                prefix={summary.total_profit >= 0 ? <RiseOutlined /> : <FallOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="胜率"
                value={summary.win_rate}
                precision={2}
                suffix="%"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均盈亏"
                value={summary.avg_profit}
                precision={2}
                suffix="USDT"
                valueStyle={{
                  color: summary.avg_profit >= 0 ? '#3f8600' : '#cf1322',
                }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 交易历史表格 */}
      <Card
        title={
          <Space>
            <HistoryOutlined />
            <span>交易历史</span>
            <Badge count={total} overflowCount={9999} showZero />
          </Space>
        }
        extra={
          <Space>
            {/* 刷新按钮 */}
            <Tooltip title="刷新">
              <Button
                icon={<ReloadOutlined spin={loading} />}
                onClick={fetchTrades}
                disabled={loading}
              />
            </Tooltip>

            {/* 导出按钮 */}
            <Tooltip title="导出CSV">
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                disabled={trades.length === 0}
              />
            </Tooltip>
          </Space>
        }
      >
        {/* 筛选栏 */}
        <Space style={{ marginBottom: 16 }} wrap>
          {/* 交易对筛选 */}
          <Select
            style={{ width: 200 }}
            placeholder="选择交易对"
            allowClear
            value={selectedSymbol}
            onChange={setSelectedSymbol}
            suffixIcon={<FilterOutlined />}
          >
            {symbols.map((item) => (
              <Option key={item.symbol} value={item.symbol}>
                {item.symbol} ({item.trade_count}笔)
              </Option>
            ))}
          </Select>

          {/* 方向筛选 */}
          <Select
            style={{ width: 150 }}
            placeholder="交易方向"
            allowClear
            value={selectedSide}
            onChange={setSelectedSide}
            suffixIcon={<FilterOutlined />}
          >
            <Option value="buy">买入</Option>
            <Option value="sell">卖出</Option>
          </Select>

          {/* 时间范围筛选 */}
          <RangePicker
            showTime
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [Dayjs | null, Dayjs | null])}
            style={{ width: 400 }}
          />

          {/* 清空筛选 */}
          {(selectedSymbol || selectedSide || dateRange[0] || dateRange[1]) && (
            <Button icon={<ClearOutlined />} onClick={handleClearFilters}>
              清空筛选
            </Button>
          )}
        </Space>

        {/* 交易记录表格 */}
        <Table
          columns={columns}
          dataSource={trades}
          rowKey={(record) => `${record.id}-${record.timestamp}`}
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 笔交易`,
            pageSizeOptions: ['20', '50', '100', '200'],
            onChange: (page, pageSize) => {
              setPage(page);
              setPageSize(pageSize);
            },
          }}
          size="small"
          scroll={{ x: 'max-content' }}
          bordered
        />
      </Card>

      {/* 交易详情弹窗 */}
      <Modal
        title="交易详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedTrade && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="交易ID" span={2}>
              {selectedTrade.id}
            </Descriptions.Item>
            <Descriptions.Item label="交易对" span={2}>
              <Tag color="blue">{selectedTrade.symbol}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="方向" span={2}>
              {renderSideTag(selectedTrade.side)}
            </Descriptions.Item>
            <Descriptions.Item label="时间" span={2}>
              {dayjs(selectedTrade.timestamp).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="价格">
              ${selectedTrade.price.toFixed(2)}
            </Descriptions.Item>
            <Descriptions.Item label="数量">
              {selectedTrade.amount.toFixed(4)}
            </Descriptions.Item>
            <Descriptions.Item label="成交额" span={2}>
              ${selectedTrade.total.toFixed(2)}
            </Descriptions.Item>
            <Descriptions.Item label="盈亏">
              <span
                style={{
                  color: selectedTrade.profit >= 0 ? '#3f8600' : '#cf1322',
                  fontWeight: 'bold',
                }}
              >
                {selectedTrade.profit >= 0 ? '+' : ''}
                {selectedTrade.profit.toFixed(2)} USDT
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="手续费">
              {selectedTrade.fee.toFixed(2)} USDT
            </Descriptions.Item>
            {selectedTrade.order_id && (
              <Descriptions.Item label="订单ID" span={2}>
                <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
                  {selectedTrade.order_id}
                </span>
              </Descriptions.Item>
            )}
            {selectedTrade.notes && (
              <Descriptions.Item label="备注" span={2}>
                {selectedTrade.notes}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default Trades;
