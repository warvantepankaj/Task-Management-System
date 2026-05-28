import { Search, Filter, ArrowUpDown } from 'lucide-react';
import { TASK_STATUS, TASK_SORT_OPTIONS } from '../../utils/constants';

/**
 * The parent (Tasks.jsx) owns the filter state and the URL sync. We just
 * forward changes back up unchanged — no in-memory filtering happens here.
 */
const TaskFilters = ({ filters, onFilterChange }) => {
  const set = (patch) => onFilterChange({ ...filters, ...patch });

  return (
    <div className="bg-white rounded-xl shadow-md p-6 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="text-gray-600" size={20} />
        <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="relative md:col-span-2">
          <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search title or description..."
            className="input-field pl-10"
            value={filters.search || ''}
            onChange={(e) => set({ search: e.target.value })}
          />
        </div>

        <select
          className="input-field"
          value={filters.status || ''}
          onChange={(e) => set({ status: e.target.value })}
        >
          <option value="">All Status</option>
          <option value={TASK_STATUS.PENDING}>Pending</option>
          <option value={TASK_STATUS.IN_PROGRESS}>In Progress</option>
          <option value={TASK_STATUS.COMPLETED}>Completed</option>
        </select>

        <div className="flex gap-2">
          <select
            className="input-field flex-1"
            value={filters.sort_by || 'created_at'}
            onChange={(e) => set({ sort_by: e.target.value })}
          >
            {TASK_SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                Sort: {o.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() =>
              set({ sort_order: filters.sort_order === 'asc' ? 'desc' : 'asc' })
            }
            className="px-3 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-100 inline-flex items-center justify-center"
            aria-label="Toggle sort order"
            title={filters.sort_order === 'asc' ? 'Ascending' : 'Descending'}
          >
            <ArrowUpDown size={18} />
            <span className="ml-1 text-xs uppercase">
              {filters.sort_order === 'asc' ? 'ASC' : 'DESC'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default TaskFilters;
