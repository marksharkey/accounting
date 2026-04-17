import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import Button from '../components/ui/Button';
import { Plus, Download, Upload, AlertCircle, Settings, Check, X } from 'lucide-react';

export default function DomainsPage() {
  const queryClient = useQueryClient();
  const [isAddDomainOpen, setIsAddDomainOpen] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showCloudflareSettings, setShowCloudflareSettings] = useState(false);
  const [filterClient, setFilterClient] = useState('');
  const [filterRegistrar, setFilterRegistrar] = useState('');

  const { data: domains, isLoading: domainsLoading } = useQuery({
    queryKey: ['domains'],
    queryFn: async () => {
      const response = await apiClient.get('/domains/');
      return response.data?.items || [];
    },
  });

  const { data: clients } = useQuery({
    queryKey: ['clients-all'],
    queryFn: async () => {
      const response = await apiClient.get('/clients/', { params: { limit: 10000 } });
      return response.data?.items || [];
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (domainId) => {
      await apiClient.delete(`/domains/${domainId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] });
    },
  });

  const getClientName = (clientId) => {
    return clients?.find(c => c.id === clientId)?.company_name || 'Unknown';
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

  // Filter domains
  let filtered = domains || [];
  if (filterClient) {
    filtered = filtered.filter(d => d.client_id === parseInt(filterClient));
  }
  if (filterRegistrar) {
    filtered = filtered.filter(d => d.registrar === filterRegistrar);
  }

  const registrars = [...new Set((domains || []).map(d => d.registrar))];

  if (domainsLoading) {
    return <Layout title="Domains">Loading...</Layout>;
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
            {clients && clients.map(c => (
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
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-3 py-2 font-semibold text-[12px]">Domain</th>
                <th className="text-left px-3 py-2 font-semibold text-[12px]">Client</th>
                <th className="text-left px-3 py-2 font-semibold text-[12px]">Registrar</th>
                <th className="text-left px-3 py-2 font-semibold text-[12px]">Expiration</th>
                <th className="text-right px-3 py-2 font-semibold text-[12px]">Renewal Cost</th>
                <th className="text-center px-3 py-2 font-semibold text-[12px]">Status</th>
                <th className="text-right px-3 py-2 font-semibold text-[12px]">Actions</th>
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
                      <td className="px-3 py-2 font-mono text-blue-600">{domain.domain_name}</td>
                      <td className="px-3 py-2 text-gray-700">{getClientName(domain.client_id)}</td>
                      <td className="px-3 py-2 text-gray-600">{domain.registrar.replace(/_/g, '.')}</td>
                      <td className="px-3 py-2 font-mono text-[12px]">{expiryStr}</td>
                      <td className="text-right px-3 py-2 font-mono">${parseFloat(domain.renewal_cost).toFixed(2)}</td>
                      <td className="text-center px-3 py-2">
                        {isExpired(domain.expiration_date) ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-red-50 text-red-700">
                            <AlertCircle className="w-3 h-3" />
                            Expired
                          </span>
                        ) : isExpiringSoon(domain.expiration_date) ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-yellow-50 text-yellow-700">
                            <AlertCircle className="w-3 h-3" />
                            {daysUntil}d
                          </span>
                        ) : (
                          <span className="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-green-50 text-green-700">
                            {daysUntil}d
                          </span>
                        )}
                      </td>
                      <td className="text-right px-3 py-2">
                        <button
                          onClick={() => deleteMutation.mutate(domain.id)}
                          disabled={deleteMutation.isPending}
                          className="text-red-600 hover:text-red-800 text-[12px] font-medium"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="7" className="px-3 py-4 text-center text-gray-500">
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
            clients={clients}
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
