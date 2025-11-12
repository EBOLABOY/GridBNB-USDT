/**
 * 现代化主题配置 - 清爽浅色主题
 */

export const modernTheme = {
  // 主色调 - 优雅蓝色
  colors: {
    primary: '#3B82F6',
    primaryDark: '#2563EB',
    primaryLight: '#60A5FA',

    // 辅助色
    secondary: '#8B5CF6',
    accent: '#EC4899',
    warning: '#F59E0B',

    // 涨跌色
    success: '#10B981',
    danger: '#EF4444',

    // 背景色 - 浅色系
    bgPrimary: '#FFFFFF',
    bgSecondary: '#F9FAFB',
    bgTertiary: '#F3F4F6',

    // 文字色
    textPrimary: '#111827',
    textSecondary: '#6B7280',
    textMuted: '#9CA3AF',

    // 边框色
    border: '#E5E7EB',
    borderLight: '#F3F4F6',

    // 玻璃态效果 - 浅色模式
    glass: '#FFFFFF',
    glassHover: '#F9FAFB',
  },

  // 渐变色
  gradients: {
    primary: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    blue: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
    green: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
    purple: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
    background: 'linear-gradient(135deg, #F9FAFB 0%, #FFFFFF 50%, #F9FAFB 100%)',
    card: 'linear-gradient(135deg, #FFFFFF 0%, #F9FAFB 100%)',
  },

  // 阴影
  shadows: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
    md: '0 2px 8px rgba(0, 0, 0, 0.06)',
    lg: '0 4px 12px rgba(0, 0, 0, 0.08)',
    xl: '0 8px 24px rgba(0, 0, 0, 0.12)',
    glow: '0 0 20px rgba(59, 130, 246, 0.15)',
    glowStrong: '0 0 30px rgba(59, 130, 246, 0.25)',
  },

  // 圆角
  borderRadius: {
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
    full: '9999px',
  },

  // 动画
  transitions: {
    fast: '0.15s ease-in-out',
    normal: '0.3s ease-in-out',
    slow: '0.5s ease-in-out',
  },

  // 毛玻璃效果
  backdropFilter: 'blur(10px)',

  // Z-index层级
  zIndex: {
    base: 1,
    dropdown: 1000,
    sticky: 1100,
    fixed: 1200,
    modal: 1300,
    popover: 1400,
    tooltip: 1500,
  },
};

// CSS变量形式（用于全局注入）
export const modernThemeVars = {
  '--color-primary': modernTheme.colors.primary,
  '--color-primary-dark': modernTheme.colors.primaryDark,
  '--color-secondary': modernTheme.colors.secondary,
  '--color-success': modernTheme.colors.success,
  '--color-danger': modernTheme.colors.danger,
  '--bg-primary': modernTheme.colors.bgPrimary,
  '--bg-secondary': modernTheme.colors.bgSecondary,
  '--text-primary': modernTheme.colors.textPrimary,
  '--text-secondary': modernTheme.colors.textSecondary,
  '--border-color': modernTheme.colors.border,
  '--gradient-background': modernTheme.gradients.background,
  '--backdrop-filter': modernTheme.backdropFilter,
};

export default modernTheme;
