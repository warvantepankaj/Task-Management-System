import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Maintains a WebSocket connection to /ws/tasks and dispatches incoming
 * lifecycle / drag events to the provided callbacks.
 *
 * @param {{
 *   onCreated?: (task) => void,
 *   onUpdated?: (task) => void,
 *   onStatusChanged?: (task) => void,
 *   onDeleted?: (payload) => void,
 *   onDragStart?: (payload) => void,
 *   onDragMove?: (payload) => void,
 *   onDragEnd?: (payload) => void,
 *   onDragRejected?: (payload) => void,
 * }} callbacks
 * @returns {{ status: 'connecting' | 'open' | 'closed', send: (event: string, data?: any) => void, wsRef: React.MutableRefObject<WebSocket | null> }}
 */
const useTaskSocket = (callbacks = {}) => {
  const [status, setStatus] = useState('connecting');
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const stoppedRef = useRef(false);
  // Keep callbacks fresh without forcing reconnects on every render.
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  const computeWsUrl = useCallback(() => {
    const token = localStorage.getItem('token') || '';
    // Default to ws://localhost:8000 since the FastAPI dev server runs there.
    // For prod, VITE_WS_URL can override.
    const explicit = import.meta.env?.VITE_WS_URL;
    if (explicit) {
      return `${explicit}/ws/tasks?token=${encodeURIComponent(token)}`;
    }
    return `ws://localhost:8000/ws/tasks?token=${encodeURIComponent(token)}`;
  }, []);

  const scheduleReconnect = useCallback((connectFn) => {
    if (stoppedRef.current) return;
    const attempt = reconnectAttemptsRef.current;
    // 1s, 2s, 4s, 8s, 16s, cap 30s.
    const delays = [1000, 2000, 4000, 8000, 16000];
    const delay = delays[Math.min(attempt, delays.length - 1)] || 30000;
    const capped = Math.min(delay, 30000);
    reconnectAttemptsRef.current = attempt + 1;
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    reconnectTimerRef.current = setTimeout(() => {
      connectFn();
    }, capped);
  }, []);

  const connect = useCallback(() => {
    if (stoppedRef.current) return;
    setStatus('connecting');
    let ws;
    try {
      ws = new WebSocket(computeWsUrl());
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('useTaskSocket: failed to open WS', err);
      scheduleReconnect(connect);
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      setStatus('open');
    };

    ws.onmessage = (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      const cbs = callbacksRef.current || {};
      const evt = msg?.event;
      if (!evt) {
        // Could be a pong or unknown type; just ignore.
        return;
      }
      switch (evt) {
        case 'task.created':
          cbs.onCreated && cbs.onCreated(msg.task, msg);
          break;
        case 'task.updated':
          cbs.onUpdated && cbs.onUpdated(msg.task, msg);
          break;
        case 'task.status_changed':
          cbs.onStatusChanged && cbs.onStatusChanged(msg.task, msg);
          break;
        case 'task.deleted':
          cbs.onDeleted && cbs.onDeleted(msg.task, msg);
          break;
        case 'task.drag_start':
          cbs.onDragStart && cbs.onDragStart(msg.data, msg);
          break;
        case 'task.drag_move':
          cbs.onDragMove && cbs.onDragMove(msg.data, msg);
          break;
        case 'task.drag_end':
          cbs.onDragEnd && cbs.onDragEnd(msg.data, msg);
          break;
        case 'task.drag_rejected':
          cbs.onDragRejected && cbs.onDragRejected(msg.data, msg);
          break;
        default:
          break;
      }
    };

    ws.onerror = () => {
      // The actual recovery happens in onclose.
    };

    ws.onclose = (event) => {
      setStatus('closed');
      wsRef.current = null;
      if (stoppedRef.current) return;
      if (event.code === 4401) {
        // Token invalid/expired. A refresh-token implementation can call
        // /auth/refresh here once it lands. For now: just reconnect with
        // whatever token is in storage (the axios interceptor will already
        // have evicted the user on 401 if needed).
        // eslint-disable-next-line no-console
        console.warn('useTaskSocket: closed 4401 — token rejected, reconnecting');
      }
      scheduleReconnect(connect);
    };
  }, [computeWsUrl, scheduleReconnect]);

  useEffect(() => {
    stoppedRef.current = false;
    connect();
    return () => {
      stoppedRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.close(1000, 'component unmounted');
        } catch {
          /* ignore */
        }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = useCallback((event, data) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      // eslint-disable-next-line no-console
      console.warn('useTaskSocket.send: socket not open, dropping', event);
      return false;
    }
    try {
      ws.send(JSON.stringify({ event, data }));
      return true;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('useTaskSocket.send: failed', err);
      return false;
    }
  }, []);

  return { status, send, wsRef };
};

export default useTaskSocket;
