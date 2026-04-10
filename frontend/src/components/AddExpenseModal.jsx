import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Input from './ui/Input';
import Button from './ui/Button';

export default function AddExpenseModal({ isOpen, onClose, expense = null }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    expense_date: '',
    vendor: '',
    amount: '',
    description: '',
    category_id: '',
    reference_number: '',
    notes: '',
  });

  // Fetch chart of accounts
  const { data: accountsData } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      const response = await apiClient.get('/services/accounts');
      return response.data;
    },
    enabled: isOpen,
  });

  // Filter for expense accounts only
  const expenseAccounts = (accountsData || []).filter(acc => acc.account_type === 'expense');

  // Populate form if editing
  useEffect(() => {
    if (expense && isOpen) {
      setFormData({
        expense_date: expense.expense_date || '',
        vendor: expense.vendor || '',
        amount: expense.amount || '',
        description: expense.description || '',
        category_id: expense.category_id || '',
        reference_number: expense.reference_number || '',
        notes: expense.notes || '',
      });
    } else if (!expense && isOpen) {
      const today = new Date().toISOString().split('T')[0];
      setFormData({
        expense_date: today,
        vendor: '',
        amount: '',
        description: '',
        category_id: '',
        reference_number: '',
        notes: '',
      });
    }
  }, [expense, isOpen]);

  const createMutation = useMutation({
    mutationFn: async (data) => {
      if (expense) {
        const response = await apiClient.put(`/expenses/${expense.id}`, data);
        return response.data;
      } else {
        const response = await apiClient.post('/expenses/', data);
        return response.data;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      handleClose();
    },
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'amount' ? (value === '' ? '' : parseFloat(value)) : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const submitData = {
      ...formData,
      amount: parseFloat(formData.amount),
      category_id: formData.category_id === '' ? null : parseInt(formData.category_id),
    };
    createMutation.mutate(submitData);
  };

  const handleClose = () => {
    const today = new Date().toISOString().split('T')[0];
    setFormData({
      expense_date: today,
      vendor: '',
      amount: '',
      description: '',
      category_id: '',
      reference_number: '',
      notes: '',
    });
    onClose();
  };

  const footerContent = (
    <div className="space-y-2">
      {createMutation.isError && (
        <div className="text-red-600 text-sm">
          Error: {createMutation.error?.response?.data?.detail || 'Failed to save expense'}
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
          form="expense-form"
        >
          {createMutation.isPending ? 'Saving...' : (expense ? 'Update Expense' : 'Create Expense')}
        </Button>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={expense ? "Edit Expense" : "Add New Expense"} footer={footerContent}>
      <form id="expense-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Expense Date *
          </label>
          <Input
            type="date"
            name="expense_date"
            value={formData.expense_date}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Vendor *
          </label>
          <Input
            type="text"
            name="vendor"
            value={formData.vendor}
            onChange={handleChange}
            placeholder="Vendor name"
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
            Description
          </label>
          <Input
            type="text"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Expense description"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Category
          </label>
          <select
            name="category_id"
            value={formData.category_id}
            onChange={handleChange}
            className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            <option value="">Select an expense category</option>
            {expenseAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} - {account.name}
              </option>
            ))}
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
            placeholder="Receipt #, Check #, etc."
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
