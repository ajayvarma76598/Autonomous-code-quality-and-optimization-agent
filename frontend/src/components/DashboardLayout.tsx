import { NavLink, Outlet } from 'react-router-dom';
import { Activity, Search, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const DashboardLayout = () => {
  const { role, logout, user } = useAuth();


  const handleLogout = () => {
    logout();
  };

  return (
    <div className="flex h-screen w-full bg-white text-black overflow-hidden selection:bg-skyblue-100">
      
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-100 flex flex-col bg-white z-10 shadow-sm relative">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl overflow-hidden flex items-center justify-center shadow-sm bg-skyblue-50 p-1">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed=AegisAI&backgroundColor=0ea5e9" alt="Aegis AI Logo" className="w-full h-full object-contain rounded-lg" />
          </div>
          <span className="font-bold text-xl tracking-tight">Aegis AI</span>
        </div>
        
        <nav className="flex-1 px-4 space-y-1">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4 mt-4 px-2">Workspaces</div>
          
          {role === 'developer' && (
            <NavLink 
              to="/developer" 
              className={({isActive}) => `flex items-center gap-3 px-3 py-2.5 rounded-md transition-all duration-200 ${isActive ? 'bg-skyblue-50 text-skyblue-600 font-medium' : 'text-gray-600 hover:bg-gray-50 hover:text-black'}`}
            >
              <Search size={18} />
              Developer
            </NavLink>
          )}
          
          {role === 'manager' && (
            <NavLink 
              to="/manager" 
              className={({isActive}) => `flex items-center gap-3 px-3 py-2.5 rounded-md transition-all duration-200 ${isActive ? 'bg-skyblue-50 text-skyblue-600 font-medium' : 'text-gray-600 hover:bg-gray-50 hover:text-black'}`}
            >
              <Activity size={18} />
              Manager
            </NavLink>
          )}
        </nav>
        
        <div className="p-4 border-t border-gray-50">
          <div className="flex items-center gap-3 px-2 py-2 mb-2">
            {user?.picture ? (
              <img src={user.picture} alt="Avatar" referrerPolicy="no-referrer" className="w-8 h-8 rounded-full shadow-sm object-cover" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-skyblue-400 to-blue-500 shadow-sm"></div>
            )}
            <div>
              <p className="text-sm font-medium line-clamp-1">{user?.name || (role === 'developer' ? 'Alex Developer' : 'Sam Manager')}</p>
              <p className="text-xs text-gray-500 capitalize">{role} Role</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative bg-[#fcfcfc] overflow-y-auto animate-fade-in">
        <div className="p-8 max-w-7xl mx-auto w-full">
          <Outlet />
        </div>
      </main>
      
    </div>
  );
};

export default DashboardLayout;
