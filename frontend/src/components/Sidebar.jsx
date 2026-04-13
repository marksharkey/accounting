import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Menu,
  X,
  LayoutDashboard,
  FileText,
  Plus,
  Users,
  DollarSign,
  Package,
  BarChart3,
  Settings,
  LogOut,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

const NavSection = ({ label, items, isCollapsed, isDrawer = false }) => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="mb-6">
      {!isCollapsed && !isDrawer && (
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-4">
          {label}
        </p>
      )}
      <div className="space-y-1">
        {items.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <button
              key={item.href}
              onClick={() => navigate(item.href)}
              title={isCollapsed && !isDrawer ? item.label : ''}
              className={`
                w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
                ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600'
                    : 'text-gray-700 hover:bg-gray-100'
                }
                ${isCollapsed && !isDrawer ? 'justify-center px-2' : ''}
              `}
            >
              <item.icon className={`flex-shrink-0 ${isCollapsed && !isDrawer ? 'w-6 h-6' : 'w-5 h-5'}`} />
              {!isCollapsed && (
                <span className="text-sm font-medium">{item.label}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default function Sidebar() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  // Handle responsive behavior
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsCollapsed(false);
        setIsDrawerOpen(false);
      } else if (window.innerWidth >= 768) {
        setIsCollapsed(true);
        setIsDrawerOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
    setIsDrawerOpen(false);
  };

  const billingItems = [
    { label: 'Invoices', href: '/invoices', icon: FileText },
    { label: 'New Invoice', href: '/invoices/new', icon: Plus },
    { label: 'Credit Memo', href: '/credit-memos/new', icon: DollarSign },
  ];

  const clientsItems = [
    { label: 'Clients', href: '/clients', icon: Users },
  ];

  const businessItems = [
    { label: 'Expenses', href: '/expenses', icon: DollarSign },
    { label: 'Service Catalog', href: '/service-catalog', icon: Package },
  ];

  const insightsItems = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Reports', href: '/reports', icon: BarChart3 },
  ];

  const accountItems = [
    { label: 'Settings', href: '/settings/company', icon: Settings },
  ];

  // Desktop & Tablet Sidebar
  const sidebarContent = (
    <>
      {/* Logo/Brand */}
      <div className="px-4 py-6 border-b">
        <h1 className={`font-bold text-blue-700 ${isCollapsed ? 'text-center text-lg' : 'text-xl'}`}>
          {isCollapsed ? 'PP' : 'PrecisionPros'}
        </h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-6 space-y-2 overflow-y-auto">
        <NavSection label="Billing" items={billingItems} isCollapsed={isCollapsed} />
        <NavSection label="Clients" items={clientsItems} isCollapsed={isCollapsed} />
        <NavSection label="Business" items={businessItems} isCollapsed={isCollapsed} />
        <NavSection label="Insights" items={insightsItems} isCollapsed={isCollapsed} />
        <NavSection label="Account" items={accountItems} isCollapsed={isCollapsed} />
      </nav>

      {/* User Info & Logout */}
      <div className="border-t p-4">
        {!isCollapsed && (
          <p className="text-sm font-medium text-gray-900 truncate mb-3">
            {user?.username}
          </p>
        )}
        <button
          onClick={handleLogout}
          className={`
            w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors
            text-gray-700 hover:bg-gray-100
            ${isCollapsed ? 'justify-center px-2' : ''}
          `}
          title={isCollapsed ? 'Logout' : ''}
        >
          <LogOut className={`flex-shrink-0 ${isCollapsed ? 'w-5 h-5' : 'w-5 h-5'}`} />
          {!isCollapsed && (
            <span className="text-sm font-medium">Logout</span>
          )}
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop: Fixed Sidebar (1024px+) */}
      <aside className="hidden lg:flex fixed left-0 top-0 w-56 h-screen bg-white border-r border-gray-200 flex-col z-50">
        {sidebarContent}
      </aside>

      {/* Tablet: Collapsed Sidebar (768px - 1023px) */}
      <aside className="hidden md:flex lg:hidden fixed left-0 top-0 w-16 h-screen bg-white border-r border-gray-200 flex-col z-50">
        {sidebarContent}
      </aside>

      {/* Mobile: Hamburger Menu & Drawer (< 768px) */}
      <div className="md:hidden flex items-center gap-2 bg-white border-b border-gray-200 px-4 py-4">
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="text-gray-700 hover:text-gray-900"
          aria-label="Open menu"
        >
          <Menu className="w-6 h-6" />
        </button>
        <h1 className="text-lg font-bold text-blue-700 ml-2">PrecisionPros</h1>
      </div>

      {/* Mobile Drawer Overlay */}
      {isDrawerOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={() => setIsDrawerOpen(false)}
        />
      )}

      {/* Mobile Drawer */}
      <div
        className={`
          fixed left-0 top-0 h-screen w-64 bg-white transform transition-transform z-50 md:hidden
          ${isDrawerOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex items-center justify-between px-4 py-4 border-b">
          <h1 className="font-bold text-xl text-blue-700">PrecisionPros</h1>
          <button
            onClick={() => setIsDrawerOpen(false)}
            className="text-gray-700 hover:text-gray-900"
            aria-label="Close menu"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
        <nav className="flex-1 px-3 py-6 space-y-2 overflow-y-auto">
          <NavSection label="Billing" items={billingItems} isCollapsed={false} isDrawer />
          <NavSection label="Clients" items={clientsItems} isCollapsed={false} isDrawer />
          <NavSection label="Business" items={businessItems} isCollapsed={false} isDrawer />
          <NavSection label="Insights" items={insightsItems} isCollapsed={false} isDrawer />
          <NavSection label="Account" items={accountItems} isCollapsed={false} isDrawer />
        </nav>
        <div className="border-t p-4">
          <p className="text-sm font-medium text-gray-900 truncate mb-3">
            {user?.username}
          </p>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors text-gray-700 hover:bg-gray-100"
          >
            <LogOut className="w-5 h-5" />
            <span className="text-sm font-medium">Logout</span>
          </button>
        </div>
      </div>
    </>
  );
}
