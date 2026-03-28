import { motion } from 'framer-motion';
import { Calendar, User, MoreVertical, Edit, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import StatusBadge from './StatusBadge';
import { Menu } from '@headlessui/react';

const STATUS_LABELS = {
  PENDING: "Pending",
  IN_PROGRESS: "In Progress",
  COMPLETED: "Completed",
};

const TaskCard = ({ task, onEdit, onDelete, onStatusChange, isAdmin }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      className="card relative"
    >
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">{task.title}</h3>
          <p className="text-gray-600 text-sm line-clamp-2">{task.description}</p>
        </div>
        
        {isAdmin && (
          <Menu as="div" className="relative">
            <Menu.Button className="p-1 hover:bg-gray-100 rounded-lg">
              <MoreVertical size={20} className="text-gray-600" />
            </Menu.Button>
            <Menu.Items className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={() => onEdit(task)}
                    className={`${active ? 'bg-gray-100' : ''} flex items-center w-full px-4 py-2 text-sm text-gray-700`}
                  >
                    <Edit size={16} className="mr-2" />
                    Edit
                  </button>
                )}
              </Menu.Item>
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={() => onDelete(task.id)}
                    className={`${active ? 'bg-gray-100' : ''} flex items-center w-full px-4 py-2 text-sm text-red-600`}
                  >
                    <Trash2 size={16} className="mr-2" />
                    Delete
                  </button>
                )}
              </Menu.Item>
            </Menu.Items>
          </Menu>
        )}
      </div>


      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <StatusBadge status={STATUS_LABELS[task.status]} />
          
          {!isAdmin && (
            <select
              value={task.status}
              onChange={(e) => onStatusChange(task.id, e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-2 py-1 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="PENDING">Pending</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
            </select>
          )}
        </div>

        <div className="flex items-center text-sm text-gray-600">
          <User size={16} className="mr-2" />
          <span className='ml-2'>Assigned To : {task.assigned_to_username || 'Unassigned'}</span>
        </div>

        <div className="flex items-center text-sm text-gray-600">
          <Calendar size={16} className="mr-2" />
          <span>Due: {format(new Date(task.due_date), 'MMM dd, yyyy')}</span>
        </div>
      </div>
    </motion.div>
  );
};

export default TaskCard;