/**
 * 配置详情页面 - 简化版（适合小白用户）
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Button,
  Space,
  message,
  Spin,
  Typography,
  Row,
  Col,
  Alert,
  Steps,
  Tooltip,
} from 'antd';
import {
  SaveOutlined,
  ArrowLeftOutlined,
  QuestionCircleOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  BellOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import {
  getConfig,
  updateConfig,
  createConfig,
} from '@/api/config';
import type { Configuration } from '@/types';
import { ConfigType, ConfigStatus } from '@/types';

const { Title, Text, Paragraph } = Typography;

// 交易所类型定义 - 添加详细说明
const EXCHANGE_TYPES = {
  BINANCE: {
    value: 'binance',
    label: '币安',
    fullName: '币安 Binance',
    icon: '🟡',
    description: '全球最大的加密货币交易所',
    helpLink: 'https://www.binance.com/zh-CN/support/faq/how-to-create-api-keys-on-binance-360002502072',
  },
  OKX: {
    value: 'okx',
    label: '欧易',
    fullName: '欧易 OKX',
    icon: '⚫',
    description: '知名的加密货币交易平台',
    helpLink: 'https://www.okx.com/zh-hans/help/iii-create-an-api-key',
  },
};

// 通知类型定义 - 添加详细说明
const NOTIFICATION_TYPES = {
  PUSHPLUS: {
    value: 'pushplus',
    label: 'PushPlus',
    fullName: 'PushPlus 微信推送',
    icon: '📱',
    description: '简单易用的微信消息推送服务',
    helpLink: 'http://www.pushplus.plus/doc/',
  },
  WECHAT: {
    value: 'wechat',
    label: '微信',
    fullName: '企业微信通知',
    icon: '💬',
    description: '通过企业微信接收交易通知',
    helpLink: 'https://developer.work.weixin.qq.com/document/path/90665',
  },
  EMAIL: {
    value: 'email',
    label: '邮件',
    fullName: '邮件通知',
    icon: '📧',
    description: '通过电子邮件接收交易通知',
    helpLink: '',
  },
  TELEGRAM: {
    value: 'telegram',
    label: 'Telegram',
    fullName: 'Telegram 通知',
    icon: '✈️',
    description: '通过 Telegram 机器人接收通知',
    helpLink: 'https://core.telegram.org/bots#how-do-i-create-a-bot',
  },
};

// AI配置类型定义
const AI_TYPES = {
  OPENAI: {
    value: 'openai',
    label: 'OpenAI',
    fullName: 'OpenAI API',
    icon: '🤖',
    description: 'OpenAI GPT系列模型',
    helpLink: 'https://platform.openai.com/api-keys',
  },
  ANTHROPIC: {
    value: 'anthropic',
    label: 'Anthropic',
    fullName: 'Anthropic Claude',
    icon: '🧠',
    description: 'Anthropic Claude系列模型',
    helpLink: 'https://console.anthropic.com/settings/keys',
  },
};

// 交易所配置字段模板 - 添加详细帮助信息
const EXCHANGE_CONFIG_FIELDS = {
  binance: [
    {
      key: 'API_KEY',
      label: 'API密钥',
      type: 'input',
      required: true,
      placeholder: '粘贴从币安获取的API Key',
      help: '从币安账户设置中获取，用于访问交易所功能',
      example: '例如: PMkLl4dQAYnOz7GvhN3j8fK2mR9tWxCq',
    },
    {
      key: 'API_SECRET',
      label: 'API密钥（保密）',
      type: 'password',
      required: true,
      placeholder: '粘贴从币安获取的API Secret',
      help: '配合API Key使用，请妥善保管，不要泄露给他人',
      example: '',
    },
    {
      key: 'BASE_URL',
      label: 'API地址（可选）',
      type: 'input',
      required: false,
      placeholder: 'https://api.binance.com',
      help: '一般不需要修改。如果使用币安测试网，可填写测试网地址',
      example: '测试网: https://testnet.binance.vision',
    },
  ],
  okx: [
    {
      key: 'API_KEY',
      label: 'API密钥',
      type: 'input',
      required: true,
      placeholder: '粘贴从欧易获取的API Key',
      help: '从欧易账户设置中获取，用于访问交易所功能',
      example: '例如: 6b3f8c2a-9d1e-4f7b-a5c8-2e9d7f1b4a3c',
    },
    {
      key: 'API_SECRET',
      label: 'API密钥（保密）',
      type: 'password',
      required: true,
      placeholder: '粘贴从欧易获取的API Secret',
      help: '配合API Key使用，请妥善保管',
      example: '',
    },
    {
      key: 'PASSPHRASE',
      label: '密码短语',
      type: 'password',
      required: true,
      placeholder: '创建API时设置的密码短语',
      help: '创建API密钥时自己设置的密码短语',
      example: '',
    },
    {
      key: 'BASE_URL',
      label: 'API地址（可选）',
      type: 'input',
      required: false,
      placeholder: 'https://www.okx.com',
      help: '一般不需要修改',
      example: '',
    },
  ],
};

// 通知配置字段模板
const NOTIFICATION_CONFIG_FIELDS = {
  pushplus: [
    {
      key: 'TOKEN',
      label: 'Token',
      type: 'password',
      required: true,
      placeholder: '粘贴从PushPlus获取的Token',
      help: '登录 pushplus.plus 网站，在"发送消息"页面获取',
      example: '例如: abc123def456ghi789jkl',
    },
    {
      key: 'TOPIC',
      label: '群组编码（可选）',
      type: 'input',
      required: false,
      placeholder: '留空则发送给自己，填写则发送给群组',
      help: '如需群发，在PushPlus网站创建群组后获取群组编码',
      example: '例如: mygroup',
    },
  ],
  wechat: [
    {
      key: 'CORP_ID',
      label: '企业ID',
      type: 'input',
      required: true,
      placeholder: '输入企业微信的企业ID',
      help: '在企业微信管理后台的"我的企业"中查看',
      example: '例如: ww1234567890abcdef',
    },
    {
      key: 'CORP_SECRET',
      label: '企业密钥',
      type: 'password',
      required: true,
      placeholder: '输入应用的Secret',
      help: '在企业微信应用管理中查看',
      example: '',
    },
    {
      key: 'AGENT_ID',
      label: '应用ID',
      type: 'input',
      required: true,
      placeholder: '输入应用的AgentId',
      help: '在企业微信应用详情中查看',
      example: '例如: 1000002',
    },
  ],
  email: [
    {
      key: 'SMTP_HOST',
      label: 'SMTP服务器',
      type: 'input',
      required: true,
      placeholder: '例如: smtp.gmail.com',
      help: '邮箱服务商的SMTP服务器地址',
      example: 'QQ邮箱: smtp.qq.com, 163邮箱: smtp.163.com',
    },
    {
      key: 'SMTP_PORT',
      label: 'SMTP端口',
      type: 'input',
      required: true,
      placeholder: '587',
      help: 'SMTP服务器端口，通常是587或465',
      example: '587（推荐）或 465',
    },
    {
      key: 'SMTP_USER',
      label: '发件邮箱',
      type: 'input',
      required: true,
      placeholder: 'your@email.com',
      help: '用于发送通知的邮箱地址',
      example: '例如: mybot@gmail.com',
    },
    {
      key: 'SMTP_PASSWORD',
      label: '邮箱密码',
      type: 'password',
      required: true,
      placeholder: '输入邮箱密码或授权码',
      help: 'QQ邮箱、163邮箱等需要使用"授权码"，不是登录密码',
      example: '',
    },
    {
      key: 'RECEIVER_EMAIL',
      label: '接收邮箱',
      type: 'input',
      required: true,
      placeholder: 'receiver@email.com',
      help: '接收交易通知的邮箱地址',
      example: '可以和发件邮箱相同',
    },
  ],
  telegram: [
    {
      key: 'BOT_TOKEN',
      label: 'Bot Token',
      type: 'password',
      required: true,
      placeholder: '粘贴从BotFather获取的Token',
      help: '向 @BotFather 发送 /newbot 创建机器人后获得',
      example: '例如: 123456789:ABCdefGhIjKlmNoPQRsTUVwxyZ',
    },
    {
      key: 'CHAT_ID',
      label: 'Chat ID',
      type: 'input',
      required: true,
      placeholder: '输入你的Chat ID',
      help: '向 @userinfobot 发送消息可查看你的Chat ID',
      example: '例如: 123456789',
    },
  ],
};

// AI配置字段模板
const AI_CONFIG_FIELDS = {
  openai: [
    {
      key: 'API_KEY',
      label: 'API密钥',
      type: 'password',
      required: true,
      placeholder: '粘贴从OpenAI获取的API Key',
      help: '登录OpenAI平台，在API Keys页面创建新密钥',
      example: '例如: sk-proj-abcdefghijklmnopqrstuvwxyz123456',
    },
    {
      key: 'BASE_URL',
      label: 'API代理地址（可选）',
      type: 'input',
      required: false,
      placeholder: 'https://api.openai.com/v1',
      help: '如果使用第三方代理或中转，请填写代理地址',
      example: '默认: https://api.openai.com/v1',
    },
  ],
  anthropic: [
    {
      key: 'API_KEY',
      label: 'API密钥',
      type: 'password',
      required: true,
      placeholder: '粘贴从Anthropic获取的API Key',
      help: '登录Anthropic Console，在Settings -> API Keys创建新密钥',
      example: '例如: sk-ant-api03-abcdefghijklmnopqrstuvwxyz',
    },
    {
      key: 'BASE_URL',
      label: 'API代理地址（可选）',
      type: 'input',
      required: false,
      placeholder: 'https://api.anthropic.com',
      help: '如果使用第三方代理或中转，请填写代理地址',
      example: '默认: https://api.anthropic.com',
    },
  ],
};

const ConfigDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<Configuration | null>(null);

  const [currentStep, setCurrentStep] = useState(0);
  const [configType, setConfigType] = useState<string>('');
  const [subType, setSubType] = useState<string>('');

  const isNew = id === 'new';

  // 加载配置详情
  useEffect(() => {
    if (!isNew) {
      loadConfig();
    }
  }, [id]);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await getConfig(Number(id));
      setConfig(data);

      // 解析配置类型和子类型
      const configKey = data.config_key;
      if (configKey.startsWith('BINANCE_')) {
        setConfigType(ConfigType.EXCHANGE);
        setSubType('binance');
      } else if (configKey.startsWith('OKX_')) {
        setConfigType(ConfigType.EXCHANGE);
        setSubType('okx');
      } else if (configKey.startsWith('PUSHPLUS_')) {
        setConfigType(ConfigType.NOTIFICATION);
        setSubType('pushplus');
      } else if (configKey.includes('WECHAT')) {
        setConfigType(ConfigType.NOTIFICATION);
        setSubType('wechat');
      } else if (configKey.includes('EMAIL') || configKey.includes('SMTP')) {
        setConfigType(ConfigType.NOTIFICATION);
        setSubType('email');
      } else if (configKey.includes('TELEGRAM')) {
        setConfigType(ConfigType.NOTIFICATION);
        setSubType('telegram');
      } else if (configKey.startsWith('OPENAI_')) {
        setConfigType(ConfigType.AI);
        setSubType('openai');
      } else if (configKey.startsWith('ANTHROPIC_')) {
        setConfigType(ConfigType.AI);
        setSubType('anthropic');
      }

      // 设置表单值
      form.setFieldsValue({
        config_value: data.config_value,
      });

      setCurrentStep(2); // 直接进入编辑步骤
    } catch (error) {
      message.error('加载配置失败');
      navigate('/configs');
    } finally {
      setLoading(false);
    }
  };

  // 选择配置类型
  const handleSelectConfigType = (type: string) => {
    setConfigType(type);
    setSubType('');
    setCurrentStep(1);
  };

  // 选择子类型
  const handleSelectSubType = (type: string) => {
    setSubType(type);
    setCurrentStep(2);
  };

  // 保存配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      if (isNew) {
        // 新增模式：批量创建配置
        const fields = configType === ConfigType.EXCHANGE
          ? EXCHANGE_CONFIG_FIELDS[subType as keyof typeof EXCHANGE_CONFIG_FIELDS]
          : configType === ConfigType.NOTIFICATION
          ? NOTIFICATION_CONFIG_FIELDS[subType as keyof typeof NOTIFICATION_CONFIG_FIELDS]
          : AI_CONFIG_FIELDS[subType as keyof typeof AI_CONFIG_FIELDS];

        const configs = fields.map((field) => {
          const value = values[`dynamic_${field.key}`];
          if (!value && field.required) {
            throw new Error(`请填写${field.label}`);
          }

          const typeLabel = configType === ConfigType.EXCHANGE
            ? EXCHANGE_TYPES[subType.toUpperCase() as keyof typeof EXCHANGE_TYPES]?.label
            : configType === ConfigType.NOTIFICATION
            ? NOTIFICATION_TYPES[subType.toUpperCase() as keyof typeof NOTIFICATION_TYPES]?.label
            : AI_TYPES[subType.toUpperCase() as keyof typeof AI_TYPES]?.label;

          return {
            config_key: `${subType.toUpperCase()}_${field.key}`,
            display_name: `${typeLabel} - ${field.label}`,
            config_value: value || field.placeholder || '',
            config_type: configType,
            status: ConfigStatus.ACTIVE,
            is_sensitive: field.type === 'password',
            is_required: field.required,
            requires_restart: configType === ConfigType.EXCHANGE || configType === ConfigType.AI,
          };
        });

        // 批量创建
        for (const config of configs) {
          if (config.config_value) { // 只创建有值的配置
            await createConfig(config);
          }
        }

        message.success('配置添加成功！');
      } else {
        // 编辑模式：更新单条配置
        await updateConfig(Number(id), {
          config_value: values.config_value,
          status: ConfigStatus.ACTIVE,
        });
        message.success('配置更新成功！');
      }

      navigate('/configs');
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请检查表单填写');
      } else {
        message.error(error.message || (isNew ? '添加失败' : '更新失败'));
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '0 24px 24px' }}>
      {/* 页面头部 */}
      <div style={{ marginBottom: 32 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/configs')}
          style={{ marginBottom: 16, color: '#6B7280' }}
        >
          返回配置列表
        </Button>
        <Title level={2} style={{ marginBottom: 8, color: '#111827' }}>
          {isNew ? '添加新配置' : '编辑配置'}
        </Title>
        <Paragraph style={{ fontSize: 15, color: '#6B7280', marginBottom: 0 }}>
          {isNew ? '按照下面的步骤，一步步完成配置' : '修改配置信息'}
        </Paragraph>
      </div>

      {/* 步骤指示器 */}
      {isNew && (
        <Card style={{ marginBottom: 24, borderRadius: 12 }}>
          <Steps
            current={currentStep}
            items={[
              {
                title: '选择类型',
                description: '选择要配置的功能',
                icon: currentStep > 0 ? <CheckCircleOutlined /> : undefined,
              },
              {
                title: '选择平台',
                description: '选择具体的平台',
                icon: currentStep > 1 ? <CheckCircleOutlined /> : undefined,
              },
              {
                title: '填写信息',
                description: '填写配置信息',
                icon: currentStep > 2 ? <CheckCircleOutlined /> : undefined,
              },
            ]}
          />
        </Card>
      )}

      {/* 步骤1：选择配置类型 */}
      {isNew && currentStep === 0 && (
        <Row gutter={16}>
          <Col span={8}>
            <Card
              hoverable
              onClick={() => handleSelectConfigType(ConfigType.EXCHANGE)}
              style={{
                height: 240,
                borderRadius: 12,
                border: '2px solid #E5E7EB',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
              styles={{
                body: {
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  padding: 32,
                },
              }}
            >
              <ThunderboltOutlined style={{ fontSize: 64, color: '#3B82F6', marginBottom: 24 }} />
              <Title level={3} style={{ marginBottom: 12, color: '#111827' }}>
                交易所配置
              </Title>
              <Paragraph style={{ textAlign: 'center', color: '#6B7280', marginBottom: 0 }}>
                连接币安、欧易等交易所，让系统可以自动交易
              </Paragraph>
            </Card>
          </Col>
          <Col span={8}>
            <Card
              hoverable
              onClick={() => handleSelectConfigType(ConfigType.NOTIFICATION)}
              style={{
                height: 240,
                borderRadius: 12,
                border: '2px solid #E5E7EB',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
              styles={{
                body: {
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  padding: 32,
                },
              }}
            >
              <BellOutlined style={{ fontSize: 64, color: '#10B981', marginBottom: 24 }} />
              <Title level={3} style={{ marginBottom: 12, color: '#111827' }}>
                通知配置
              </Title>
              <Paragraph style={{ textAlign: 'center', color: '#6B7280', marginBottom: 0 }}>
                设置微信、邮件等通知方式，及时接收交易提醒
              </Paragraph>
            </Card>
          </Col>
          <Col span={8}>
            <Card
              hoverable
              onClick={() => handleSelectConfigType(ConfigType.AI)}
              style={{
                height: 240,
                borderRadius: 12,
                border: '2px solid #E5E7EB',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
              styles={{
                body: {
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  padding: 32,
                },
              }}
            >
              <span style={{ fontSize: 64, marginBottom: 24 }}>🤖</span>
              <Title level={3} style={{ marginBottom: 12, color: '#111827' }}>
                AI配置
              </Title>
              <Paragraph style={{ textAlign: 'center', color: '#6B7280', marginBottom: 0 }}>
                配置OpenAI、Claude等AI服务，启用智能分析功能
              </Paragraph>
            </Card>
          </Col>
        </Row>
      )}

      {/* 步骤2：选择具体类型 */}
      {isNew && currentStep === 1 && (
        <>
          <Alert
            message={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <InfoCircleOutlined />
                <span>
                  {configType === ConfigType.EXCHANGE
                    ? '选择你想连接的交易所'
                    : configType === ConfigType.NOTIFICATION
                    ? '选择你想使用的通知方式'
                    : '选择你想使用的AI服务'}
                </span>
              </div>
            }
            type="info"
            style={{ marginBottom: 24, borderRadius: 8 }}
          />

          {configType === ConfigType.EXCHANGE ? (
            <Row gutter={16}>
              {Object.values(EXCHANGE_TYPES).map((exchange) => (
                <Col span={12} key={exchange.value}>
                  <Card
                    hoverable
                    onClick={() => handleSelectSubType(exchange.value)}
                    style={{
                      height: 200,
                      borderRadius: 12,
                      border: '2px solid #E5E7EB',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease',
                    }}
                    styles={{
                      body: {
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        padding: 24,
                      },
                    }}
                  >
                    <div style={{ fontSize: 56, marginBottom: 16 }}>{exchange.icon}</div>
                    <Title level={4} style={{ marginBottom: 8, color: '#111827' }}>
                      {exchange.fullName}
                    </Title>
                    <Text style={{ textAlign: 'center', color: '#6B7280', fontSize: 13 }}>
                      {exchange.description}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>
          ) : configType === ConfigType.NOTIFICATION ? (
            <Row gutter={[16, 16]}>
              {Object.values(NOTIFICATION_TYPES).map((notif) => (
                <Col span={12} key={notif.value}>
                  <Card
                    hoverable
                    onClick={() => handleSelectSubType(notif.value)}
                    style={{
                      height: 180,
                      borderRadius: 12,
                      border: '2px solid #E5E7EB',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease',
                    }}
                    styles={{
                      body: {
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        padding: 20,
                      },
                    }}
                  >
                    <div style={{ fontSize: 48, marginBottom: 12 }}>{notif.icon}</div>
                    <Title level={4} style={{ marginBottom: 8, color: '#111827' }}>
                      {notif.fullName}
                    </Title>
                    <Text style={{ textAlign: 'center', color: '#6B7280', fontSize: 13 }}>
                      {notif.description}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>
          ) : (
            <Row gutter={16}>
              {Object.values(AI_TYPES).map((ai) => (
                <Col span={12} key={ai.value}>
                  <Card
                    hoverable
                    onClick={() => handleSelectSubType(ai.value)}
                    style={{
                      height: 200,
                      borderRadius: 12,
                      border: '2px solid #E5E7EB',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease',
                    }}
                    styles={{
                      body: {
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        padding: 24,
                      },
                    }}
                  >
                    <div style={{ fontSize: 56, marginBottom: 16 }}>{ai.icon}</div>
                    <Title level={4} style={{ marginBottom: 8, color: '#111827' }}>
                      {ai.fullName}
                    </Title>
                    <Text style={{ textAlign: 'center', color: '#6B7280', fontSize: 13 }}>
                      {ai.description}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </>
      )}

      {/* 步骤3：填写配置信息 */}
      {((isNew && currentStep === 2) || !isNew) && (
        <Card style={{ borderRadius: 12 }}>
          {isNew && (
            <Alert
              message={
                <div>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>
                    {configType === ConfigType.EXCHANGE
                      ? `配置 ${EXCHANGE_TYPES[subType.toUpperCase() as keyof typeof EXCHANGE_TYPES]?.fullName}`
                      : configType === ConfigType.NOTIFICATION
                      ? `配置 ${NOTIFICATION_TYPES[subType.toUpperCase() as keyof typeof NOTIFICATION_TYPES]?.fullName}`
                      : `配置 ${AI_TYPES[subType.toUpperCase() as keyof typeof AI_TYPES]?.fullName}`}
                  </div>
                  <div style={{ fontSize: 13, color: '#6B7280' }}>
                    请仔细填写以下信息，确保信息准确无误
                    {configType === ConfigType.EXCHANGE && (
                      <>
                        {' '}· <a
                          href={EXCHANGE_TYPES[subType.toUpperCase() as keyof typeof EXCHANGE_TYPES]?.helpLink}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          如何获取API密钥？
                        </a>
                      </>
                    )}
                    {configType === ConfigType.AI && (
                      <>
                        {' '}· <a
                          href={AI_TYPES[subType.toUpperCase() as keyof typeof AI_TYPES]?.helpLink}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          如何获取API密钥？
                        </a>
                      </>
                    )}
                  </div>
                </div>
              }
              type="info"
              style={{ marginBottom: 24, borderRadius: 8 }}
              icon={<InfoCircleOutlined />}
            />
          )}

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSave}
          >
            {isNew ? (
              // 新增模式：显示所有字段
              <>
                {configType === ConfigType.EXCHANGE &&
                  EXCHANGE_CONFIG_FIELDS[subType as keyof typeof EXCHANGE_CONFIG_FIELDS]?.map((field) => (
                    <Form.Item
                      key={field.key}
                      name={`dynamic_${field.key}`}
                      label={
                        <Space>
                          <span style={{ fontSize: 14, fontWeight: 500, color: '#111827' }}>
                            {field.label}
                          </span>
                          {field.help && (
                            <Tooltip title={
                              <div>
                                <div style={{ marginBottom: 4 }}>{field.help}</div>
                                {field.example && (
                                  <div style={{ fontSize: 12, opacity: 0.85 }}>
                                    {field.example}
                                  </div>
                                )}
                              </div>
                            }>
                              <QuestionCircleOutlined style={{ color: '#9CA3AF', cursor: 'help' }} />
                            </Tooltip>
                          )}
                        </Space>
                      }
                      rules={[
                        { required: field.required, message: `请输入${field.label}` },
                      ]}
                    >
                      {field.type === 'password' ? (
                        <Input.Password
                          placeholder={field.placeholder}
                          size="large"
                          style={{ fontSize: 14 }}
                        />
                      ) : (
                        <Input
                          placeholder={field.placeholder}
                          size="large"
                          style={{ fontSize: 14 }}
                        />
                      )}
                    </Form.Item>
                  ))}

                {configType === ConfigType.NOTIFICATION &&
                  NOTIFICATION_CONFIG_FIELDS[subType as keyof typeof NOTIFICATION_CONFIG_FIELDS]?.map((field) => (
                    <Form.Item
                      key={field.key}
                      name={`dynamic_${field.key}`}
                      label={
                        <Space>
                          <span style={{ fontSize: 14, fontWeight: 500, color: '#111827' }}>
                            {field.label}
                          </span>
                          {field.help && (
                            <Tooltip title={
                              <div>
                                <div style={{ marginBottom: 4 }}>{field.help}</div>
                                {field.example && (
                                  <div style={{ fontSize: 12, opacity: 0.85 }}>
                                    {field.example}
                                  </div>
                                )}
                              </div>
                            }>
                              <QuestionCircleOutlined style={{ color: '#9CA3AF', cursor: 'help' }} />
                            </Tooltip>
                          )}
                        </Space>
                      }
                      rules={[
                        { required: field.required, message: `请输入${field.label}` },
                      ]}
                    >
                      {field.type === 'password' ? (
                        <Input.Password
                          placeholder={field.placeholder}
                          size="large"
                          style={{ fontSize: 14 }}
                        />
                      ) : (
                        <Input
                          placeholder={field.placeholder}
                          size="large"
                          style={{ fontSize: 14 }}
                        />
                      )}
                    </Form.Item>
                  ))}

                {configType === ConfigType.AI &&
                  AI_CONFIG_FIELDS[subType as keyof typeof AI_CONFIG_FIELDS]?.map((field) => (
                    <Form.Item
                      key={field.key}
                      name={`dynamic_${field.key}`}
                      label={
                        <Space>
                          <span style={{ fontSize: 14, fontWeight: 500, color: '#111827' }}>
                            {field.label}
                          </span>
                          {field.help && (
                            <Tooltip title={
                              <div>
                                <div style={{ marginBottom: 4 }}>{field.help}</div>
                                {field.example && (
                                  <div style={{ fontSize: 12, opacity: 0.85 }}>
                                    {field.example}
                                  </div>
                                )}
                              </div>
                            }>
                              <QuestionCircleOutlined style={{ color: '#9CA3AF', cursor: 'help' }} />
                            </Tooltip>
                          )}
                        </Space>
                      }
                      rules={[
                        { required: field.required, message: `请输入${field.label}` },
                      ]}
                    >
                      {field.type === 'password' ? (
                        <Input.Password
                          placeholder={field.placeholder}
                          size="large"
                          style={{ fontSize: 14 }}
                        />
                      ) : (
                        <Input
                          placeholder={field.placeholder}
                          size="large"
                          style={{ fontSize: 14 }}
                        />
                      )}
                    </Form.Item>
                  ))}
              </>
            ) : (
              // 编辑模式：只显示配置值
              <>
                <Alert
                  message="提示"
                  description={`正在编辑：${config?.display_name}`}
                  type="info"
                  style={{ marginBottom: 24, borderRadius: 8 }}
                  icon={<InfoCircleOutlined />}
                />
                <Form.Item
                  name="config_value"
                  label={
                    <span style={{ fontSize: 14, fontWeight: 500, color: '#111827' }}>
                      配置值
                    </span>
                  }
                  rules={[{ required: true, message: '请输入配置值' }]}
                >
                  {config?.is_sensitive ? (
                    <Input.Password
                      placeholder="请输入新的配置值"
                      size="large"
                      style={{ fontSize: 14 }}
                    />
                  ) : (
                    <Input
                      placeholder="请输入新的配置值"
                      size="large"
                      style={{ fontSize: 14 }}
                    />
                  )}
                </Form.Item>
              </>
            )}

            <Form.Item style={{ marginTop: 32, marginBottom: 0 }}>
              <Space size={12}>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  loading={saving}
                  size="large"
                  style={{ minWidth: 120 }}
                >
                  {isNew ? '保存配置' : '更新配置'}
                </Button>
                <Button
                  onClick={() => navigate('/configs')}
                  size="large"
                >
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      )}

      {/* 底部帮助提示 */}
      {isNew && currentStep === 2 && (
        <Alert
          message="需要帮助？"
          description={
            <div>
              <p style={{ marginBottom: 8 }}>
                如果您不知道如何填写这些信息，可以：
              </p>
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li>查看每个字段旁边的 <QuestionCircleOutlined /> 图标获取详细说明</li>
                {configType === ConfigType.EXCHANGE && (
                  <li>
                    访问交易所的帮助文档了解如何创建API密钥
                  </li>
                )}
                {configType === ConfigType.AI && (
                  <li>
                    访问AI服务商的帮助文档了解如何创建API密钥
                  </li>
                )}
                <li>如果遇到问题，可以联系技术支持</li>
              </ul>
            </div>
          }
          type="warning"
          showIcon
          style={{ marginTop: 24, borderRadius: 8 }}
        />
      )}
    </div>
  );
};

export default ConfigDetail;
