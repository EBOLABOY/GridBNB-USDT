/**
 * 仓位分布饼图组件 - 现代化科技风格
 */

import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { useTheme } from '@/contexts/ThemeContext';
import { modernTheme } from '@/styles/modernTheme';
import type { EChartsOption } from 'echarts';

interface PositionPieChartProps {
  data: Array<{ symbol: string; value: number }>;
  height?: number;
}

const PositionPieChart: React.FC<PositionPieChartProps> = ({ data, height = 350 }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // 响应式高度
  const [chartHeight, setChartHeight] = React.useState(height);

  React.useEffect(() => {
    const updateHeight = () => {
      const width = window.innerWidth;
      if (width < 576) {
        setChartHeight(Math.min(height, 280));
      } else if (width < 768) {
        setChartHeight(Math.min(height, 300));
      } else {
        setChartHeight(height);
      }
    };

    updateHeight();
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, [height]);

  // 科技感配色方案
  const techColors = [
    modernTheme.colors.primary,      // 科技蓝
    modernTheme.colors.secondary,    // 青色
    modernTheme.colors.success,      // 绿色
    modernTheme.colors.accent,       // 紫色
    modernTheme.colors.warning,      // 橙色
    '#6366F1',                        // 靛蓝
    '#EC4899',                        // 粉色
    '#14B8A6',                        // 青绿
  ];

  const option: EChartsOption = useMemo(() => {
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: '{b}: ${c} ({d}%)',
        backgroundColor: modernTheme.colors.bgSecondary,
        borderColor: modernTheme.colors.primary,
        borderWidth: 1,
        textStyle: {
          color: modernTheme.colors.textPrimary,
        },
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
        textStyle: {
          color: modernTheme.colors.textSecondary,
          fontSize: 12,
        },
        itemWidth: 14,
        itemHeight: 14,
      },
      series: [
        {
          name: '持仓价值',
          type: 'pie',
          radius: ['50%', '75%'],
          center: ['60%', '50%'],
          avoidLabelOverlap: false,
          label: {
            show: false,
            position: 'center',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 18,
              fontWeight: 'bold',
              color: modernTheme.colors.textPrimary,
              formatter: '{b}\n${c}',
            },
            itemStyle: {
              shadowBlur: 20,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 212, 255, 0.5)',
            },
          },
          labelLine: {
            show: false,
          },
          data: data.map((item, index) => ({
            value: item.value,
            name: item.symbol,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 1,
                y2: 1,
                colorStops: [
                  { offset: 0, color: techColors[index % techColors.length] },
                  { offset: 1, color: techColors[index % techColors.length] + '99' },
                ],
              },
              borderColor: modernTheme.colors.bgPrimary,
              borderWidth: 2,
              shadowBlur: 10,
              shadowColor: techColors[index % techColors.length] + '66',
            },
          })),
        },
      ],
    };
  }, [data, isDark]);

  return <ReactECharts option={option} style={{ height: `${chartHeight}px` }} />;
};

export default PositionPieChart;
