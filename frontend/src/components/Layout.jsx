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
              <nav className="flex flex-wrap gap-3 items-center">
                <a href="/dashboard" className="text-gray-700 hover:text-gray-900 whitespace-nowrap">
                  Dashboard
                </a>
                <a href="/clients" className="text-gray-700 hover:text-gray-900 whitespace-nowrap">
                  Clients
                </a>
                <a href="/invoices" className="text-gray-700 hover:text-gray-900 whitespace-nowrap">
                  Invoices
                </a>
                <a href="/invoices/new" className="text-gray-700 hover:text-gray-900 whitespace-nowrap">
                  New Invoice
                </a>
                <a href="/credit-memos/new" className="text-gray-700 hover:text-gray-900 whitespace-nowrap">
                  Credit Memo
                </a>
                <a href="/service-catalog" className="text-gray-700 hover:text-gray-900">
                  Service Catalog
                </a>
                <a href="/expenses" className="text-gray-700 hover:text-gray-900 whitespace-nowrap">
                  Expenses
                </a>
                <a href="/reports" className="text-gray-700 hover:text-gray-900 whitespace-nowrap">
                  Reports
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
