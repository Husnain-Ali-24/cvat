// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import { useEffect, useRef, useState, useCallback } from 'react';

export interface ClassCountItem {
    class_id: number;
    class_name: string;
    color: string;
    image_count: number;
    annotation_count: number;
    annotated_frames?: number[];
}

export interface AnalyticsData {
    task_id: number;
    task_name?: string;
    total_frames?: number;
    total_annotated_images?: number;
    total_annotations?: number;
    classes: ClassCountItem[];
    class_counts: ClassCountItem[];
    updated_at?: string;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

interface UseAnalyticsWebSocketResult {
    data: AnalyticsData | null;
    status: ConnectionStatus;
    reconnectCount: number;
    lastUpdated: Date | null;
    reconnect: () => void;
}

const BASE_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 10000;
const HEARTBEAT_INTERVAL_MS = 30000;

function normalizeAnalyticsData(raw: any): AnalyticsData | null {
    if (!raw) return null;

    const rawList = raw.classes || raw.class_counts || [];
    const normalizedClasses: ClassCountItem[] = rawList.map((item: any) => ({
        class_id: item.class_id ?? item.id ?? 0,
        class_name: item.class_name ?? item.name ?? 'Unknown',
        color: item.color || '#1890ff',
        image_count: item.image_count || 0,
        annotation_count: item.annotation_count || 0,
        annotated_frames: item.annotated_frames || [],
    }));

    return {
        task_id: raw.task_id,
        task_name: raw.task_name,
        total_frames: raw.total_frames,
        total_annotated_images: raw.total_annotated_images,
        total_annotations: raw.total_annotations,
        classes: normalizedClasses,
        class_counts: normalizedClasses,
        updated_at: raw.updated_at,
    };
}

export function useAnalyticsWebSocket(taskId: number | null): UseAnalyticsWebSocketResult {
    const [data, setData] = useState<AnalyticsData | null>(null);
    const [status, setStatus] = useState<ConnectionStatus>('disconnected');
    const [reconnectCount, setReconnectCount] = useState<number>(0);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
    const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
    const backoffDelayRef = useRef<number>(BASE_RECONNECT_DELAY_MS);
    const isManuallyClosedRef = useRef<boolean>(false);

    const clearTimers = useCallback(() => {
        if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
            reconnectTimerRef.current = null;
        }
        if (heartbeatTimerRef.current) {
            clearInterval(heartbeatTimerRef.current);
            heartbeatTimerRef.current = null;
        }
    }, []);

    const connect = useCallback(() => {
        if (taskId === null || taskId === undefined) {
            setStatus('disconnected');
            return;
        }

        clearTimers();
        isManuallyClosedRef.current = false;

        // Determine correct WebSocket protocol based on current browser URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/api/test/analytics/ws/${taskId}/`;

        setStatus((prev) => (prev === 'disconnected' ? 'connecting' : 'reconnecting'));

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setStatus('connected');
                backoffDelayRef.current = BASE_RECONNECT_DELAY_MS;
                setReconnectCount(0);

                // Start periodic ping/pong heartbeat to keep socket alive
                heartbeatTimerRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ action: 'ping' }));
                    }
                }, HEARTBEAT_INTERVAL_MS);
            };

            ws.onmessage = (event: MessageEvent) => {
                try {
                    const message = JSON.parse(event.data);
                    const { event: eventType, data: eventData } = message;

                    if (eventType === 'initial_data' || eventType === 'class_counts_updated' || eventType === 'subscribed') {
                        if (eventData) {
                            const normalized = normalizeAnalyticsData(eventData);
                            setData(normalized);
                            setLastUpdated(new Date());
                        }
                    }
                } catch {
                    // Ignore unparseable frames (e.g. raw ping/pong)
                }
            };

            ws.onerror = () => {
                // Handled in onclose
            };

            ws.onclose = (event: CloseEvent) => {
                clearTimers();
                wsRef.current = null;

                // Only attempt reconnection if the close was NOT intentional
                if (!isManuallyClosedRef.current && event.code !== 1000) {
                    setStatus('reconnecting');
                    setReconnectCount((count) => count + 1);

                    const nextDelay = Math.min(
                        backoffDelayRef.current * 2,
                        MAX_RECONNECT_DELAY_MS,
                    );
                    const delay = backoffDelayRef.current;
                    backoffDelayRef.current = nextDelay;

                    reconnectTimerRef.current = setTimeout(() => {
                        connect();
                    }, delay);
                } else {
                    setStatus('disconnected');
                }
            };
        } catch {
            setStatus('disconnected');
        }
    }, [taskId, clearTimers]);

    const reconnect = useCallback(() => {
        if (wsRef.current) {
            isManuallyClosedRef.current = true;
            wsRef.current.close();
        }
        backoffDelayRef.current = BASE_RECONNECT_DELAY_MS;
        setReconnectCount(0);
        connect();
    }, [connect]);

    useEffect(() => {
        connect();

        return () => {
            isManuallyClosedRef.current = true;
            clearTimers();
            if (wsRef.current) {
                wsRef.current.close(1000, 'Component unmounted');
                wsRef.current = null;
            }
        };
    }, [connect, clearTimers]);

    return {
        data,
        status,
        reconnectCount,
        lastUpdated,
        reconnect,
    };
}
