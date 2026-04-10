import { useAuthStore } from '../store/authStore';
import { useNavigate } from 'react-router-dom';

export default function Layout({ children, title }) {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold">PrecisionPros</h1>
            </div>
            <div className="flex items-center space-x-4">
              <nav className="space-x-4">
                <a href="/dashboard" className="text-gray-700 hover:text-gray-900">
                  Dashboard
                </a>
                <a href="/clients" className="text-gray-700 hover:text-gray-900">
                  Clients
                </a>
              </nav>
              <span className="text-sm text-gray-600">{user?.username}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-700 hover:text-gray-900"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {title && <h2 className="text-2xl font-bold mb-6">{title}</h2>}
        {children}
      </div>
    </div>
  );
}
