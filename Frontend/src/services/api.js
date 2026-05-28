import axios from 'axios';
import toast from 'react-hot-toast';
import { API_BASE_URL, STORAGE_KEYS } from '../utils/constants';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ---------- Single-flight refresh state ----------
// `refreshPromise` is a module-level promise so that N concurrent 401s all
// await the same /auth/refresh call instead of each firing their own.
let refreshPromise = null;

const clearSessionAndRedirect = (reason) => {
  localStorage.removeItem(STORAGE_KEYS.ACCESS);
  localStorage.removeItem(STORAGE_KEYS.REFRESH);
  localStorage.removeItem(STORAGE_KEYS.USER);
  if (reason) toast.error(reason);
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
};

export const performRefresh = async () => {
  const refresh_token = localStorage.getItem(STORAGE_KEYS.REFRESH);
  if (!refresh_token) throw new Error('no_refresh_token');

  // Use a bare axios call so the interceptor doesn't recursively wrap us.
  const res = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token });
  const { access_token, refresh_token: new_refresh, user } = res.data;
  localStorage.setItem(STORAGE_KEYS.ACCESS, access_token);
  localStorage.setItem(STORAGE_KEYS.REFRESH, new_refresh);
  if (user) localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
  return access_token;
};

// Request interceptor: attach current access token (re-read each request so we
// pick up a token rotated in by performRefresh).
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: on 401, try one refresh and replay. Concurrent 401s
// share the in-flight `refreshPromise`.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    // No retry if we already retried, if it wasn't a 401, or if the failing
    // request was the refresh endpoint itself (avoid infinite loop).
    const requestUrl = originalRequest?.url || '';
    const isRefreshCall = requestUrl.includes('/auth/refresh');
    const isLoginCall = requestUrl.endsWith('/login') || requestUrl.endsWith('/register');

    if (status !== 401 || !originalRequest || originalRequest._retry || isRefreshCall || isLoginCall) {
      if (status === 401 && (isRefreshCall || originalRequest?._retry)) {
        clearSessionAndRedirect('Session expired. Please login again.');
      }
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      // Coalesce concurrent 401s onto a single refresh.
      if (!refreshPromise) {
        refreshPromise = performRefresh().finally(() => {
          // Always clear so a later 401 can trigger a new refresh.
          refreshPromise = null;
        });
      }
      const newAccess = await refreshPromise;
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${newAccess}`;
      return api(originalRequest);
    } catch (refreshErr) {
      clearSessionAndRedirect('Session expired. Please login again.');
      return Promise.reject(refreshErr);
    }
  }
);

// ---------- Auth APIs ----------
export const authAPI = {
  login: (credentials) => api.post('/login', credentials),
  signup: (userData) => api.post('/register', userData),
  refresh: (refresh_token) => api.post('/auth/refresh', { refresh_token }),
  logout: (refresh_token) => api.post('/auth/logout', { refresh_token }),
  forgotPassword: ({ email }) => api.post('/auth/forgot-password', { email }),
  resetPassword: ({ token, new_password }) =>
    api.post('/auth/reset-password', { token, new_password }),
};

// ---------- Task APIs ----------
export const taskAPI = {
  // Server-side paginated / filtered / sorted listing. `params` is a plain
  // object — axios will serialise it as query string.
  getTasks: (params) => api.get('/tasks/filtered', { params }),

  // Legacy unpaginated endpoints (kept for one release; new code uses getTasks).
  getAllTasks: () => api.get('/tasks/admin'),
  getMyTasks: () => api.get('/tasks/user/me'),

  getTaskById: (id) => api.get(`/tasks/${id}`),
  createTask: (taskData) => api.post('/tasks/create_task', taskData),
  updateTask: (id, taskData) => api.put(`/tasks/${id}/admin`, taskData),
  deleteTask: (id) => api.delete(`/tasks/${id}/delete`),
  updateTaskStatus: (id, status) => api.patch(`/tasks/${id}/status`, { status }),
};

// ---------- User APIs ----------
export const userAPI = {
  getAllUsers: () => api.get('/user/'),
  getUsers: (params) => api.get('/user/paginated', { params }),
  getUserById: (id) => api.get(`/user/id/${id}`),
};

export default api;
