/**
 * SSE (Server-Sent Events) Hook
 * 管理EventSource连接、自动重连、状态管理
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export type SSEStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface SSEOptions {
  url: string;
  enabled?: boolean;
  onMessage?: (event: MessageEvent) => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number; // 重连间隔（毫秒）
  maxReconnectAttempts?: number; // 最大重连次数，0表示无限重连
}

export interface SSEState {
  status: SSEStatus;
  error: string | null;
  reconnectCount: number;
}

/**
 * useSSE Hook
 *
 * @example
 * ```tsx
 * const { status, error, reconnectCount } = useSSE({
 *   url: '/api/sse/events',
 *   enabled: true,
 *   onMessage: (event) => {
 *     const data = JSON.parse(event.data);
 *     console.log('Received:', data);
 *   },
 * });
 * ```
 */
export const useSSE = (options: SSEOptions): SSEState => {
  const {
    url,
    enabled = true,
    onMessage,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 0,
  } = options;

  const [status, setStatus] = useState<SSEStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  // 清理连接
  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // 重连逻辑
  const reconnect = useCallback(() => {
    if (!shouldReconnectRef.current) {
      return;
    }

    // 检查最大重连次数
    if (maxReconnectAttempts > 0 && reconnectCount >= maxReconnectAttempts) {
      setStatus('error');
      setError(`达到最大重连次数 (${maxReconnectAttempts})`);
      return;
    }

    setStatus('connecting');
    setReconnectCount((prev) => prev + 1);

    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, reconnectInterval);
  }, [reconnectCount, maxReconnectAttempts, reconnectInterval]);

  // 建立连接
  const connect = useCallback(() => {
    cleanup();

    if (!enabled || !url) {
      setStatus('disconnected');
      return;
    }

    try {
      setStatus('connecting');
      setError(null);

      // 获取token
      const token = localStorage.getItem('token');
      if (!token) {
        setStatus('error');
        setError('未找到认证令牌，请先登录');
        return;
      }

      // 创建EventSource
      // 注意：EventSource不支持自定义headers，需要通过URL参数传递token
      const eventSourceUrl = `${url}?token=${encodeURIComponent(token)}`;
      const eventSource = new EventSource(eventSourceUrl);

      eventSourceRef.current = eventSource;

      // 连接成功
      eventSource.addEventListener('connected', (event) => {
        setStatus('connected');
        setReconnectCount(0);
        console.log('SSE connected:', event);
      });

      // 接收消息
      eventSource.onmessage = (event) => {
        if (onMessage) {
          onMessage(event);
        }
      };

      // 连接打开
      eventSource.onopen = () => {
        setStatus('connected');
        setReconnectCount(0);
      };

      // 连接错误
      eventSource.onerror = (event) => {
        console.error('SSE error:', event);
        setStatus('error');
        setError('SSE连接错误');

        if (onError) {
          onError(event);
        }

        // 自动重连
        cleanup();
        reconnect();
      };
    } catch (err: any) {
      console.error('SSE connection error:', err);
      setStatus('error');
      setError(err.message || 'SSE连接失败');
      reconnect();
    }
  }, [url, enabled, onMessage, onError, cleanup, reconnect]);

  // 初始连接和清理
  useEffect(() => {
    shouldReconnectRef.current = true;

    if (enabled) {
      connect();
    }

    return () => {
      shouldReconnectRef.current = false;
      cleanup();
    };
  }, [enabled, url]);

  return {
    status,
    error,
    reconnectCount,
  };
};

export default useSSE;
