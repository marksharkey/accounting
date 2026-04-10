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

  const { data: prefilled } = useQuery({
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
  });

  const handlePrefillClick = () => {
    if (prefilled && prefilled.line_items) {
      setLineItems(prefilled.line_items);
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
      await createInvoice.mutateAsync({
        client_id: parseInt(selectedClient),
        line_items: lineItems,
        status: 'draft',
      });
      alert('Invoice saved as draft');
      setSelectedClient('');
      setLineItems([]);
    } catch (error) {
      alert('Error saving invoice');
    }
  };

  const handleMarkReady = async () => {
    if (!selectedClient || lineItems.length === 0) {
      alert('Select a client and add line items');
      return;
    }

    try {
      await createInvoice.mutateAsync({
        client_id: parseInt(selectedClient),
        line_items: lineItems,
        status: 'ready',
        authnet_verified: isAuthNetVerified,
      });
      alert('Invoice marked as ready');
      setSelectedClient('');
      setLineItems([]);
    } catch (error) {
      alert('Error creating invoice');
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

            {selectedClient && (
              <Button
                onClick={handlePrefillClick}
                className="w-full"
              >
                Prefill from Schedules
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
                    className="flex justify-between text-sm border-b border-gray-200 pb-2 last:border-b-0"
                  >
                    <span className="font-medium text-gray-700">{item.service_name || item.description || item.name || 'Unnamed Service'}</span>
                    <span className="font-medium text-gray-900">${item.amount.toFixed(2)}</span>
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
