import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  ListTodo,
  TrendingUp,
  Calendar,
  Users,
  Plus,
  PieChart
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../hooks/useAuth';
import { taskAPI, userAPI } from '../services/api';
import Navbar from '../components/common/Navbar';
import StatsCard from '../components/dashboard/StatsCard';
import TaskCard from '../components/tasks/TaskCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import TaskForm from '../components/tasks/TaskForm';
import { TASK_STATUS } from '../utils/constants';
import { isTaskOverdue } from '../utils/helpers';

const AdminDashboard = () => {
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.role === 'admin';
  
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    inProgress: 0,
    completed: 0,
    overdue: 0,
    totalUsers: 0,
    activeUsers: 0,
  });

  useEffect(() => {
  if (authLoading) return;
  if (!user) return;        

  fetchDashboardData();
}, [authLoading, user]);


  useEffect(() => {
  console.log("TASKS:", tasks);
}, [tasks]);


  const fetchDashboardData = async () => {
  setLoading(true);
  try {
    let tasksResponse;
    if (isAdmin) {
      tasksResponse = await taskAPI.getAllTasks();
    } else {
      tasksResponse = await taskAPI.getMyTasks();
    }

    const usersResponse = isAdmin ? await userAPI.getAllUsers() : { data: [] };

    const tasksData = tasksResponse.data;
    const usersData = usersResponse.data;

    setTasks(tasksData);
    setUsers(usersData);
    calculateStats(tasksData, usersData);

  } catch (error) {
    toast.error('Failed to fetch dashboard data');
    console.error(error);
  } finally {
    setLoading(false);
  }
};


  const calculateStats = (tasksData, usersData) => {
    const stats = {
      total: tasksData.length,
      pending: tasksData.filter(t => t.status === TASK_STATUS.PENDING).length,
      inProgress: tasksData.filter(t => t.status === TASK_STATUS.IN_PROGRESS).length,
      completed: tasksData.filter(t => t.status === TASK_STATUS.COMPLETED).length,
      overdue: tasksData.filter(t => isTaskOverdue(t.due_date, t.status)).length,
      totalUsers: usersData.length,
      activeUsers: usersData.filter(u => u.is_active).length || usersData.length,
    };
    setStats(stats);
  };

  const handleCreateTask = () => {
    setSelectedTask(null);
    setIsModalOpen(true);
  };

  const handleEditTask = (task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task?')) {
      return;
    }

    try {
      await taskAPI.deleteTask(taskId);
      toast.success('Task deleted successfully');
      fetchDashboardData();
    } catch (error) {
      toast.error('Failed to delete task');
    }
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
      fetchDashboardData();
    } catch (error) {
      toast.error(error.response?.data?.message || 'Operation failed');
      throw error;
    }
  };

  const handleStatusChange = async (taskId, newStatus) => {
    try {
      await taskAPI.updateTaskStatus(taskId, newStatus);
      toast.success('Task status updated');
      fetchDashboardData();
    } catch (error) {
      toast.error('Failed to update task status');
    }
  };

  const recentTasks = tasks.slice(0, 6);

  // Calculate task distribution by user (Admin only)
  const getTaskDistribution = () => {
    const distribution = {};
    tasks.forEach(task => {
      const userName = task.assigned_user || 'Unassigned';
      if (!distribution[userName]) {
        distribution[userName] = { total: 0, completed: 0 };
      }
      distribution[userName].total++;
      if (task.status === TASK_STATUS.COMPLETED) {
        distribution[userName].completed++;
      }
    });
    return distribution;
  };

  if (authLoading || loading) {
  return (
    <>
      <Navbar />
      <LoadingSpinner fullScreen />
    </>
  );
}


  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header with Create Button (Admin Only) */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between mb-8"
          >
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {isAdmin ? `Welcome back, ${user.username}!` : `Welcome back, ${user.username}!`} 👋
              </h1>
              <p className="text-gray-600">
                {isAdmin 
                  ? 'Manage all tasks and monitor team performance' 
                  : "Here's what's happening with your tasks today."}
              </p>
            </div>
            
            {isAdmin && (
              <Button
                variant="primary"
                icon={<Plus size={20} />}
                onClick={handleCreateTask}
                className="shadow-lg"
              >
                Create Task
              </Button>
            )}
          </motion.div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatsCard
              title="Total Tasks"
              value={stats.total}
              icon={ListTodo}
              color="indigo"
              trend={5}
            />
            <StatsCard
              title="In Progress"
              value={stats.inProgress}
              icon={Clock}
              color="blue"
              trend={12}
            />
            <StatsCard
              title="Completed"
              value={stats.completed}
              icon={CheckCircle2}
              color="green"
              trend={8}
            />
            <StatsCard
              title="Overdue"
              value={stats.overdue}
              icon={AlertCircle}
              color="red"
              trend={-3}
            />
          </div>

          {/* Admin-Only Stats */}
          {isAdmin && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-lg p-6 text-white"
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-purple-100 text-sm font-medium">Total Users</p>
                    <p className="text-3xl font-bold">{stats.totalUsers}</p>
                  </div>
                  <div className="p-3 bg-white/20 rounded-lg backdrop-blur-sm">
                    <Users className="w-8 h-8" />
                  </div>
                </div>
                <p className="text-purple-100 text-sm">Team members registered</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl shadow-lg p-6 text-white"
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-indigo-100 text-sm font-medium">This Week</p>
                    <p className="text-3xl font-bold">{stats.pending}</p>
                  </div>
                  <div className="p-3 bg-white/20 rounded-lg backdrop-blur-sm">
                    <Calendar className="w-8 h-8" />
                  </div>
                </div>
                <p className="text-indigo-100 text-sm">Pending tasks to assign</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-lg p-6 text-white"
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-green-100 text-sm font-medium">Completion Rate</p>
                    <p className="text-3xl font-bold">
                      {stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0}%
                    </p>
                  </div>
                  <div className="p-3 bg-white/20 rounded-lg backdrop-blur-sm">
                    <TrendingUp className="w-8 h-8" />
                  </div>
                </div>
                <p className="text-green-100 text-sm">Overall team performance</p>
              </motion.div>
            </div>
          )}

          {/* Employee Stats (Non-Admin) */}
          {!isAdmin && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-lg p-6 text-white"
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-indigo-100 text-sm font-medium">This Week</p>
                    <p className="text-3xl font-bold">{stats.pending}</p>
                  </div>
                  <div className="p-3 bg-white/20 rounded-lg backdrop-blur-sm">
                    <Calendar className="w-8 h-8" />
                  </div>
                </div>
                <p className="text-indigo-100 text-sm">Pending tasks to complete</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-lg p-6 text-white"
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-green-100 text-sm font-medium">Completion Rate</p>
                    <p className="text-3xl font-bold">
                      {stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0}%
                    </p>
                  </div>
                  <div className="p-3 bg-white/20 rounded-lg backdrop-blur-sm">
                    <TrendingUp className="w-8 h-8" />
                  </div>
                </div>
                <p className="text-green-100 text-sm">Keep up the great work!</p>
              </motion.div>
            </div>
          )}

          {/* Task Distribution by User (Admin Only) */}
          {isAdmin && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-white rounded-xl shadow-md p-6 mb-8"
            >
              <div className="flex items-center gap-2 mb-6">
                <PieChart className="text-indigo-600" size={24} />
                <h2 className="text-xl font-bold text-gray-900">Task Distribution by User</h2>
              </div>
              
              <div className="space-y-4">
                {Object.entries(getTaskDistribution()).map(([userName, data], index) => {
                  const completionRate = data.total > 0 ? (data.completed / data.total) * 100 : 0;
                  
                  return (
                    <div key={index} className="border-b border-gray-100 pb-4 last:border-0">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-semibold text-sm">
                            {userName.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{userName}</p>
                            <p className="text-sm text-gray-500">
                              {data.completed} of {data.total} tasks completed
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-gray-900">{Math.round(completionRate)}%</p>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-gradient-to-r from-indigo-500 to-purple-600 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${completionRate}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {/* Recent Tasks */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">
                {isAdmin ? 'All Tasks' : 'Recent Tasks'}
              </h2>
              <a
                href="/tasks"
                className="text-indigo-600 hover:text-indigo-700 font-medium text-sm"
              >
                View all →
              </a>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {recentTasks.map((task, index) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <TaskCard
                    task={task}
                    onEdit={handleEditTask}
                    onDelete={handleDeleteTask}
                    onStatusChange={handleStatusChange}
                    isAdmin={isAdmin}
                  />
                </motion.div>
              ))}
            </div>

            {recentTasks.length === 0 && (
              <div className="text-center py-12 bg-white rounded-xl shadow-md">
                <ListTodo className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-600">
                  {isAdmin 
                    ? 'No tasks yet. Create your first task to get started!' 
                    : 'No tasks assigned yet.'}
                </p>
                {isAdmin && (
                  <Button
                    variant="primary"
                    icon={<Plus size={20} />}
                    onClick={handleCreateTask}
                    className="mt-4"
                  >
                    Create First Task
                  </Button>
                )}
              </div>
            )}
          </motion.div>

          {/* Create/Edit Task Modal (Admin Only) */}
          {isAdmin && (
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
          )}
        </div>
      </div>
    </>
  );
};

export default AdminDashboard;