import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

export default function InvoiceBuilderPage() {
  const [selectedClient, setSelectedClient] = useState('');
  const [lineItems, setLineItems] = useState([]);
  const [isAuthNetVerified, setIsAuthNetVerified] = useState(false);
  const [dueDate, setDueDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1).toISOString().split('T')[0]);
  const [notesToClient, setNotesToClient] = useState('');
  const [internalNotes, setInternalNotes] = useState('');
  const [customItemDesc, setCustomItemDesc] = useState('');
  const [customItemQty, setCustomItemQty] = useState(1);
  const [customItemPrice, setCustomItemPrice] = useState('');

  const { data: clientData } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const response = await apiClient.get('/clients/');
      return response.data;
    },
  });

  const clients = clientData?.items || [];

  const { data: serviceData } = useQuery({
    queryKey: ['services'],
    queryFn: async () => {
      const response = await apiClient.get('/services/');
      return response.data;
    },
  });

  const services = Array.isArray(serviceData) ? serviceData : serviceData?.items || [];

  const { data: prefilled, isLoading: isPrefillLoading } = useQuery({
    queryKey: ['invoices', 'prefill', selectedClient],
    queryFn: async () => {
      if (!selectedClient) return null;
      const response = await apiClient.post(
        `/invoices/prefill/${selectedClient}`,
      );
      return response.data;
    },
    enabled: !!selectedClient,
  });

  const createInvoice = useMutation({
    mutationFn: async (invoiceData) => {
      return apiClient.post('/invoices/', invoiceData);
    },
    onSuccess: () => {
      setSelectedClient('');
      setLineItems([]);
      setIsAuthNetVerified(false);
      setDueDate(new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1).toISOString().split('T')[0]);
      setNotesToClient('');
      setInternalNotes('');
      setCustomItemDesc('');
      setCustomItemQty(1);
      setCustomItemPrice('');
    },
  });

  const handlePrefillClick = () => {
    if (prefilled && prefilled.line_items) {
      setLineItems(prefilled.line_items);
      setDueDate(prefilled.suggested_due_date);
    }
  };

  const handleAddService = (serviceId) => {
    const service = services.find(s => s.id === parseInt(serviceId));
    if (service) {
      setLineItems([
        ...lineItems,
        {
          service_id: service.id,
          description: service.name,
          quantity: 1,
          unit_amount: service.default_amount,
        },
      ]);
    }
  };

  const handleAddCustomItem = () => {
    if (!customItemDesc || !customItemPrice) {
      alert('Please fill in description and price');
      return;
    }
    setLineItems([
      ...lineItems,
      {
        service_id: null,
        description: customItemDesc,
        quantity: customItemQty,
        unit_amount: parseFloat(customItemPrice),
      },
    ]);
    setCustomItemDesc('');
    setCustomItemQty(1);
    setCustomItemPrice('');
  };

  const handleUpdateLineItem = (idx, field, value) => {
    const updated = [...lineItems];
    updated[idx] = { ...updated[idx], [field]: field === 'quantity' || field === 'unit_amount' ? parseFloat(value) || 0 : value };
    setLineItems(updated);
  };

  const calculateLineItemTotal = (item) => {
    return (item.quantity || 0) * (item.unit_amount || 0);
  };

  const calculateInvoiceTotal = () => {
    return lineItems.reduce((sum, item) => sum + calculateLineItemTotal(item), 0);
  };

  const handleSaveDraft = async () => {
    if (!selectedClient || lineItems.length === 0) {
      alert('Select a client and add line items');
      return;
    }

    try {
      const formattedItems = lineItems.map(item => ({
        description: item.description || 'Service',
        quantity: item.quantity || 1.0,
        unit_amount: item.unit_amount || 0,
        service_id: item.service_id || null,
      }));

      await createInvoice.mutateAsync({
        client_id: parseInt(selectedClient),
        created_date: new Date().toISOString().split('T')[0],
        due_date: dueDate,
        line_items: formattedItems,
        notes: notesToClient || null,
        internal_notes: internalNotes || null,
        status: 'draft',
      });
      alert('Invoice saved as draft');
    } catch (error) {
      alert('Error saving invoice: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleMarkReady = async () => {
    if (!selectedClient || lineItems.length === 0) {
      alert('Select a client and add line items');
      return;
    }

    try {
      const formattedItems = lineItems.map(item => ({
        description: item.description || 'Service',
        quantity: item.quantity || 1.0,
        unit_amount: item.unit_amount || 0,
        service_id: item.service_id || null,
      }));

      await createInvoice.mutateAsync({
        client_id: parseInt(selectedClient),
        created_date: new Date().toISOString().split('T')[0],
        due_date: dueDate,
        line_items: formattedItems,
        notes: notesToClient || null,
        internal_notes: internalNotes || null,
        status: 'ready',
        authnet_verified: isAuthNetVerified,
      });
      alert('Invoice marked as ready');
    } catch (error) {
      alert('Error creating invoice: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <Layout title="Invoice Builder">
      <div className="grid grid-cols-3 gap-6">
        {/* Client Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Select Client</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Choose a client...</option>
              {clients && clients.length > 0 &&
                clients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.company_name || client.name}
                  </option>
                ))}
            </select>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Due Date
              </label>
              <Input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>

            {selectedClient && (
              <Button
                onClick={handlePrefillClick}
                className="w-full"
                disabled={isPrefillLoading}
              >
                {isPrefillLoading ? 'Loading...' : 'Prefill from Schedules'}
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Service Catalog & Custom Items */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Add Line Items</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-2 block">From Service Catalog</label>
              <select
                onChange={(e) => {
                  if (e.target.value) {
                    handleAddService(e.target.value);
                    e.target.value = '';
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                defaultValue=""
              >
                <option value="">Select a service...</option>
                {services && services.length > 0 ? (
                  services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} - ${service.default_amount.toFixed(2)}
                    </option>
                  ))
                ) : (
                  <option disabled>No services available</option>
                )}
              </select>
            </div>

            <div className="border-t pt-4">
              <label className="text-xs font-medium text-gray-600 mb-2 block">Custom Item</label>
              <div className="space-y-2">
                <Input
                  type="text"
                  placeholder="Description"
                  value={customItemDesc}
                  onChange={(e) => setCustomItemDesc(e.target.value)}
                  className="text-sm"
                />
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    placeholder="Qty"
                    value={customItemQty}
                    onChange={(e) => setCustomItemQty(parseFloat(e.target.value) || 1)}
                    min="0.01"
                    step="0.01"
                    className="text-sm"
                  />
                  <Input
                    type="number"
                    placeholder="Unit Price"
                    value={customItemPrice}
                    onChange={(e) => setCustomItemPrice(e.target.value)}
                    step="0.01"
                    className="text-sm"
                  />
                </div>
                <Button
                  onClick={handleAddCustomItem}
                  variant="outline"
                  className="w-full text-sm"
                >
                  Add Item
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Invoice Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Invoice Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 max-h-[800px] overflow-y-auto">
            {/* Line Items Table */}
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-600">Line Items</p>
              {lineItems.length > 0 ? (
                <div className="space-y-2 border rounded-lg p-3 bg-gray-50">
                  {/* Header */}
                  <div className="grid grid-cols-12 gap-1 text-xs font-medium text-gray-600 pb-2 border-b">
                    <div className="col-span-5">Description</div>
                    <div className="col-span-2 text-center">Qty</div>
                    <div className="col-span-2 text-right">Price</div>
                    <div className="col-span-2 text-right">Amount</div>
                    <div className="col-span-1"></div>
                  </div>
                  {/* Items */}
                  {lineItems.map((item, idx) => (
                    <div key={idx} className="grid grid-cols-12 gap-1 items-center text-xs pb-2 border-b last:border-b-0">
                      <input
                        type="text"
                        value={item.description}
                        onChange={(e) => handleUpdateLineItem(idx, 'description', e.target.value)}
                        className="col-span-5 px-2 py-1 border border-gray-200 rounded text-xs"
                      />
                      <input
                        type="number"
                        value={item.quantity}
                        onChange={(e) => handleUpdateLineItem(idx, 'quantity', e.target.value)}
                        step="0.01"
                        min="0"
                        className="col-span-2 px-2 py-1 border border-gray-200 rounded text-xs text-center"
                      />
                      <input
                        type="number"
                        value={item.unit_amount}
                        onChange={(e) => handleUpdateLineItem(idx, 'unit_amount', e.target.value)}
                        step="0.01"
                        min="0"
                        className="col-span-2 px-2 py-1 border border-gray-200 rounded text-xs text-right"
                      />
                      <div className="col-span-2 text-right font-medium">
                        ${calculateLineItemTotal(item).toFixed(2)}
                      </div>
                      <button
                        onClick={() => setLineItems(lineItems.filter((_, i) => i !== idx))}
                        className="col-span-1 text-red-600 hover:text-red-800 font-medium text-xs"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">No line items yet</p>
              )}
            </div>

            {/* Total */}
            {lineItems.length > 0 && (
              <div className="border-t pt-2">
                <div className="flex justify-between font-semibold">
                  <span>Total:</span>
                  <span>${calculateInvoiceTotal().toFixed(2)}</span>
                </div>
              </div>
            )}

            {/* Notes Fields */}
            <div className="space-y-3 border-t pt-4">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">
                  Notes to Client
                </label>
                <textarea
                  value={notesToClient}
                  onChange={(e) => setNotesToClient(e.target.value)}
                  placeholder="Visible to client on invoice..."
                  rows="2"
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">
                  Internal Notes
                </label>
                <textarea
                  value={internalNotes}
                  onChange={(e) => setInternalNotes(e.target.value)}
                  placeholder="For internal use only..."
                  rows="2"
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* A.net & Buttons */}
            <div className="space-y-3 border-t pt-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={isAuthNetVerified}
                  onChange={(e) => setIsAuthNetVerified(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-xs">A.net Verified</span>
              </label>

              <div className="space-y-2">
                <Button
                  onClick={handleSaveDraft}
                  disabled={createInvoice.isPending}
                  className="w-full"
                  variant="secondary"
                >
                  {createInvoice.isPending ? 'Saving...' : 'Save Draft'}
                </Button>
                <Button
                  onClick={handleMarkReady}
                  disabled={createInvoice.isPending}
                  className="w-full"
                >
                  {createInvoice.isPending ? 'Creating...' : 'Mark Ready'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
