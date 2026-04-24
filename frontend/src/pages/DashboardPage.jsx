import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/Table';

function formatCurrency(value) {
  const num = parseFloat(value) || 0;
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function CategoryBadge({ category }) {
  const variants = {
    invoiced_and_due: 'bg-blue-100 text-blue-700',
    past_due: 'bg-red-100 text-red-700',
    suspension: 'bg-amber-100 text-amber-700',
    termination: 'bg-red-100 text-red-700',
  };

  const labels = {
    invoiced_and_due: 'Due Today',
    past_due: 'Past Due',
    suspension: 'Suspension',
    termination: 'Termination',
  };

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${variants[category]}`}>
      {labels[category]}
    </span>
  );
}

function KPIBar({ navigate, data, isLoading }) {
  const mrr = data?.monthly_recurring_revenue || 0;
  const arr = data?.annual_recurring_revenue || 0;

  if (isLoading) {
    return <div className="h-16 bg-gray-50 animate-pulse mb-4 rounded" />;
  }

  return (
    <div className="mb-4 flex items-center justify-between text-sm border-b border-gray-200 pb-3">
      <div className="flex items-center gap-6">
        <div>
          <div className="text-xs text-gray-500 uppercase font-medium tracking-wide">MRR</div>
          <div className="text-base font-semibold text-gray-900">${formatCurrency(mrr)}</div>
        </div>
        <div className="h-6 w-px bg-gray-300" />
        <div>
          <div className="text-xs text-gray-500 uppercase font-medium tracking-wide">ARR</div>
          <div className="text-base font-semibold text-gray-900">${formatCurrency(arr)}</div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div
          onClick={() => navigate('/invoices?status=open')}
          className="cursor-pointer hover:text-blue-600"
        >
          <div className="text-xs text-gray-500 uppercase font-medium tracking-wide">Open Invoices</div>
          <div className="text-base font-semibold text-gray-900">{data?.open_invoice_count || 0}</div>
        </div>
        <div className="h-6 w-px bg-gray-300" />
        <div
          onClick={() => navigate('/invoices?status=overdue')}
          className="cursor-pointer hover:text-red-600"
        >
          <div className="text-xs text-gray-500 uppercase font-medium tracking-wide">Past Due</div>
          <div className="text-base font-semibold text-red-600">{data?.past_due_count || 0}</div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const { data: recurringRevenue, isLoading: revenueLoading } = useQuery({
    queryKey: ['reports', 'recurring-revenue'],
    queryFn: async () => {
      const response = await apiClient.get('/reports/recurring-revenue');
      return response.data;
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
      return response.data || {
        invoiced_and_due: [],
        past_due: [],
        suspension_candidates: [],
        termination_candidates: [],
      };
    },
  });

  // Build action items from all invoice queues
  const actionItems = [];
  if (dailyQueue) {
    dailyQueue.invoiced_and_due?.forEach((inv) => {
      actionItems.push({
        ...inv,
        category: 'invoiced_and_due',
      });
    });
    dailyQueue.past_due?.forEach((inv) => {
      actionItems.push({
        ...inv,
        category: 'past_due',
      });
    });
    dailyQueue.suspension_candidates?.forEach((inv) => {
      actionItems.push({
        ...inv,
        category: 'suspension',
      });
    });
    dailyQueue.termination_candidates?.forEach((inv) => {
      actionItems.push({
        ...inv,
        category: 'termination',
      });
    });
  }

  // Sort by days_overdue descending
  actionItems.sort((a, b) => (b.days_overdue || 0) - (a.days_overdue || 0));

  const dueBillingList = dueBilling || [];

  // Enrich KPI data with counts from queue
  const kpiData = {
    ...recurringRevenue,
    open_invoice_count: (dailyQueue?.invoiced_and_due?.length || 0),
    past_due_count: (dailyQueue?.past_due?.length || 0),
  };

  return (
    <Layout title="Dashboard">
      {/* KPI Bar */}
      <KPIBar navigate={navigate} data={kpiData} isLoading={revenueLoading} />

      {/* Action Items Table */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Action Items</CardTitle>
        </CardHeader>
        <CardContent>
          {queueLoading ? (
            <div className="h-32 bg-gray-50 animate-pulse rounded" />
          ) : actionItems.length === 0 ? (
            <div className="text-center text-gray-500 text-sm py-8">
              No action items today
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Client</TableHead>
                    <TableHead>Invoice #</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Days Overdue</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {actionItems.map((item, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="text-gray-900">{item.client_name}</TableCell>
                      <TableCell className="text-gray-900">{item.invoice_number}</TableCell>
                      <TableCell className="text-gray-900">
                        ${formatCurrency(item.balance_due)}
                      </TableCell>
                      <TableCell className="text-gray-900">{item.days_overdue || 0}</TableCell>
                      <TableCell>
                        <CategoryBadge category={item.category} />
                      </TableCell>
                      <TableCell>
                        <button
                          onClick={() => navigate(`/invoices`)}
                          className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                        >
                          View
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Due for Billing Table */}
      <Card>
        <CardHeader>
          <CardTitle>Due for Billing</CardTitle>
        </CardHeader>
        <CardContent>
          {dueLoading ? (
            <div className="h-32 bg-gray-50 animate-pulse rounded" />
          ) : dueBillingList.length === 0 ? (
            <div className="text-center text-gray-500 text-sm py-8">
              No clients due for billing
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Client</TableHead>
                    <TableHead>Billing Type</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Next Bill Date</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dueBillingList.map((item, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="text-gray-900">
                        {item.client.display_name}
                      </TableCell>
                      <TableCell className="text-gray-900">
                        {item.client.autocc_recurring ? 'Auto-charge' : 'Fixed recurring'}
                      </TableCell>
                      <TableCell className="text-gray-900">
                        ${formatCurrency(
                          item.schedules && item.schedules.length > 0 ? item.schedules[0].amount : 0
                        )}
                      </TableCell>
                      <TableCell className="text-gray-900">
                        {item.schedules && item.schedules.length > 0
                          ? new Date(item.schedules[0].next_billing_date).toLocaleDateString()
                          : '—'}
                      </TableCell>
                      <TableCell>
                        <button
                          onClick={() => navigate(`/clients/${item.client.id}`)}
                          className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                        >
                          View
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
