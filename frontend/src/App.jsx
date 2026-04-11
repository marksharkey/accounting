import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { useAuthStore } from './store/authStore';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ClientsListPage from './pages/ClientsListPage';
import ClientDetailPage from './pages/ClientDetailPage';
import InvoiceBuilderPage from './pages/InvoiceBuilderPage';
import InvoiceDetailPage from './pages/InvoiceDetailPage';
import InvoiceListPage from './pages/InvoiceListPage';
import CreditMemoBuilderPage from './pages/CreditMemoBuilderPage';
import ServiceCatalogPage from './pages/ServiceCatalogPage';
import ExpensesPage from './pages/ExpensesPage';
import ReportsPage from './pages/ReportsPage';
import CompanySettingsPage from './pages/CompanySettingsPage';
import './App.css';

const queryClient = new QueryClient();

function ProtectedRoute({ children }) {
  const token = useAuthStore((state) => state.token);
  const isLoading = useAuthStore((state) => state.isLoading);

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return token ? children : <Navigate to="/login" replace />;
}

function App() {
  const token = useAuthStore((state) => state.token);
  const me = useAuthStore((state) => state.me);

  useEffect(() => {
    if (token) {
      me().catch(() => {
        // Token is invalid, will be cleared by the auth store
      });
    }
  }, [token, me]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients"
            element={
              <ProtectedRoute>
                <ClientsListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients/:id"
            element={
              <ProtectedRoute>
                <ClientDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invoices"
            element={
              <ProtectedRoute>
                <InvoiceListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invoices/new"
            element={
              <ProtectedRoute>
                <InvoiceBuilderPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invoices/:id"
            element={
              <ProtectedRoute>
                <InvoiceDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/credit-memos/new"
            element={
              <ProtectedRoute>
                <CreditMemoBuilderPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/service-catalog"
            element={
              <ProtectedRoute>
                <ServiceCatalogPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/expenses"
            element={
              <ProtectedRoute>
                <ExpensesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                <ReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings/company"
            element={
              <ProtectedRoute>
                <CompanySettingsPage />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
