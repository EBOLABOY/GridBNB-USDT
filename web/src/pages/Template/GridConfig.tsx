/**
 * 网格策略配置页面 - 专业网格条件单
 * 参考专业交易平台的网格交易条件单设计
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Space,
  message,
  Typography,
  Alert,
  Row,
  Col,
  Divider,
  Tooltip,
  Spin,
  Radio,
  Select,
  Slider,
  Badge,
  Statistic,
  Tag,
  DatePicker,
  TimePicker,
} from 'antd';
import {
  SaveOutlined,
  QuestionCircleOutlined,
  LeftOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CloseOutlined,
  CheckOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons';
import type { GridStrategy } from '@/types';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

const GridConfig: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [gridData, setGridData] = useState<GridStrategy | null>(null);

  // 实时行情数据（模拟）
  const [marketData, setMarketData] = useState({
    currentPrice: 628.50,
    priceChange: 2.35,
    priceChangePercent: 0.375,
    highPrice: 635.20,
    lowPrice: 618.80,
    volume24h: '125,847',
    costPrice: 620.00,
  });

  const isNew = id === 'new';

  // 加载网格配置
  useEffect(() => {
    if (!isNew) {
      loadGridData();
    }
    // 模拟实时价格更新
    const interval = setInterval(() => {
      setMarketData(prev => ({
        ...prev,
        currentPrice: prev.currentPrice + (Math.random() - 0.5) * 2,
        priceChangePercent: prev.priceChangePercent + (Math.random() - 0.5) * 0.1,
      }));
    }, 3000);
    return () => clearInterval(interval);
  }, [id]);

  const loadGridData = async () => {
    setLoading(true);
    try {
      // TODO: 替换为真实API
      message.info('加载网格数据（模拟）');
    } catch (error) {
      message.error('加载网格配置失败');
      navigate('/templates');
    } finally {
      setLoading(false);
    }
  };

  // 保存配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      // 组合交易对
      const symbol = `${values.base_currency}${values.quote_currency}`;
      const submitData = {
        ...values,
        symbol, // 添加组合后的交易对
      };

      console.log('网格策略配置:', submitData);

      // TODO: 调用API保存配置
      if (isNew) {
        message.success('网格策略创建成功');
      } else {
        message.success('网格策略更新成功');
      }

      navigate('/templates');
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请检查表单填写');
      } else {
        message.error('保存失败');
      }
    } finally {
      setSaving(false);
    }
  };

  // 加载中
  if (loading && !isNew) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '100px 0',
        background: '#FFFFFF',
        borderRadius: 12,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
      }}>
        <Spin size="large" tip="加载中...">
          <div style={{ padding: '50px' }} />
        </Spin>
      </div>
    );
  }

  return (
    <div style={{ background: 'transparent', minHeight: '100vh' }}>
      {/* 顶部导航栏 */}
      <div style={{
        background: 'linear-gradient(135deg, #F43F5E 0%, #E11D48 100%)',
        padding: '16px 24px',
        borderRadius: '12px 12px 0 0',
        marginBottom: 0,
        boxShadow: '0 2px 8px rgba(244, 63, 94, 0.2)',
      }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Button
              type="text"
              icon={<CloseOutlined />}
              onClick={() => navigate('/templates')}
              style={{
                color: '#FFFFFF',
                fontSize: 16,
                fontWeight: 500,
              }}
            >
              取消
            </Button>
          </Col>
          <Col>
            <div style={{ textAlign: 'center' }}>
              <Title level={4} style={{ margin: 0, color: '#FFFFFF' }}>
                新建网格交易条件单
              </Title>
              <Tag color="#FCA5A5" style={{ marginTop: 4, border: 'none' }}>
                网格交易
              </Tag>
            </div>
          </Col>
          <Col>
            <Tooltip title="查看帮助文档">
              <Button
                type="text"
                icon={<QuestionCircleOutlined />}
                style={{
                  color: '#FFFFFF',
                  fontSize: 18,
                }}
              />
            </Tooltip>
          </Col>
        </Row>
      </div>

      {/* 风险提示 */}
      <Alert
        message={
          <Space>
            <WarningOutlined />
            <Text strong>风险提示</Text>
          </Space>
        }
        description="网格交易适合震荡行情，单边行情可能导致亏损。请合理设置参数并做好风险控制。"
        type="warning"
        showIcon={false}
        closable
        style={{
          marginBottom: 16,
          background: '#FEF3C7',
          border: '1px solid #F59E0B',
          borderRadius: 0,
        }}
      />

      <Card
        style={{
          background: '#FFFFFF',
          borderRadius: '0 0 12px 12px',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
          border: 'none',
        }}
        styles={{ body: { padding: '24px' } }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            base_currency: 'BNB',
            quote_currency: 'USDT',
            grid_type: 'percent',
            trigger_base_price_type: 'current',
            trigger_base_price: null,
            price_min: null,
            price_max: null,
            rise_sell_percent: 1.0,
            fall_buy_percent: 1.0,
            enable_pullback_sell: false,
            pullback_sell_percent: 0.5,
            enable_rebound_buy: false,
            rebound_buy_percent: 0.5,
            order_type: 'limit',
            buy_price_mode: 'bid1',
            sell_price_mode: 'ask1',
            buy_price_offset: null,
            sell_price_offset: null,
            amount_mode: 'percent',
            grid_symmetric: true,
            order_quantity: null,
            buy_quantity: null,
            sell_quantity: null,
            max_position: 100,
            min_position: null,
            enable_multiplier: false,
            expiry_days: -1,
            expiry_date: null,
            enable_monitor_period: false,
            enable_deviation_control: false,
            enable_price_optimization: false,
            enable_delay_confirm: false,
            enable_floor_price: false,
            enable_auto_close: false,
            enable_volatility_adjustment: false,
            base_grid: 2.5,
            center_volatility: 0.25,
            sensitivity_k: 10.0,
            enable_dynamic_interval: false,
            default_interval_hours: 1.0,
            enable_volume_weighting: true,
          }}
        >
          {/* ========== 标的选择区 ========== */}
          <div style={{
            background: '#F9FAFB',
            padding: '20px',
            borderRadius: 8,
            marginBottom: 24,
            border: '1px dashed #D1D5DB',
          }}>
            <Text type="secondary" style={{ fontSize: 13, marginBottom: 12, display: 'block' }}>
              请选择/输入交易对
            </Text>

            <Row gutter={8} style={{ marginBottom: 16 }}>
              <Col span={11}>
                <Form.Item
                  name="base_currency"
                  rules={[
                    { required: true, message: '请输入基础货币' },
                    { pattern: /^[A-Z0-9]+$/, message: '请输入大写字母或数字' }
                  ]}
                  style={{ marginBottom: 0 }}
                >
                  <Input
                    size="large"
                    placeholder="如：BNB"
                    style={{ fontSize: 14, textAlign: 'center' }}
                    maxLength={10}
                  />
                </Form.Item>
              </Col>
              <Col span={2} style={{ textAlign: 'center', paddingTop: 8 }}>
                <Text style={{ fontSize: 16, color: '#9CA3AF', fontWeight: 600 }}>/</Text>
              </Col>
              <Col span={11}>
                <Form.Item
                  name="quote_currency"
                  rules={[
                    { required: true, message: '请输入报价货币' },
                    { pattern: /^[A-Z0-9]+$/, message: '请输入大写字母或数字' }
                  ]}
                  style={{ marginBottom: 0 }}
                >
                  <Input
                    size="large"
                    placeholder="如：USDT"
                    style={{ fontSize: 14, textAlign: 'center' }}
                    maxLength={10}
                  />
                </Form.Item>
              </Col>
            </Row>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                常用稳定币：USDT、BUSD、USDC、DAI
              </Text>
            </div>

            {/* 实时行情信息 */}
            <div style={{
              background: '#FFFFFF',
              padding: '12px',
              borderRadius: 6,
              border: '1px solid #E5E7EB',
            }}>
              <Row gutter={[12, 12]}>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>当前价</Text>
                    <div style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginTop: 4 }}>
                      ${marketData.currentPrice.toFixed(2)}
                    </div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>涨跌幅</Text>
                    <div style={{
                      fontSize: 16,
                      fontWeight: 600,
                      color: marketData.priceChangePercent >= 0 ? '#10B981' : '#EF4444',
                      marginTop: 4,
                    }}>
                      {marketData.priceChangePercent >= 0 ? '+' : ''}{marketData.priceChangePercent.toFixed(2)}%
                    </div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>成本价</Text>
                    <div style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginTop: 4 }}>
                      ${marketData.costPrice.toFixed(2)}
                    </div>
                  </div>
                </Col>
              </Row>
              <Divider style={{ margin: '12px 0' }} />
              <Row gutter={[12, 12]}>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>24H最高</Text>
                    <div style={{ fontSize: 14, fontWeight: 500, color: '#111827', marginTop: 4 }}>
                      ${marketData.highPrice.toFixed(2)}
                    </div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>24H最低</Text>
                    <div style={{ fontSize: 14, fontWeight: 500, color: '#111827', marginTop: 4 }}>
                      ${marketData.lowPrice.toFixed(2)}
                    </div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>盈亏率</Text>
                    <div style={{
                      fontSize: 14,
                      fontWeight: 500,
                      color: '#10B981',
                      marginTop: 4,
                    }}>
                      +1.37%
                    </div>
                  </div>
                </Col>
              </Row>
            </div>
          </div>

          <Divider style={{ margin: '24px 0' }} />

          {/* ========== 触发条件 ========== */}
          <div style={{
            fontSize: 15,
            fontWeight: 600,
            color: '#111827',
            marginBottom: 20,
          }}>
            触发条件
          </div>

          {/* 价格区间 */}
          <div style={{
            background: '#F9FAFB',
            padding: '16px',
            borderRadius: 8,
            marginBottom: 16,
          }}>
            <Text strong style={{ fontSize: 14, color: '#111827' }}>价格区间</Text>
            <Row gutter={16} style={{ marginTop: 12 }}>
              <Col span={11}>
                <Form.Item
                  name="price_min"
                  label={<Text style={{ fontSize: 13, color: '#6B7280' }}>最低价(元)</Text>}
                  rules={[{ required: true, message: '请输入最低价' }]}
                >
                  <InputNumber
                    placeholder="最低价"
                    min={0.01}
                    step={0.01}
                    size="large"
                    style={{ width: '100%' }}
                    prefix="$"
                  />
                </Form.Item>
              </Col>
              <Col span={2} style={{ textAlign: 'center', paddingTop: 30 }}>
                <Text style={{ fontSize: 16, color: '#9CA3AF' }}>~</Text>
              </Col>
              <Col span={11}>
                <Form.Item
                  name="price_max"
                  label={<Text style={{ fontSize: 13, color: '#6B7280' }}>最高价(元)</Text>}
                  rules={[{ required: true, message: '请输入最高价' }]}
                >
                  <InputNumber
                    placeholder="最高价"
                    min={0.01}
                    step={0.01}
                    size="large"
                    style={{ width: '100%' }}
                    prefix="$"
                  />
                </Form.Item>
              </Col>
            </Row>
            <Button
              type="link"
              size="small"
              style={{ padding: 0, fontSize: 13, color: '#3B82F6' }}
            >
              超出价格设置
            </Button>
          </div>

          {/* 触发基准价 */}
          <div style={{
            background: '#F9FAFB',
            padding: '16px',
            borderRadius: 8,
            marginBottom: 16,
          }}>
            <Text strong style={{ fontSize: 14, color: '#111827' }}>触发基准价</Text>
            <Form.Item name="trigger_base_price" style={{ marginTop: 12, marginBottom: 0 }}>
              <InputNumber
                placeholder="价格(元)"
                min={0.01}
                step={0.01}
                size="large"
                style={{ width: '100%' }}
                prefix="$"
              />
            </Form.Item>
            <Form.Item name="trigger_base_price_type" style={{ marginTop: 12, marginBottom: 0 }}>
              <Select size="large">
                <Option value="current">当前价</Option>
                <Option value="cost">成本价</Option>
                <Option value="avg_24h">24小时均价</Option>
                <Option value="manual">手动输入</Option>
              </Select>
            </Form.Item>
          </div>

          {/* 涨跌类型 */}
          <div style={{
            background: '#F9FAFB',
            padding: '16px',
            borderRadius: 8,
            marginBottom: 16,
          }}>
            <Text strong style={{ fontSize: 14, color: '#111827', marginRight: 24 }}>涨跌类型</Text>
            <Form.Item name="grid_type" style={{ marginBottom: 0, display: 'inline-block' }}>
              <Radio.Group size="large">
                <Radio.Button value="percent">按百分比</Radio.Button>
                <Radio.Button value="price">≈ 差价</Radio.Button>
              </Radio.Group>
            </Form.Item>
          </div>

          {/* 网格策略设置 */}
          <div style={{
            background: '#F9FAFB',
            padding: '16px',
            borderRadius: 8,
            marginBottom: 16,
          }}>
            <Row gutter={16}>
              <Col span={20}>
                <Form.Item
                  noStyle
                  shouldUpdate={(prevValues, currentValues) =>
                    prevValues.grid_type !== currentValues.grid_type
                  }
                >
                  {({ getFieldValue }) => {
                    const gridType = getFieldValue('grid_type');
                    const isPercent = gridType === 'percent';

                    return (
                      <Form.Item
                        name="rise_sell_percent"
                        label={
                          <Text style={{ fontSize: 14, color: '#111827' }}>
                            上涨<Text style={{ color: '#EF4444' }}>...卖出</Text>
                          </Text>
                        }
                        rules={[{ required: true, message: `请输入上涨卖出${isPercent ? '百分比' : '价格差'}` }]}
                      >
                        <InputNumber
                          key={`rise-sell-${gridType}`}
                          placeholder={isPercent ? "百分比(%)" : "价格差(USDT)"}
                          min={0.01}
                          max={isPercent ? 100 : undefined}
                          step={isPercent ? 0.1 : 0.01}
                          size="large"
                          style={{ width: '100%' }}
                          formatter={(value) => isPercent ? `${value}%` : `${value} U`}
                          parser={(value) => value!.replace('%', '').replace(' U', '').replace('U', '').trim()}
                        />
                      </Form.Item>
                    );
                  }}
                </Form.Item>
              </Col>
              <Col span={4} style={{ paddingTop: 30 }}>
                <div style={{ textAlign: 'right' }}>
                  <Form.Item name="enable_pullback_sell" valuePropName="checked" style={{ marginBottom: 0 }}>
                    <Switch />
                  </Form.Item>
                  <Text style={{ fontSize: 12, color: '#6B7280', display: 'block', marginTop: 4 }}>
                    回落卖出
                  </Text>
                </div>
              </Col>
            </Row>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) =>
                prevValues.enable_pullback_sell !== currentValues.enable_pullback_sell ||
                prevValues.grid_type !== currentValues.grid_type
              }
            >
              {({ getFieldValue }) =>
                getFieldValue('enable_pullback_sell') ? (
                  <Form.Item
                    noStyle
                    shouldUpdate={(prevValues, currentValues) =>
                      prevValues.grid_type !== currentValues.grid_type
                    }
                  >
                    {({ getFieldValue }) => {
                      const gridType = getFieldValue('grid_type');
                      const isPercent = gridType === 'percent';

                      return (
                        <Form.Item
                          name="pullback_sell_percent"
                          label={
                            <Text style={{ fontSize: 14, color: '#111827' }}>
                              回落<Text style={{ color: '#EF4444' }}>...卖出</Text>
                            </Text>
                          }
                          rules={[{ required: true, message: `请输入回落卖出${isPercent ? '百分比' : '价格差'}` }]}
                        >
                          <InputNumber
                            key={`pullback-sell-${gridType}`}
                            placeholder={isPercent ? "百分比(%)" : "价格差(USDT)"}
                            min={0.01}
                            max={isPercent ? 100 : undefined}
                            step={isPercent ? 0.1 : 0.01}
                            size="large"
                            style={{ width: '100%' }}
                            formatter={(value) => isPercent ? `${value}%` : `${value} U`}
                            parser={(value) => value!.replace('%', '').replace(' U', '').replace('U', '').trim()}
                          />
                        </Form.Item>
                      );
                    }}
                  </Form.Item>
                ) : null
              }
            </Form.Item>

            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={20}>
                <Form.Item
                  noStyle
                  shouldUpdate={(prevValues, currentValues) =>
                    prevValues.grid_type !== currentValues.grid_type
                  }
                >
                  {({ getFieldValue }) => {
                    const gridType = getFieldValue('grid_type');
                    const isPercent = gridType === 'percent';

                    return (
                      <Form.Item
                        name="fall_buy_percent"
                        label={
                          <Text style={{ fontSize: 14, color: '#111827' }}>
                            下跌<Text style={{ color: '#10B981' }}>...买入</Text>
                          </Text>
                        }
                        rules={[{ required: true, message: `请输入下跌买入${isPercent ? '百分比' : '价格差'}` }]}
                      >
                        <InputNumber
                          key={`fall-buy-${gridType}`}
                          placeholder={isPercent ? "百分比(%)" : "价格差(USDT)"}
                          min={0.01}
                          max={isPercent ? 100 : undefined}
                          step={isPercent ? 0.1 : 0.01}
                          size="large"
                          style={{ width: '100%' }}
                          formatter={(value) => isPercent ? `${value}%` : `${value} U`}
                          parser={(value) => value!.replace('%', '').replace(' U', '').replace('U', '').trim()}
                        />
                      </Form.Item>
                    );
                  }}
                </Form.Item>
              </Col>
              <Col span={4} style={{ paddingTop: 30 }}>
                <div style={{ textAlign: 'right' }}>
                  <Form.Item name="enable_rebound_buy" valuePropName="checked" style={{ marginBottom: 0 }}>
                    <Switch />
                  </Form.Item>
                  <Text style={{ fontSize: 12, color: '#6B7280', display: 'block', marginTop: 4 }}>
                    拐点买入
                  </Text>
                </div>
              </Col>
            </Row>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) =>
                prevValues.enable_rebound_buy !== currentValues.enable_rebound_buy ||
                prevValues.grid_type !== currentValues.grid_type
              }
            >
              {({ getFieldValue }) =>
                getFieldValue('enable_rebound_buy') ? (
                  <Form.Item
                    noStyle
                    shouldUpdate={(prevValues, currentValues) =>
                      prevValues.grid_type !== currentValues.grid_type
                    }
                  >
                    {({ getFieldValue }) => {
                      const gridType = getFieldValue('grid_type');
                      const isPercent = gridType === 'percent';

                      return (
                        <Form.Item
                          name="rebound_buy_percent"
                          label={
                            <Text style={{ fontSize: 14, color: '#111827' }}>
                              反弹<Text style={{ color: '#10B981' }}>...买入</Text>
                            </Text>
                          }
                          rules={[{ required: true, message: `请输入反弹买入${isPercent ? '百分比' : '价格差'}` }]}
                        >
                          <InputNumber
                            key={`rebound-buy-${gridType}`}
                            placeholder={isPercent ? "百分比(%)" : "价格差(USDT)"}
                            min={0.01}
                            max={isPercent ? 100 : undefined}
                            step={isPercent ? 0.1 : 0.01}
                            size="large"
                            style={{ width: '100%' }}
                            formatter={(value) => isPercent ? `${value}%` : `${value} U`}
                            parser={(value) => value!.replace('%', '').replace(' U', '').replace('U', '').trim()}
                          />
                        </Form.Item>
                      );
                    }}
                  </Form.Item>
                ) : null
              }
            </Form.Item>
          </div>

          <Divider style={{ margin: '24px 0' }} />

          {/* ========== 委托设置 ========== */}
          <div style={{
            fontSize: 15,
            fontWeight: 600,
            color: '#111827',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
          }}>
            委托设置
            <Tooltip title="行情数据刷新频率: 3秒/次">
              <WarningOutlined style={{ marginLeft: 8, fontSize: 14, color: '#F59E0B' }} />
            </Tooltip>
          </div>

          {/* 委托类型 */}
          <div style={{
            background: '#F9FAFB',
            padding: '16px',
            borderRadius: 8,
            marginBottom: 16,
          }}>
            <Text strong style={{ fontSize: 14, color: '#111827', marginBottom: 12, display: 'block' }}>
              委托类型
            </Text>
            <Form.Item name="order_type" style={{ marginBottom: 0 }}>
              <Radio.Group size="large" style={{ width: '100%' }}>
                <Row gutter={16}>
                  <Col span={12}>
                    <Radio.Button value="limit" style={{ width: '100%', textAlign: 'center', height: 'auto', padding: '12px 0' }}>
                      <div>
                        <div style={{ fontSize: 16, fontWeight: 600 }}>限价委托</div>
                        <div style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>指定价格成交</div>
                      </div>
                    </Radio.Button>
                  </Col>
                  <Col span={12}>
                    <Radio.Button value="market" style={{ width: '100%', textAlign: 'center', height: 'auto', padding: '12px 0' }}>
                      <div>
                        <div style={{ fontSize: 16, fontWeight: 600 }}>市价委托</div>
                        <div style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>立即按市价成交</div>
                      </div>
                    </Radio.Button>
                  </Col>
                </Row>
              </Radio.Group>
            </Form.Item>
          </div>

          {/* 价格设置 - 根据委托类型动态显示 */}
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.order_type !== currentValues.order_type
            }
          >
            {({ getFieldValue }) => {
              const orderType = getFieldValue('order_type');

              if (orderType === 'market') {
                // 市价委托 - 显示说明
                return (
                  <div style={{
                    background: '#EFF6FF',
                    padding: '16px',
                    borderRadius: 8,
                    marginBottom: 16,
                    border: '1px solid #BFDBFE',
                  }}>
                    <Row align="middle" gutter={12}>
                      <Col>
                        <InfoCircleOutlined style={{ fontSize: 18, color: '#3B82F6' }} />
                      </Col>
                      <Col flex={1}>
                        <Text style={{ fontSize: 14, color: '#1E40AF', display: 'block', fontWeight: 500 }}>
                          市价委托说明
                        </Text>
                        <Text style={{ fontSize: 13, color: '#3B82F6' }}>
                          触发时按照当时的市场价格立即成交，无需设置价格，确保快速成交
                        </Text>
                      </Col>
                    </Row>
                  </div>
                );
              }

              // 限价委托 - 显示价格设置
              return (
                <div style={{
                  background: '#F9FAFB',
                  padding: '16px',
                  borderRadius: 8,
                  marginBottom: 16,
                }}>
                  <Text strong style={{ fontSize: 14, color: '#111827', marginBottom: 12, display: 'block' }}>
                    价格设置
                  </Text>

                  {/* 买入价格档位选择 */}
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={12}>
                      <Form.Item
                        name="buy_price_mode"
                        label={<Text style={{ fontSize: 14, color: '#10B981' }}>买入参考价</Text>}
                        initialValue="bid1"
                      >
                        <Select size="large">
                          <Option value="bid1">买一档价格</Option>
                          <Option value="bid2">买二档价格</Option>
                          <Option value="bid3">买三档价格</Option>
                          <Option value="bid4">买四档价格</Option>
                          <Option value="bid5">买五档价格</Option>
                          <Option value="ask1">卖一档价格</Option>
                          <Option value="ask2">卖二档价格</Option>
                          <Option value="ask3">卖三档价格</Option>
                          <Option value="ask4">卖四档价格</Option>
                          <Option value="ask5">卖五档价格</Option>
                          <Option value="trigger">触发价格</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="buy_price_offset"
                        label={<Text style={{ fontSize: 14, color: '#10B981' }}>买入价格偏移</Text>}
                        tooltip="相对于参考价的偏移，负数表示更低价格"
                      >
                        <InputNumber
                          placeholder="价格偏移(USDT)"
                          step={0.01}
                          size="large"
                          style={{ width: '100%' }}
                          prefix="±"
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  {/* 卖出价格档位选择 */}
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="sell_price_mode"
                        label={<Text style={{ fontSize: 14, color: '#EF4444' }}>卖出参考价</Text>}
                        initialValue="ask1"
                      >
                        <Select size="large">
                          <Option value="ask1">卖一档价格</Option>
                          <Option value="ask2">卖二档价格</Option>
                          <Option value="ask3">卖三档价格</Option>
                          <Option value="ask4">卖四档价格</Option>
                          <Option value="ask5">卖五档价格</Option>
                          <Option value="bid1">买一档价格</Option>
                          <Option value="bid2">买二档价格</Option>
                          <Option value="bid3">买三档价格</Option>
                          <Option value="bid4">买四档价格</Option>
                          <Option value="bid5">买五档价格</Option>
                          <Option value="trigger">触发价格</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="sell_price_offset"
                        label={<Text style={{ fontSize: 14, color: '#EF4444' }}>卖出价格偏移</Text>}
                        tooltip="相对于参考价的偏移，正数表示更高价格"
                      >
                        <InputNumber
                          placeholder="价格偏移(USDT)"
                          step={0.01}
                          size="large"
                          style={{ width: '100%' }}
                          prefix="±"
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  <div style={{
                    background: '#FEF3C7',
                    padding: '8px 12px',
                    borderRadius: 4,
                    marginTop: 12,
                  }}>
                    <Text style={{ fontSize: 12, color: '#92400E' }}>
                      <InfoCircleOutlined style={{ marginRight: 4 }} />
                      买档价格通常低于卖档价格。建议：买入用买一档+负偏移，卖出用卖一档+正偏移
                    </Text>
                  </div>
                </div>
              );
            }}
          </Form.Item>

          {/* 数量/金额设置 */}
          <div style={{
            background: '#F9FAFB',
            padding: '16px',
            borderRadius: 8,
            marginBottom: 16,
          }}>
            <Form.Item name="amount_mode" style={{ marginBottom: 16 }}>
              <Radio.Group size="large">
                <Radio.Button value="percent" style={{ marginRight: 24 }}>
                  <InfoCircleOutlined style={{ marginRight: 4 }} />
                  按百分比
                </Radio.Button>
                <Radio.Button value="amount">
                  <InfoCircleOutlined style={{ marginRight: 4 }} />
                  按金额(USDT)
                </Radio.Button>
              </Radio.Group>
            </Form.Item>

            <Form.Item name="grid_symmetric" style={{ marginBottom: 16 }}>
              <Radio.Group size="large">
                <Radio.Button value={true} style={{ marginRight: 24 }}>
                  <CheckOutlined style={{ marginRight: 4 }} />
                  对称网格
                </Radio.Button>
                <Radio.Button value={false}>
                  不对称网格
                </Radio.Button>
              </Radio.Group>
            </Form.Item>

            {/* 根据对称/不对称网格和数量/金额模式动态显示 */}
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) =>
                prevValues.amount_mode !== currentValues.amount_mode ||
                prevValues.grid_symmetric !== currentValues.grid_symmetric
              }
            >
              {({ getFieldValue }) => {
                const amountMode = getFieldValue('amount_mode');
                const gridSymmetric = getFieldValue('grid_symmetric');
                const isPercent = amountMode === 'percent';

                if (gridSymmetric) {
                  // 对称网格：只显示一个"每笔委托"字段
                  return (
                    <Form.Item
                      name="order_quantity"
                      label={<Text style={{ fontSize: 14, color: '#111827' }}>每笔委托</Text>}
                      rules={[{ required: true, message: `请输入每笔委托${isPercent ? '百分比' : '金额'}` }]}
                    >
                      <InputNumber
                        placeholder={isPercent ? "百分比 (%)" : "金额 (USDT)"}
                        min={isPercent ? 0.1 : 1}
                        max={isPercent ? 100 : undefined}
                        step={isPercent ? 0.1 : 1}
                        size="large"
                        style={{ width: '100%' }}
                        precision={2}
                        formatter={(value) => isPercent ? `${value}%` : `${value}`}
                        parser={(value) => value!.replace('%', '').trim()}
                      />
                    </Form.Item>
                  );
                } else {
                  // 不对称网格：显示"每笔买入"和"每笔卖出"
                  return (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name="buy_quantity"
                          label={<Text style={{ fontSize: 14, color: '#10B981' }}>每笔买入</Text>}
                          rules={[{ required: true, message: `请输入每笔买入${isPercent ? '百分比' : '金额'}` }]}
                        >
                          <InputNumber
                            placeholder={isPercent ? "百分比 (%)" : "金额 (USDT)"}
                            min={isPercent ? 0.1 : 1}
                            max={isPercent ? 100 : undefined}
                            step={isPercent ? 0.1 : 1}
                            size="large"
                            style={{ width: '100%' }}
                            precision={2}
                            formatter={(value) => isPercent ? `${value}%` : `${value}`}
                            parser={(value) => value!.replace('%', '').trim()}
                          />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="sell_quantity"
                          label={<Text style={{ fontSize: 14, color: '#EF4444' }}>每笔卖出</Text>}
                          rules={[{ required: true, message: `请输入每笔卖出${isPercent ? '百分比' : '金额'}` }]}
                        >
                          <InputNumber
                            placeholder={isPercent ? "百分比 (%)" : "金额 (USDT)"}
                            min={isPercent ? 0.1 : 1}
                            max={isPercent ? 100 : undefined}
                            step={isPercent ? 0.1 : 1}
                            size="large"
                            style={{ width: '100%' }}
                            precision={2}
                            formatter={(value) => isPercent ? `${value}%` : `${value}`}
                            parser={(value) => value!.replace('%', '').trim()}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  );
                }
              }}
            </Form.Item>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) =>
                prevValues.amount_mode !== currentValues.amount_mode
              }
            >
              {({ getFieldValue }) => {
                const amountMode = getFieldValue('amount_mode');
                const isPercent = amountMode === 'percent';

                return (
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="max_position"
                        label={<Text style={{ fontSize: 14, color: '#111827' }}>最大持仓</Text>}
                        rules={[{ required: true, message: '请输入最大持仓' }]}
                        tooltip={isPercent ? "占总资金的百分比" : "USDT金额"}
                        initialValue={100}
                      >
                        <InputNumber
                          placeholder={isPercent ? "百分比 (%)" : "金额 (USDT)"}
                          min={isPercent ? 1 : 10}
                          max={isPercent ? 100 : undefined}
                          step={isPercent ? 1 : 10}
                          precision={2}
                          size="large"
                          style={{ width: '100%' }}
                          formatter={(value) => isPercent ? `${value}%` : `${value}`}
                          parser={(value) => value!.replace('%', '').trim()}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="min_position"
                        label={<Text style={{ fontSize: 14, color: '#111827' }}>最小底仓</Text>}
                        tooltip={isPercent ? "占总资金的百分比" : "USDT金额"}
                      >
                        <InputNumber
                          placeholder="选填"
                          min={0}
                          step={isPercent ? 1 : 10}
                          precision={2}
                          size="large"
                          style={{ width: '100%' }}
                          formatter={(value) => isPercent && value ? `${value}%` : value ? `${value}` : ''}
                          parser={(value) => value!.replace('%', '').trim()}
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                );
              }}
            </Form.Item>

            <div style={{
              background: '#FEF3C7',
              padding: '8px 12px',
              borderRadius: 4,
              marginBottom: 12,
            }}>
              <Text style={{ fontSize: 12, color: '#92400E' }}>
                可买数量: -- &nbsp;&nbsp;|&nbsp;&nbsp; 当前持仓: --
              </Text>
            </div>
          </div>

          <Divider style={{ margin: '24px 0' }} />

          {/* ========== 截止日期 ========== */}
          <div style={{
            fontSize: 15,
            fontWeight: 600,
            color: '#111827',
            marginBottom: 20,
          }}>
            截止日期
          </div>

          <div style={{
            background: '#F9FAFB',
            padding: '16px',
            borderRadius: 8,
            marginBottom: 16,
          }}>
            <Form.Item name="expiry_days" style={{ marginBottom: 16 }}>
              <Radio.Group size="large" style={{ width: '100%' }}>
                <Row gutter={[8, 8]}>
                  <Col span={4}>
                    <Radio.Button value={1} style={{ width: '100%', textAlign: 'center' }}>1日</Radio.Button>
                  </Col>
                  <Col span={4}>
                    <Radio.Button value={5} style={{ width: '100%', textAlign: 'center' }}>5日</Radio.Button>
                  </Col>
                  <Col span={4}>
                    <Radio.Button value={10} style={{ width: '100%', textAlign: 'center' }}>10日</Radio.Button>
                  </Col>
                  <Col span={4}>
                    <Radio.Button value={20} style={{ width: '100%', textAlign: 'center' }}>20日</Radio.Button>
                  </Col>
                  <Col span={4}>
                    <Radio.Button value={60} style={{ width: '100%', textAlign: 'center' }}>60日</Radio.Button>
                  </Col>
                  <Col span={4}>
                    <Radio.Button value={-1} style={{ width: '100%', textAlign: 'center' }}>永久</Radio.Button>
                  </Col>
                </Row>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) =>
                prevValues.expiry_days !== currentValues.expiry_days
              }
            >
              {({ getFieldValue }) => {
                const days = getFieldValue('expiry_days');

                // 永久有效
                if (days === -1) {
                  return (
                    <div style={{
                      background: '#FFFFFF',
                      padding: '12px',
                      borderRadius: 6,
                      textAlign: 'center',
                      border: '1px solid #E5E7EB',
                    }}>
                      <Text style={{ fontSize: 14, color: '#10B981', fontWeight: 600 }}>
                        永久有效，策略不会自动过期
                      </Text>
                    </div>
                  );
                }

                // 有期限
                const expiryDays = days || 20;
                const expiryDate = dayjs().add(expiryDays, 'day');
                return (
                  <div style={{
                    background: '#FFFFFF',
                    padding: '12px',
                    borderRadius: 6,
                    textAlign: 'center',
                    border: '1px solid #E5E7EB',
                  }}>
                    <Text style={{ fontSize: 14, color: '#111827' }}>
                      {expiryDate.format('YYYY年MM月DD日')}({expiryDays}个交易日) 收盘前
                    </Text>
                  </div>
                );
              }}
            </Form.Item>
          </div>

          <Divider style={{ margin: '24px 0' }} />

          {/* ========== 高级功能配置 ========== */}
          <div style={{
            fontSize: 16,
            fontWeight: 600,
            color: '#111827',
            marginBottom: 20,
          }}>
            高级功能配置
          </div>

          <div style={{
            background: '#F9FAFB',
            padding: '20px',
            borderRadius: 8,
            marginBottom: 24,
          }}>
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              <Row align="middle" justify="space-between">
                <Col>
                  <Text style={{ fontSize: 14, color: '#111827' }}>监控时段</Text>
                </Col>
                <Col>
                  <Form.Item name="enable_monitor_period" valuePropName="checked" style={{ marginBottom: 0 }}>
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Row align="middle" justify="space-between">
                <Col>
                  <Text style={{ fontSize: 14, color: '#111827' }}>偏差控制</Text>
                </Col>
                <Col>
                  <Form.Item name="enable_deviation_control" valuePropName="checked" style={{ marginBottom: 0 }}>
                    <Switch />
                  </Form.Item>
                  </Col>
                </Row>

                <Row align="middle" justify="space-between">
                  <Col>
                    <Text style={{ fontSize: 14, color: '#111827' }}>报价优化</Text>
                  </Col>
                  <Col>
                    <Form.Item name="enable_price_optimization" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>

                <Row align="middle" justify="space-between">
                  <Col>
                    <Text style={{ fontSize: 14, color: '#111827' }}>延迟确认</Text>
                  </Col>
                  <Col>
                    <Form.Item name="enable_delay_confirm" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>

                <Row align="middle" justify="space-between">
                  <Col>
                    <Text style={{ fontSize: 14, color: '#111827' }}>保底价触发</Text>
                  </Col>
                  <Col>
                    <Form.Item name="enable_floor_price" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>

                <Row align="middle" justify="space-between">
                  <Col>
                    <Text style={{ fontSize: 14, color: '#111827' }}>清仓设置</Text>
                  </Col>
                  <Col>
                    <Form.Item name="enable_auto_close" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider style={{ margin: '16px 0' }} />

                {/* 波动率自动调整配置 */}
                <Row align="middle" justify="space-between">
                  <Col>
                    <Space>
                      <Text style={{ fontSize: 14, color: '#111827', fontWeight: 600 }}>📊 波动率自动调整</Text>
                      <Tooltip title="根据市场波动率自动调整网格大小，提升策略适应性">
                        <QuestionCircleOutlined style={{ color: '#9CA3AF', fontSize: 12 }} />
                      </Tooltip>
                    </Space>
                  </Col>
                  <Col>
                    <Form.Item name="enable_volatility_adjustment" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item
                  noStyle
                  shouldUpdate={(prevValues, currentValues) =>
                    prevValues.enable_volatility_adjustment !== currentValues.enable_volatility_adjustment
                  }
                >
                  {({ getFieldValue }) =>
                    getFieldValue('enable_volatility_adjustment') ? (
                      <div style={{
                        background: '#FEF3C7',
                        padding: '16px',
                        borderRadius: 8,
                        marginTop: 12,
                        border: '1px solid #F59E0B',
                      }}>
                        <Space direction="vertical" style={{ width: '100%' }} size={16}>
                          <Form.Item
                            name="base_grid"
                            label={
                              <Space>
                                <Text style={{ fontSize: 13, color: '#111827' }}>基础网格大小 (%)</Text>
                                <Tooltip title="波动率为中心值时使用的网格大小">
                                  <QuestionCircleOutlined style={{ color: '#9CA3AF', fontSize: 12 }} />
                                </Tooltip>
                              </Space>
                            }
                            rules={[{ required: true, message: '请输入基础网格大小' }]}
                            style={{ marginBottom: 0 }}
                          >
                            <InputNumber
                              min={0.5}
                              max={10}
                              step={0.1}
                              style={{ width: '100%' }}
                              precision={1}
                              formatter={(value) => `${value}%`}
                              parser={(value) => value!.replace('%', '')}
                            />
                          </Form.Item>

                          <Form.Item
                            name="center_volatility"
                            label={
                              <Space>
                                <Text style={{ fontSize: 13, color: '#111827' }}>中心波动率</Text>
                                <Tooltip title="市场正常波动率的参考值，范围0-1">
                                  <QuestionCircleOutlined style={{ color: '#9CA3AF', fontSize: 12 }} />
                                </Tooltip>
                              </Space>
                            }
                            rules={[{ required: true, message: '请输入中心波动率' }]}
                            style={{ marginBottom: 0 }}
                          >
                            <InputNumber
                              min={0.01}
                              max={1}
                              step={0.01}
                              style={{ width: '100%' }}
                              precision={2}
                            />
                          </Form.Item>

                          <Form.Item
                            name="sensitivity_k"
                            label={
                              <Space>
                                <Text style={{ fontSize: 13, color: '#111827' }}>敏感度系数</Text>
                                <Tooltip title="波动率变化对网格调整的影响程度，越大越敏感">
                                  <QuestionCircleOutlined style={{ color: '#9CA3AF', fontSize: 12 }} />
                                </Tooltip>
                              </Space>
                            }
                            rules={[{ required: true, message: '请输入敏感度系数' }]}
                            style={{ marginBottom: 0 }}
                          >
                            <InputNumber
                              min={1}
                              max={50}
                              step={1}
                              style={{ width: '100%' }}
                              precision={1}
                            />
                          </Form.Item>

                          <Alert
                            message="波动率调整说明"
                            description="系统会实时计算市场波动率，当波动率偏离中心值时，根据敏感度系数自动调整网格大小。波动率高时网格变大，波动率低时网格变小。"
                            type="info"
                            showIcon
                            style={{ fontSize: 12 }}
                          />
                        </Space>
                      </div>
                    ) : null
                  }
                </Form.Item>

                <Divider style={{ margin: '16px 0' }} />

                {/* 动态交易间隔配置 */}
                <Row align="middle" justify="space-between">
                  <Col>
                    <Space>
                      <Text style={{ fontSize: 14, color: '#111827', fontWeight: 600 }}>⏱️ 动态交易间隔</Text>
                      <Tooltip title="根据波动率自动调整交易频率，波动大时交易更频繁">
                        <QuestionCircleOutlined style={{ color: '#9CA3AF', fontSize: 12 }} />
                      </Tooltip>
                    </Space>
                  </Col>
                  <Col>
                    <Form.Item name="enable_dynamic_interval" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item
                  noStyle
                  shouldUpdate={(prevValues, currentValues) =>
                    prevValues.enable_dynamic_interval !== currentValues.enable_dynamic_interval
                  }
                >
                  {({ getFieldValue }) =>
                    getFieldValue('enable_dynamic_interval') ? (
                      <div style={{
                        background: '#EFF6FF',
                        padding: '16px',
                        borderRadius: 8,
                        marginTop: 12,
                        border: '1px solid #3B82F6',
                      }}>
                        <Form.Item
                          name="default_interval_hours"
                          label={
                            <Space>
                              <Text style={{ fontSize: 13, color: '#111827' }}>默认交易间隔 (小时)</Text>
                              <Tooltip title="波动率正常时的交易间隔">
                                <QuestionCircleOutlined style={{ color: '#9CA3AF', fontSize: 12 }} />
                              </Tooltip>
                            </Space>
                          }
                          rules={[{ required: true, message: '请输入默认交易间隔' }]}
                          style={{ marginBottom: 0 }}
                        >
                          <InputNumber
                            min={0.1}
                            max={24}
                            step={0.1}
                            style={{ width: '100%' }}
                            precision={1}
                            formatter={(value) => `${value} 小时`}
                            parser={(value) => value!.replace(' 小时', '')}
                          />
                        </Form.Item>

                        <Alert
                          message="动态间隔规则"
                          description={
                            <div style={{ fontSize: 12 }}>
                              系统会根据波动率自动调整交易间隔：<br />
                              • 波动率 0-10%: 1小时交易一次<br />
                              • 波动率 10-20%: 0.5小时交易一次<br />
                              • 波动率 20-30%: 0.25小时交易一次<br />
                              • 波动率 &gt;30%: 0.125小时交易一次
                            </div>
                          }
                          type="info"
                          showIcon
                          style={{ marginTop: 12, fontSize: 12 }}
                        />
                      </div>
                    ) : null
                  }
                </Form.Item>

                <Divider style={{ margin: '16px 0' }} />

                {/* 成交量加权 */}
                <Row align="middle" justify="space-between">
                  <Col>
                    <Space>
                      <Text style={{ fontSize: 14, color: '#111827' }}>成交量加权</Text>
                      <Tooltip title="根据成交量调整交易决策权重，成交量大时更可靠">
                        <QuestionCircleOutlined style={{ color: '#9CA3AF', fontSize: 12 }} />
                      </Tooltip>
                    </Space>
                  </Col>
                  <Col>
                    <Form.Item name="enable_volume_weighting" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>
              </Space>

              <div style={{
                background: '#FEF3C7',
                padding: '8px 12px',
                borderRadius: 4,
                marginTop: 16,
              }}>
                <Text style={{ fontSize: 12, color: '#92400E' }}>
                  <InfoCircleOutlined style={{ marginRight: 4 }} />
                  条件单采用交易所提供的Level-1行情，刷新频率: 3秒/次
                </Text>
              </div>
            </div>

          {/* ========== 底部操作按钮 ========== */}
          <Button
            type="primary"
            size="large"
            block
            onClick={handleSave}
            loading={saving}
            style={{
              background: 'linear-gradient(135deg, #F43F5E 0%, #E11D48 100%)',
              borderColor: 'transparent',
              height: 50,
              fontSize: 16,
              fontWeight: 600,
              borderRadius: 8,
              boxShadow: '0 4px 12px rgba(244, 63, 94, 0.3)',
            }}
          >
            提交创建
          </Button>
        </Form>
      </Card>
    </div>
  );
};

export default GridConfig;
