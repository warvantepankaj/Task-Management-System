import { format, formatDistanceToNow, isPast, differenceInDays } from 'date-fns';

export const formatDate = (date) => {
  return format(new Date(date), 'MMM dd, yyyy');
};

export const formatDateTime = (date) => {
  return format(new Date(date), 'MMM dd, yyyy HH:mm');
};

export const getRelativeTime = (date) => {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
};

export const isTaskOverdue = (dueDate, status) => {
  return status !== 'Completed' && isPast(new Date(dueDate));
};

export const getDaysUntilDue = (dueDate) => {
  return differenceInDays(new Date(dueDate), new Date());
};

export const getTaskPriority = (dueDate) => {
  const days = getDaysUntilDue(dueDate);
  
  if (days < 0) return 'overdue';
  if (days <= 2) return 'urgent';
  if (days <= 7) return 'high';
  return 'normal';
};

export const truncateText = (text, maxLength = 100) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

export const getInitials = (name) => {
  if (!name) return '?';
  return name
    .split(' ')
    .map(word => word[0])
    .join('')
    .toUpperCase()
    .substring(0, 2);
};

export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export const validatePassword = (password) => {
  return password.length >= 6;
};

export const classNames = (...classes) => {
  return classes.filter(Boolean).join(' ');
};