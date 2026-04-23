import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import Button from '../components/ui/Button';
import { Plus, Download, Upload, AlertCircle, Settings, Check, X } from 'lucide-react';

export default function DomainsPage() {
  const queryClient = useQueryClient();
  const [isAddDomainOpen, setIsAddDomainOpen] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showCloudflareSettings, setShowCloudflareSettings] = useState(false);
  const [showSchedulingModal, setShowSchedulingModal] = useState(false);
  const [selectedForScheduling, setSelectedForScheduling] = useState(new Set());
  const [filterClient, setFilterClient] = useState('');
  const [filterRegistrar, setFilterRegistrar] = useState('');
  const [sortColumn, setSortColumn] = useState('expiration_date');
  const [sortDirection, setSortDirection] = useState('asc');

  const { data: domains = [], isLoading: domainsLoading, error: domainsError } = useQuery({
    queryKey: ['domains'],
    queryFn: async () => {
      const response = await apiClient.get('/domains/');
      return response.data?.items || [];
    },
    retry: 3,
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
    refetchOnMount: 'always',
  });

  const { data: clients = [], isLoading: clientsLoading } = useQuery({
    queryKey: ['clients-all'],
    queryFn: async () => {
      const response = await apiClient.get('/clients/', { params: { limit: 10000 } });
      return response.data?.items || [];
    },
    refetchOnMount: 'always',
    gcTime: 0,
  });

  const { data: unscheduledData = null, isLoading: unscheduledLoading } = useQuery({
    queryKey: ['domains-unscheduled'],
    queryFn: async () => {
      const response = await apiClient.get('/domains/scheduling/unscheduled');
      return response.data;
    },
    enabled: showSchedulingModal,
  });

  const batchScheduleMutation = useMutation({
    mutationFn: async (domainIds) => {
      const response = await apiClient.post('/domains/scheduling/batch-schedule', {
        domain_ids: Array.from(domainIds)
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] });
      queryClient.invalidateQueries({ queryKey: ['domains-unscheduled'] });
      setShowSchedulingModal(false);
      setSelectedForScheduling(new Set());
    },
  });

  const clientsList = Array.isArray(clients) ? clients : [];
  const domainsList = Array.isArray(domains) ? domains : [];
  const unscheduled = unscheduledData?.domains || [];

  const deleteMutation = useMutation({
    mutationFn: async (domainId) => {
      await apiClient.delete(`/domains/${domainId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] });
    },
  });

  const getClientName = (clientId) => {
    return clientsList?.find(c => c.id === clientId)?.company_name || 'Unknown';
  };

  const getDaysUntilExpiry = (expirationDate) => {
    const today = new Date();
    const expiry = new Date(expirationDate);
    const diffTime = expiry - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const isExpiringSoon = (expirationDate) => {
    const days = getDaysUntilExpiry(expirationDate);
    return days <= 30 && days > 0;
  };

  const isExpired = (expirationDate) => {
    return getDaysUntilExpiry(expirationDate) <= 0;
  };

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const SortIndicator = ({ column }) => {
    if (sortColumn !== column) return <span className="text-gray-300 ml-1">⇅</span>;
    return <span className="text-blue-600 ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>;
  };

  // Filter domains
  let filtered = domainsList || [];
  if (filterClient) {
    filtered = filtered.filter(d => d.client_id === parseInt(filterClient));
  }
  if (filterRegistrar) {
    filtered = filtered.filter(d => d.registrar === filterRegistrar);
  }

  // Sort domains
  filtered = [...filtered].sort((a, b) => {
    let aVal, bVal;

    switch (sortColumn) {
      case 'domain_name':
        aVal = a.domain_name.toLowerCase();
        bVal = b.domain_name.toLowerCase();
        break;
      case 'client_id':
        aVal = getClientName(a.client_id);
        bVal = getClientName(b.client_id);
        break;
      case 'registrar':
        aVal = a.registrar;
        bVal = b.registrar;
        break;
      case 'expiration_date':
        aVal = new Date(a.expiration_date);
        bVal = new Date(b.expiration_date);
        break;
      case 'renewal_cost':
        aVal = parseFloat(a.renewal_cost);
        bVal = parseFloat(b.renewal_cost);
        break;
      default:
        return 0;
    }

    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  const registrars = [...new Set(domainsList.map(d => d.registrar))];

  if (domainsLoading) {
    return <Layout title="Domains">Loading...</Layout>;
  }

  if (domainsError) {
    return <Layout title="Domains">
      <div className="text-center text-red-600 py-8">
        <p>Failed to load domains. Please try again.</p>
      </div>
    </Layout>;
  }

  return (
    <Layout title="Domains">
      <div className="space-y-3">
        {/* Toolbar */}
        <div className="flex items-center gap-2">
          <Button onClick={() => setIsAddDomainOpen(true)} className="!px-3 !py-1.5 !text-sm">
            <Plus className="w-4 h-4 mr-1" />
            Add Domain
          </Button>
          <Button onClick={() => setShowSchedulingModal(true)} variant="secondary" className="!px-3 !py-1.5 !text-sm">
            <AlertCircle className="w-4 h-4 mr-1" />
            Schedule Renewals
          </Button>
          <SyncCloudflareButton />
          <Button onClick={() => setShowImportModal(true)} variant="secondary" className="!px-3 !py-1.5 !text-sm">
            <Upload className="w-4 h-4 mr-1" />
            Import CSV
          </Button>
          <Button onClick={downloadCSVTemplate} variant="secondary" className="!px-3 !py-1.5 !text-sm">
            <Download className="w-4 h-4 mr-1" />
            CSV Template
          </Button>
          <Button onClick={() => setShowCloudflareSettings(true)} variant="secondary" className="!px-3 !py-1.5 !text-sm" title="Test or update credentials">
            <Settings className="w-4 h-4" />
          </Button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <select
            value={filterClient}
            onChange={(e) => setFilterClient(e.target.value)}
            className="px-2 py-1 border border-gray-300 rounded text-[13px] focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Clients</option>
            {clientsList.map(c => (
              <option key={c.id} value={c.id}>{c.company_name}</option>
            ))}
          </select>

          <select
            value={filterRegistrar}
            onChange={(e) => setFilterRegistrar(e.target.value)}
            className="px-2 py-1 border border-gray-300 rounded text-[13px] focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Registrars</option>
            {registrars.map(r => (
              <option key={r} value={r}>{r.replace(/_/g, '.')}</option>
            ))}
          </select>
        </div>

        {/* Domains Table */}
        <div className="border border-gray-200 rounded overflow-hidden">
          <table className="w-full text-[12px] border-collapse">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th
                  onClick={() => handleSort('domain_name')}
                  className="text-left px-1.5 py-1 font-semibold text-[10px] cursor-pointer hover:bg-gray-100 select-none flex-1"
                >
                  Domain{sortColumn === 'domain_name' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th
                  onClick={() => handleSort('client_id')}
                  className="text-left px-1.5 py-1 font-semibold text-[10px] cursor-pointer hover:bg-gray-100 select-none"
                >
                  Client{sortColumn === 'client_id' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th
                  onClick={() => handleSort('registrar')}
                  className="text-left px-1.5 py-1 font-semibold text-[10px] cursor-pointer hover:bg-gray-100 select-none hidden sm:table-cell"
                >
                  Reg{sortColumn === 'registrar' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th
                  onClick={() => handleSort('expiration_date')}
                  className="text-left px-1.5 py-1 font-semibold text-[10px] cursor-pointer hover:bg-gray-100 select-none"
                >
                  Exp{sortColumn === 'expiration_date' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th
                  onClick={() => handleSort('renewal_cost')}
                  className="text-right px-1.5 py-1 font-semibold text-[10px] cursor-pointer hover:bg-gray-100 select-none"
                >
                  $
                </th>
                <th className="text-center px-1.5 py-1 font-semibold text-[10px]">Status</th>
                <th className="text-center px-1.5 py-1 font-semibold text-[10px]">Del</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? (
                filtered.map(domain => {
                  const daysUntil = getDaysUntilExpiry(domain.expiration_date);
                  const expiry = new Date(domain.expiration_date);
                  const expiryStr = expiry.toLocaleDateString();

                  return (
                    <tr key={domain.id} className="border-b border-gray-200 hover:bg-gray-50">
                      <td className="text-left px-1.5 py-1 font-mono text-gray-900 text-[11px] truncate">{domain.domain_name}</td>
                      <td className="text-left px-1.5 py-1 text-[11px] truncate">
                        {domain.client_id ? (
                          <Link to={`/clients/${domain.client_id}`} className="text-blue-600 hover:text-blue-800 hover:underline">
                            {getClientName(domain.client_id)}
                          </Link>
                        ) : (
                          <span className="text-gray-700">Unknown</span>
                        )}
                      </td>
                      <td className="text-left px-1.5 py-1 text-gray-600 text-[10px] hidden sm:table-cell">{domain.registrar === 'cloudflare' ? 'CF' : domain.registrar.replace(/_/g, '.')}</td>
                      <td className="text-left px-1.5 py-1 font-mono text-[10px] whitespace-nowrap">{expiryStr}</td>
                      <td className="text-right px-1.5 py-1 font-mono text-[11px]">${parseFloat(domain.renewal_cost).toFixed(2)}</td>
                      <td className="text-left px-1.5 py-1">
                        {isExpired(domain.expiration_date) ? (
                          <span className="inline-block px-1 py-0 rounded text-[9px] font-medium bg-red-100 text-red-700">Exp</span>
                        ) : isExpiringSoon(domain.expiration_date) ? (
                          <span className="inline-block px-1 py-0 rounded text-[9px] font-medium bg-yellow-100 text-yellow-700">{daysUntil}d</span>
                        ) : (
                          <span className="inline-block px-1 py-0 rounded text-[9px] font-medium bg-green-100 text-green-700">{daysUntil}d</span>
                        )}
                      </td>
                      <td className="text-left px-1.5 py-1">
                        <button
                          onClick={() => deleteMutation.mutate(domain.id)}
                          disabled={deleteMutation.isPending}
                          className="text-red-600 hover:text-red-800 text-[10px] font-medium hover:underline"
                        >
                          Del
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="7" className="px-3 py-8 text-center text-gray-500">
                    No domains found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Import Modal */}
        {showImportModal && (
          <ImportModal
            isOpen={showImportModal}
            onClose={() => setShowImportModal(false)}
            onSuccess={() => {
              queryClient.invalidateQueries({ queryKey: ['domains'] });
              setShowImportModal(false);
            }}
          />
        )}

        {/* Add Domain Modal */}
        {isAddDomainOpen && (
          <AddDomainModal
            isOpen={isAddDomainOpen}
            onClose={() => setIsAddDomainOpen(false)}
            clients={clientsList}
            onSuccess={() => {
              queryClient.invalidateQueries({ queryKey: ['domains'] });
              setIsAddDomainOpen(false);
            }}
          />
        )}

        {/* Cloudflare Settings Modal */}
        {showCloudflareSettings && (
          <CloudflareSettingsModal
            isOpen={showCloudflareSettings}
            onClose={() => setShowCloudflareSettings(false)}
          />
        )}

        {/* Domain Scheduling Modal */}
        {showSchedulingModal && (
          <SchedulingModal
            isOpen={showSchedulingModal}
            onClose={() => {
              setShowSchedulingModal(false);
              setSelectedForScheduling(new Set());
            }}
            unscheduled={unscheduled}
            isLoading={unscheduledLoading}
            selectedForScheduling={selectedForScheduling}
            setSelectedForScheduling={setSelectedForScheduling}
            onSchedule={() => batchScheduleMutation.mutate(selectedForScheduling)}
            isScheduling={batchScheduleMutation.isPending}
          />
        )}
      </div>
    </Layout>
  );
}

function SyncCloudflareButton() {
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState(null);
  const queryClient = useQueryClient();

  const handleSync = async () => {
    setSyncing(true);
    setMessage(null);

    try {
      const response = await apiClient.post('/domains/sync/cloudflare');
      setMessage({
        type: 'success',
        imported: response.data.imported,
        updated: response.data.updated,
        debug: response.data.debug,
      });
      queryClient.invalidateQueries({ queryKey: ['domains'] });
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Sync failed';
      setMessage({
        type: 'error',
        text: typeof errorMsg === 'string' ? errorMsg : 'Sync failed',
      });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <>
      <Button
        onClick={handleSync}
        disabled={syncing}
        variant="secondary"
        className="!px-3 !py-1.5 !text-sm"
        title="Sync domains from Cloudflare (uses saved credentials)"
      >
        {syncing ? 'Syncing...' : 'Sync Cloudflare'}
      </Button>
      {message && (
        <div className={`text-[12px] px-3 py-2 rounded ${
          message.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          <div>
            {message.type === 'success'
              ? `✓ Imported ${message.imported}, Updated ${message.updated}`
              : `✗ ${message.text}`
            }
          </div>
          {message.debug && (
            <div className="text-[11px] mt-1 opacity-75 font-mono">
              <div>Domains found: {message.debug.domains_found}</div>
              {message.debug.first_domain && (
                <div className="mt-1">First domain keys: {Object.keys(message.debug.first_domain).join(', ')}</div>
              )}
            </div>
          )}
        </div>
      )}
    </>
  );
}

function downloadCSVTemplate() {
  const csv = `domain_name,client_name,registrar,expiration_date,renewal_cost
example.com,Client Name,godaddy,2025-12-31,25.00
test.org,Another Client,hosting.com,2026-06-15,35.00`;

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'domains_import_template.csv';
  a.click();
  window.URL.revokeObjectURL(url);
}

function ImportModal({ isOpen, onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);

  const handleImport = async () => {
    if (!file) return;

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post('/domains/import/csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setResult(response.data);
      if (response.data.imported > 0) {
        setTimeout(onSuccess, 1500);
      }
    } catch (error) {
      setResult({ error: error.response?.data?.detail || 'Import failed' });
    } finally {
      setImporting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
        <h2 className="text-lg font-semibold mb-4">Import Domains from CSV</h2>

        {result ? (
          <div className="space-y-2">
            {result.error ? (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-[13px]">
                {result.error}
              </div>
            ) : (
              <div className="p-3 bg-green-50 border border-green-200 rounded text-green-700 text-[13px]">
                <div>Imported: {result.imported}</div>
                <div>Skipped: {result.skipped}</div>
                {result.errors && result.errors.length > 0 && (
                  <div className="mt-2 text-[12px]">
                    {result.errors.slice(0, 3).map((e, i) => (
                      <div key={i}>{e}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="flex gap-2 mt-4">
              <Button onClick={onClose} variant="secondary" className="flex-1">Close</Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-[13px] font-medium mb-2">CSV File</label>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
              />
              <p className="text-[12px] text-gray-600 mt-1">
                Format: domain_name, client_name, registrar, expiration_date (YYYY-MM-DD), renewal_cost (optional)
              </p>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => setFile(null)} variant="secondary" className="flex-1">Clear</Button>
              <Button onClick={handleImport} disabled={!file || importing} className="flex-1">
                {importing ? 'Importing...' : 'Import'}
              </Button>
              <Button onClick={onClose} variant="secondary" className="flex-1">Cancel</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AddDomainModal({ isOpen, onClose, clients, onSuccess }) {
  const [formData, setFormData] = useState({
    domain_name: '',
    client_id: '',
    registrar: 'cloudflare',
    expiration_date: '',
    renewal_cost: '25.00',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      await apiClient.post('/domains/', {
        ...formData,
        client_id: parseInt(formData.client_id),
        renewal_cost: parseFloat(formData.renewal_cost),
      });
      onSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create domain');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
        <h2 className="text-lg font-semibold mb-4">Add Domain</h2>

        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="p-2 bg-red-50 border border-red-200 rounded text-red-700 text-[13px]">{error}</div>}

          <div>
            <label className="block text-[13px] font-medium mb-1">Domain</label>
            <input
              type="text"
              value={formData.domain_name}
              onChange={(e) => setFormData({ ...formData, domain_name: e.target.value.toLowerCase() })}
              placeholder="example.com"
              className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
              required
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium mb-1">Client</label>
            <select
              value={formData.client_id}
              onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
              className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
              required
            >
              <option value="">Select client</option>
              {clients && clients.map(c => (
                <option key={c.id} value={c.id}>{c.company_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[13px] font-medium mb-1">Registrar</label>
            <select
              value={formData.registrar}
              onChange={(e) => setFormData({ ...formData, registrar: e.target.value })}
              className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
            >
              <option value="cloudflare">Cloudflare</option>
              <option value="godaddy">GoDaddy</option>
              <option value="hosting_com">Hosting.com</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-[13px] font-medium mb-1">Expiration Date</label>
            <input
              type="date"
              value={formData.expiration_date}
              onChange={(e) => setFormData({ ...formData, expiration_date: e.target.value })}
              className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
              required
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium mb-1">Renewal Cost ($/year)</label>
            <input
              type="number"
              step="0.01"
              value={formData.renewal_cost}
              onChange={(e) => setFormData({ ...formData, renewal_cost: e.target.value })}
              className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
              required
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button type="submit" disabled={saving} className="flex-1">
              {saving ? 'Adding...' : 'Add'}
            </Button>
            <Button type="button" onClick={onClose} variant="secondary" className="flex-1">
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CloudflareSettingsModal({ isOpen, onClose }) {
  const [apiKey, setApiKey] = useState('');
  const [email, setEmail] = useState('billing@precisionpros.com');
  const [accountId, setAccountId] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const queryClient = useQueryClient();

  const handleTest = async () => {
    if (!apiKey || !email || !accountId) {
      setTestResult({ error: 'Please enter API key, email, and Account ID' });
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      const response = await apiClient.post('/domains/cloudflare/test?save=true', {
        api_key: apiKey,
        email: email,
        account_id: accountId,
      });

      setTestResult({
        success: true,
        account_name: response.data.account_name,
        message: 'Credentials are valid',
      });
    } catch (error) {
      setTestResult({
        error: error.response?.data?.detail || 'Test failed',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);

    try {
      // If user filled in credentials, send them; otherwise use .env
      const syncPayload = (apiKey && email && accountId)
        ? { api_key: apiKey, email: email, account_id: accountId }
        : {};

      const response = await apiClient.post('/domains/sync/cloudflare', syncPayload);
      setTestResult({
        success: true,
        syncResult: response.data,
        account_name: testResult?.account_name || 'Cloudflare',
      });
      queryClient.invalidateQueries({ queryKey: ['domains'] });
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Sync failed';
      setTestResult({
        error: typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg),
      });
    } finally {
      setSyncing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-lg w-full max-h-96 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Cloudflare API Setup</h2>

        <div className="space-y-4">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded text-[12px] text-blue-800">
            <div className="font-medium mb-1">Get your Cloudflare Global API Key:</div>
            <ol className="list-decimal list-inside space-y-1">
              <li>Go to <span className="font-mono">dash.cloudflare.com</span></li>
              <li>Click profile icon → <span className="font-mono">My Profile</span></li>
              <li>Scroll to <span className="font-mono">API Tokens</span> section</li>
              <li>Copy your <span className="font-mono">Global API Key</span> (you may need to click "View")</li>
              <li>Go to <span className="font-mono">Accounts</span> tab, find your Account ID</li>
            </ol>
          </div>

          <div>
            <label className="block text-[13px] font-medium mb-1">Global API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Your Cloudflare Global API Key"
              className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
            />
            <p className="text-[11px] text-gray-600 mt-1">Found in Profile → API Tokens (scroll down)</p>
          </div>

          <div>
            <label className="block text-[13px] font-medium mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="billing@precisionpros.com"
              className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium mb-1">Account ID</label>
            <input
              type="text"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              placeholder="Your Cloudflare Account ID"
              className="w-full px-2 py-1 border border-gray-300 rounded text-[13px]"
            />
            <p className="text-[11px] text-gray-600 mt-1">Found in Accounts tab</p>
          </div>

          {testResult && (
            <div className={`p-3 border rounded text-[13px] ${
              testResult.error
                ? 'bg-red-50 border-red-200 text-red-800'
                : 'bg-green-50 border-green-200 text-green-800'
            }`}>
              {testResult.error ? (
                <div className="flex items-start gap-2">
                  <X className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>{typeof testResult.error === 'string' ? testResult.error : testResult.error.message || 'Unknown error'}</div>
                </div>
              ) : testResult.syncResult ? (
                <div className="flex items-start gap-2">
                  <Check className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium">Sync Complete!</div>
                    <div className="text-[12px] mt-1">
                      Imported: {testResult.syncResult.imported} | Updated: {testResult.syncResult.updated}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-2">
                  <Check className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium">Valid credentials{testResult.saved && ' — saved to .env'}</div>
                    <div className="text-[12px]">Account: {testResult.account_name}</div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <Button
              onClick={handleTest}
              disabled={testing || !apiKey || !email || !accountId}
              className="flex-1"
            >
              {testing ? 'Testing...' : 'Test Credentials'}
            </Button>
            {testResult?.success && !testResult.syncResult && (
              <Button
                onClick={handleSync}
                disabled={syncing}
                className="flex-1"
              >
                {syncing ? 'Syncing...' : 'Sync Domains'}
              </Button>
            )}
            <Button onClick={onClose} variant="secondary" className="flex-1">
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SchedulingModal({
  isOpen,
  onClose,
  unscheduled,
  isLoading,
  selectedForScheduling,
  setSelectedForScheduling,
  onSchedule,
  isScheduling,
}) {
  const [schedulingComplete, setSchedulingComplete] = useState(false);
  const [schedulingResult, setSchedulingResult] = useState(null);

  const toggleDomain = (domainId) => {
    const newSelected = new Set(selectedForScheduling);
    if (newSelected.has(domainId)) {
      newSelected.delete(domainId);
    } else {
      newSelected.add(domainId);
    }
    setSelectedForScheduling(newSelected);
  };

  const toggleAll = () => {
    if (selectedForScheduling.size === unscheduled.length) {
      setSelectedForScheduling(new Set());
    } else {
      setSelectedForScheduling(new Set(unscheduled.map(d => d.domain_id)));
    }
  };

  const handleSchedule = async () => {
    try {
      await onSchedule();
      setSchedulingComplete(true);
      setSchedulingResult({ success: true, count: selectedForScheduling.size });
      setTimeout(() => onClose(), 2000);
    } catch (error) {
      setSchedulingResult({ success: false, error: error.message });
    }
  };

  if (!isOpen) return null;

  if (schedulingComplete && schedulingResult?.success) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-lg max-w-sm w-full p-6 text-center">
          <div className="text-green-600 text-4xl mb-4">✓</div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Success!</h2>
          <p className="text-gray-600 mb-4">
            {schedulingResult.count} domain{schedulingResult.count !== 1 ? 's' : ''} scheduled to billing calendars.
          </p>
          <p className="text-sm text-gray-500">Redirecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-3xl w-full max-h-96 overflow-hidden flex flex-col">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Schedule Domain Renewals</h2>
          <p className="text-sm text-gray-600 mt-1">
            Select domains to add to their recommended annual billing schedules
          </p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-40">
              <div className="text-gray-500">Loading unscheduled domains...</div>
            </div>
          ) : unscheduled.length === 0 ? (
            <div className="flex items-center justify-center h-40">
              <div className="text-gray-500">All domains are scheduled!</div>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">
                    <input
                      type="checkbox"
                      checked={selectedForScheduling.size === unscheduled.length && unscheduled.length > 0}
                      onChange={toggleAll}
                      className="h-4 w-4"
                    />
                  </th>
                  <th className="px-4 py-2 text-left font-medium">Domain</th>
                  <th className="px-4 py-2 text-left font-medium">Client</th>
                  <th className="px-4 py-2 text-left font-medium">Expires</th>
                  <th className="px-4 py-2 text-left font-medium">Due Date</th>
                  <th className="px-4 py-2 text-right font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {unscheduled.map(domain => (
                  <tr key={domain.domain_id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={selectedForScheduling.has(domain.domain_id)}
                        onChange={() => toggleDomain(domain.domain_id)}
                        className="h-4 w-4"
                      />
                    </td>
                    <td className="px-4 py-2 font-mono text-sm">{domain.domain_name}</td>
                    <td className="px-4 py-2 text-sm">{domain.client_name}</td>
                    <td className="px-4 py-2 text-sm">{new Date(domain.expiration_date).toLocaleDateString()}</td>
                    <td className="px-4 py-2 text-sm">{new Date(domain.recommended_due_date).toLocaleDateString()}</td>
                    <td className="px-4 py-2 text-right font-mono text-sm">${parseFloat(domain.renewal_cost).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex gap-3 justify-end">
          <button
            onClick={onClose}
            disabled={isScheduling}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100 text-sm font-medium disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSchedule}
            disabled={isScheduling || selectedForScheduling.size === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
          >
            {isScheduling ? 'Scheduling...' : `Schedule ${selectedForScheduling.size} Domain${selectedForScheduling.size !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}
