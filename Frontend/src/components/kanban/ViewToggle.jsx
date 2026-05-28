import { List, LayoutGrid } from 'lucide-react';

const ViewToggle = ({ view, onChange }) => {
  const options = [
    { value: 'list', label: 'List', Icon: List },
    { value: 'board', label: 'Board', Icon: LayoutGrid },
  ];

  return (
    <div className="inline-flex items-center bg-white border border-gray-200 rounded-lg p-1">
      {options.map(({ value, label, Icon }) => {
        const active = view === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => onChange(value)}
            aria-pressed={active}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm transition-all duration-200 ${
              active
                ? 'bg-indigo-50 text-indigo-600 font-medium'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Icon size={16} />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
};

export default ViewToggle;
