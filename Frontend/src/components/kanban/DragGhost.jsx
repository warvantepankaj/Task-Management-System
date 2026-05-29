import { motion } from 'framer-motion';
import { Calendar, User } from 'lucide-react';
import StatusBadge from '../tasks/StatusBadge';
import { formatDate, getInitials } from '../../utils/helpers';

const STATUS_LABELS = {
  PENDING: 'Pending',
  IN_PROGRESS: 'In Progress',
  COMPLETED: 'Completed',
};

/**
 * Floating ghost rendered at the cursor position from incoming remote
 * `task.drag_move` events. Mirrors the look of a real KanbanCard so the
 * watcher feels like the card itself is gliding under the actor's cursor.
 *
 * Position comes from MotionValues (x, y) on `remoteDrag.position`. Writing
 * to those motion values updates the DOM directly via framer-motion, with
 * no React re-render — that's what keeps the ghost glued to the cursor at
 * 60+ Hz regardless of how busy React is elsewhere on the board.
 */
const DragGhost = ({ remoteDrag }) => {
  if (!remoteDrag || !remoteDrag.position) return null;
  const { position, task, user } = remoteDrag;
  const label = user?.username || user?.email || 'Someone';

  return (
    <motion.div
      className="card pointer-events-none fixed z-50 w-72 shadow-2xl border border-indigo-300"
      style={{
        left: 0,
        top: 0,
        x: position.x,
        y: position.y,
        translateX: '-50%',
        translateY: '-50%',
        opacity: 0.85,
        scale: 1.04,
        rotate: 1,
      }}
    >
      {/* "X is moving this" pill */}
      <div className="absolute -top-2 -right-2 flex items-center bg-white border border-gray-200 rounded-full shadow-md px-2 py-1">
        <div className="w-6 h-6 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-md flex items-center justify-center text-white text-xs font-semibold mr-2">
          {getInitials(label)}
        </div>
        <span className="text-xs text-gray-700">{label} is moving</span>
      </div>

      <div className="mb-4 pr-2">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {task?.title || `Task #${remoteDrag.task_id}`}
        </h3>
        {task?.description && (
          <p className="text-gray-600 text-sm line-clamp-2">{task.description}</p>
        )}
      </div>

      <div className="space-y-3">
        {task?.status && (
          <div className="flex items-center justify-between">
            <StatusBadge status={STATUS_LABELS[task.status] || task.status} />
          </div>
        )}
        {(task?.assigned_to_username || task?.assigned_to) && (
          <div className="flex items-center text-sm text-gray-600">
            <User size={16} className="mr-2" />
            <span className="ml-1">
              Assigned To: {task.assigned_to_username || task.assigned_to}
            </span>
          </div>
        )}
        {task?.due_date && (
          <div className="flex items-center text-sm text-gray-600">
            <Calendar size={16} className="mr-2" />
            <span>Due: {formatDate(task.due_date)}</span>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default DragGhost;
