import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

export default function EstimateBuilderPage() {
  const navigate = useNavigate();
  const [selectedClient, setSelectedClient] = useState('');
  const [lineItems, setLineItems] = useState([]);
  const [expiryDate, setExpiryDate] = useState('');
  const [notes, setNotes] = useState('');

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

  const createEstimate = useMutation({
    mutationFn: async (estimateData) => {
      return apiClient.post('/estimates/', estimateData);
    },
    onSuccess: (response) => {
      alert('Estimate created successfully');
      navigate(`/estimates/${response.data.id}`);
    },
    onError: (error) => {
      alert('Error creating estimate: ' + (error.response?.data?.detail || error.message));
    },
  });

  const handleAddService = (serviceId) => {
    const service = services.find(s => s.id === parseInt(serviceId));
    if (service) {
      setLineItems([
        ...lineItems,
        {
          service_id: service.id,
          service_name: service.name,
          amount: service.default_amount,
          description: service.name,
        },
      ]);
    }
  };

  const handleAddManualLine = () => {
    setLineItems([
      ...lineItems,
      {
        description: 'New Line Item',
        amount: 0,
      },
    ]);
  };

  const handleUpdateLineItem = (idx, field, value) => {
    const updated = [...lineItems];
    updated[idx] = { ...updated[idx], [field]: value };
    setLineItems(updated);
  };

  const handleSaveDraft = async () => {
    if (!selectedClient || lineItems.length === 0) {
      alert('Select a client and add line items');
      return;
    }

    try {
      const formattedItems = lineItems.map(item => ({
        description: item.description || 'Estimate Item',
        quantity: 1.0,
        unit_amount: parseFloat(item.amount) || 0,
        service_id: item.service_id || null,
      }));

      await createEstimate.mutateAsync({
        client_id: parseInt(selectedClient),
        created_date: new Date().toISOString().split('T')[0],
        expiry_date: expiryDate || null,
        line_items: formattedItems,
        notes,
        status: 'draft',
      });
    } catch (error) {
      // Error is handled in onError
    }
  };

  const handleMarkReady = async () => {
    if (!selectedClient || lineItems.length === 0) {
      alert('Select a client and add line items');
      return;
    }

    try {
      const formattedItems = lineItems.map(item => ({
        description: item.description || 'Estimate Item',
        quantity: 1.0,
        unit_amount: parseFloat(item.amount) || 0,
        service_id: item.service_id || null,
      }));

      await createEstimate.mutateAsync({
        client_id: parseInt(selectedClient),
        created_date: new Date().toISOString().split('T')[0],
        expiry_date: expiryDate || null,
        line_items: formattedItems,
        notes,
        status: 'sent',
      });
    } catch (error) {
      // Error is handled in onError
    }
  };

  return (
    <Layout title="Create Estimate">
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
                Expiry Date
              </label>
              <Input
                type="date"
                value={expiryDate}
                onChange={(e) => setExpiryDate(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Additional notes..."
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </CardContent>
        </Card>

        {/* Add Items */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Add Items</CardTitle>
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
            <Button
              onClick={handleAddManualLine}
              variant="outline"
              className="w-full"
            >
              + Add Manual Line Item
            </Button>
            <p className="text-xs text-gray-500">Add services or manual line items for the estimate</p>
          </CardContent>
        </Card>

        {/* Estimate Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Estimate Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border rounded-lg p-3 bg-gray-50 space-y-2 max-h-48 overflow-y-auto">
              {lineItems.length > 0 ? (
                lineItems.map((item, idx) => (
                  <div key={idx} className="border-b border-gray-200 pb-2 last:border-b-0">
                    <div className="flex gap-2 mb-2">
                      <input
                        type="text"
                        value={item.description || ''}
                        onChange={(e) => handleUpdateLineItem(idx, 'description', e.target.value)}
                        placeholder="Description"
                        className="flex-1 px-2 py-1 text-xs border border-gray-200 rounded"
                      />
                      <input
                        type="number"
                        value={item.amount || ''}
                        onChange={(e) => handleUpdateLineItem(idx, 'amount', e.target.value)}
                        placeholder="Amount"
                        step="0.01"
                        className="w-20 px-2 py-1 text-xs border border-gray-200 rounded"
                      />
                      <button
                        onClick={() => setLineItems(lineItems.filter((_, i) => i !== idx))}
                        className="text-red-600 hover:text-red-800 text-xs font-medium"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">No line items yet</p>
              )}
            </div>

            {lineItems.length > 0 && (
              <div className="border-t pt-2">
                <div className="flex justify-between font-semibold">
                  <span>Total Estimate:</span>
                  <span>
                    ${lineItems
                      .reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0)
                      .toFixed(2)}
                  </span>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Button
                onClick={handleSaveDraft}
                disabled={createEstimate.isPending}
                className="w-full"
                variant="secondary"
              >
                {createEstimate.isPending ? 'Saving...' : 'Save Draft'}
              </Button>
              <Button
                onClick={handleMarkReady}
                disabled={createEstimate.isPending}
                className="w-full"
              >
                {createEstimate.isPending ? 'Creating...' : 'Mark Ready & Send'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
