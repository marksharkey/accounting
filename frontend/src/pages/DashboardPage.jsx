import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';

export default function DashboardPage() {
  const { data: reports, isLoading: reportsLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: async () => {
      const [arAging, recurringRevenue] = await Promise.all([
        apiClient.get('/reports/ar-aging'),
        apiClient.get('/reports/recurring-revenue'),
      ]);
      return {
        arAging: arAging.data,
        recurringRevenue: recurringRevenue.data,
      };
    },
  });

  const { data: dueBilling, isLoading: dueLoading } = useQuery({
    queryKey: ['invoices', 'due-for-billing'],
    queryFn: async () => {
      const response = await apiClient.get('/invoices/due-for-billing', {
        params: { days_ahead: 7 },
      });
      return response.data;
    },
  });

  const { data: dailyQueue, isLoading: queueLoading } = useQuery({
    queryKey: ['collections', 'daily-queue'],
    queryFn: async () => {
      const response = await apiClient.get('/collections/daily-queue');
      return response.data;
    },
  });

  const isLoading = reportsLoading || dueLoading || queueLoading;

  if (isLoading) {
    return <Layout title="Dashboard">Loading...</Layout>;
  }

  return (
    <Layout title="Dashboard">
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-600 text-sm font-medium">Overdue Amount</h3>
          <p className="text-3xl font-bold text-red-600 mt-2">
            ${reports?.arAging?.overdue || 0}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-600 text-sm font-medium">MRR</h3>
          <p className="text-3xl font-bold text-blue-600 mt-2">
            ${reports?.recurringRevenue?.mrr || 0}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-600 text-sm font-medium">ARR</h3>
          <p className="text-3xl font-bold text-green-600 mt-2">
            ${reports?.recurringRevenue?.arr || 0}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Daily Action Queue</h3>
          {dailyQueue && dailyQueue.length > 0 ? (
            <ul className="space-y-2">
              {dailyQueue.slice(0, 5).map((item) => (
                <li key={item.id} className="text-sm text-gray-600 border-b pb-2">
                  {item.action} - {item.client_name}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No items in queue</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Due for Billing</h3>
          {dueBilling && dueBilling.length > 0 ? (
            <ul className="space-y-2">
              {dueBilling.slice(0, 5).map((client) => (
                <li key={client.id} className="text-sm text-gray-600 border-b pb-2">
                  {client.name} - {client.billing_type}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No clients due</p>
          )}
        </div>
      </div>
    </Layout>
  );
}
