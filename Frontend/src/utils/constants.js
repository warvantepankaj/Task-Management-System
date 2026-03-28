export const TASK_STATUS = {
  PENDING: 'PENDING',
  IN_PROGRESS: 'IN_PROGRESS',
  COMPLETED: 'COMPLETED',
};

export const USER_ROLES = {
  ADMIN: 'admin',
  EMPLOYEE: 'employee',
};

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  SIGNUP: '/signup',
  DASHBOARD: '/dashboard',
  TASKS: '/tasks',
};

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const TASK_STATUS_COLORS = {
  [TASK_STATUS.PENDING]: {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    dot: 'bg-amber-400',
  },
  [TASK_STATUS.IN_PROGRESS]: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
    dot: 'bg-blue-400',
  },
  [TASK_STATUS.COMPLETED]: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    dot: 'bg-emerald-400',
  },
};