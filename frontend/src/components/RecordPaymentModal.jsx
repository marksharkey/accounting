import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Input from './ui/Input';
import Button from './ui/Button';

export default function RecordPaymentModal({ isOpen, onClose, invoiceId, balanceDue, onSuccess }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    amount: balanceDue || '',
    method: 'check',
    reference_number: '',
    payment_date: new Date().toISOString().split('T')[0],
  });

  const recordPaymentMutation = useMutation({
    mutationFn: async (data) => {
      const response = await apiClient.post('/payments/', {
        invoice_id: invoiceId,
        ...data,
        amount: parseFloat(data.amount),
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices', invoiceId] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      if (onSuccess) onSuccess();
      handleClose();
    },
    onError: (error) => {
      console.error('Payment recording error:', error);
    },
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      alert('Please enter a valid payment amount');
      return;
    }
    recordPaymentMutation.mutate(formData);
  };

  const handleClose = () => {
    setFormData({
      amount: balanceDue || '',
      method: 'check',
      reference_number: '',
      payment_date: new Date().toISOString().split('T')[0],
    });
    onClose();
  };

  const footerContent = (
    <div className="space-y-2">
      {recordPaymentMutation.isError && (
        <div className="text-red-600 text-sm">
          Error: {recordPaymentMutation.error?.response?.data?.detail || 'Failed to record payment'}
        </div>
      )}
      <div className="flex gap-3 justify-end">
        <Button
          type="button"
          variant="secondary"
          onClick={handleClose}
          disabled={recordPaymentMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={recordPaymentMutation.isPending}
          form="payment-form"
        >
          {recordPaymentMutation.isPending ? 'Recording...' : 'Record Payment'}
        </Button>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Record Payment" footer={footerContent}>
      <form id="payment-form" onSubmit={handleSubmit} className="space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
          <p className="text-sm text-gray-700">
            <span className="font-medium">Balance Due:</span> ${balanceDue?.toFixed(2) || '0.00'}
          </p>
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
            min="0"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Payment Method *
          </label>
          <select
            name="method"
            value={formData.method}
            onChange={handleChange}
            className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            required
          >
            <option value="check">Check</option>
            <option value="cash">Cash</option>
            <option value="credit_card">Credit Card</option>
            <option value="autocc">AutoCC</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Reference Number
          </label>
          <Input
            type="text"
            name="reference_number"
            value={formData.reference_number}
            onChange={handleChange}
            placeholder="Check #, transaction ID, etc."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Payment Date *
          </label>
          <Input
            type="date"
            name="payment_date"
            value={formData.payment_date}
            onChange={handleChange}
            required
          />
        </div>
      </form>
    </Modal>
  );
}
