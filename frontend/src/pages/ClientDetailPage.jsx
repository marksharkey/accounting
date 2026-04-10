import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';

export default function ClientDetailPage() {
  const { id } = useParams();

  const { data: client, isLoading: clientLoading } = useQuery({
    queryKey: ['clients', id],
    queryFn: async () => {
      const response = await apiClient.get(`/clients/${id}`);
      return response.data;
    },
  });

  const { data: schedules, isLoading: schedulesLoading } = useQuery({
    queryKey: ['clients', id, 'schedules'],
    queryFn: async () => {
      const response = await apiClient.get(`/clients/${id}/billing-schedules`);
      return response.data;
    },
  });

  const { data: invoices, isLoading: invoicesLoading } = useQuery({
    queryKey: ['clients', id, 'invoices'],
    queryFn: async () => {
      const response = await apiClient.get(`/clients/${id}/invoices`);
      return response.data;
    },
  });

  const { data: activity, isLoading: activityLoading } = useQuery({
    queryKey: ['clients', id, 'activity'],
    queryFn: async () => {
      const response = await apiClient.get(`/clients/${id}/activity`);
      return response.data;
    },
  });

  const isLoading = clientLoading || schedulesLoading || invoicesLoading || activityLoading;

  if (isLoading) {
    return <Layout title="Client Detail">Loading...</Layout>;
  }

  if (!client) {
    return <Layout title="Client Detail">Client not found</Layout>;
  }

  return (
    <Layout title={client.name}>
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-600 text-sm font-medium">Account Balance</h3>
          <p
            className={`text-3xl font-bold mt-2 ${
              client.account_balance < 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            ${Math.abs(client.account_balance).toFixed(2)}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-600 text-sm font-medium">Billing Type</h3>
          <p className="text-2xl font-bold mt-2">{client.billing_type}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-600 text-sm font-medium">Status</h3>
          <p className="text-2xl font-bold mt-2">{client.account_status || 'Active'}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Billing Schedules</h3>
          {schedules && schedules.length > 0 ? (
            <ul className="space-y-2">
              {schedules.map((schedule) => (
                <li key={schedule.id} className="text-sm text-gray-600 border-b pb-2">
                  {schedule.service_name} - ${schedule.amount} / {schedule.billing_cycle}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No billing schedules</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Invoices</h3>
          {invoices && invoices.length > 0 ? (
            <ul className="space-y-2">
              {invoices.slice(0, 5).map((invoice) => (
                <li key={invoice.id} className="text-sm text-gray-600 border-b pb-2">
                  {invoice.number} - ${invoice.total} ({invoice.status})
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No invoices</p>
          )}
        </div>
      </div>

      <div className="mt-6 bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Activity Log</h3>
        {activity && activity.length > 0 ? (
          <ul className="space-y-2">
            {activity.slice(0, 10).map((log) => (
              <li key={log.id} className="text-sm text-gray-600 border-b pb-2">
                {log.action} - {new Date(log.timestamp).toLocaleDateString()}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">No activity</p>
        )}
      </div>
    </Layout>
  );
}
