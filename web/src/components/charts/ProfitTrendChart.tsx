/**
 * 盈亏趋势图表组件 - 现代化科技风格
 */

import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { useTheme } from '@/contexts/ThemeContext';
import { modernTheme } from '@/styles/modernTheme';
import type { EChartsOption } from 'echarts';

interface ProfitTrendChartProps {
  data: Array<{ time: string; profit: number }>;
  height?: number;
}

const ProfitTrendChart: React.FC<ProfitTrendChartProps> = ({ data, height = 300 }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // 响应式高度：在小屏幕上降低高度
  const [chartHeight, setChartHeight] = React.useState(height);

  React.useEffect(() => {
    const updateHeight = () => {
      const width = window.innerWidth;
      if (width < 576) {
        // 手机
        setChartHeight(Math.min(height, 250));
      } else if (width < 768) {
        // 平板竖屏
        setChartHeight(Math.min(height, 280));
      } else {
        setChartHeight(height);
      }
    };

    updateHeight();
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, [height]);

  const option: EChartsOption = useMemo(() => {
    const times = data.map(item => item.time);
    const profits = data.map(item => item.profit);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          lineStyle: {
            color: modernTheme.colors.primary,
            type: 'dashed',
          },
        },
        backgroundColor: modernTheme.colors.bgSecondary,
        borderColor: modernTheme.colors.primary,
        borderWidth: 1,
        textStyle: {
          color: modernTheme.colors.textPrimary,
        },
        formatter: (params: any) => {
          const param = params[0];
          const profit = param.value;
          const color = profit >= 0 ? modernTheme.colors.success : modernTheme.colors.danger;
          return `
            <div style="padding: 8px;">
              <div style="margin-bottom: 4px; font-weight: bold; color: ${modernTheme.colors.primary};">${param.axisValue}</div>
              <div style="color: ${color};">
                盈亏: <span style="font-weight: bold;">${profit >= 0 ? '+' : ''}${profit.toFixed(2)} USDT</span>
              </div>
            </div>
          `;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: times,
        axisLabel: {
          color: modernTheme.colors.textSecondary,
          fontSize: 11,
        },
        axisLine: {
          lineStyle: {
            color: modernTheme.colors.border,
          },
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: modernTheme.colors.textSecondary,
          formatter: '{value} USDT',
          fontSize: 11,
        },
        axisLine: {
          show: false,
        },
        splitLine: {
          lineStyle: {
            color: modernTheme.colors.borderLight,
            type: 'dashed',
          },
        },
      },
      series: [
        {
          name: '累计盈亏',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          data: profits,
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(0, 255, 136, 0.3)' }, // modernTheme.colors.success
                { offset: 1, color: 'rgba(0, 255, 136, 0.05)' },
              ],
            },
          },
          lineStyle: {
            width: 3,
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: modernTheme.colors.success },
                { offset: 0.5, color: modernTheme.colors.secondary },
                { offset: 1, color: modernTheme.colors.primary },
              ],
            },
            shadowColor: modernTheme.colors.primary,
            shadowBlur: 10,
          },
          itemStyle: {
            color: modernTheme.colors.success,
            borderColor: modernTheme.colors.primary,
            borderWidth: 2,
            shadowColor: modernTheme.colors.primary,
            shadowBlur: 5,
          },
        },
      ],
    };
  }, [data, isDark]);

  return <ReactECharts option={option} style={{ height: `${chartHeight}px` }} />;
};

export default ProfitTrendChart;
