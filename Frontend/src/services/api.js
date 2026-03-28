import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = 'http://localhost:8000/';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      toast.error('Session expired. Please login again.');
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  login: (credentials) => api.post('/login', credentials),
  signup: (userData) => api.post('/register', userData),
  getProfile: () => api.get('/profile'),
};

// Task APIs
export const taskAPI = {
  getAllTasks: () => api.get('/tasks/admin'),
  getMyTasks: () => api.get('/tasks/user/me'),
  getTaskById: (id) => api.get(`/tasks/${id}`),
  createTask: (taskData) => api.post('/tasks/create_task', taskData),
  updateTask: (id, taskData) => api.put(`/tasks/${id}/admin`, taskData),
  deleteTask: (id) => api.delete(`/tasks/${id}/delete`),
  updateTaskStatus: (id, status) => api.patch(`/tasks/${id}/status`, { status }),
};

export const userAPI = {
  getAllUsers: () => api.get('/user/'),
  getUserById: (id) => api.get(`/user/id/${id}`),
};

export default api;