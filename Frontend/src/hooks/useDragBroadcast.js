import { useCallback, useRef } from 'react';

const DRAG_MOVE_INTERVAL_MS = 1000 / 120; // 120 Hz
const BUFFER_THRESHOLD_BYTES = 64 * 1024;

/**
 * Wraps useTaskSocket.send with throttling + backpressure logic for
 * `task.drag_move` events. drag_start and drag_end pass through unchanged.
 *
 * @param {{
 *   send: (event: string, data?: any) => boolean,
 *   wsRef: React.MutableRefObject<WebSocket | null>
 * }} socket  - result from useTaskSocket()
 * @returns {{
 *   sendDragStart: (data) => void,
 *   sendDragMove: (data) => void,
 *   sendDragEnd: (data) => void,
 * }}
 */
const useDragBroadcast = (socket) => {
  const lastMoveAtRef = useRef(0);

  const sendDragStart = useCallback(
    (data) => {
      lastMoveAtRef.current = 0;
      if (socket?.send) socket.send('task.drag_start', data);
    },
    [socket],
  );

  const sendDragMove = useCallback(
    (data) => {
      const now =
        typeof performance !== 'undefined' && performance.now
          ? performance.now()
          : Date.now();
      if (now - lastMoveAtRef.current < DRAG_MOVE_INTERVAL_MS) {
        return;
      }
      // Backpressure: drop frames if the socket buffer is backing up.
      const ws = socket?.wsRef?.current;
      if (ws && ws.bufferedAmount > BUFFER_THRESHOLD_BYTES) {
        return;
      }
      lastMoveAtRef.current = now;
      if (socket?.send) socket.send('task.drag_move', data);
    },
    [socket],
  );

  const sendDragEnd = useCallback(
    (data) => {
      lastMoveAtRef.current = 0;
      if (socket?.send) socket.send('task.drag_end', data);
    },
    [socket],
  );

  return { sendDragStart, sendDragMove, sendDragEnd };
};

export default useDragBroadcast;
