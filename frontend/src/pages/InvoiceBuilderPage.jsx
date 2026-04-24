import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

export default function InvoiceBuilderPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // State
  const [selectedClient, setSelectedClient] = useState('');
  const [lineItems, setLineItems] = useState([]);
  const [isAuthNetVerified, setIsAuthNetVerified] = useState(false);
  const [dueDate, setDueDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1).toISOString().split('T')[0]);
  const [notesToClient, setNotesToClient] = useState('');
  const [internalNotes, setInternalNotes] = useState('');
  const [catalogSelectOpen, setCatalogSelectOpen] = useState(false);
  const [previousBalance, setPreviousBalance] = useState(0.0);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [billingScheduleIds, setBillingScheduleIds] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [duplicatePreviousData, setDuplicatePreviousData] = useState(null);
  const [isDuplicateLoading, setIsDuplicateLoading] = useState(false);

  // Refs for auto-expanding textareas
  const textareaRefs = useRef({});

  const adjustTextareaHeight = (textareaId) => {
    const textarea = textareaRefs.current[textareaId];
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.max(textarea.scrollHeight, 60) + 'px';
    }
  };

  // Adjust textarea heights when line items change or content updates
  useEffect(() => {
    lineItems.forEach(item => {
      // Use setTimeout to ensure DOM is updated
      setTimeout(() => adjustTextareaHeight(item.id), 0);
    });
  }, [lineItems]);

  // Pre-select client from URL parameter if provided
  useEffect(() => {
    const clientId = searchParams.get('client_id');
    if (clientId) {
      setSelectedClient(clientId);
    }
  }, [searchParams]);

  // Queries
  const { data: clientData } = useQuery({
    queryKey: ['clients-all'],
    queryFn: async () => {
      const response = await apiClient.get('/clients/', {
        params: { limit: 10000 },
      });
      return response.data;
    },
  });

  const { data: companyInfo } = useQuery({
    queryKey: ['company-info'],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/company-info/');
        return response.data;
      } catch {
        return null;
      }
    },
  });

  const clients = clientData?.items || [];
  const selectedClientObj = clients.find(c => c.id === parseInt(selectedClient));

  const { data: serviceData } = useQuery({
    queryKey: ['services'],
    queryFn: async () => {
      const response = await apiClient.get('/services/');
      return response.data;
    },
  });

  const services = Array.isArray(serviceData) ? serviceData : serviceData?.items || [];

  const { data: prefilled, isLoading: isPrefillLoading } = useQuery({
    queryKey: ['invoices', 'prefill', selectedClient, dueDate],
    queryFn: async () => {
      if (!selectedClient || !dueDate) return null;
      const response = await apiClient.post(`/invoices/prefill/${selectedClient}?due_date=${dueDate}`);
      return response.data;
    },
    enabled: !!selectedClient && !!dueDate,
  });

  // Populate previousBalance when prefilled data arrives or client changes
  useEffect(() => {
    if (selectedClient && prefilled?.client) {
      setPreviousBalance(prefilled.client.account_balance || 0.0);
    } else {
      setPreviousBalance(0.0);
    }
  }, [selectedClient, prefilled]);

  // Fetch duplicate previous invoice data
  useEffect(() => {
    if (!selectedClient) {
      setDuplicatePreviousData(null);
      return;
    }

    setIsDuplicateLoading(true);
    apiClient
      .get(`/invoices/duplicate-previous/${selectedClient}`)
      .then(response => {
        setDuplicatePreviousData(response.data);
      })
      .catch(() => {
        setDuplicatePreviousData(null);
      })
      .finally(() => {
        setIsDuplicateLoading(false);
      });
  }, [selectedClient]);


  const resetForm = () => {
    setSelectedClient('');
    setLineItems([]);
    setIsAuthNetVerified(false);
    setDueDate(new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1).toISOString().split('T')[0]);
    setNotesToClient('');
    setInternalNotes('');
    setPreviousBalance(0.0);
    setBillingScheduleIds([]);
  };

  // Handlers
  const handleAddService = (serviceId) => {
    const service = services.find(s => s.id === parseInt(serviceId));
    if (service) {
      setLineItems([
        ...lineItems,
        {
          id: crypto.randomUUID(),
          service_id: service.id,
          description: service.name,
          qty: 1,
          unitPrice: service.default_amount,
        },
      ]);
      setCatalogSelectOpen(false);
    }
  };

  const handleAddCustomItem = () => {
    setLineItems([
      ...lineItems,
      {
        id: crypto.randomUUID(),
        service_id: null,
        description: '',
        qty: 1,
        unitPrice: 0,
      },
    ]);
  };

  const updateLineItem = (id, field, value) => {
    setLineItems(lineItems.map(item =>
      item.id === id
        ? { ...item, [field]: field === 'qty' || field === 'unitPrice' ? parseFloat(value) || 0 : value }
        : item
    ));
  };

  const removeLineItem = (id) => {
    setLineItems(lineItems.filter(item => item.id !== id));
  };

  const handleApplyPrefilled = () => {
    if (prefilled && prefilled.line_items) {
      setLineItems(prefilled.line_items.map((item) => ({
        id: crypto.randomUUID(),
        service_id: item.service_id || null,
        description: item.description,
        qty: item.quantity || 1,
        unitPrice: item.unit_amount || 0,
      })));
      setDueDate(prefilled.suggested_due_date);
      setBillingScheduleIds(prefilled.billing_schedule_ids || []);
    }
  };

  const handleApplyDuplicatePrevious = () => {
    if (duplicatePreviousData && duplicatePreviousData.line_items) {
      setLineItems(duplicatePreviousData.line_items.map((item) => ({
        id: crypto.randomUUID(),
        service_id: item.service_id || null,
        description: item.description,
        qty: item.quantity || 1,
        unitPrice: item.unit_amount || 0,
      })));
      setBillingScheduleIds([]);
    }
  };

  const calculateLineTotal = (item) => (item.qty || 0) * (item.unitPrice || 0);
  const calculateTotal = () => lineItems.reduce((sum, item) => sum + calculateLineTotal(item), 0);

  const handleSaveDraft = async () => {
    if (!selectedClient || lineItems.length === 0) {
      setErrorMessage('Select a client and add line items');
      setTimeout(() => setErrorMessage(''), 3000);
      return;
    }

    const formattedItems = lineItems.map((item, idx) => ({
      description: item.description || 'Service',
      quantity: item.qty || 1.0,
      unit_amount: item.unitPrice || 0,
      service_id: item.service_id || null,
      is_prorated: false,
      sort_order: idx,
    }));

    const invoiceData = {
      client_id: parseInt(selectedClient),
      created_date: new Date().toISOString().split('T')[0],
      due_date: dueDate,
      line_items: formattedItems,
      previous_balance: previousBalance,
      notes: notesToClient || null,
      internal_notes: internalNotes || null,
      status: 'draft',
      billing_schedule_ids: billingScheduleIds.length > 0 ? billingScheduleIds : null,
    };

    setIsLoading(true);
    try {
      await apiClient.post('/invoices/', invoiceData);
      setSuccessMessage('Invoice saved as draft!');
      setTimeout(() => setSuccessMessage(''), 3000);
      resetForm();
    } catch (error) {
      const detail = error.response?.data?.detail;
      let message = error.message;
      if (Array.isArray(detail)) {
        message = detail.map(e => `${e.msg}`).join(', ');
      } else if (typeof detail === 'string') {
        message = detail;
      }
      setErrorMessage(message);
      setTimeout(() => setErrorMessage(''), 5000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!selectedClient || lineItems.length === 0) {
      setErrorMessage('Select a client and add line items');
      setTimeout(() => setErrorMessage(''), 3000);
      return;
    }

    const formattedItems = lineItems.map((item, idx) => ({
      description: item.description || 'Service',
      quantity: item.qty || 1.0,
      unit_amount: item.unitPrice || 0,
      service_id: item.service_id || null,
      is_prorated: false,
      sort_order: idx,
    }));

    const invoiceData = {
      client_id: parseInt(selectedClient),
      created_date: new Date().toISOString().split('T')[0],
      due_date: dueDate,
      line_items: formattedItems,
      previous_balance: previousBalance,
      notes: notesToClient || null,
      internal_notes: internalNotes || null,
      status: 'draft',
      autocc_verified: isAuthNetVerified,
      billing_schedule_ids: billingScheduleIds.length > 0 ? billingScheduleIds : null,
    };

    setIsLoading(true);
    try {
      const createResponse = await apiClient.post('/invoices/', invoiceData);
      const invoiceId = createResponse.data.id;

      // Now send the invoice
      await apiClient.post(`/invoices/${invoiceId}/send`);
      setSuccessMessage('Invoice sent successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
      resetForm();
    } catch (error) {
      const detail = error.response?.data?.detail;
      let message = error.message;
      if (Array.isArray(detail)) {
        message = detail.map(e => `${e.msg}`).join(', ');
      } else if (typeof detail === 'string') {
        message = detail;
      }
      setErrorMessage(message);
      setTimeout(() => setErrorMessage(''), 5000);
    } finally {
      setIsLoading(false);
    }
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <Layout onBack={() => navigate(-1)}>
      {/* Sticky Toolbar */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-4 py-3 -mx-4 sm:-mx-6 lg:-mx-8 mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          {/* Client Dropdown */}
          <div className="w-full sm:flex-1 min-w-0">
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="">Select client...</option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.company_name}
                </option>
              ))}
            </select>
          </div>

          {/* Due Date */}
          <div className="w-full sm:w-40 min-w-0">
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="text-sm"
            />
          </div>

          {/* AutoCC Checkbox */}
          <label className="flex items-center whitespace-nowrap">
            <input
              type="checkbox"
              checked={isAuthNetVerified}
              onChange={(e) => setIsAuthNetVerified(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="ml-2 text-sm">AutoCC</span>
          </label>

          {/* Action Buttons */}
          <div className="w-full sm:w-auto flex gap-2">
            <Button
              onClick={handleSaveDraft}
              disabled={isLoading}
              variant="secondary"
              className="flex-1 sm:flex-none text-sm"
            >
              {isLoading ? 'Saving...' : 'Draft'}
            </Button>
            <Button
              onClick={handleSend}
              disabled={isLoading}
              className="flex-1 sm:flex-none text-sm"
            >
              {isLoading ? 'Sending...' : 'Send'}
            </Button>
          </div>
        </div>
      </div>

      {/* Messages */}
      {successMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800 flex gap-2">
          <span>✓</span>
          <span>{successMessage}</span>
        </div>
      )}
      {errorMessage && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
          {errorMessage}
        </div>
      )}

      {/* Invoice Canvas */}
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow-lg rounded-lg p-4 sm:p-5 lg:p-6 space-y-3">
          {/* Header */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start pb-3 border-b border-gray-200">
            {/* Company Info */}
            <div>
              {companyInfo ? (
                <>
                  <h3 className="text-xl font-bold text-gray-900">{companyInfo.company_name}</h3>
                  {(companyInfo.address_line1 || companyInfo.city) && (
                    <>
                      {companyInfo.address_line1 && <p className="text-xs text-gray-600 mt-0.5">{companyInfo.address_line1}</p>}
                      {companyInfo.address_line2 && <p className="text-xs text-gray-600">{companyInfo.address_line2}</p>}
                      {(companyInfo.city || companyInfo.state || companyInfo.zip_code) && (
                        <p className="text-xs text-gray-600">
                          {[companyInfo.city, companyInfo.state, companyInfo.zip_code].filter(Boolean).join(' ')}
                        </p>
                      )}
                    </>
                  )}
                  {companyInfo.phone && <p className="text-xs text-gray-600 mt-1">{companyInfo.phone}</p>}
                  {companyInfo.email && <p className="text-xs text-gray-600">{companyInfo.email}</p>}
                </>
              ) : (
                <>
                  <h3 className="text-xl font-bold text-gray-900">Your Company</h3>
                  <p className="text-xs text-gray-500 mt-1">Set up your company information in Settings</p>
                </>
              )}
            </div>

            {/* Invoice Meta */}
            <div className="space-y-1 text-right md:text-right text-left">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Invoice</p>
              <p className="text-xs font-semibold text-gray-900">Draft</p>
              <p className="text-xs text-gray-600">Created: {today}</p>
              <p className="text-xs text-gray-600">Due: {dueDate}</p>
            </div>
          </div>

          {/* Bill To */}
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Bill To</p>
            {selectedClientObj ? (
              <div className="text-sm text-gray-700 space-y-1">
                <p className="font-semibold text-gray-900">{selectedClientObj.display_name}</p>
                {selectedClientObj.display_name && <p>{selectedClientObj.display_name}</p>}
                {selectedClientObj.email && <p>{selectedClientObj.email}</p>}
                {selectedClientObj.phone && <p>{selectedClientObj.phone}</p>}
                {selectedClientObj.address_line1 && <p>{selectedClientObj.address_line1}</p>}
                {selectedClientObj.address_line2 && <p>{selectedClientObj.address_line2}</p>}
                {selectedClientObj.city && <p>{selectedClientObj.city}, {selectedClientObj.state} {selectedClientObj.zip_code}</p>}
              </div>
            ) : (
              <p className="text-sm text-gray-500 italic">Select a client above</p>
            )}
          </div>

          {/* Prefill Banner - only show if there are actual items */}
          {selectedClient && prefilled && prefilled.line_items && prefilled.line_items.length > 0 && lineItems.length === 0 && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex justify-between items-center">
              <span className="text-sm text-blue-900">Apply items from billing schedules?</span>
              <Button
                onClick={handleApplyPrefilled}
                disabled={isPrefillLoading}
                className="text-sm"
                size="sm"
              >
                {isPrefillLoading ? 'Loading...' : 'Apply'}
              </Button>
            </div>
          )}

          {/* Duplicate Previous Banner */}
          {selectedClient && duplicatePreviousData && duplicatePreviousData.line_items && duplicatePreviousData.line_items.length > 0 && lineItems.length === 0 && (!prefilled?.line_items || prefilled.line_items.length === 0) && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg flex justify-between items-center">
              <span className="text-sm text-green-900">
                Duplicate items from invoice #{duplicatePreviousData.previous_invoice.number} ({duplicatePreviousData.previous_invoice.date})?
              </span>
              <Button
                onClick={handleApplyDuplicatePrevious}
                disabled={isDuplicateLoading}
                className="text-sm"
                size="sm"
              >
                {isDuplicateLoading ? 'Loading...' : 'Duplicate'}
              </Button>
            </div>
          )}

          {/* Line Items */}
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Items</p>

            {/* Desktop Table Header */}
            <div className="hidden md:grid grid-cols-[1fr_60px_90px_80px_36px] gap-3 text-xs font-medium text-gray-600 pb-1 border-b border-gray-300 mb-1">
              <div>Description</div>
              <div className="text-center">Qty</div>
              <div className="text-right">Unit Price</div>
              <div className="text-right">Amount</div>
              <div></div>
            </div>

            {/* Line Items */}
            {lineItems.length > 0 ? (
              <div className="space-y-1">
                {lineItems.map((item) => (
                  <div
                    key={item.id}
                    className="grid grid-cols-1 md:grid-cols-[1fr_60px_90px_80px_36px] gap-2 md:gap-3 items-start md:items-center p-2 rounded-lg hover:bg-gray-50 border border-transparent hover:border-gray-200"
                  >
                    {/* Description */}
                    <textarea
                      ref={el => {
                        if (el) textareaRefs.current[item.id] = el;
                      }}
                      value={item.description}
                      onChange={(e) => {
                        updateLineItem(item.id, 'description', e.target.value);
                        setTimeout(() => adjustTextareaHeight(item.id), 0);
                      }}
                      className="w-full min-w-0 px-2 py-1.5 bg-transparent border-0 outline-none focus:bg-gray-50 focus:ring-1 focus:ring-blue-400 rounded text-sm resize-none"
                      placeholder="Item description"
                      rows="1"
                    />

                    {/* Qty */}
                    <input
                      type="number"
                      value={item.qty}
                      onChange={(e) => updateLineItem(item.id, 'qty', e.target.value)}
                      min="0"
                      step="any"
                      className="w-full min-w-0 px-2 py-1.5 bg-transparent border-0 outline-none focus:bg-gray-50 focus:ring-1 focus:ring-blue-400 rounded text-sm text-center appearance-none"
                    />

                    {/* Unit Price */}
                    <input
                      type="number"
                      value={item.unitPrice}
                      onChange={(e) => updateLineItem(item.id, 'unitPrice', e.target.value)}
                      min="0"
                      step="0.01"
                      className="w-full min-w-0 px-2 py-1.5 bg-transparent border-0 outline-none focus:bg-gray-50 focus:ring-1 focus:ring-blue-400 rounded text-sm text-right appearance-none"
                    />

                    {/* Amount */}
                    <div className="text-sm font-medium text-gray-900 text-right">
                      ${calculateLineTotal(item).toFixed(2)}
                    </div>

                    {/* Remove */}
                    <button
                      onClick={() => removeLineItem(item.id)}
                      className="text-red-600 hover:text-red-800 font-medium text-lg w-full md:w-auto text-center"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 italic py-3 text-center">No items yet</p>
            )}

            {/* Add Item Row */}
            <div className="flex flex-wrap gap-2 mt-2">
              <div className="relative">
                {catalogSelectOpen ? (
                  <select
                    autoFocus
                    onChange={(e) => {
                      if (e.target.value) {
                        handleAddService(e.target.value);
                        setCatalogSelectOpen(false);
                      }
                    }}
                    onBlur={() => setTimeout(() => setCatalogSelectOpen(false), 200)}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    defaultValue=""
                  >
                    <option value="">Choose service...</option>
                    {services.map((service) => (
                      <option key={service.id} value={service.id}>
                        {service.name} - ${service.default_amount.toFixed(2)}
                      </option>
                    ))}
                  </select>
                ) : (
                  <Button
                    onClick={() => setCatalogSelectOpen(true)}
                    variant="outline"
                    size="sm"
                    className="text-sm"
                  >
                    + Catalog
                  </Button>
                )}
              </div>
              <Button
                onClick={handleAddCustomItem}
                variant="outline"
                size="sm"
                className="text-sm"
              >
                + Custom
              </Button>
            </div>
          </div>

          {/* Account Balance Banner */}
          {previousBalance !== 0 && (
            <div className={`p-2 rounded-lg text-xs ${previousBalance > 0 ? 'bg-amber-50 border border-amber-200 text-amber-900' : 'bg-green-50 border border-green-200 text-green-900'}`}>
              {previousBalance > 0 ? (
                <span>ℹ️ Previous balance due: <strong>${previousBalance.toFixed(2)}</strong></span>
              ) : (
                <span>✓ Client has a credit balance: <strong>${Math.abs(previousBalance).toFixed(2)}</strong></span>
              )}
            </div>
          )}

          {/* Totals */}
          {lineItems.length > 0 && (
            <div className="ml-auto w-full max-w-xs space-y-0.5 text-right border-t border-gray-200 pt-2">
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Subtotal:</span>
                <span>${calculateTotal().toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm font-bold text-gray-900 border-t border-gray-300 pt-1">
                <span>Total:</span>
                <span>${calculateTotal().toFixed(2)}</span>
              </div>
            </div>
          )}

          {/* Notes to Client */}
          {lineItems.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">
                Notes to Client
              </label>
              <textarea
                value={notesToClient}
                onChange={(e) => setNotesToClient(e.target.value)}
                placeholder="Visible on the invoice..."
                className="w-full min-h-[60px] px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm resize-y"
              />
            </div>
          )}

          {/* Internal Notes */}
          {lineItems.length > 0 && (
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">
                🔒 Internal Notes — not included on invoice
              </label>
              <textarea
                value={internalNotes}
                onChange={(e) => setInternalNotes(e.target.value)}
                placeholder="For your reference only..."
                className="w-full min-h-[60px] px-3 py-2 border border-amber-200 bg-amber-50 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400 text-sm resize-y"
              />
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
