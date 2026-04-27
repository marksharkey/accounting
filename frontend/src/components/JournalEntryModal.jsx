import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Input from './ui/Input';
import Button from './ui/Button';

export default function JournalEntryModal({ isOpen, onClose, entry = null }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    transaction_date: '',
    gl_account_code: '',
    gl_account_name: '',
    debit: '',
    credit: '',
    description: '',
    reference_number: '',
    source: 'manual',
  });
  const [error, setError] = useState('');

  useEffect(() => {
    if (entry && isOpen) {
      setFormData({
        transaction_date: entry.transaction_date || '',
        gl_account_code: entry.gl_account_code || '',
        gl_account_name: entry.gl_account_name || '',
        debit: entry.debit ? parseFloat(entry.debit) : '',
        credit: entry.credit ? parseFloat(entry.credit) : '',
        description: entry.description || '',
        reference_number: entry.reference_number || '',
        source: entry.source || 'manual',
      });
      setError('');
    } else if (!entry && isOpen) {
      const today = new Date().toISOString().split('T')[0];
      setFormData({
        transaction_date: today,
        gl_account_code: '',
        gl_account_name: '',
        debit: '',
        credit: '',
        description: '',
        reference_number: '',
        source: 'manual',
      });
      setError('');
    }
  }, [entry, isOpen]);

  const createMutation = useMutation({
    mutationFn: async (data) => {
      if (entry) {
        const response = await apiClient.put(`/journal-entries/${entry.id}`, data);
        return response.data;
      } else {
        const response = await apiClient.post('/journal-entries/', data);
        return response.data;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      handleClose();
    },
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => {
      const updated = { ...prev, [name]: value };
      if (name === 'debit' || name === 'credit') {
        setError('');
      }
      return updated;
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    const debit = formData.debit === '' ? '0' : parseFloat(formData.debit).toString();
    const credit = formData.credit === '' ? '0' : parseFloat(formData.credit).toString();

    if (debit === '0' && credit === '0') {
      setError('Either debit or credit amount must be greater than 0');
      return;
    }

    const submitData = {
      transaction_date: formData.transaction_date,
      gl_account_code: formData.gl_account_code,
      gl_account_name: formData.gl_account_name,
      debit: debit,
      credit: credit,
      description: formData.description || null,
      reference_number: formData.reference_number || null,
      source: formData.source,
    };
    createMutation.mutate(submitData);
  };

  const handleClose = () => {
    const today = new Date().toISOString().split('T')[0];
    setFormData({
      transaction_date: today,
      gl_account_code: '',
      gl_account_name: '',
      debit: '',
      credit: '',
      description: '',
      reference_number: '',
      source: 'manual',
    });
    setError('');
    onClose();
  };

  const footerContent = (
    <div className="space-y-2">
      {(createMutation.isError || error) && (
        <div className="text-red-600 text-sm">
          {error || (createMutation.error?.response?.data?.detail || 'Failed to save journal entry')}
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
          form="journal-entry-form"
        >
          {createMutation.isPending ? 'Saving...' : (entry ? 'Update Entry' : 'Create Entry')}
        </Button>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={entry ? "Edit Journal Entry" : "Add New Journal Entry"} footer={footerContent}>
      <form id="journal-entry-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Transaction Date *
          </label>
          <Input
            type="date"
            name="transaction_date"
            value={formData.transaction_date}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            GL Account Code *
          </label>
          <Input
            type="text"
            name="gl_account_code"
            value={formData.gl_account_code}
            onChange={handleChange}
            placeholder="e.g., 4100, 5000"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            GL Account Name *
          </label>
          <Input
            type="text"
            name="gl_account_name"
            value={formData.gl_account_name}
            onChange={handleChange}
            placeholder="e.g., Service Revenue, Rent Expense"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Debit
            </label>
            <Input
              type="number"
              name="debit"
              value={formData.debit}
              onChange={handleChange}
              placeholder="0.00"
              step="0.01"
              min="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Credit
            </label>
            <Input
              type="number"
              name="credit"
              value={formData.credit}
              onChange={handleChange}
              placeholder="0.00"
              step="0.01"
              min="0"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Description or notes about this entry"
            rows="3"
            className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
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
            placeholder="Check #, Invoice #, etc."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Source
          </label>
          <select
            name="source"
            value={formData.source}
            onChange={handleChange}
            className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            disabled={!!entry}
          >
            <option value="manual">Manual Entry</option>
            <option value="qbo_journal">QuickBooks Online</option>
            <option value="bank_import">Bank Import</option>
          </select>
          {entry && <p className="text-xs text-gray-500 mt-1">Source cannot be changed for existing entries</p>}
        </div>
      </form>
    </Modal>
  );
}
