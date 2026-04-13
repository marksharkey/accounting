import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Input from './ui/Input';
import Button from './ui/Button';

export default function EditClientModal({ isOpen, onClose, client }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({});
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (client) {
      setForm({
        company_name: client.company_name || '',
        contact_name: client.contact_name || '',
        email: client.email || '',
        email_cc: client.email_cc || '',
        phone: client.phone || '',
        address_line1: client.address_line1 || '',
        address_line2: client.address_line2 || '',
        city: client.city || '',
        state: client.state || '',
        zip_code: client.zip_code || '',
        notes: client.notes || '',
      });
    }
  }, [client, isOpen]);

  const updateMutation = useMutation({
    mutationFn: async (data) => {
      const response = await apiClient.put(`/clients/${client.id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients', client.id] });
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      handleClose();
    },
    onError: (error) => {
      setErrorMessage(error.response?.data?.detail || 'Failed to update client');
    },
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!form.company_name.trim()) {
      setErrorMessage('Company name is required');
      return;
    }

    if (!form.email.trim()) {
      setErrorMessage('Email is required');
      return;
    }

    updateMutation.mutate(form);
  };

  const handleClose = () => {
    setForm({});
    setErrorMessage('');
    onClose();
  };

  const footerContent = (
    <div className="space-y-2">
      {errorMessage && (
        <div className="text-red-600 text-sm">Error: {errorMessage}</div>
      )}
      <div className="flex gap-3 justify-end">
        <Button
          type="button"
          variant="secondary"
          onClick={handleClose}
          disabled={updateMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={updateMutation.isPending}
          form="edit-client-form"
        >
          {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Edit Client" footer={footerContent}>
      <form id="edit-client-form" onSubmit={handleSubmit} className="space-y-4">
        {/* Company Info */}
        <div className="space-y-4 border-b pb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Company Name *
            </label>
            <Input
              type="text"
              name="company_name"
              value={form.company_name}
              onChange={handleInputChange}
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
              value={form.contact_name}
              onChange={handleInputChange}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <Input
              type="email"
              name="email"
              value={form.email}
              onChange={handleInputChange}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email CC
            </label>
            <Input
              type="email"
              name="email_cc"
              value={form.email_cc}
              onChange={handleInputChange}
            />
          </div>
        </div>

        {/* Contact Info */}
        <div className="space-y-4 border-b pb-4">
          <h3 className="font-semibold text-gray-900">Contact Information</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Phone
            </label>
            <Input
              type="tel"
              name="phone"
              value={form.phone}
              onChange={handleInputChange}
            />
          </div>
        </div>

        {/* Address */}
        <div className="space-y-4">
          <h3 className="font-semibold text-gray-900">Address</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Address Line 1
            </label>
            <Input
              type="text"
              name="address_line1"
              value={form.address_line1}
              onChange={handleInputChange}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Address Line 2
            </label>
            <Input
              type="text"
              name="address_line2"
              value={form.address_line2}
              onChange={handleInputChange}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                City
              </label>
              <Input
                type="text"
                name="city"
                value={form.city}
                onChange={handleInputChange}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                State
              </label>
              <Input
                type="text"
                name="state"
                value={form.state}
                onChange={handleInputChange}
                maxLength={2}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Zip Code
              </label>
              <Input
                type="text"
                name="zip_code"
                value={form.zip_code}
                onChange={handleInputChange}
              />
            </div>
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            name="notes"
            value={form.notes}
            onChange={handleInputChange}
            placeholder="Optional internal notes"
            rows="3"
            className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          />
        </div>
      </form>
    </Modal>
  );
}
