import { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../hooks/useAuth';
import { taskAPI } from '../services/api';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Pagination from '../components/common/Pagination';
import TaskForm from '../components/tasks/TaskForm';
import TaskFilters from '../components/tasks/TaskFilters';
import TaskList from '../components/tasks/TaskList';

const DEFAULT_PAGE_SIZE = 9;

// Helpers: read / write filter+page state from URL query params so a hard
// refresh preserves the user's view.
const parseFromURL = (sp) => ({
  page: Math.max(1, parseInt(sp.get('page') || '1', 10) || 1),
  size: Math.max(1, parseInt(sp.get('size') || String(DEFAULT_PAGE_SIZE), 10) || DEFAULT_PAGE_SIZE),
  search: sp.get('search') || '',
  status: sp.get('status') || '',
  sort_by: sp.get('sort_by') || 'created_at',
  sort_order: sp.get('sort_order') === 'asc' ? 'asc' : 'desc',
});

// Strip empty values so the URL stays tidy.
const toURLParams = (state) => {
  const out = {};
  if (state.page && state.page !== 1) out.page = String(state.page);
  if (state.size && state.size !== DEFAULT_PAGE_SIZE) out.size = String(state.size);
  if (state.search) out.search = state.search;
  if (state.status) out.status = state.status;
  if (state.sort_by && state.sort_by !== 'created_at') out.sort_by = state.sort_by;
  if (state.sort_order && state.sort_order !== 'desc') out.sort_order = state.sort_order;
  return out;
};

const Tasks = () => {
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [searchParams, setSearchParams] = useSearchParams();
  const urlState = useMemo(() => parseFromURL(searchParams), [searchParams]);

  const [tasks, setTasks] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);

  // The filter bar drives `urlState` indirectly through setSearchParams.
  const filters = {
    search: urlState.search,
    status: urlState.status,
    sort_by: urlState.sort_by,
    sort_order: urlState.sort_order,
  };

  const updateState = useCallback(
    (patch) => {
      const next = { ...urlState, ...patch };
      // Whenever any filter changes, reset to page 1 (unless the patch
      // explicitly sets page).
      if (!('page' in patch)) next.page = 1;
      setSearchParams(toURLParams(next));
    },
    [urlState, setSearchParams]
  );

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: urlState.page,
        size: urlState.size,
        sort_by: urlState.sort_by,
        sort_order: urlState.sort_order,
      };
      if (urlState.status) params.status = urlState.status;
      if (urlState.search) params.search = urlState.search;

      const { data } = await taskAPI.getTasks(params);
      setTasks(data.data || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
    } catch (error) {
      toast.error('Failed to fetch tasks');
      // eslint-disable-next-line no-console
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [urlState]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchTasks();
  }, [authLoading, user, fetchTasks]);

  const handleCreateTask = () => {
    setSelectedTask(null);
    setIsModalOpen(true);
  };

  const handleEditTask = (task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleSubmitTask = async (formData) => {
    try {
      if (selectedTask) {
        await taskAPI.updateTask(selectedTask.id, formData);
        toast.success('Task updated successfully');
      } else {
        await taskAPI.createTask(formData);
        toast.success('Task created successfully');
      }
      setIsModalOpen(false);
      setSelectedTask(null);
      fetchTasks();
    } catch (error) {
      toast.error(error.response?.data?.message || 'Operation failed');
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task?')) return;
    try {
      await taskAPI.deleteTask(taskId);
      toast.success('Task deleted successfully');
      fetchTasks();
    } catch (error) {
      toast.error('Failed to delete task');
    }
  };

  const handleStatusChange = async (taskId, newStatus) => {
    try {
      await taskAPI.updateTaskStatus(taskId, newStatus);
      toast.success('Task status updated');
      fetchTasks();
    } catch (error) {
      toast.error('Failed to update task status');
    }
  };

  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between mb-8"
          >
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {isAdmin ? 'All Tasks' : 'My Tasks'}
              </h1>
              <p className="text-gray-600">
                Manage and track your tasks efficiently
              </p>
            </div>

            {isAdmin && (
              <Button
                variant="primary"
                icon={<Plus size={20} />}
                onClick={handleCreateTask}
              >
                Create Task
              </Button>
            )}
          </motion.div>

          <TaskFilters filters={filters} onFilterChange={updateState} />

          <TaskList
            tasks={tasks}
            onEdit={handleEditTask}
            onDelete={handleDeleteTask}
            onStatusChange={handleStatusChange}
            isAdmin={isAdmin}
            loading={loading}
          />

          {total > 0 && (
            <Pagination
              page={urlState.page}
              totalPages={totalPages}
              total={total}
              pageSize={urlState.size}
              onChange={(newPage) => updateState({ page: newPage })}
            />
          )}

          <Modal
            isOpen={isModalOpen}
            onClose={() => {
              setIsModalOpen(false);
              setSelectedTask(null);
            }}
            title={selectedTask ? 'Edit Task' : 'Create New Task'}
            size="lg"
          >
            <TaskForm
              task={selectedTask}
              onSubmit={handleSubmitTask}
              onCancel={() => {
                setIsModalOpen(false);
                setSelectedTask(null);
              }}
              isAdmin={isAdmin}
            />
          </Modal>
        </div>
      </div>
    </>
  );
};

export default Tasks;
