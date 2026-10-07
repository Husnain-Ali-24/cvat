// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import React, { useState, useEffect } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import Empty from 'antd/lib/empty';

import { ClassCountItem } from './use-analytics-websocket';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
);

const PALETTE = [
    '#1890ff',
    '#52c41a',
    '#faad14',
    '#f5222d',
    '#722ed1',
    '#13c2c2',
    '#eb2f96',
    '#fa8c16',
    '#a0d911',
    '#2f54eb',
];

interface ChartProps {
    classCounts: ClassCountItem[];
}

/**
 * Responsive window width hook to adapt chart options across screen sizes.
 */
function useWindowWidth(): number {
    const [width, setWidth] = useState<number>(
        typeof window !== 'undefined' ? window.innerWidth : 1200,
    );

    useEffect(() => {
        let timeoutId: any;
        const handleResize = () => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                setWidth(window.innerWidth);
            }, 100);
        };
        window.addEventListener('resize', handleResize);
        return () => {
            window.removeEventListener('resize', handleResize);
            clearTimeout(timeoutId);
        };
    }, []);

    return width;
}

export const ClassCountsBarChart: React.FC<ChartProps> = ({ classCounts }) => {
    const width = useWindowWidth();
    const isMobile = width < 576;
    const isTablet = width >= 576 && width < 992;

    if (!classCounts || classCounts.length === 0) {
        return <Empty description='No annotation data available for this task' image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    }

    const labels = classCounts.map((item) => item.class_name);
    const imageCounts = classCounts.map((item) => item.image_count);
    const annotationCounts = classCounts.map((item) => item.annotation_count);

    const chartData = {
        labels,
        datasets: [
            {
                label: isMobile ? 'Images' : 'Unique Images Containing Class',
                data: imageCounts,
                backgroundColor: 'rgba(24, 144, 255, 0.75)',
                borderColor: '#1890ff',
                borderWidth: 1.5,
                borderRadius: 4,
            },
            {
                label: isMobile ? 'Annotations' : 'Total Annotations Count',
                data: annotationCounts,
                backgroundColor: 'rgba(114, 46, 209, 0.75)',
                borderColor: '#722ed1',
                borderWidth: 1.5,
                borderRadius: 4,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index' as const,
            intersect: false,
        },
        plugins: {
            legend: {
                position: 'top' as const,
                align: (isMobile ? 'start' : 'center') as any,
                labels: {
                    boxWidth: isMobile ? 10 : 14,
                    padding: isMobile ? 8 : 14,
                    font: {
                        size: isMobile ? 10 : 12,
                        weight: 'bold' as const,
                    },
                },
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.85)',
                padding: isMobile ? 8 : 12,
                cornerRadius: 6,
                callbacks: {
                    label: (context: any) => {
                        const label = context.dataset.label || '';
                        const value = context.parsed.y || 0;
                        return ` ${label}: ${value}`;
                    },
                },
            },
        },
        scales: {
            x: {
                grid: {
                    display: false,
                },
                ticks: {
                    font: {
                        size: isMobile ? 9 : isTablet ? 10 : 11,
                    },
                    maxRotation: isMobile ? 45 : 30,
                    minRotation: 0,
                    autoSkip: true,
                    maxTicksLimit: isMobile ? 6 : 12,
                },
            },
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0,
                    font: {
                        size: isMobile ? 9 : 11,
                    },
                },
                grid: {
                    color: 'rgba(0, 0, 0, 0.06)',
                },
            },
        },
    };

    return (
        <div className='chart-container'>
            <Bar data={chartData} options={options} />
        </div>
    );
};

export const ClassDistributionPieChart: React.FC<ChartProps> = ({ classCounts }) => {
    const width = useWindowWidth();
    const isMobile = width < 768; // Under 768px, position legend below chart for full visibility

    if (!classCounts || classCounts.length === 0) {
        return <Empty description='No annotations to display' image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    }

    const labels = classCounts.map((item) => item.class_name);
    const dataValues = classCounts.map((item) => item.annotation_count);
    const backgroundColors = classCounts.map((item, index) => item.color || PALETTE[index % PALETTE.length]);

    const chartData = {
        labels,
        datasets: [
            {
                data: dataValues,
                backgroundColor: backgroundColors,
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverOffset: 6,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: (isMobile ? 'bottom' : 'right') as any,
                labels: {
                    boxWidth: isMobile ? 10 : 12,
                    padding: isMobile ? 6 : 12,
                    font: {
                        size: isMobile ? 10 : 11,
                    },
                },
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.85)',
                padding: 10,
                cornerRadius: 6,
                callbacks: {
                    label: (context: any) => {
                        const total = dataValues.reduce((acc, val) => acc + val, 0);
                        const value = context.parsed || 0;
                        const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0';
                        return ` ${context.label}: ${value} (${percentage}%)`;
                    },
                },
            },
        },
        cutout: isMobile ? '55%' : '62%',
    };

    return (
        <div className='chart-container'>
            <Doughnut data={chartData} options={options} />
        </div>
    );
};
