/**
 * 交易量分布图表组件 - 现代化科技风格
 */

import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { useTheme } from '@/contexts/ThemeContext';
import { modernTheme } from '@/styles/modernTheme';
import type { EChartsOption } from 'echarts';

interface TradeVolumeChartProps {
  data: Array<{ symbol: string; buyCount: number; sellCount: number }>;
  height?: number;
}

const TradeVolumeChart: React.FC<TradeVolumeChartProps> = ({ data, height = 300 }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // 响应式高度
  const [chartHeight, setChartHeight] = React.useState(height);

  React.useEffect(() => {
    const updateHeight = () => {
      const width = window.innerWidth;
      if (width < 576) {
        setChartHeight(Math.min(height, 250));
      } else if (width < 768) {
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
    const symbols = data.map(item => item.symbol);
    const buyVolumes = data.map(item => item.buyCount);
    const sellVolumes = data.map(item => item.sellCount);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
          shadowStyle: {
            color: 'rgba(0, 212, 255, 0.1)',
          },
        },
        backgroundColor: modernTheme.colors.bgSecondary,
        borderColor: modernTheme.colors.primary,
        borderWidth: 1,
        textStyle: {
          color: modernTheme.colors.textPrimary,
        },
      },
      legend: {
        data: ['买入', '卖出'],
        top: 10,
        textStyle: {
          color: modernTheme.colors.textSecondary,
          fontSize: 12,
        },
        itemWidth: 20,
        itemHeight: 12,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 50,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: symbols,
        axisLabel: {
          color: modernTheme.colors.textSecondary,
          interval: 0,
          rotate: symbols.length > 4 ? 30 : 0,
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
          name: '买入',
          type: 'bar',
          data: buyVolumes,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: modernTheme.colors.success },
                { offset: 1, color: modernTheme.colors.secondary },
              ],
            },
            borderRadius: [4, 4, 0, 0],
            shadowColor: modernTheme.colors.success,
            shadowBlur: 8,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 15,
              shadowColor: modernTheme.colors.success,
            },
          },
        },
        {
          name: '卖出',
          type: 'bar',
          data: sellVolumes,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: modernTheme.colors.danger },
                { offset: 1, color: '#FF6B6B' },
              ],
            },
            borderRadius: [4, 4, 0, 0],
            shadowColor: modernTheme.colors.danger,
            shadowBlur: 8,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 15,
              shadowColor: modernTheme.colors.danger,
            },
          },
        },
      ],
    };
  }, [data, isDark]);

  return <ReactECharts option={option} style={{ height: `${chartHeight}px` }} />;
};

export default TradeVolumeChart;
