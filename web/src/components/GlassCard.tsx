/**
 * 玻璃态卡片组件 - 现代化UI
 */

import React, { CSSProperties, ReactNode } from 'react';
import { modernTheme } from '@/styles/modernTheme';

interface GlassCardProps {
  children: ReactNode;
  hover?: boolean;
  glow?: boolean;
  gradient?: boolean;
  style?: CSSProperties;
  className?: string;
  onClick?: () => void;
}

const GlassCard: React.FC<GlassCardProps> = ({
  children,
  hover = true,
  glow = false,
  gradient = false,
  style,
  className,
  onClick,
}) => {
  const baseStyle: CSSProperties = {
    background: gradient
      ? modernTheme.gradients.card
      : modernTheme.colors.glass,
    backdropFilter: modernTheme.backdropFilter,
    WebkitBackdropFilter: modernTheme.backdropFilter,
    border: `1px solid ${modernTheme.colors.border}`,
    borderRadius: modernTheme.borderRadius.lg,
    padding: '24px',
    boxShadow: glow ? modernTheme.shadows.glow : modernTheme.shadows.md,
    transition: `all ${modernTheme.transitions.normal}`,
    position: 'relative',
    overflow: 'hidden',
    ...style,
  };

  const hoverStyle: CSSProperties = hover
    ? {
        cursor: onClick ? 'pointer' : 'default',
      }
    : {};

  const handleMouseEnter = (e: React.MouseEvent<HTMLDivElement>) => {
    if (hover) {
      e.currentTarget.style.background = gradient
        ? modernTheme.gradients.card
        : modernTheme.colors.glassHover;
      e.currentTarget.style.transform = 'translateY(-2px)';
      e.currentTarget.style.boxShadow = glow
        ? modernTheme.shadows.glowStrong
        : modernTheme.shadows.lg;
    }
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    if (hover) {
      e.currentTarget.style.background = gradient
        ? modernTheme.gradients.card
        : modernTheme.colors.glass;
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = glow
        ? modernTheme.shadows.glow
        : modernTheme.shadows.md;
    }
  };

  return (
    <div
      style={{ ...baseStyle, ...hoverStyle }}
      className={className}
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* 发光效果（可选） */}
      {glow && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: modernTheme.gradients.blue,
            opacity: 0.6,
          }}
        />
      )}
      {children}
    </div>
  );
};

export default GlassCard;
