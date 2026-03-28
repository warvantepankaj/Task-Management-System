export const API_BASE_URL = "http://localhost:8000";

import axios from "axios";

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  login: ({ email, password }) =>
    api.post(
      '/login',
      new URLSearchParams({
        username: email,   
        password: password,
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    ),
};

export const taskAPI = {
  getAllTasks: () => api.get('/tasks/admin'),
  getMyTasks: () => api.get('/tasks/user/me'),
  createTask: (data) => api.post('/tasks/create_task', data),
  updateTask: (id, data) => api.put(`/tasks/${id}`, data),
  deleteTask: (id) => api.delete(`/tasks/${id}`),
  updateTaskStatus: (id, status) =>
    api.patch(`/tasks/${id}/status`, { status }),
};


export default api;
