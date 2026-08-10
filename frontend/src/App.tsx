import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import DashboardLayout from './components/DashboardLayout';
import DeveloperDashboard from './pages/DeveloperDashboard';
import ManagerDashboard from './pages/ManagerDashboard';
import Login from './pages/Login';

// A wrapper for protecting routes based on role
const ProtectedRoute = ({ children, allowedRole }: { children: React.ReactNode, allowedRole: 'developer' | 'manager' }) => {
  const { role, isLoading, isAuthenticated } = useAuth();
  if (isLoading) return <div className="h-screen w-full flex items-center justify-center">Loading authentication...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (role !== allowedRole) return <Navigate to={`/${role || 'login'}`} replace />;
  return <>{children}</>;
};

// Redirect root based on role
const RootRedirect = () => {
  const { role, isLoading, isAuthenticated } = useAuth();
  if (isLoading) return <div className="h-screen w-full flex items-center justify-center">Loading authentication...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={`/${role || 'login'}`} replace />;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<DashboardLayout />}>
        <Route index element={<RootRedirect />} />
        
        <Route path="developer" element={
          <ProtectedRoute allowedRole="developer">
            <DeveloperDashboard />
          </ProtectedRoute>
        } />
        
        <Route path="manager" element={
          <ProtectedRoute allowedRole="manager">
            <ManagerDashboard />
          </ProtectedRoute>
        } />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
