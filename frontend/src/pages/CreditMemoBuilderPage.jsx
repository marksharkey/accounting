import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

export default function CreditMemoBuilderPage() {
  const navigate = useNavigate();
  const [selectedClient, setSelectedClient] = useState('');
  const [lineItems, setLineItems] = useState([]);
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

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

  const { data: clientData } = useQuery({
    queryKey: ['clients-all'],
    queryFn: async () => {
      const response = await apiClient.get('/clients/', {
        params: { limit: 10000 },
      });
      return response.data;
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

  const createMemo = useMutation({
    mutationFn: async (memoData) => {
      return apiClient.post('/credit-memos/', memoData);
    },
    onSuccess: (response) => {
      setSuccessMessage('Credit memo created successfully');
      setTimeout(() => {
        navigate(`/credit-memos/${response.data.id}`);
      }, 1000);
    },
    onError: (error) => {
      setErrorMessage(error.response?.data?.detail || error.message);
      setTimeout(() => setErrorMessage(''), 5000);
    },
  });

  const handleAddService = (serviceId) => {
    const service = services.find(s => s.id === parseInt(serviceId));
    if (service) {
      setLineItems([
        ...lineItems,
        {
          id: crypto.randomUUID(),
          service_id: service.id,
          description: service.name,
          amount: service.default_amount,
        },
      ]);
    }
  };

  const handleAddManualLine = () => {
    setLineItems([
      ...lineItems,
      {
        id: crypto.randomUUID(),
        service_id: null,
        description: '',
        amount: 0,
      },
    ]);
  };

  const handleUpdateLineItem = (id, field, value) => {
    setLineItems(lineItems.map(item =>
      item.id === id
        ? { ...item, [field]: field === 'amount' ? parseFloat(value) || 0 : value }
        : item
    ));
  };

  const removeLineItem = (id) => {
    setLineItems(lineItems.filter(item => item.id !== id));
  };

  const calculateTotal = () => lineItems.reduce((sum, item) => sum + (item.amount || 0), 0);

  const handleSaveDraft = async () => {
    if (!selectedClient || lineItems.length === 0) {
      setErrorMessage('Select a client and add line items');
      setTimeout(() => setErrorMessage(''), 3000);
      return;
    }

    const formattedItems = lineItems.map(item => ({
      description: item.description || 'Credit Memo Item',
      quantity: 1.0,
      unit_amount: item.amount || 0,
      service_id: item.service_id || null,
    }));

    setIsLoading(true);
    try {
      await createMemo.mutateAsync({
        client_id: parseInt(selectedClient),
        created_date: new Date().toISOString().split('T')[0],
        line_items: formattedItems,
        reason,
        notes,
        status: 'draft',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMemo = async () => {
    if (!selectedClient || lineItems.length === 0) {
      setErrorMessage('Select a client and add line items');
      setTimeout(() => setErrorMessage(''), 3000);
      return;
    }

    const formattedItems = lineItems.map(item => ({
      description: item.description || 'Credit Memo Item',
      quantity: 1.0,
      unit_amount: item.amount || 0,
      service_id: item.service_id || null,
    }));

    setIsLoading(true);
    try {
      // Create as draft first
      const response = await createMemo.mutateAsync({
        client_id: parseInt(selectedClient),
        created_date: new Date().toISOString().split('T')[0],
        line_items: formattedItems,
        reason,
        notes,
        status: 'draft',
      });

      // Then send it (which sends the email)
      await apiClient.post(`/credit-memos/${response.data.id}/send`);
      setSuccessMessage('Credit memo created and sent successfully');
      setTimeout(() => {
        navigate(`/credit-memos/${response.data.id}`);
      }, 1000);
    } catch (error) {
      setErrorMessage(error.response?.data?.detail || error.message);
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
              onClick={handleSendMemo}
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

      {/* Credit Memo Canvas */}
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow-lg rounded-lg p-6 sm:p-8 lg:p-10 space-y-6">
          {/* Header */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start pb-6 border-b border-gray-200">
            {/* Memo Info */}
            <div>
              <h3 className="text-2xl font-bold text-gray-900">Credit Memo</h3>
              <p className="text-sm text-gray-500 mt-2">Created: {today}</p>
            </div>

            {/* Client Display */}
            <div className="text-right text-left md:text-right">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Bill To</p>
              {selectedClientObj ? (
                <div className="text-sm text-gray-700">
                  <p className="font-semibold text-gray-900">{selectedClientObj.display_name}</p>
                </div>
              ) : (
                <p className="text-sm text-gray-500 italic">Select a client above</p>
              )}
            </div>
          </div>

          {/* Line Items */}
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Credit Items</p>

            {/* Desktop Table Header */}
            <div className="hidden md:grid grid-cols-[1fr_100px_36px] gap-3 text-xs font-medium text-gray-600 pb-2 border-b border-gray-300 mb-2">
              <div>Description</div>
              <div className="text-right">Amount</div>
              <div></div>
            </div>

            {/* Line Items */}
            {lineItems.length > 0 ? (
              <div className="space-y-3">
                {lineItems.map((item) => (
                  <div
                    key={item.id}
                    className="grid grid-cols-1 md:grid-cols-[1fr_100px_36px] gap-2 md:gap-3 items-start md:items-center p-3 rounded-lg hover:bg-gray-50 border border-transparent hover:border-gray-200"
                  >
                    {/* Description */}
                    <textarea
                      ref={el => {
                        if (el) textareaRefs.current[item.id] = el;
                      }}
                      value={item.description}
                      onChange={(e) => {
                        handleUpdateLineItem(item.id, 'description', e.target.value);
                        setTimeout(() => adjustTextareaHeight(item.id), 0);
                      }}
                      className="w-full min-w-0 px-2 py-1.5 bg-transparent border-0 outline-none focus:bg-gray-50 focus:ring-1 focus:ring-blue-400 rounded text-sm resize-none"
                      placeholder="Item description"
                      rows="1"
                    />

                    {/* Amount */}
                    <input
                      type="number"
                      value={item.amount}
                      onChange={(e) => handleUpdateLineItem(item.id, 'amount', e.target.value)}
                      min="0"
                      step="0.01"
                      className="w-full min-w-0 px-2 py-1.5 bg-transparent border-0 outline-none focus:bg-gray-50 focus:ring-1 focus:ring-blue-400 rounded text-sm text-right appearance-none"
                      placeholder="0.00"
                    />

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
              <p className="text-sm text-gray-500 italic py-6 text-center">No items yet</p>
            )}

            {/* Add Item Buttons */}
            <div className="flex flex-wrap gap-2 mt-4">
              <Button
                onClick={handleAddManualLine}
                variant="outline"
                size="sm"
                className="text-sm"
              >
                + Manual Credit
              </Button>
              <div className="relative">
                <select
                  onChange={(e) => {
                    if (e.target.value) {
                      handleAddService(e.target.value);
                      e.target.value = '';
                    }
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  defaultValue=""
                >
                  <option value="">+ From Catalog</option>
                  {services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} - ${service.default_amount.toFixed(2)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Totals */}
          {lineItems.length > 0 && (
            <div className="ml-auto w-full max-w-xs space-y-1 text-right border-t border-gray-200 pt-4">
              <div className="flex justify-between text-base font-bold text-gray-900">
                <span>Total Credit:</span>
                <span>${calculateTotal().toFixed(2)}</span>
              </div>
            </div>
          )}

          {/* Reason for Credit */}
          {selectedClient && (
            <div className="pt-6 border-t border-gray-200">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                Reason for Credit
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g., Service refund, adjustment, etc."
                className="w-full min-h-[80px] px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm resize-y"
              />
            </div>
          )}

          {/* Notes */}
          {selectedClient && (
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-2">
                🔒 Internal Notes — not included on memo
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="For your reference only..."
                className="w-full min-h-[80px] px-3 py-2 border border-amber-200 bg-amber-50 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400 text-sm resize-y"
              />
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
