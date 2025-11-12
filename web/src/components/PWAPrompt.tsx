/**
 * PWA安装提示组件
 */

import React, { useEffect, useState } from 'react';
import { Button, message, Space } from 'antd';
import { CloudDownloadOutlined, CloseOutlined } from '@ant-design/icons';

// 简化版PWA组件（不依赖vite-plugin-pwa的虚拟模块）
const PWAPrompt: React.FC = () => {
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showUpdatePrompt, setShowUpdatePrompt] = useState(false);

  // 监听PWA安装事件
  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstallPrompt(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // 监听Service Worker更新
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        setShowUpdatePrompt(true);
      });
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  // 安装PWA
  const handleInstallClick = async () => {
    if (!deferredPrompt) return;

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;

    if (outcome === 'accepted') {
      message.success('应用安装成功！');
      setShowInstallPrompt(false);
    } else {
      message.info('您取消了安装');
    }

    setDeferredPrompt(null);
  };

  // 刷新页面以应用更新
  const handleUpdate = () => {
    window.location.reload();
  };

  return (
    <>
      {/* Service Worker更新提示 */}
      {showUpdatePrompt && (
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 1000,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            padding: '16px 20px',
            borderRadius: 12,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            maxWidth: 400,
          }}
        >
          <div style={{ color: '#fff', marginBottom: 12 }}>
            🔔 发现新版本，点击更新
          </div>
          <Space>
            <Button
              type="primary"
              size="small"
              onClick={handleUpdate}
              style={{
                background: '#fff',
                color: '#667eea',
                border: 'none',
              }}
            >
              立即更新
            </Button>
            <Button
              type="text"
              size="small"
              icon={<CloseOutlined />}
              onClick={() => setShowUpdatePrompt(false)}
              style={{ color: '#fff' }}
            >
              关闭
            </Button>
          </Space>
        </div>
      )}

      {/* PWA安装提示 */}
      {showInstallPrompt && (
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            left: 24,
            zIndex: 1000,
            background: 'linear-gradient(135deg, #0093E9 0%, #80D0C7 100%)',
            padding: '16px 20px',
            borderRadius: 12,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            maxWidth: 400,
          }}
        >
          <div style={{ color: '#fff', marginBottom: 12 }}>
            <CloudDownloadOutlined style={{ marginRight: 8 }} />
            <strong>安装GridBNB到桌面</strong>
          </div>
          <div style={{ color: 'rgba(255,255,255,0.9)', fontSize: 12, marginBottom: 12 }}>
            无需下载APP，即可快速访问交易系统
          </div>
          <Space>
            <Button
              type="primary"
              size="small"
              onClick={handleInstallClick}
              style={{
                background: '#fff',
                color: '#0093E9',
                border: 'none',
              }}
            >
              立即安装
            </Button>
            <Button
              type="text"
              size="small"
              onClick={() => setShowInstallPrompt(false)}
              style={{ color: '#fff' }}
            >
              暂不安装
            </Button>
          </Space>
        </div>
      )}
    </>
  );
};

export default PWAPrompt;
