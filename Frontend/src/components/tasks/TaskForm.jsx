import { useState, useEffect } from 'react';
import { Calendar, User, FileText, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import Input from '../common/Input';
import Button from '../common/Button';
import { TASK_STATUS } from '../../utils/constants';
import { userAPI } from '../../services/api';

const TaskForm = ({ task = null, onSubmit, onCancel, isAdmin }) => {
  const isEditMode = Boolean(task);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    assigned_to: '',
    status: TASK_STATUS.PENDING,
    due_date: '',
  });
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (task) {
      setFormData({
        title: task.title || '',
        description: task.description || '',
        assigned_to: task.assigned_to || '',
        status: task.status || TASK_STATUS.PENDING,
        due_date: task.due_date ? task.due_date.split('T')[0] : '',
      });
    }
  }, [task]);

  useEffect(() => {
    if (isAdmin) {
      fetchUsers();
    }
  }, [isAdmin]);

  const fetchUsers = async () => {
    try {
      const response = await userAPI.getAllUsers();
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const handleSubmit = async (e) => {
  e.preventDefault();

  // Validation
  if (!formData.title.trim()) {
    toast.error('Please enter a task title');
    return;
  }

  if (!formData.due_date) {
    toast.error('Please select a due date');
    return;
  }

  if (isAdmin && !formData.assigned_to) {
    toast.error('Please assign the task to a user');
    return;
  }

  setLoading(true);

  try {
    // Only send assigned_to if admin and valid
    const payload = {
      title: formData.title,
      description: formData.description || null,
      status: formData.status,
      due_date: formData.due_date,
      assigned_to: isAdmin && formData.assigned_to
        ? Number(formData.assigned_to)
        : undefined,
    };

    await onSubmit(payload);
    toast.success('Task submitted successfully!');
  } catch (error) {
    console.error('Submit error:', error.response?.data);

    // Handle Pydantic validation errors
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      const message = Array.isArray(detail)
        ? detail.map(err => `${err.loc.join('.')} : ${err.msg}`).join(', ')
        : detail;
      toast.error(message);
    } else {
      toast.error('Failed to create task');
    }
  } finally {
    setLoading(false);
  }
};


  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Input
        label="Task Title"
        icon={<FileText size={20} />}
        placeholder="Enter task title"
        value={formData.title}
        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
        required
      />

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description
        </label>
        <textarea
          className="input-field min-h-[100px] resize-y"
          placeholder="Enter task description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          rows={4}
        />
      </div>

      {isAdmin && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Assign To
          </label>
          <div className="relative">
            <User size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <select
              className="input-field pl-10"
              value={formData.assigned_to}
              onChange={(e) => setFormData({ ...formData, assigned_to: Number(e.target.value) })}
            >
              <option value="">Select a user</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name} ({user.email})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

  {isEditMode && (
  <div>
  <label className="block text-sm font-medium text-gray-700 mb-2">
    Status
  </label>
      <div className="relative">
        <Clock size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <select
          className="input-field pl-10"
          value={formData.status}
          onChange={(e) => setFormData({ ...formData, status: e.target.value })}
          required
        >
          <option value="PENDING">PENDING</option>
          <option value="IN_PROGRESS">IN_PROGRESS</option>
          <option value="COMPLETED">COMPLETED</option>
        </select>
      </div>
    </div>
  )}


      <Input
        label="Due Date"
        type="date"
        icon={<Calendar size={20} />}
        value={formData.due_date}
        onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
        min={new Date().toISOString().split('T')[0]}
        required
      />

      <div className="flex justify-end gap-3 pt-4">
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="primary"
          loading={loading}
        >
          {task ? 'Update Task' : 'Create Task'}
        </Button>
      </div>
    </form>
  );
};

export default TaskForm;