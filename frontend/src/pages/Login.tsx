import { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const { login, isAuthenticated, role, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated && role && !isLoading) {
      navigate(`/${role}`);
    }
  }, [isAuthenticated, role, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fcfcfc] text-black">
        <p className="text-gray-500 animate-pulse">Checking authentication status...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#fcfcfc] text-black">
      <div className="max-w-md w-full p-8 bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 animate-slide-up">
        <div className="text-center mb-8">
          <div className="w-24 h-24 rounded-2xl mx-auto flex items-center justify-center mb-4 shadow-sm overflow-hidden bg-skyblue-50 p-4">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed=AegisAI&backgroundColor=0ea5e9" alt="Aegis AI Logo" className="w-full h-full object-contain rounded-xl" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Welcome to Aegis AI</h1>
          <p className="text-gray-500 mt-2 text-sm">Secure Authentication via Auth0</p>
        </div>

        <div className="space-y-4">
          <button 
            onClick={login}
            className="w-full flex items-center justify-center gap-2 p-4 bg-black text-white rounded-xl hover:bg-gray-900 transition-colors shadow-sm font-medium"
          >
            Sign In with Auth0
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;
