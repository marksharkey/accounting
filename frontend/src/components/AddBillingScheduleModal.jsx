import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Input from './ui/Input';
import Button from './ui/Button';

export default function AddBillingScheduleModal({ isOpen, onClose, clientId }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    description: '',
    amount: '',
    cycle: 'monthly',
    next_bill_date: '',
    authnet_recurring: false,
    notes: '',
  });

  const createMutation = useMutation({
    mutationFn: async (data) => {
      const response = await apiClient.post(`/clients/${clientId}/billing-schedules`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients', clientId, 'schedules'] });
      handleClose();
    },
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (name === 'amount' ? (value === '' ? '' : parseFloat(value)) : value),
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const submitData = {
      ...formData,
      amount: parseFloat(formData.amount),
    };
    createMutation.mutate(submitData);
  };

  const handleClose = () => {
    setFormData({
      description: '',
      amount: '',
      cycle: 'monthly',
      next_bill_date: '',
      authnet_recurring: false,
      notes: '',
    });
    onClose();
  };

  const footerContent = (
    <div className="space-y-2">
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
          disabled={createMutation.isPending}
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
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description *
          </label>
          <Input
            type="text"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="e.g., Monthly Retainer"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Amount *
          </label>
          <Input
            type="number"
            name="amount"
            value={formData.amount}
            onChange={handleChange}
            placeholder="0.00"
            step="0.01"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Billing Cycle *
          </label>
          <select
            name="cycle"
            value={formData.cycle}
            onChange={handleChange}
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
            name="next_bill_date"
            value={formData.next_bill_date}
            onChange={handleChange}
            required
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="authnet_recurring"
            name="authnet_recurring"
            checked={formData.authnet_recurring}
            onChange={handleChange}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
          />
          <label htmlFor="authnet_recurring" className="text-sm font-medium text-gray-700">
            AuthNet Recurring
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            placeholder="Optional notes"
            rows="3"
            className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
      </form>
    </Modal>
  );
}
