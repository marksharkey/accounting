import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';

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

  const handleAddService = (service) => {
    setLineItems([
      ...lineItems,
      {
        service_id: service.id,
        service_name: service.name,
        amount: service.default_amount,
      },
    ]);
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
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Select Client</h3>
          <select
            value={selectedClient}
            onChange={(e) => setSelectedClient(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Choose a client...</option>
            {clients &&
              clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
          </select>

          {selectedClient && (
            <button
              onClick={handlePrefillClick}
              className="mt-4 w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700"
            >
              Prefill from Schedules
            </button>
          )}
        </div>

        {/* Service Catalog */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Add Services</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {services &&
              services.map((service) => (
                <button
                  key={service.id}
                  onClick={() => handleAddService(service)}
                  className="w-full text-left px-3 py-2 border border-gray-200 rounded hover:bg-gray-50"
                >
                  <div className="font-medium text-sm">{service.name}</div>
                  <div className="text-xs text-gray-600">${service.default_amount}</div>
                </button>
              ))}
          </div>
        </div>

        {/* Invoice Preview */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Line Items</h3>
          <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
            {lineItems.map((item, idx) => (
              <div
                key={idx}
                className="flex justify-between text-sm border-b pb-2"
              >
                <span>{item.service_name}</span>
                <span>${item.amount}</span>
              </div>
            ))}
          </div>

          {lineItems.length > 0 && (
            <div className="border-t pt-2 mb-4">
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

          <label className="flex items-center mb-4">
            <input
              type="checkbox"
              checked={isAuthNetVerified}
              onChange={(e) => setIsAuthNetVerified(e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm">A.net Verified</span>
          </label>

          <div className="space-y-2">
            <button
              onClick={handleSaveDraft}
              disabled={createInvoice.isPending}
              className="w-full bg-gray-600 text-white py-2 rounded-lg hover:bg-gray-700 disabled:opacity-50"
            >
              Save Draft
            </button>
            <button
              onClick={handleMarkReady}
              disabled={createInvoice.isPending}
              className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              Mark Ready
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
