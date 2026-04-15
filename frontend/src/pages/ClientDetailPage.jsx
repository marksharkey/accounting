import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useRef } from 'react';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import Button from '../components/ui/Button';
import Toggle from '../components/ui/Toggle';
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

  const getStatusColor = (status) => {
    if (status === 'active') return 'text-green-700 bg-green-50';
    if (status === 'overdue') return 'text-red-700 bg-red-50';
    if (status === 'suspended') return 'text-yellow-700 bg-yellow-50';
    return 'text-gray-700 bg-gray-50';
  };

  if (isLoading) {
    return <Layout title="Client Detail">Loading...</Layout>;
  }

  if (!client) {
    return <Layout title="Client Detail">Client not found</Layout>;
  }

  return (
    <Layout title={client.company_name}>
      {/* Toolbar */}
      <div className="relative mb-3">
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyPress={handleKeyPress}
              className="px-2 py-1 border border-gray-300 rounded text-[13px] focus:outline-none focus:ring-1 focus:ring-blue-500 w-full"
              autoComplete="off"
            />
            {isSearching && (
              <button
                onClick={handleClearSearch}
                className="absolute right-1 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            {isSearching && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded shadow-sm z-50 max-h-48 overflow-y-auto">
                {searchResults.length > 0 ? (
                  searchResults.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => handleSelectClient(c.id)}
                      className={`w-full text-left px-2 py-1 border-b text-[13px] hover:bg-blue-50 ${
                        c.id === parseInt(id) ? 'bg-blue-100 font-medium' : ''
                      }`}
                    >
                      <div className="font-medium">{c.company_name}</div>
                      <div className="text-xs text-gray-600">
                        {c.email && <span>{c.email}</span>}
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="px-2 py-1 text-[13px] text-gray-500">No clients found</div>
                )}
              </div>
            )}
          </div>

          {/* Toolbar Items */}
          <div className="flex items-center gap-3 flex-1 px-2 py-1 border-l border-gray-300">
            {/* Name */}
            <span className="font-medium text-[14px] text-gray-900">{client.company_name}</span>

            {/* Status Badge */}
            <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium ${getStatusColor(client.account_status)}`}>
              {client.account_status || 'Active'}
            </span>

            {/* Balance */}
            <span className={`font-mono text-[13px] font-semibold ${
              client.account_balance < 0 ? 'text-green-700' : 'text-red-700'
            }`}>
              ${Math.abs(client.account_balance).toFixed(2)}
            </span>

            {/* AutoCC Toggle */}
            <div className="flex items-center gap-1 border-l border-gray-300 pl-3">
              <span className="text-[12px] text-gray-600">AutoCC:</span>
              <Toggle
                checked={client.autocc_recurring}
                onChange={handleToggleAutocc}
                disabled={toggleAutoccMutation.isPending}
              />
            </div>

            {/* Actions */}
            <div className="flex gap-1 border-l border-gray-300 pl-3 ml-auto">
              <Button
                size="sm"
                onClick={() => setIsEditClientOpen(true)}
                className="!px-2 !py-0.5 !text-[12px]"
              >
                Edit
              </Button>
              <Button
                size="sm"
                onClick={() => navigate(`/invoices/new?client_id=${id}`)}
                className="!px-2 !py-0.5 !text-[12px]"
              >
                <Plus className="w-3 h-3 mr-0.5" />
                Invoice
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-[1fr_350px] gap-3">
        {/* LEFT COLUMN - 65% */}
        <div className="space-y-3">
          {/* Client Info Panel */}
          <div className="border border-gray-200 rounded text-[13px]">
            <div className="grid grid-cols-3 gap-3 p-3">
              <div>
                <div className="text-[11px] font-semibold text-gray-600 mb-1">CONTACT</div>
                <div className="text-gray-900">{client.contact_name || '—'}</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-gray-600 mb-1">EMAIL</div>
                <div>
                  {client.email ? (
                    <a href={`mailto:${client.email}`} className="text-blue-600 hover:text-blue-800">
                      {client.email}
                    </a>
                  ) : (
                    '—'
                  )}
                </div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-gray-600 mb-1">PHONE</div>
                <div className="text-gray-900">{client.phone || '—'}</div>
              </div>
              <div className="col-span-3">
                <div className="text-[11px] font-semibold text-gray-600 mb-1">ADDRESS</div>
                <div className="text-gray-900">
                  {client.address_line1 ? (
                    <>
                      {client.address_line1}
                      {client.address_line2 && <>, {client.address_line2}</>}
                      {client.city && <>, {client.city} {client.state} {client.zip_code}</>}
                    </>
                  ) : (
                    '—'
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Billing Schedules Table */}
          <div className="border border-gray-200 rounded overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
              <div className="font-semibold text-[13px]">Billing Schedules</div>
              <Button
                size="sm"
                onClick={() => setIsAddScheduleOpen(true)}
                className="!px-2 !py-0.5 !text-[12px]"
              >
                Add
              </Button>
            </div>
            {schedules && schedules.length > 0 ? (
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="text-left px-3 py-1 font-semibold text-[12px]">Frequency</th>
                    <th className="text-right px-3 py-1 font-semibold text-[12px]">Amount</th>
                    <th className="text-left px-3 py-1 font-semibold text-[12px]">Next Date</th>
                    <th className="text-left px-3 py-1 font-semibold text-[12px]">Components</th>
                  </tr>
                </thead>
                <tbody>
                  {schedules.map((schedule) => (
                    <tr key={schedule.id} className="border-b border-gray-200 hover:bg-gray-50">
                      <td className="px-3 py-1 font-medium">{schedule.cycle.replace('_', ' ').toUpperCase()}</td>
                      <td className="text-right px-3 py-1 font-mono">${parseFloat(schedule.amount).toFixed(2)}</td>
                      <td className="px-3 py-1 text-gray-600">{new Date(schedule.next_bill_date).toLocaleDateString()}</td>
                      <td className="px-3 py-1 text-gray-600">
                        {schedule.line_items && schedule.line_items.length > 0 ? (
                          <div className="text-[12px]">
                            {schedule.line_items.map((item, idx) => (
                              <div key={item.id}>{item.description} ×{parseFloat(item.quantity).toFixed(2)}</div>
                            ))}
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="px-3 py-2 text-gray-500 text-[13px]">No billing schedules</div>
            )}
          </div>

          {/* Activity Log Table */}
          <div className="border border-gray-200 rounded overflow-hidden">
            <div className="px-3 py-2 bg-gray-50 border-b border-gray-200 font-semibold text-[13px]">
              Activity Log
            </div>
            {activity && activity.length > 0 ? (
              <div className="overflow-y-auto max-h-80">
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50 sticky top-0">
                      <th className="text-left px-3 py-1 font-semibold text-[12px]">Timestamp</th>
                      <th className="text-left px-3 py-1 font-semibold text-[12px]">Action</th>
                      <th className="text-left px-3 py-1 font-semibold text-[12px]">User</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activity.map((log) => {
                      const timestamp = new Date(log.timestamp);
                      const dateStr = timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                      const timeStr = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                      let actionLabel = log.action.replace(/_/g, ' ').charAt(0).toUpperCase() + log.action.slice(1).replace(/_/g, ' ');
                      if (log.entity_type === 'invoice' && log.action === 'sent') actionLabel = 'Invoice sent';
                      if (log.entity_type === 'invoice' && log.action === 'created') actionLabel = 'Invoice created';

                      const link =
                        log.entity_type === 'invoice' ? `/invoices/${log.entity_id}` :
                        log.entity_type === 'credit_memo' ? `/credit-memos/${log.entity_id}` :
                        log.entity_type === 'payment' ? `/payments/${log.entity_id}` :
                        null;

                      return (
                        <tr key={log.id} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="px-3 py-1 text-gray-600 font-mono text-[12px]">
                            {dateStr} {timeStr}
                          </td>
                          <td className="px-3 py-1">
                            {link ? (
                              <Link to={link} className="text-blue-600 hover:text-blue-800">
                                {actionLabel}
                              </Link>
                            ) : (
                              actionLabel
                            )}
                          </td>
                          <td className="px-3 py-1 text-gray-600 text-[12px]">{log.performed_by_name || '—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="px-3 py-2 text-gray-500 text-[13px]">No activity</div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN - 35% */}
        <div className="space-y-3">
          {/* Recent Invoices Table */}
          <div className="border border-gray-200 rounded overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
              <div className="font-semibold text-[13px]">Recent Invoices</div>
              <Button
                size="sm"
                onClick={() => navigate(`/invoices?client_id=${id}`)}
                className="!px-1.5 !py-0.5 !text-[11px]"
              >
                <Eye className="w-3 h-3" />
              </Button>
            </div>
            {invoices && invoices.length > 0 ? (
              <div className="overflow-y-auto max-h-60">
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50 sticky top-0">
                      <th className="text-left px-3 py-1 font-semibold text-[12px]">Invoice #</th>
                      <th className="text-right px-3 py-1 font-semibold text-[12px]">Amount</th>
                      <th className="text-left px-3 py-1 font-semibold text-[12px]">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.slice(0, 20).map((invoice) => (
                      <tr key={invoice.id} className="border-b border-gray-200 hover:bg-gray-50">
                        <td className="px-3 py-1">
                          <Link
                            to={`/invoices/${invoice.id}`}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            {invoice.invoice_number || invoice.number}
                          </Link>
                        </td>
                        <td className="text-right px-3 py-1 font-mono">${parseFloat(invoice.total).toFixed(2)}</td>
                        <td className="px-3 py-1">
                          <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium ${
                            invoice.status === 'paid' ? 'bg-green-50 text-green-700' :
                            invoice.status === 'sent' ? 'bg-blue-50 text-blue-700' :
                            invoice.status === 'draft' ? 'bg-gray-50 text-gray-700' :
                            'bg-yellow-50 text-yellow-700'
                          }`}>
                            {invoice.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="px-3 py-2 text-gray-500 text-[13px]">No invoices</div>
            )}
          </div>

          {/* Quick Details */}
          <div className="border border-gray-200 rounded p-3 text-[13px] space-y-2">
            <div className="text-[11px] font-semibold text-gray-600 mb-2">QUICK INFO</div>

            {client.email_cc && (
              <div>
                <div className="text-[11px] text-gray-600">CC Email</div>
                <div className="text-gray-900">{client.email_cc}</div>
              </div>
            )}

            {client.late_fee_type !== 'none' && (
              <div>
                <div className="text-[11px] text-gray-600">Late Fee</div>
                <div className="text-gray-900">
                  {client.late_fee_type === 'flat' ? `$${client.late_fee_amount.toFixed(2)}` : `${client.late_fee_amount}%`}
                  {client.late_fee_grace_days > 0 && ` after ${client.late_fee_grace_days}d`}
                </div>
              </div>
            )}

            <div>
              <div className="text-[11px] text-gray-600">Auto-Send</div>
              <div className="text-gray-900">{client.auto_send_invoices ? 'On' : 'Off'}</div>
            </div>

            <div>
              <div className="text-[11px] text-gray-600">Collections</div>
              <div className="text-gray-900">{client.collections_exempt ? 'Exempt' : 'Active'}</div>
            </div>

            {client.notes && (
              <div>
                <div className="text-[11px] text-gray-600">Notes</div>
                <div className="text-gray-900 text-[12px] line-clamp-3">{client.notes}</div>
              </div>
            )}
          </div>
        </div>
      </div>

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
