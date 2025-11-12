/**
 * Ant Design 主题配置 - 现代化浅色风格
 */

import type { ThemeConfig } from 'antd';

// 现代化配色方案 - 专业交易平台风格
export const modernColors = {
  // 主题色 - 优雅的蓝色
  primary: '#3B82F6',        // 蓝色
  primaryHover: '#2563EB',
  primaryActive: '#1D4ED8',
  primaryLight: '#DBEAFE',

  // 涨跌色
  success: '#10B981',        // 绿色（涨）
  error: '#EF4444',          // 红色（跌）

  // 辅助色
  warning: '#F59E0B',
  info: '#3B82F6',

  // 浅色模式 - 背景色
  bgPrimary: '#FFFFFF',
  bgSecondary: '#F9FAFB',
  bgTertiary: '#F3F4F6',

  // 浅色模式 - 文字色
  textPrimary: '#111827',
  textSecondary: '#6B7280',
  textTertiary: '#9CA3AF',

  // 暗色模式 - 背景色
  bgDark: '#0F172A',
  bgDarkSecondary: '#1E293B',
  bgDarkTertiary: '#334155',

  // 暗色模式 - 文字色
  textDarkPrimary: '#F1F5F9',
  textDarkSecondary: '#CBD5E1',
  textDarkTertiary: '#94A3B8',

  // 边框色
  border: '#E5E7EB',
  borderDark: '#374151',
};

// 亮色主题 - 现代专业风格
export const lightTheme: ThemeConfig = {
  token: {
    colorPrimary: modernColors.primary,
    colorSuccess: modernColors.success,
    colorWarning: modernColors.warning,
    colorError: modernColors.error,
    colorInfo: modernColors.info,

    colorBgBase: modernColors.bgPrimary,
    colorTextBase: modernColors.textPrimary,
    colorBorder: modernColors.border,

    borderRadius: 8,
    fontSize: 14,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',

    // 阴影
    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02)',
    boxShadowSecondary: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  },
  components: {
    Layout: {
      headerBg: modernColors.bgPrimary,
      bodyBg: '#F5F7FA',  // 更柔和的浅灰色背景
      triggerBg: modernColors.bgTertiary,
      siderBg: modernColors.bgPrimary,
      headerHeight: 64,
      headerPadding: '0 24px',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: modernColors.primaryLight,
      itemSelectedColor: modernColors.primary,
      itemHoverBg: modernColors.bgTertiary,
      itemColor: modernColors.textSecondary,
      itemActiveBg: modernColors.primaryLight,
      itemMarginInline: 4,
      itemBorderRadius: 6,
    },
    Card: {
      colorBgContainer: modernColors.bgPrimary,
      boxShadowTertiary: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02)',
      paddingLG: 24,
      borderRadiusLG: 12,
    },
    Table: {
      headerBg: '#F9FAFB',
      rowHoverBg: '#F3F4F6',
      colorBgContainer: '#FFFFFF',
      headerColor: '#111827',
      colorText: '#1F2937',
      borderColor: modernColors.border,
      fontSize: 14,
    },
    Button: {
      primaryShadow: 'none',
      controlHeight: 36,
      borderRadius: 6,
      fontWeight: 500,
    },
    Input: {
      colorBgContainer: '#FFFFFF',
      colorBorder: '#D1D5DB',
      colorText: '#111827',
      colorTextPlaceholder: '#9CA3AF',
      controlHeight: 36,
      borderRadius: 6,
      fontSize: 14,
    },
    Select: {
      colorBgContainer: '#FFFFFF',
      colorBorder: '#D1D5DB',
      colorText: '#111827',
      controlHeight: 36,
      borderRadius: 6,
      fontSize: 14,
    },
    Tabs: {
      itemActiveColor: modernColors.primary,
      itemSelectedColor: modernColors.primary,
      itemHoverColor: modernColors.primaryHover,
      inkBarColor: modernColors.primary,
    },
  },
};

// 暗色主题 - 现代专业风格
export const darkTheme: ThemeConfig = {
  token: {
    colorPrimary: modernColors.primary,
    colorSuccess: modernColors.success,
    colorWarning: modernColors.warning,
    colorError: modernColors.error,
    colorInfo: modernColors.info,

    colorBgBase: modernColors.bgDark,
    colorTextBase: modernColors.textDarkPrimary,
    colorBorder: modernColors.borderDark,
    colorBgContainer: modernColors.bgDarkSecondary,
    colorBgElevated: modernColors.bgDarkTertiary,

    borderRadius: 8,
    fontSize: 14,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',

    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.3), 0 1px 6px -1px rgba(0, 0, 0, 0.2)',
    boxShadowSecondary: '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3)',
  },
  components: {
    Layout: {
      headerBg: modernColors.bgDarkSecondary,
      bodyBg: modernColors.bgDark,
      triggerBg: modernColors.bgDarkTertiary,
      siderBg: modernColors.bgDarkSecondary,
      headerHeight: 64,
      headerPadding: '0 24px',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(59, 130, 246, 0.15)',
      itemSelectedColor: modernColors.primary,
      itemHoverBg: 'rgba(59, 130, 246, 0.08)',
      itemColor: modernColors.textDarkSecondary,
      itemActiveBg: 'rgba(59, 130, 246, 0.2)',
      itemMarginInline: 4,
      itemBorderRadius: 6,
    },
    Card: {
      colorBgContainer: modernColors.bgDarkSecondary,
      colorBorderSecondary: modernColors.borderDark,
      boxShadowTertiary: '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
      paddingLG: 24,
      borderRadiusLG: 12,
    },
    Table: {
      headerBg: modernColors.bgDarkTertiary,
      rowHoverBg: 'rgba(59, 130, 246, 0.05)',
      colorBgContainer: modernColors.bgDarkSecondary,
      headerColor: modernColors.textDarkSecondary,
      colorText: modernColors.textDarkPrimary,
      borderColor: modernColors.borderDark,
    },
    Button: {
      primaryShadow: 'none',
      colorBgContainer: modernColors.bgDarkTertiary,
      colorBorder: modernColors.borderDark,
      controlHeight: 36,
      borderRadius: 6,
    },
    Input: {
      colorBgContainer: modernColors.bgDarkTertiary,
      colorBorder: modernColors.borderDark,
      colorText: modernColors.textDarkPrimary,
      controlHeight: 36,
      borderRadius: 6,
    },
    Select: {
      colorBgContainer: modernColors.bgDarkTertiary,
      colorBorder: modernColors.borderDark,
      controlHeight: 36,
      borderRadius: 6,
    },
    Tabs: {
      itemActiveColor: modernColors.primary,
      itemSelectedColor: modernColors.primary,
      itemHoverColor: modernColors.primaryHover,
      inkBarColor: modernColors.primary,
    },
  },
};

// 导出币安配色（保持兼容性）
export const binanceColors = modernColors;
