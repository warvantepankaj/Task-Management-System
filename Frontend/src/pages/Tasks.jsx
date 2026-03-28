import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../hooks/useAuth';
import { taskAPI } from '../services/api';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import TaskForm from '../components/tasks/TaskForm';
import TaskFilters from '../components/tasks/TaskFilters';
import TaskList from '../components/tasks/TaskList';
import LoadingSpinner from '../components/common/LoadingSpinner';

const Tasks = () => {
   const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.role === 'admin';
  
  const [tasks, setTasks] = useState([]);
  const [filteredTasks, setFilteredTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    sortBy: 'due_date',
  });

  useEffect(() => {
  if (authLoading) return;
  if (!user) return;        

  fetchTasks();
}, [authLoading, user]);

  useEffect(() => {
    applyFilters();
  }, [tasks, filters]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = isAdmin 
        ? await taskAPI.getAllTasks()
        : await taskAPI.getMyTasks();
      
      setTasks(response.data);
    } catch (error) {
      toast.error('Failed to fetch tasks');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...tasks];

    // Search filter
    if (filters.search) {
      filtered = filtered.filter(task =>
        task.title.toLowerCase().includes(filters.search.toLowerCase()) ||
        task.description?.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    // Status filter
    if (filters.status) {
      filtered = filtered.filter(task => task.status === filters.status);
    }

    // Sort
    filtered.sort((a, b) => {
      switch (filters.sortBy) {
        case 'due_date':
          return new Date(a.due_date) - new Date(b.due_date);
        case 'created_date':
          return new Date(b.created_date) - new Date(a.created_date);
        case 'title':
          return a.title.localeCompare(b.title);
        case 'status':
          return a.status.localeCompare(b.status);
        default:
          return 0;
      }
    });

    setFilteredTasks(filtered);
  };

  const handleCreateTask = () => {
    setSelectedTask(null);
    setIsModalOpen(true);
  };

  const handleEditTask = (task) => {
    console.log("Editing task:", task);
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
    if (!window.confirm('Are you sure you want to delete this task?')) {
      return;
    }

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
          {/* Header */}
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

          {/* Filters */}
          <TaskFilters filters={filters} onFilterChange={setFilters} />

          {/* Task Count */}
          <div className="mb-6">
            <p className="text-sm text-gray-600">
              Showing <span className="font-semibold text-gray-900">{filteredTasks.length}</span> of{' '}
              <span className="font-semibold text-gray-900">{tasks.length}</span> tasks
            </p>
          </div>

          {/* Tasks List */}
          <TaskList
            tasks={filteredTasks}
            onEdit={handleEditTask}
            onDelete={handleDeleteTask}
            onStatusChange={handleStatusChange}
            isAdmin={isAdmin}
            loading={loading}
          />

          {/* Create/Edit Task Modal */}
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