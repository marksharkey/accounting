import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Input from './ui/Input';
import Button from './ui/Button';

export default function AddBillingScheduleModal({ isOpen, onClose, clientId }) {
  const queryClient = useQueryClient();
  const [lineItems, setLineItems] = useState([]);
  const [cycle, setCycle] = useState('monthly');
  const [nextBillDate, setNextBillDate] = useState('');
  const [autoccRecurring, setAutoccRecurring] = useState(false);
  const [notes, setNotes] = useState('');
  const [catalogSelectOpen, setCatalogSelectOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Fetch services
  const { data: serviceData } = useQuery({
    queryKey: ['services'],
    queryFn: async () => {
      const response = await apiClient.get('/services/');
      return response.data;
    },
    enabled: isOpen,
  });

  const services = Array.isArray(serviceData) ? serviceData : serviceData?.items || [];

  const createMutation = useMutation({
    mutationFn: async (data) => {
      const response = await apiClient.post(`/clients/${clientId}/billing-schedules`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients', clientId, 'schedules'] });
      handleClose();
    },
    onError: (error) => {
      setErrorMessage(error.response?.data?.detail || 'Failed to create billing schedule');
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

  const calculateLineTotal = (item) => (item.qty || 0) * (item.unitPrice || 0);
  const calculateTotal = () => lineItems.reduce((sum, item) => sum + calculateLineTotal(item), 0);

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (lineItems.length === 0) {
      setErrorMessage('Add at least one line item');
      return;
    }

    if (!nextBillDate) {
      setErrorMessage('Set the next bill date');
      return;
    }

    const formattedItems = lineItems.map((item, idx) => ({
      description: item.description || 'Service',
      quantity: item.qty || 1,
      unit_amount: item.unitPrice || 0,
      service_id: item.service_id || null,
      sort_order: idx,
    }));

    const submitData = {
      cycle,
      next_bill_date: nextBillDate,
      autocc_recurring: autoccRecurring,
      notes,
      line_items: formattedItems,
    };

    createMutation.mutate(submitData);
  };

  const handleClose = () => {
    setLineItems([]);
    setCycle('monthly');
    setNextBillDate('');
    setAutoccRecurring(false);
    setNotes('');
    setCatalogSelectOpen(false);
    setErrorMessage('');
    onClose();
  };

  const footerContent = (
    <div className="space-y-2">
      {errorMessage && (
        <div className="text-red-600 text-sm">Error: {errorMessage}</div>
      )}
      {createMutation.isError && (
        <div className="text-red-600 text-sm">
          Error: {createMutation.error?.response?.data?.detail || 'Failed to create billing schedule'}
        </div>
      )}
      <div className="flex gap-3 justify-end">
        <Button
          type="button"
          variant="secondary"
          onClick={handleClose}
          disabled={createMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={createMutation.isPending || lineItems.length === 0}
          form="billing-schedule-form"
        >
          {createMutation.isPending ? 'Creating...' : 'Create Schedule'}
        </Button>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add Billing Schedule" footer={footerContent}>
      <form id="billing-schedule-form" onSubmit={handleSubmit} className="space-y-4">
        {/* Schedule Details */}
        <div className="space-y-4 border-b pb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Billing Cycle *
            </label>
            <select
              value={cycle}
              onChange={(e) => setCycle(e.target.value)}
              className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              required
            >
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="semi_annual">Semi-Annual</option>
              <option value="annual">Annual</option>
              <option value="multi_year">Multi-Year</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Next Bill Date *
            </label>
            <Input
              type="date"
              value={nextBillDate}
              onChange={(e) => setNextBillDate(e.target.value)}
              required
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autocc_recurring"
              checked={autoccRecurring}
              onChange={(e) => setAutoccRecurring(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
            />
            <label htmlFor="autocc_recurring" className="text-sm font-medium text-gray-700">
              AutoCC Recurring
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes"
              rows="2"
              className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            />
          </div>
        </div>

        {/* Line Items */}
        <div className="space-y-3">
          <div className="flex gap-2">
            <div className="flex-1">
              <button
                type="button"
                onClick={() => setCatalogSelectOpen(!catalogSelectOpen)}
                className="w-full px-3 py-2 text-sm bg-blue-50 border border-blue-200 text-blue-700 rounded-md hover:bg-blue-100"
              >
                + Catalog
              </button>
            </div>
            <div className="flex-1">
              <button
                type="button"
                onClick={handleAddCustomItem}
                className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 text-gray-700 rounded-md hover:bg-gray-100"
              >
                + Custom
              </button>
            </div>
          </div>

          {catalogSelectOpen && (
            <div>
              <select
                onChange={(e) => handleAddService(e.target.value)}
                defaultValue=""
                className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                <option value="">Select a service...</option>
                {services.map(service => (
                  <option key={service.id} value={service.id}>
                    {service.name} (${parseFloat(service.default_amount).toFixed(2)})
                  </option>
                ))}
              </select>
            </div>
          )}

          {lineItems.length > 0 && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-700">Line Items</div>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {lineItems.map((item) => (
                  <div key={item.id} className="flex gap-2 items-start bg-gray-50 p-2 rounded border border-gray-200">
                    <div className="flex-1 space-y-1 min-w-0">
                      <input
                        type="text"
                        value={item.description}
                        onChange={(e) => updateLineItem(item.id, 'description', e.target.value)}
                        placeholder="Description"
                        className="w-full text-xs rounded border border-gray-300 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                      <div className="flex gap-2 text-xs">
                        <input
                          type="number"
                          value={item.qty}
                          onChange={(e) => updateLineItem(item.id, 'qty', e.target.value)}
                          placeholder="Qty"
                          step="0.01"
                          className="w-16 rounded border border-gray-300 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                        <input
                          type="number"
                          value={item.unitPrice}
                          onChange={(e) => updateLineItem(item.id, 'unitPrice', e.target.value)}
                          placeholder="Unit Price"
                          step="0.01"
                          className="w-20 rounded border border-gray-300 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                        <div className="flex-1 text-right pt-1 font-medium">
                          ${calculateLineTotal(item).toFixed(2)}
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeLineItem(item.id)}
                      className="text-red-600 hover:text-red-800 font-bold mt-1"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>

              <div className="border-t pt-2 flex justify-end">
                <div className="text-right">
                  <div className="text-sm text-gray-600">Total:</div>
                  <div className="text-lg font-bold text-gray-900">
                    ${calculateTotal().toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </form>
    </Modal>
  );
}
