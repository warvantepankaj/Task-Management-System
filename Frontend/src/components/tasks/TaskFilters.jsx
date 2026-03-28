import { Search, Filter } from 'lucide-react';
import { TASK_STATUS } from '../../utils/constants';

const TaskFilters = ({ filters, onFilterChange }) => {
  return (
    <div className="bg-white rounded-xl shadow-md p-6 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="text-gray-600" size={20} />
        <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Search */}
        <div className="relative">
          <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search tasks..."
            className="input-field pl-10"
            value={filters.search}
            onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
          />
        </div>

        {/* Status Filter */}
        <select
          className="input-field"
          value={filters.status}
          onChange={(e) => onFilterChange({ ...filters, status: e.target.value })}
        >
          <option value="">All Status</option>
          <option value={TASK_STATUS.PENDING}>Pending</option>
          <option value={TASK_STATUS.IN_PROGRESS}>In Progress</option>
          <option value={TASK_STATUS.COMPLETED}>Completed</option>
        </select>

        {/* Sort By */}
        <select
          className="input-field"
          value={filters.sortBy}
          onChange={(e) => onFilterChange({ ...filters, sortBy: e.target.value })}
        >
          <option value="due_date">Due Date</option>
          <option value="created_date">Created Date</option>
          <option value="title">Title</option>
          <option value="status">Status</option>
        </select>
      </div>
    </div>
  );
};

export default TaskFilters;