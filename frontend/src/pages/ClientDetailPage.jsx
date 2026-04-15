import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useRef } from 'react';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import Button from '../components/ui/Button';
import AddBillingScheduleModal from '../components/AddBillingScheduleModal';
import EditClientModal from '../components/EditClientModal';
import { Plus, Eye, Search, X } from 'lucide-react';

export default function ClientDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isAddScheduleOpen, setIsAddScheduleOpen] = useState(false);
  const [isEditClientOpen, setIsEditClientOpen] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const searchInputRef = useRef(null);

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
    queryKey: ['clients-all'],
    queryFn: async () => {
      const response = await apiClient.get('/clients/', {
        params: { limit: 10000 },
      });
      return response.data?.items || response.data || [];
    },
  });

  const toggleAutoccMutation = useMutation({
    mutationFn: async (newValue) => {
      const response = await apiClient.put(`/clients/${id}`, {
        company_name: client.company_name,
        contact_name: client.contact_name,
        email: client.email,
        email_cc: client.email_cc,
        phone: client.phone,
        address_line1: client.address_line1,
        address_line2: client.address_line2,
        city: client.city,
        state: client.state,
        zip_code: client.zip_code,
        autocc_recurring: newValue,
        autocc_customer_id: client.autocc_customer_id,
        late_fee_type: client.late_fee_type,
        late_fee_amount: client.late_fee_amount,
        late_fee_grace_days: client.late_fee_grace_days,
        collections_exempt: client.collections_exempt,
        auto_send_invoices: client.auto_send_invoices,
        notes: client.notes,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients', id] });
      queryClient.invalidateQueries({ queryKey: ['clients'] });
    },
    onError: (error) => {
      console.error('Failed to toggle AutoCC:', error);
    },
  });

  const handleToggleAutocc = async () => {
    toggleAutoccMutation.mutate(!client.autocc_recurring);
  };

  const isLoading = clientLoading || schedulesLoading || invoicesLoading || activityLoading;

  const handleSearch = () => {
    if (!searchInput.trim()) {
      setSearchResults([]);
      return;
    }

    const query = searchInput.toLowerCase();
    const results = (allClients || []).filter(c => {
      const companyName = c.company_name?.toLowerCase() || '';
      const contactName = c.contact_name?.toLowerCase() || '';
      const email = c.email?.toLowerCase() || '';
      const phone = c.phone?.toLowerCase() || '';
      const address1 = c.address_line1?.toLowerCase() || '';
      const address2 = c.address_line2?.toLowerCase() || '';
      const city = c.city?.toLowerCase() || '';
      const state = c.state?.toLowerCase() || '';
      const zip = c.zip_code?.toLowerCase() || '';

      return (
        companyName.includes(query) ||
        contactName.includes(query) ||
        email.includes(query) ||
        phone.includes(query) ||
        address1.includes(query) ||
        address2.includes(query) ||
        city.includes(query) ||
        state.includes(query) ||
        zip.includes(query)
      );
    });

    setSearchResults(results);
    setIsSearching(true);
  };

  const handleSelectClient = (clientId) => {
    navigate(`/clients/${clientId}`);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearchResults([]);
    setIsSearching(false);
    searchInputRef.current?.focus();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  if (isLoading) {
    return <Layout title="Client Detail">Loading...</Layout>;
  }

  if (!client) {
    return <Layout title="Client Detail">Client not found</Layout>;
  }

  return (
    <Layout title={client.company_name}>
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-sm font-medium text-gray-700">
            Client: <span className="font-semibold text-gray-900">{client?.company_name}</span>
          </span>
          <Button
            size="sm"
            onClick={() => setIsEditClientOpen(true)}
          >
            Edit
          </Button>
        </div>

        <div className="relative">
          <div className="flex gap-2">
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search by name, email, address..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyPress={handleKeyPress}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
              autoComplete="off"
            />
            <button
              onClick={handleSearch}
              className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm flex items-center gap-1"
            >
              <Search className="w-4 h-4" />
              Search
            </button>
            {isSearching && (
              <button
                onClick={handleClearSearch}
                className="px-3 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-md text-sm flex items-center gap-1"
              >
                <X className="w-4 h-4" />
                Clear
              </button>
            )}
          </div>

          {isSearching && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-300 rounded-md shadow-lg z-50 max-h-64 overflow-y-auto">
              {searchResults.length > 0 ? (
                searchResults.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => handleSelectClient(c.id)}
                    className={`w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-blue-50 transition-colors ${
                      c.id === parseInt(id) ? 'bg-blue-100 font-medium' : ''
                    }`}
                  >
                    <div className="font-medium">{c.company_name}</div>
                    <div className="text-xs text-gray-600">
                      {c.contact_name && <div>{c.contact_name}</div>}
                      {c.email && <div>{c.email}</div>}
                      {c.city && <div>{c.city}, {c.state}</div>}
                    </div>
                  </button>
                ))
              ) : (
                <div className="px-4 py-3 text-sm text-gray-500">No clients found</div>
              )}
            </div>
          )}
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
            <p className="text-gray-600 text-sm font-medium mb-2">Status</p>
            <p className="text-2xl font-bold">{client.account_status || 'Active'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-gray-600 text-sm font-medium mb-2">AutoCC Recurring</p>
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold">{client.autocc_recurring ? 'Active' : 'Inactive'}</p>
              <button
                onClick={handleToggleAutocc}
                disabled={toggleAutoccMutation.isPending}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  client.autocc_recurring
                    ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 disabled:opacity-50'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50'
                }`}
              >
                {toggleAutoccMutation.isPending ? 'Saving...' : 'Toggle'}
              </button>
            </div>
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
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Recent Invoices</CardTitle>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => navigate(`/invoices/new?client_id=${id}`)}
              >
                <Plus className="w-4 h-4 mr-1" />
                New Invoice
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => navigate(`/invoices?client_id=${id}`)}
              >
                <Eye className="w-4 h-4 mr-1" />
                View All
              </Button>
            </div>
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
            <div className="h-64 overflow-y-auto border border-gray-200 rounded-md p-3">
              <ul className="space-y-3">
                {activity.slice(0, 5).map((log) => {
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
                    const byUser = log.performed_by_name ? ` (${log.performed_by_name})` : '';

                    let entityLabel = '';
                    switch (log.entity_type) {
                      case 'invoice':
                        entityLabel = 'Invoice';
                        break;
                      case 'credit_memo':
                        entityLabel = 'Credit Memo';
                        break;
                      case 'payment':
                        entityLabel = 'Payment';
                        break;
                      case 'client':
                        entityLabel = 'Client Profile';
                        break;
                      case 'billing_schedule':
                        entityLabel = 'Billing Schedule';
                        break;
                      default:
                        entityLabel = log.entity_type?.replace(/_/g, ' ') || 'Record';
                    }

                    let description = '';
                    switch (log.action) {
                      case 'created':
                        description = `Created ${entityLabel}`;
                        break;
                      case 'sent':
                        description = `Sent ${entityLabel}`;
                        break;
                      case 'resent':
                        description = `Resent ${entityLabel}`;
                        break;
                      case 'marked_sent':
                        description = `Marked ${entityLabel} as Sent`;
                        break;
                      case 'status_changed':
                        description = `Changed ${entityLabel} Status`;
                        break;
                      case 'voided':
                        description = `Voided ${entityLabel}`;
                        break;
                      case 'updated':
                        description = `Updated ${entityLabel}`;
                        break;
                      case 'deactivated':
                        description = `Deactivated ${entityLabel}`;
                        break;
                      case 'autocc_verified':
                        description = `Verified Payment (AutoCC)`;
                        break;
                      case 'autocc_charge_declined':
                        description = `AutoCC Charge Declined`;
                        break;
                      case 'marked_paid_via_autocc_batch':
                        description = `Marked as Paid (AutoCC Batch)`;
                        break;
                      case 'paid':
                        description = `Marked ${entityLabel} as Paid`;
                        break;
                      default:
                        description = log.action.replace(/_/g, ' ').charAt(0).toUpperCase() + log.action.slice(1).replace(/_/g, ' ');
                    }

                    // Add notes with detail
                    if (log.notes) {
                      description += `: ${log.notes}`;
                    }

                    return `${description} on ${dateStr} at ${timeStr}${byUser}`;
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
            </div>
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
