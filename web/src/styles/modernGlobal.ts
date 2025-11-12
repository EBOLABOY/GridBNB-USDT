/**
 * 现代化全局样式
 */

import { modernThemeVars } from './modernTheme';

// 注入CSS变量到根元素
export const injectModernTheme = () => {
  const root = document.documentElement;
  Object.entries(modernThemeVars).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
};

// 全局样式（可以在main.tsx中导入）
export const modernGlobalStyles = `
  /* 现代化主题全局样式 */

  body {
    background: var(--gradient-background);
    background-attachment: fixed;
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  }

  /* 滚动条样式 */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.3);
    border-radius: 4px;
    transition: background 0.3s ease;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 212, 255, 0.5);
  }

  /* 选中文本样式 */
  ::selection {
    background: rgba(0, 212, 255, 0.3);
    color: #fff;
  }

  /* Ant Design组件覆盖 */
  .ant-card {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-color) !important;
    backdrop-filter: var(--backdrop-filter);
  }

  .ant-statistic-title {
    color: var(--text-secondary) !important;
  }

  .ant-statistic-content {
    color: var(--text-primary) !important;
  }

  .ant-table {
    background: transparent !important;
  }

  .ant-table-thead > tr > th {
    background: rgba(255, 255, 255, 0.05) !important;
    color: var(--text-secondary) !important;
    border-bottom: 1px solid var(--border-color) !important;
  }

  .ant-table-tbody > tr > td {
    border-bottom: 1px solid var(--border-color) !important;
    color: var(--text-primary) !important;
  }

  .ant-table-tbody > tr:hover > td {
    background: rgba(0, 212, 255, 0.05) !important;
  }

  .ant-tag {
    border: none !important;
  }

  .ant-btn-primary {
    background: var(--color-primary) !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3) !important;
  }

  .ant-btn-primary:hover {
    background: var(--color-primary-dark) !important;
    box-shadow: 0 6px 16px rgba(0, 212, 255, 0.4) !important;
  }

  /* 输入框样式 */
  .ant-input,
  .ant-select-selector,
  .ant-picker {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-primary) !important;
  }

  .ant-input:hover,
  .ant-select-selector:hover,
  .ant-picker:hover {
    border-color: var(--color-primary) !important;
  }

  .ant-input:focus,
  .ant-select-focused .ant-select-selector {
    border-color: var(--color-primary) !important;
    box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.1) !important;
  }

  /* Modal样式 */
  .ant-modal-content {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-color) !important;
    backdrop-filter: var(--backdrop-filter);
  }

  .ant-modal-header {
    background: transparent !important;
    border-bottom: 1px solid var(--border-color) !important;
  }

  .ant-modal-title {
    color: var(--text-primary) !important;
  }

  .ant-modal-close {
    color: var(--text-secondary) !important;
  }

  /* Tabs样式 */
  .ant-tabs-tab {
    color: var(--text-secondary) !important;
  }

  .ant-tabs-tab-active .ant-tabs-tab-btn {
    color: var(--color-primary) !important;
  }

  .ant-tabs-ink-bar {
    background: var(--color-primary) !important;
  }

  /* 动画 */
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes glow {
    0%, 100% {
      box-shadow: 0 0 5px rgba(0, 212, 255, 0.5);
    }
    50% {
      box-shadow: 0 0 20px rgba(0, 212, 255, 0.8);
    }
  }

  .fade-in {
    animation: fadeIn 0.5s ease-out;
  }

  .glow {
    animation: glow 2s ease-in-out infinite;
  }
`;

export default modernGlobalStyles;
