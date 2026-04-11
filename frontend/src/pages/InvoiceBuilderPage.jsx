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
          service_name: service.name,
          amount: service.default_amount,
        },
      ]);
    }
  };

  const handleSaveDraft = async () => {
    if (!selectedClient || lineItems.length === 0) {
      alert('Select a client and add line items');
      return;
    }

    try {
      const formattedItems = lineItems.map(item => ({
        description: item.service_name || item.description || 'Service',
        quantity: 1.0,
        unit_amount: item.amount || 0,
        service_id: item.service_id || null,
      }));

      await createInvoice.mutateAsync({
        client_id: parseInt(selectedClient),
        created_date: new Date().toISOString().split('T')[0],
        due_date: dueDate,
        line_items: formattedItems,
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
        description: item.service_name || item.description || 'Service',
        quantity: 1.0,
        unit_amount: item.amount || 0,
        service_id: item.service_id || null,
      }));

      await createInvoice.mutateAsync({
        client_id: parseInt(selectedClient),
        created_date: new Date().toISOString().split('T')[0],
        due_date: dueDate,
        line_items: formattedItems,
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

        {/* Service Catalog */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Add Services</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <select
              onChange={(e) => {
                if (e.target.value) {
                  handleAddService(e.target.value);
                  e.target.value = '';
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              defaultValue=""
            >
              <option value="">Select a service to add...</option>
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
            <p className="text-xs text-gray-500">Select a service and it will be added to your invoice</p>
          </CardContent>
        </Card>

        {/* Invoice Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Invoice Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border rounded-lg p-3 bg-gray-50 space-y-2 max-h-48 overflow-y-auto">
              {lineItems.length > 0 ? (
                lineItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center text-sm border-b border-gray-200 pb-2 last:border-b-0"
                  >
                    <div className="flex-1">
                      <span className="font-medium text-gray-700">{item.service_name || item.description || item.name || 'Unnamed Service'}</span>
                      <span className="font-medium text-gray-900 ml-2">${item.amount.toFixed(2)}</span>
                    </div>
                    <button
                      onClick={() => setLineItems(lineItems.filter((_, i) => i !== idx))}
                      className="ml-2 text-red-600 hover:text-red-800 text-xs font-medium"
                    >
                      Remove
                    </button>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">No line items yet</p>
              )}
            </div>

            {lineItems.length > 0 && (
              <div className="border-t pt-2">
                <div className="flex justify-between font-semibold">
                  <span>Total:</span>
                  <span>
                    ${lineItems
                      .reduce((sum, item) => sum + item.amount, 0)
                      .toFixed(2)}
                  </span>
                </div>
              </div>
            )}

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={isAuthNetVerified}
                onChange={(e) => setIsAuthNetVerified(e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm">A.net Verified</span>
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
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
