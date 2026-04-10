import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';

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
      return response.data || { late_fee_candidates: [], suspension_candidates: [], deletion_candidates: [] };
    },
  });

  const isLoading = reportsLoading || dueLoading || queueLoading;

  if (isLoading) {
    return <Layout title="Dashboard">Loading...</Layout>;
  }

  return (
    <Layout title="Dashboard">
      <div className="grid grid-cols-3 gap-6 mb-8">
        <Card>
          <CardContent className="pt-6">
            <CardDescription className="text-gray-600 text-sm font-medium">
              Overdue Amount
            </CardDescription>
            <p className="text-3xl font-bold text-red-600 mt-2">
              ${reports?.arAging?.totals?.over_90 || 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <CardDescription className="text-gray-600 text-sm font-medium">
              MRR
            </CardDescription>
            <p className="text-3xl font-bold text-blue-600 mt-2">
              ${reports?.recurringRevenue?.mrr?.toFixed(2) || '0.00'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <CardDescription className="text-gray-600 text-sm font-medium">
              ARR
            </CardDescription>
            <p className="text-3xl font-bold text-green-600 mt-2">
              ${reports?.recurringRevenue?.arr?.toFixed(2) || '0.00'}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Daily Action Queue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {dailyQueue?.late_fee_candidates && dailyQueue.late_fee_candidates.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-red-600">Late Fees ({dailyQueue.late_fee_candidates.length})</p>
                  <ul className="space-y-1 mt-1">
                    {dailyQueue.late_fee_candidates.slice(0, 3).map((item) => (
                      <li key={item.id} className="text-xs text-gray-600">
                        {item.client_name} - Invoice {item.invoice_number}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {dailyQueue?.suspension_candidates && dailyQueue.suspension_candidates.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-orange-600">Suspension ({dailyQueue.suspension_candidates.length})</p>
                  <ul className="space-y-1 mt-1">
                    {dailyQueue.suspension_candidates.slice(0, 3).map((item) => (
                      <li key={item.id} className="text-xs text-gray-600">
                        {item.client_name}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!dailyQueue?.late_fee_candidates?.length && !dailyQueue?.suspension_candidates?.length && (
                <p className="text-sm text-gray-500">No pending actions</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Due for Billing (Next 7 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            {dueBilling && dueBilling.length > 0 ? (
              <ul className="space-y-2">
                {dueBilling.slice(0, 5).map((item) => (
                  <li key={item.client.id} className="text-sm text-gray-600 border-b pb-2">
                    {item.client.company_name} - {item.client.billing_type}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No clients due</p>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
