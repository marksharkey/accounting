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
    contact_name: '',
    email: '',
    phone: '',
    billing_type: 'fixed_recurring',
    authnet_customer_id: '',
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
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'late_fee_amount' || name === 'late_fee_grace_days'
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
      contact_name: '',
      email: '',
      phone: '',
      billing_type: 'fixed_recurring',
      authnet_customer_id: '',
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
            Contact Name
          </label>
          <Input
            type="text"
            name="contact_name"
            value={formData.contact_name}
            onChange={handleChange}
            placeholder="Contact name"
          />
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

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Billing Type
          </label>
          <select
            name="billing_type"
            value={formData.billing_type}
            onChange={handleChange}
            className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            <option value="fixed_recurring">Fixed Recurring</option>
            <option value="authnet_recurring">AuthNet Recurring</option>
            <option value="mixed">Mixed</option>
            <option value="one_off">One Off</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            AuthNet Customer ID
          </label>
          <Input
            type="text"
            name="authnet_customer_id"
            value={formData.authnet_customer_id}
            onChange={handleChange}
            placeholder="AuthNet customer ID"
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
