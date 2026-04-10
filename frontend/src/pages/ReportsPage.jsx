import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

export default function ReportsPage() {
  const { data: reportsData, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: async () => {
      const response = await apiClient.get('/reports/');
      return response.data;
    },
  });

  if (isLoading) {
    return <Layout title="Reports">Loading...</Layout>;
  }

  return (
    <Layout title="Reports">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Revenue by Period</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">Detailed revenue breakdown by time period</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Accounts Receivable Aging</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">Outstanding invoices grouped by aging period</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Profit & Loss</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">Income and expense summary by category</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Collections</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">Collections events and overdue account tracking</p>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
