import { motion } from 'framer-motion';
import { getInitials } from '../../utils/helpers';

/**
 * Floating ghost rendered at the cursor position from incoming remote
 * `task.drag_move` events. One ghost per active remote drag.
 */
const DragGhost = ({ remoteDrag }) => {
  if (!remoteDrag || !remoteDrag.cursor) return null;
  const { cursor, task, user } = remoteDrag;
  const label = user?.username || user?.email || 'Someone';

  return (
    <motion.div
      className="card pointer-events-none fixed z-50 opacity-40 w-72"
      style={{ left: cursor.x, top: cursor.y }}
      transition={{ duration: 0.08, ease: 'linear' }}
      initial={false}
      animate={{ x: 0, y: 0 }}
    >
      <div className="flex items-center mb-3">
        <div className="w-6 h-6 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-md flex items-center justify-center text-white text-xs font-semibold mr-2">
          {getInitials(label)}
        </div>
        <span className="text-xs text-gray-700">{label} is moving</span>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-1">
        {task?.title || `Task #${remoteDrag.task_id}`}
      </h3>
      {task?.description && (
        <p className="text-gray-600 text-sm line-clamp-2">{task.description}</p>
      )}
    </motion.div>
  );
};

export default DragGhost;
