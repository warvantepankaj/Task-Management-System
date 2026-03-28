import api from "./api";


export const getUserTasks = (userId) =>
  api.get(`/tasks/user/me`);

export const getAllTasksAdmin = () =>
  api.get("/tasks/filtered");

export const createTask = async (data) => {
  return api.post("/tasks/create_task", data);
};

export const updateTaskStatus = (taskId, status) =>
  api.patch(`/tasks/${taskId}/status`, { status });

export const updateTask = (taskId, taskData) =>
  console.log("Updating task with data:", taskData) ||
  api.put(`/tasks/${taskId}/admin`, taskData);

export const deleteTask = (taskId) => 
  api.delete(`/tasks/${taskId}/delete`);
