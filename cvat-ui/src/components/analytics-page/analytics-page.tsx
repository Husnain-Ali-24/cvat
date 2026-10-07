// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import './styles.scss';
import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useLocation, useHistory } from 'react-router';
import { Row, Col } from 'antd/lib/grid';
import Card from 'antd/lib/card';
import Select from 'antd/lib/select';
import Statistic from 'antd/lib/statistic';
import Button from 'antd/lib/button';
import Tooltip from 'antd/lib/tooltip';
import Spin from 'antd/lib/spin';
import Badge from 'antd/lib/badge';
import Empty from 'antd/lib/empty';
import Alert from 'antd/lib/alert';
import {
    BarChartOutlined,
    ReloadOutlined,
    AppstoreOutlined,
    PictureOutlined,
    TagsOutlined,
    NumberOutlined,
} from '@ant-design/icons';
import { getCore, Task } from 'cvat-core-wrapper';

import { useAnalyticsWebSocket } from './use-analytics-websocket';
import { ClassCountsBarChart, ClassDistributionPieChart } from './analytics-chart';

const core = getCore();

interface TaskOption {
    id: number;
    name: string;
    size: number;
}

export function AnalyticsPageComponent(): JSX.Element {
    const location = useLocation();
    const history = useHistory();

    // Parse task_id from query params: /test-analytics?task_id=1
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const initialTaskId = queryParams.get('task_id') ? parseInt(queryParams.get('task_id')!, 10) : null;

    const [selectedTaskId, setSelectedTaskId] = useState<number | null>(initialTaskId);
    const [taskList, setTaskList] = useState<TaskOption[]>([]);
    const [tasksLoading, setTasksLoading] = useState<boolean>(true);

    // Fetch tasks list using authenticated cvat-core with fallback
    const loadTasks = useCallback(() => {
        setTasksLoading(true);

        core.tasks.get({ page_size: 50 })
            .then((tasks: Task[]) => {
                if (tasks && tasks.length > 0) {
                    const results: TaskOption[] = tasks.map((t: Task) => ({
                        id: t.id,
                        name: t.name,
                        size: t.size || 0,
                    }));
                    setTaskList(results);

                    setSelectedTaskId((current) => {
                        if (current && results.some((r) => r.id === current)) return current;
                        return results[0].id;
                    });
                }
            })
            .catch(() => {
                fetch('/api/tasks?page_size=50', { credentials: 'include' })
                    .then((res) => (res.ok ? res.json() : Promise.reject(res)))
                    .then((data) => {
                        if (data.results && data.results.length > 0) {
                            const results: TaskOption[] = data.results.map((t: any) => ({
                                id: t.id,
                                name: t.name,
                                size: t.size || 0,
                            }));
                            setTaskList(results);

                            setSelectedTaskId((current) => {
                                if (current && results.some((r) => r.id === current)) return current;
                                return results[0].id;
                            });
                        }
                    })
                    .catch(() => {
                        setSelectedTaskId((current) => current || 1);
                    });
            })
            .finally(() => {
                setTasksLoading(false);
            });
    }, []);

    useEffect(() => {
        loadTasks();
    }, [loadTasks]);

    // Handle task change in dropdown
    const handleTaskChange = (newTaskId: number) => {
        setSelectedTaskId(newTaskId);
        history.replace(`/test-analytics?task_id=${newTaskId}`);
    };

    // Connect WebSocket hook for live streaming analytics
    const { data, status, reconnectCount, lastUpdated, reconnect } = useAnalyticsWebSocket(selectedTaskId);

    const handleManualRefresh = () => {
        loadTasks();
        reconnect();
    };

    // Calculate summary statistics
    const totalClasses = data?.class_counts?.length ?? 0;
    const totalImagesAnnotated = useMemo(() => {
        if (!data?.class_counts || data.class_counts.length === 0) return 0;
        return Math.max(...data.class_counts.map((c) => c.image_count));
    }, [data]);
    const totalAnnotations = useMemo(() => {
        if (!data?.class_counts) return 0;
        return data.class_counts.reduce((acc, curr) => acc + curr.annotation_count, 0);
    }, [data]);

    // Connection status indicator
    const renderConnectionStatus = (): JSX.Element => {
        if (status === 'connected') {
            return <Badge status='success' text='Live' />;
        }
        if (status === 'reconnecting' || status === 'connecting') {
            return (
                <Badge
                    status='processing'
                    text={status === 'reconnecting' ? `Reconnecting (${reconnectCount})` : 'Connecting'}
                />
            );
        }
        return <Badge status='error' text='Disconnected' />;
    };

    return (
        <div className='cvat-analytics-page'>
            {/* Top Bar - responsive CVAT header */}
            <div className='cvat-analytics-top-bar'>
                <Row justify='center'>
                    <Col xs={24} sm={24} md={22} lg={20} xl={18} xxl={16}>
                        <div className='cvat-analytics-top-bar-inner'>
                            <div className='cvat-analytics-title-group'>
                                <h4 className='cvat-title'>Real-Time Analytics</h4>
                                <div className='cvat-analytics-mobile-badge'>
                                    {renderConnectionStatus()}
                                </div>
                            </div>
                            <div className='cvat-analytics-controls'>
                                <Select
                                    className='cvat-analytics-task-select'
                                    loading={tasksLoading}
                                    value={selectedTaskId || undefined}
                                    onChange={handleTaskChange}
                                    onDropdownVisibleChange={(open) => {
                                        if (open) loadTasks();
                                    }}
                                    placeholder='Select a task'
                                    showSearch
                                    optionFilterProp='children'
                                >
                                    {taskList.map((task) => (
                                        <Select.Option key={task.id} value={task.id}>
                                            #{task.id} — {task.name}
                                        </Select.Option>
                                    ))}
                                </Select>

                                <div className='cvat-analytics-status-group'>
                                    <div className='cvat-analytics-desktop-badge'>
                                        {renderConnectionStatus()}
                                    </div>
                                    {lastUpdated && (
                                        <span className='cvat-analytics-last-updated'>
                                            {lastUpdated.toLocaleTimeString()}
                                        </span>
                                    )}
                                    <Tooltip title='Refresh task list & reconnect'>
                                        <Button
                                            size='small'
                                            icon={<ReloadOutlined />}
                                            onClick={handleManualRefresh}
                                            className='cvat-analytics-reconnect-btn'
                                        />
                                    </Tooltip>
                                </div>
                            </div>
                        </div>
                    </Col>
                </Row>
            </div>

            {/* Content area */}
            <div className='cvat-analytics-content'>
                <Row justify='center'>
                    <Col xs={24} sm={24} md={22} lg={20} xl={18} xxl={16}>
                        {/* Error Alert - Requirement 4 (failed request handling) */}
                        {status === 'disconnected' && reconnectCount > 3 && (
                            <Alert
                                type='error'
                                message='Failed to Load Analytics Stream'
                                description='Unable to establish WebSocket connection with the analytics server. Please verify your network connection and task permissions.'
                                showIcon
                                style={{ marginBottom: 16 }}
                            />
                        )}

                        {/* Summary Statistics */}
                        <Row gutter={[12, 12]} className='cvat-analytics-stats-row'>
                            <Col xs={24} sm={8} md={8}>
                                <Card className='cvat-analytics-stat-card' bordered>
                                    <Statistic
                                        title='Unique Classes'
                                        value={totalClasses}
                                        prefix={<AppstoreOutlined />}
                                    />
                                </Card>
                            </Col>
                            <Col xs={24} sm={8} md={8}>
                                <Card className='cvat-analytics-stat-card' bordered>
                                    <Statistic
                                        title='Images Annotated'
                                        value={totalImagesAnnotated}
                                        prefix={<PictureOutlined />}
                                    />
                                </Card>
                            </Col>
                            <Col xs={24} sm={8} md={8}>
                                <Card className='cvat-analytics-stat-card' bordered>
                                    <Statistic
                                        title='Total Annotations'
                                        value={totalAnnotations}
                                        prefix={<TagsOutlined />}
                                    />
                                </Card>
                            </Col>
                        </Row>

                        {/* Charts Section with Empty State (Requirement 4: no data handling) */}
                        {!data && (status === 'connecting' || status === 'reconnecting') ? (
                            <div className='cvat-analytics-loading'>
                                <Spin size='large' className='cvat-spinner' />
                            </div>
                        ) : data && totalAnnotations === 0 ? (
                            <Card className='cvat-analytics-empty-card' bordered style={{ textAlign: 'center', padding: '40px 0', marginTop: 16 }}>
                                <Empty
                                    description='No annotations found for this task. Draw and save annotations in the CVAT workspace to view live analytics.'
                                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                                />
                            </Card>
                        ) : (
                            <Row gutter={[16, 16]}>
                                <Col xs={24} lg={14} xl={14}>
                                    <Card
                                        className='cvat-analytics-chart-card'
                                        title='Class-wise Counts'
                                        bordered
                                        extra={<BarChartOutlined style={{ color: '#1890ff' }} />}
                                    >
                                        <ClassCountsBarChart classCounts={data?.class_counts || []} />
                                    </Card>
                                </Col>

                                <Col xs={24} lg={10} xl={10}>
                                    <Card
                                        className='cvat-analytics-chart-card'
                                        title='Class Distribution'
                                        bordered
                                        extra={<NumberOutlined style={{ color: '#722ed1' }} />}
                                    >
                                        <ClassDistributionPieChart classCounts={data?.class_counts || []} />
                                    </Card>
                                </Col>
                            </Row>
                        )}
                    </Col>
                </Row>
            </div>
        </div>
    );
}

export default React.memo(AnalyticsPageComponent);
