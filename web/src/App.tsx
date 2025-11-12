import { Suspense } from 'react';
import { BrowserRouter, useRoutes } from 'react-router-dom';
import { ConfigProvider, Spin, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext';
import ParticleBackground from '@/components/ParticleBackground';
import PWAPrompt from '@/components/PWAPrompt';
import routes from './routes';
import './App.css';

// 路由组件
const AppRoutes = () => {
  return useRoutes(routes);
};

// 加载中组件
const PageLoading = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
    <Spin size="large" tip="加载中...">
      <div style={{ padding: '50px' }} />
    </Spin>
  </div>
);

// 内部App组件，使用主题
const AppContent = () => {
  const { theme: currentTheme, themeConfig } = useTheme();

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        ...themeConfig,
        algorithm: currentTheme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      }}
    >
      {/* 粒子背景 */}
      <ParticleBackground />

      {/* PWA安装提示 */}
      <PWAPrompt />

      <BrowserRouter>
        <Suspense fallback={<PageLoading />}>
          <AppRoutes />
        </Suspense>
      </BrowserRouter>
    </ConfigProvider>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
