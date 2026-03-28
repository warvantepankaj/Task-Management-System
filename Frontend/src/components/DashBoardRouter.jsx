import { useAuth } from '../hooks/useAuth';
import AdminDashboard from '../pages/Dashboard';
import Dashboard from '../pages/Dashboard';

const DashboardRouter = () => {
  const { user } = useAuth();
  
  // Route to appropriate dashboard based on user role
  if (user?.role === 'admin') {
    return <AdminDashboard   />;
  }
  
  return <Dashboard />;
};

export default DashboardRouter;