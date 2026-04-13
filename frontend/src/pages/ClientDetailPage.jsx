import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import Button from '../components/ui/Button';
import AddBillingScheduleModal from '../components/AddBillingScheduleModal';
import EditClientModal from '../components/EditClientModal';
import { formatBillingType } from '../utils/formatting';

export default function ClientDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [isAddScheduleOpen, setIsAddScheduleOpen] = useState(false);
  const [isEditClientOpen, setIsEditClientOpen] = useState(false);

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

  const { data: allClients } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const response = await apiClient.get('/clients');
      return response.data?.items || response.data || [];
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
      <div className="mb-6">
        <div className="flex items-center gap-2">
          <label htmlFor="client-select" className="text-sm font-medium text-gray-700">
            Client:
          </label>
          <select
            id="client-select"
            value={id}
            onChange={(e) => navigate(`/clients/${e.target.value}`)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {allClients && allClients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.company_name}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            onClick={() => setIsEditClientOpen(true)}
          >
            Edit
          </Button>
        </div>
      </div>

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
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Billing Schedules</CardTitle>
            <Button size="sm" onClick={() => setIsAddScheduleOpen(true)}>Add</Button>
          </CardHeader>
          <CardContent>
            {schedules && schedules.length > 0 ? (
              <div className="space-y-4">
                {schedules.map((schedule) => (
                  <div key={schedule.id} className="border-b pb-3 last:border-b-0">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="font-medium text-gray-900">{schedule.cycle.replace('_', '-').toUpperCase()}</p>
                        <p className="text-xs text-gray-500">Next: {new Date(schedule.next_bill_date).toLocaleDateString()}</p>
                        {schedule.notes && (
                          <p className="text-xs text-gray-600 mt-1">{schedule.notes}</p>
                        )}
                      </div>
                      <p className="text-lg font-bold text-gray-900">${parseFloat(schedule.amount).toFixed(2)}</p>
                    </div>
                    {schedule.line_items && schedule.line_items.length > 0 && (
                      <ul className="space-y-1 ml-2">
                        {schedule.line_items.map((item) => (
                          <li key={item.id} className="text-xs text-gray-600">
                            {item.description} × {parseFloat(item.quantity).toFixed(2)} = ${parseFloat(item.amount).toFixed(2)}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
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
                    <Link
                      to={`/invoices/${invoice.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {invoice.invoice_number || invoice.number}
                    </Link>
                    {' '} — ${invoice.total} ({invoice.status})
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
            <ul className="space-y-3">
              {activity.slice(0, 10).map((log) => {
                const getActivityLink = () => {
                  if (log.entity_type === 'invoice') {
                    return `/invoices/${log.entity_id}`;
                  } else if (log.entity_type === 'credit_memo') {
                    return `/credit-memos/${log.entity_id}`;
                  } else if (log.entity_type === 'payment') {
                    return `/payments/${log.entity_id}`;
                  }
                  return null;
                };

                const getActivityDescription = () => {
                  const timestamp = new Date(log.timestamp);
                  const dateStr = timestamp.toLocaleDateString();
                  const timeStr = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                  const byUser = log.performed_by_name ? ` by ${log.performed_by_name}` : '';

                  let description = '';
                  switch (log.action) {
                    case 'created':
                      description = `Created ${log.entity_type === 'invoice' ? 'Invoice' : log.entity_type === 'credit_memo' ? 'Credit Memo' : log.entity_type === 'payment' ? 'Payment' : 'Record'}`;
                      break;
                    case 'sent':
                      description = `Sent Invoice`;
                      break;
                    case 'resent':
                      description = `Resent Invoice`;
                      break;
                    case 'marked_sent':
                      description = `Marked Invoice as Sent`;
                      break;
                    case 'status_changed':
                      description = `Changed Status: ${log.notes || 'status updated'}`;
                      break;
                    case 'voided':
                      description = `Voided Invoice${log.notes ? ': ' + log.notes : ''}`;
                      break;
                    case 'authnet_verified':
                      description = `Verified Payment (AuthNet)`;
                      break;
                    case 'paid':
                      description = `Marked as Paid`;
                      break;
                    default:
                      description = log.action.replace(/_/g, ' ').charAt(0).toUpperCase() + log.action.slice(1).replace(/_/g, ' ');
                  }

                  return `${description}${byUser} on ${dateStr} at ${timeStr}`;
                };

                const link = getActivityLink();
                const isClickable = link !== null;

                return (
                  <li
                    key={log.id}
                    className={`border-b pb-3 last:border-b-0 ${isClickable ? 'cursor-pointer' : ''}`}
                  >
                    {isClickable ? (
                      <Link
                        to={link}
                        className="text-sm text-blue-600 hover:text-blue-800 hover:underline block"
                      >
                        {getActivityDescription()}
                      </Link>
                    ) : (
                      <p className="text-sm text-gray-700">{getActivityDescription()}</p>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No activity</p>
          )}
        </CardContent>
      </Card>

      <AddBillingScheduleModal
        isOpen={isAddScheduleOpen}
        onClose={() => setIsAddScheduleOpen(false)}
        clientId={id}
      />

      <EditClientModal
        isOpen={isEditClientOpen}
        onClose={() => setIsEditClientOpen(false)}
        client={client}
      />
    </Layout>
  );
}
