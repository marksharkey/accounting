import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { formatBillingType } from '../utils/formatting';

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
        <Card>
          <CardContent className="pt-6">
            <p className="text-gray-600 text-sm font-medium mb-2">Account Balance</p>
            <p
              className={`text-3xl font-bold ${
                client.account_balance < 0 ? 'text-green-600' : 'text-red-600'
              }`}
            >
              ${Math.abs(client.account_balance).toFixed(2)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-gray-600 text-sm font-medium mb-2">Billing Type</p>
            <p className="text-2xl font-bold">{formatBillingType(client.billing_type)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-gray-600 text-sm font-medium mb-2">Status</p>
            <p className="text-2xl font-bold">{client.account_status || 'Active'}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Billing Schedules</CardTitle>
          </CardHeader>
          <CardContent>
            {schedules && schedules.length > 0 ? (
              <ul className="space-y-2">
                {schedules.map((schedule) => (
                  <li key={schedule.id} className="text-sm text-gray-600 border-b pb-2">
                    {schedule.description || schedule.service_name} — ${schedule.amount} / {schedule.cycle || schedule.billing_cycle}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No billing schedules</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Invoices</CardTitle>
          </CardHeader>
          <CardContent>
            {invoices && invoices.length > 0 ? (
              <ul className="space-y-2">
                {invoices.slice(0, 5).map((invoice) => (
                  <li key={invoice.id} className="text-sm text-gray-600 border-b pb-2">
                    {invoice.invoice_number || invoice.number} — ${invoice.total} ({invoice.status})
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No invoices</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">Activity Log</CardTitle>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>
    </Layout>
  );
}
