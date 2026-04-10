import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Input from './ui/Input';
import Button from './ui/Button';

export default function AddServiceModal({ isOpen, onClose, service = null }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    default_amount: '',
    default_cycle: 'monthly',
    description: '',
    income_account_id: '',
  });

  // Fetch categories
  const { data: categoriesData } = useQuery({
    queryKey: ['service-categories'],
    queryFn: async () => {
      const response = await apiClient.get('/services/categories');
      return response.data;
    },
    enabled: isOpen,
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

  // Filter for income accounts only
  const incomeAccounts = (accountsData || []).filter(acc => acc.account_type === 'income');

  const categories = categoriesData || [];

  // Populate form if editing
  useEffect(() => {
    if (service && isOpen) {
      setFormData({
        name: service.name || '',
        category: service.category || '',
        default_amount: service.default_amount || '',
        default_cycle: service.default_cycle || 'monthly',
        description: service.description || '',
        income_account_id: service.income_account_id || '',
      });
    } else if (!service && isOpen) {
      setFormData({
        name: '',
        category: '',
        default_amount: '',
        default_cycle: 'monthly',
        description: '',
        income_account_id: '',
      });
    }
  }, [service, isOpen]);

  const createMutation = useMutation({
    mutationFn: async (data) => {
      if (service) {
        const response = await apiClient.put(`/services/${service.id}`, data);
        return response.data;
      } else {
        const response = await apiClient.post('/services/', data);
        return response.data;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      handleClose();
    },
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'default_amount' ? (value === '' ? '' : parseFloat(value)) : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const submitData = {
      ...formData,
      default_amount: parseFloat(formData.default_amount),
      income_account_id: formData.income_account_id === '' ? null : parseInt(formData.income_account_id),
    };
    createMutation.mutate(submitData);
  };

  const handleClose = () => {
    setFormData({
      name: '',
      category: '',
      default_amount: '',
      default_cycle: 'monthly',
      description: '',
      income_account_id: '',
    });
    onClose();
  };

  const footerContent = (
    <div className="space-y-2">
      {createMutation.isError && (
        <div className="text-red-600 text-sm">
          Error: {createMutation.error?.response?.data?.detail || 'Failed to save service'}
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
          form="service-form"
        >
          {createMutation.isPending ? 'Saving...' : (service ? 'Update Service' : 'Create Service')}
        </Button>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={service ? "Edit Service" : "Add New Service"} footer={footerContent}>
      <form id="service-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Service Name *
          </label>
          <Input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="Service name"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Category
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              name="category"
              list="categories-list"
              value={formData.category}
              onChange={handleChange}
              placeholder="Select or enter custom category"
              className="flex-1 h-10 rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            />
            <datalist id="categories-list">
              {categories.map((cat) => (
                <option key={cat} value={cat} />
              ))}
            </datalist>
          </div>
          {formData.category && !categories.includes(formData.category) && (
            <p className="text-xs text-gray-500 mt-1">Custom category</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Default Amount *
          </label>
          <Input
            type="number"
            name="default_amount"
            value={formData.default_amount}
            onChange={handleChange}
            placeholder="0.00"
            step="0.01"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Default Cycle *
          </label>
          <select
            name="default_cycle"
            value={formData.default_cycle}
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
            Description
          </label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Service description"
            rows="3"
            className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Income Account
          </label>
          <select
            name="income_account_id"
            value={formData.income_account_id}
            onChange={handleChange}
            className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            <option value="">Select an income account</option>
            {incomeAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} - {account.name}
              </option>
            ))}
          </select>
        </div>
      </form>
    </Modal>
  );
}
