# GridBNB Trading System - 前端项目

企业级网格交易配置管理系统的React前端应用。

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite 7
- **UI库**: Ant Design 5 + Ant Design Pro Components
- **路由**: React Router v6
- **HTTP客户端**: Axios
- **国际化**: 中文 (zh-CN)

## 项目结构

```
web/
├── src/
│   ├── api/              # API接口封装
│   ├── components/       # 通用组件
│   ├── layouts/          # 布局组件
│   ├── pages/            # 页面组件
│   ├── routes/           # 路由配置
│   ├── types/            # TypeScript类型定义
│   └── utils/            # 工具函数
├── .env.development      # 开发环境配置
├── .env.production       # 生产环境配置
└── vite.config.ts        # Vite配置
```

## 快速开始

### 安装依赖
```bash
npm install
```

### 开发模式
```bash
npm run dev
```
访问 http://localhost:3000

### 构建生产版本
```bash
npm run build
```

## 默认登录信息

- 用户名: `admin`
- 密码: `admin123`

⚠️ **首次登录后请立即修改密码**
