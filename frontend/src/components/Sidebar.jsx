import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Menu,
  X,
  LayoutDashboard,
  FileText,
  Users,
  UserCog,
  DollarSign,
  Package,
  BarChart3,
  Settings,
  LogOut,
  Zap,
  Mail,
  Globe,
  CreditCard,
  CheckSquare,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

const NavSection = ({ items, isCollapsed, isDrawer = false }) => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="mb-4">
      {/* Headers removed */}
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
    { label: 'AutoCC Batch', href: '/autocc-batch', icon: Zap },
  ];

  const clientsItems = [
    { label: 'Clients', href: '/clients', icon: Users },
    { label: 'Domains', href: '/domains', icon: Globe },
  ];

  const businessItems = [
    { label: 'Expenses', href: '/expenses', icon: DollarSign },
    { label: 'Service Catalog', href: '/service-catalog', icon: Package },
  ];

  const insightsItems = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Reports', href: '/reports', icon: BarChart3 },
  ];

  const accountingItems = [
    { label: 'Check Register', href: '/check-register', icon: CheckSquare },
  ];

  const accountItems = [
    { label: 'Settings', href: '/settings/company', icon: Settings },
    { label: 'Email Templates', href: '/settings/email-templates', icon: Mail },
    ...(user?.is_admin ? [{ label: 'Users', href: '/settings/users', icon: UserCog }] : []),
  ];

  // Desktop & Tablet Sidebar
  const sidebarContent = (
    <>
      {/* Navigation */}
      <nav className="flex-1 px-3 py-6 space-y-2 overflow-y-auto">
        <NavSection items={billingItems} isCollapsed={isCollapsed} />
        <NavSection items={clientsItems} isCollapsed={isCollapsed} />
        <NavSection items={businessItems} isCollapsed={isCollapsed} />
        <NavSection items={insightsItems} isCollapsed={isCollapsed} />
        <NavSection items={accountingItems} isCollapsed={isCollapsed} />
        <NavSection items={accountItems} isCollapsed={isCollapsed} />
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
      <aside className="hidden lg:flex fixed left-0 top-0 h-screen bg-white border-r border-gray-200 flex-col z-50" style={{ width: 'var(--sidebar-width-desktop)' }}>
        {sidebarContent}
      </aside>

      {/* Tablet: Collapsed Sidebar (768px - 1023px) */}
      <aside className="hidden md:flex lg:hidden fixed left-0 top-0 h-screen bg-white border-r border-gray-200 flex-col z-50" style={{ width: 'var(--sidebar-width-tablet)' }}>
        {sidebarContent}
      </aside>

      {/* Mobile: Hamburger Menu & Drawer (< 768px) */}
      <div className="md:hidden flex items-center gap-3 bg-white border-b border-gray-200 px-4 py-4">
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="text-gray-700 hover:text-gray-900"
          aria-label="Open menu"
        >
          <Menu className="w-6 h-6" />
        </button>
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
          <button
            onClick={() => setIsDrawerOpen(false)}
            className="text-gray-700 hover:text-gray-900"
            aria-label="Close menu"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
        <nav className="flex-1 px-3 py-6 space-y-2 overflow-y-auto">
          <NavSection items={billingItems} isCollapsed={false} isDrawer />
          <NavSection items={clientsItems} isCollapsed={false} isDrawer />
          <NavSection items={businessItems} isCollapsed={false} isDrawer />
          <NavSection items={insightsItems} isCollapsed={false} isDrawer />
          <NavSection items={accountItems} isCollapsed={false} isDrawer />
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
