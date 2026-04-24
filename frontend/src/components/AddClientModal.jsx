import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Input from './ui/Input';
import Button from './ui/Button';

export default function AddClientModal({ isOpen, onClose }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    company_name: '',
    display_name: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    autocc_recurring: false,
    autocc_customer_id: '',
    late_fee_type: 'none',
    late_fee_amount: '',
    late_fee_grace_days: '',
    notes: '',
  });

  const createMutation = useMutation({
    mutationFn: async (data) => {
      const response = await apiClient.post('/clients/', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      handleClose();
    },
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox'
        ? checked
        : name === 'late_fee_amount' || name === 'late_fee_grace_days'
        ? value === '' ? '' : Number(value)
        : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const submitData = {
      ...formData,
      late_fee_amount: formData.late_fee_amount === '' ? 0 : parseFloat(formData.late_fee_amount),
      late_fee_grace_days: formData.late_fee_grace_days === '' ? 0 : parseInt(formData.late_fee_grace_days),
    };
    createMutation.mutate(submitData);
  };

  const handleClose = () => {
    setFormData({
      company_name: '',
      display_name: '',
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      autocc_recurring: false,
      autocc_customer_id: '',
      late_fee_type: 'none',
      late_fee_amount: '',
      late_fee_grace_days: '',
      notes: '',
    });
    onClose();
  };

  const footerContent = (
    <div className="space-y-2">
      {createMutation.isError && (
        <div className="text-red-600 text-sm">
          Error: {createMutation.error?.response?.data?.detail || 'Failed to create client'}
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
          form="client-form"
        >
          {createMutation.isPending ? 'Creating...' : 'Create Client'}
        </Button>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add New Client" footer={footerContent}>
      <form id="client-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Company Name *
          </label>
          <Input
            type="text"
            name="company_name"
            value={formData.company_name}
            onChange={handleChange}
            placeholder="Company name"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Display Name
          </label>
          <Input
            type="text"
            name="display_name"
            value={formData.display_name}
            onChange={handleChange}
            placeholder="e.g. 'Smith, John'"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              First Name
            </label>
            <Input
              type="text"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              placeholder="First name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Last Name
            </label>
            <Input
              type="text"
              name="last_name"
              value={formData.last_name}
              onChange={handleChange}
              placeholder="Last name"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Email *
          </label>
          <Input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="Email address"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Phone
          </label>
          <Input
            type="tel"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            placeholder="Phone number"
          />
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="autocc_recurring"
            name="autocc_recurring"
            checked={formData.autocc_recurring}
            onChange={handleChange}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
          />
          <label htmlFor="autocc_recurring" className="ml-2 block text-sm font-medium text-gray-700 cursor-pointer">
            Use AutoCC Recurring Billing
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            AutoCC Customer ID
          </label>
          <Input
            type="text"
            name="autocc_customer_id"
            value={formData.autocc_customer_id}
            onChange={handleChange}
            placeholder="AutoCC customer ID"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Late Fee Type
          </label>
          <select
            name="late_fee_type"
            value={formData.late_fee_type}
            onChange={handleChange}
            className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            <option value="none">None</option>
            <option value="flat">Flat</option>
            <option value="percentage">Percentage</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Late Fee Amount
          </label>
          <Input
            type="number"
            name="late_fee_amount"
            value={formData.late_fee_amount}
            onChange={handleChange}
            placeholder="0.00"
            step="0.01"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Late Fee Grace Days
          </label>
          <Input
            type="number"
            name="late_fee_grace_days"
            value={formData.late_fee_grace_days}
            onChange={handleChange}
            placeholder="0"
            min="0"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            placeholder="Additional notes"
            rows="3"
            className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
      </form>
    </Modal>
  );
}
