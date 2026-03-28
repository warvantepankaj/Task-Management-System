
const StatusBadge = ({ status }) => {
  const statusConfig = {
    'Pending': 'bg-yellow-100 text-yellow-800 border-yellow-300',
    'In Progress': 'bg-blue-100 text-blue-800 border-blue-300',
    'Completed': 'bg-green-100 text-green-800 border-green-300',
  };

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${statusConfig[status]}`}>
      {status}
    </span>
  );
};

export default StatusBadge;