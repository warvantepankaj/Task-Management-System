import { motion } from 'framer-motion';
import { Calendar, User, GripVertical } from 'lucide-react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import StatusBadge from '../tasks/StatusBadge';
import { formatDate, getInitials } from '../../utils/helpers';

const STATUS_LABELS = {
  PENDING: 'Pending',
  IN_PROGRESS: 'In Progress',
  COMPLETED: 'Completed',
};

const KanbanCard = ({ task, remoteDrag, index = 0 }) => {
  const sortableId = String(task.id);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: sortableId, data: { status: task.status } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const isRemoteDragging = Boolean(remoteDrag);
  const remoteLabel = remoteDrag?.user?.username || remoteDrag?.user?.email || 'Someone';

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      layoutId={`kanban-card-${task.id}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ layout: { duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }, delay: index * 0.05 }}
      whileHover={!isDragging && !isRemoteDragging ? { y: -4 } : undefined}
      whileDrag={{ scale: 1.04, rotate: 1 }}
      {...attributes}
      className={`card relative ${isDragging ? 'cursor-grabbing shadow-xl' : 'cursor-grab'} ${
        isRemoteDragging
          ? 'opacity-50 pointer-events-none ring-2 ring-indigo-400 ring-dashed'
          : ''
      }`}
    >
      {/* Remote-drag "moving by X" pill */}
      {isRemoteDragging && (
        <div className="absolute -top-2 -right-2 flex items-center bg-white border border-gray-200 rounded-full shadow-md px-2 py-1 z-10">
          <div className="w-6 h-6 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-md flex items-center justify-center text-white text-xs font-semibold mr-2">
            {getInitials(remoteLabel)}
          </div>
          <span className="text-xs text-gray-700">{remoteLabel} is moving this</span>
        </div>
      )}

      {/* Drag handle */}
      <button
        type="button"
        aria-label="Drag task"
        {...listeners}
        className="absolute top-3 right-3 p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <GripVertical size={18} />
      </button>

      <div className="mb-4 pr-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{task.title}</h3>
        {task.description && (
          <p className="text-gray-600 text-sm line-clamp-2">{task.description}</p>
        )}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <StatusBadge status={STATUS_LABELS[task.status] || task.status} />
        </div>

        <div className="flex items-center text-sm text-gray-600">
          <User size={16} className="mr-2" />
          <span className="ml-1">
            Assigned To: {task.assigned_to_username || task.assigned_to || 'Unassigned'}
          </span>
        </div>

        {task.due_date && (
          <div className="flex items-center text-sm text-gray-600">
            <Calendar size={16} className="mr-2" />
            <span>Due: {formatDate(task.due_date)}</span>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default KanbanCard;
