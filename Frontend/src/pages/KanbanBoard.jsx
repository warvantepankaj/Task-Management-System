import { useEffect, useMemo, useRef, useState } from 'react';
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { motionValue } from 'framer-motion';
import toast from 'react-hot-toast';
import { taskAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import useTaskSocket from '../hooks/useTaskSocket';
import useDragBroadcast from '../hooks/useDragBroadcast';
import KanbanColumn from '../components/kanban/KanbanColumn';
import DragGhost from '../components/kanban/DragGhost';
import { KANBAN_COLUMN_ORDER, KANBAN_COLUMN_LABEL, TASK_STATUS } from '../utils/constants';

/**
 * KanbanBoard renders three columns inside a single DndContext. It owns
 * - `tasks`: the displayed list (filtered by the parent via the `filter`
 *   callback)
 * - `remoteDrags`: a record keyed by task_id of drags happening on other
 *   clients, fed by `useTaskSocket`.
 */
const KanbanBoard = ({ tasks: initialTasks = [], loading = false, filter = (t) => t }) => {
  const { user } = useAuth();
  const [tasks, setTasks] = useState(initialTasks);
  // `remoteDrags` holds metadata (task, user) only — position is held in
  // motion values out-of-band so that 60+ Hz cursor updates do NOT trigger
  // a React render. The DragGhost subscribes to these motion values directly
  // and writes them to the DOM with no virtual-DOM diff in the hot path.
  const [remoteDrags, setRemoteDrags] = useState({});
  const positionsRef = useRef(new Map()); // task_id -> { x: MotionValue, y: MotionValue }

  useEffect(() => {
    setTasks(initialTasks);
  }, [initialTasks]);

  // Track the cursor at high frequency for outbound drag_move events. We avoid
  // re-rendering on every mouse move by storing the value in a ref.
  const cursorRef = useRef({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e) => {
      cursorRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener('pointermove', onMove);
    return () => window.removeEventListener('pointermove', onMove);
  }, []);

  const ensurePosition = (taskId, initialX = 0, initialY = 0) => {
    let pos = positionsRef.current.get(taskId);
    if (!pos) {
      pos = { x: motionValue(initialX), y: motionValue(initialY) };
      positionsRef.current.set(taskId, pos);
    }
    return pos;
  };

  // ---- WebSocket wiring -------------------------------------------------
  const socket = useTaskSocket({
    onCreated: (task, env) => {
      if (!task || !task.id) return;
      // Skip if we caused this and have it locally already (optimistic UI).
      setTasks((prev) =>
        prev.some((t) => t.id === task.id) ? prev : [task, ...prev],
      );
    },
    onUpdated: (task) => {
      if (!task || !task.id) return;
      setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, ...task } : t)));
    },
    onStatusChanged: (task, env) => {
      if (!task || !task.id) return;
      // If this echoes our own optimistic change, skip.
      if (env?.actor_id && user?.id && env.actor_id === user.id) {
        setTasks((prev) =>
          prev.map((t) => (t.id === task.id ? { ...t, ...task } : t)),
        );
        return;
      }
      setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, ...task } : t)));
    },
    onDeleted: (payload) => {
      if (!payload || !payload.id) return;
      setTasks((prev) => prev.filter((t) => t.id !== payload.id));
    },
    onDragStart: (data, env) => {
      if (!data?.task_id) return;
      const initX = data.x ?? 0;
      const initY = data.y ?? 0;
      const pos = ensurePosition(data.task_id, initX, initY);
      pos.x.set(initX);
      pos.y.set(initY);
      setRemoteDrags((prev) => ({
        ...prev,
        [data.task_id]: {
          task_id: data.task_id,
          user: { id: env?.actor_id, username: `User ${env?.actor_id}` },
          position: pos,
          over_status: data.from_status || null,
          task: tasks.find((t) => t.id === data.task_id) || null,
        },
      }));
    },
    onDragMove: (data) => {
      // Hot path: write directly to motion values. No setState, no re-render.
      if (!data?.task_id) return;
      const pos = positionsRef.current.get(data.task_id);
      if (!pos) return;
      if (typeof data.x === 'number') pos.x.set(data.x);
      if (typeof data.y === 'number') pos.y.set(data.y);
    },
    onDragEnd: (data) => {
      if (!data?.task_id) return;
      positionsRef.current.delete(data.task_id);
      setRemoteDrags((prev) => {
        if (!(data.task_id in prev)) return prev;
        const next = { ...prev };
        delete next[data.task_id];
        return next;
      });
    },
    onDragRejected: (data) => {
      toast.error('Another user is already moving this card.');
      // Revert any optimistic local state for this task (we still have the
      // original because we never mutated until the API call resolved).
      void data;
    },
  });

  const drag = useDragBroadcast(socket);

  // ---- DnD-kit sensors --------------------------------------------------
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  // Local drag tracking — what column the user dragged from.
  const activeDragRef = useRef(null);

  const handleDragStart = (event) => {
    const taskId = Number(event.active.id);
    const t = tasks.find((x) => x.id === taskId);
    if (!t) return;
    activeDragRef.current = { taskId, fromStatus: t.status };
    const { x, y } = cursorRef.current;
    drag.sendDragStart({ task_id: taskId, from_status: t.status, x, y });
  };

  const handleDragMove = () => {
    const active = activeDragRef.current;
    if (!active) return;
    const { x, y } = cursorRef.current;
    drag.sendDragMove({ task_id: active.taskId, x, y, over_status: null });
  };

  const handleDragCancel = () => {
    const active = activeDragRef.current;
    if (active) {
      drag.sendDragEnd({ task_id: active.taskId, cancelled: true });
    }
    activeDragRef.current = null;
  };

  const handleDragEnd = async (event) => {
    const active = activeDragRef.current;
    activeDragRef.current = null;
    if (!active) return;
    const { taskId, fromStatus } = active;
    const overId = event.over?.id;
    if (!overId) {
      drag.sendDragEnd({ task_id: taskId, cancelled: true });
      return;
    }

    // Resolve the target status: drop target may be a column or another card.
    let targetStatus = null;
    const overIdStr = String(overId);
    if (overIdStr.startsWith('column-')) {
      targetStatus = overIdStr.replace('column-', '');
    } else {
      const overTask = tasks.find((t) => String(t.id) === overIdStr);
      targetStatus = overTask?.status ?? null;
    }

    drag.sendDragEnd({ task_id: taskId, cancelled: false });

    if (!targetStatus || targetStatus === fromStatus) {
      return;
    }

    // Optimistic UI: snap the card into the new column immediately.
    const prevSnapshot = tasks;
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: targetStatus } : t)),
    );

    try {
      await taskAPI.updateTaskStatus(taskId, targetStatus);
      // The server will broadcast `task.status_changed`; that handler is
      // idempotent so we don't need to do anything else here.
    } catch (err) {
      console.error(err);
      toast.error('Failed to update task status; reverting.');
      setTasks(prevSnapshot);
    }
  };

  // ---- Render -----------------------------------------------------------
  const filteredTasks = useMemo(() => tasks.filter(filter), [tasks, filter]);

  const tasksByStatus = useMemo(() => {
    const groups = {
      [TASK_STATUS.PENDING]: [],
      [TASK_STATUS.IN_PROGRESS]: [],
      [TASK_STATUS.COMPLETED]: [],
    };
    for (const t of filteredTasks) {
      if (groups[t.status]) groups[t.status].push(t);
    }
    return groups;
  }, [filteredTasks]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {KANBAN_COLUMN_ORDER.map((status) => (
          <div key={status} className="bg-white/70 backdrop-blur-sm rounded-xl p-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-gray-200 rounded-xl h-32 animate-pulse"
              />
            ))}
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragMove={handleDragMove}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {KANBAN_COLUMN_ORDER.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              label={KANBAN_COLUMN_LABEL[status]}
              tasks={tasksByStatus[status]}
              remoteDrags={remoteDrags}
            />
          ))}
        </div>
      </DndContext>

      {/* Floating remote-drag ghosts */}
      {Object.values(remoteDrags).map((rd) => (
        <DragGhost key={rd.task_id} remoteDrag={rd} />
      ))}
    </>
  );
};

export default KanbanBoard;
