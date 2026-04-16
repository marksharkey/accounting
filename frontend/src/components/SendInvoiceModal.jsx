import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Modal from './ui/Modal';
import Button from './ui/Button';

const TEMPLATE_LABELS = {
  new_invoice: 'New Invoice (Default)',
  reminder_invoice: 'Payment Reminder',
  invoice_past_due: 'Past Due Notice',
  suspension_invoice: 'Suspension Warning',
  cancellation_invoice: 'Cancellation Notice',
  default: 'Default Template',
};

export default function SendInvoiceModal({
  isOpen,
  onClose,
  invoiceId,
  onSuccess,
  mode = 'send', // 'send' or 'resend'
}) {
  const [selectedType, setSelectedType] = useState('new_invoice');
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Fetch list of active templates
  const { data: templates = [] } = useQuery({
    queryKey: ['email-templates', 'active'],
    queryFn: async () => {
      const response = await apiClient.get('/email-templates?active_only=true');
      return response.data;
    },
    enabled: isOpen,
  });

  // Fetch preview for selected template
  useEffect(() => {
    if (isOpen && invoiceId && selectedType) {
      fetchPreview();
    }
  }, [isOpen, invoiceId, selectedType]);

  const fetchPreview = async () => {
    setPreviewLoading(true);
    try {
      const response = await apiClient.get(`/invoices/${invoiceId}/email-preview`, {
        params: { template_type: selectedType },
      });
      setPreview(response.data);
    } catch (error) {
      console.error('Error loading preview:', error);
      console.error('Selected template type:', selectedType);
      console.error('Response:', error.response?.data);
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Send email mutation
  const sendMutation = useMutation({
    mutationFn: async () => {
      const endpoint = mode === 'resend' ? 'resend' : 'send';
      const response = await apiClient.post(
        `/invoices/${invoiceId}/${endpoint}`,
        {},
        { params: { template_type: selectedType } }
      );
      return response.data;
    },
    onSuccess: () => {
      onSuccess();
      handleClose();
    },
    onError: (error) => {
      alert(error.response?.data?.detail || `Failed to ${mode} invoice`);
    },
  });

  const handleClose = () => {
    setSelectedType('new_invoice');
    setPreview(null);
    onClose();
  };

  const filteredTemplates = templates.filter((t) => t.template_type !== 'default');

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={mode === 'resend' ? 'Resend Invoice' : 'Send Invoice'}
      footer={
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={handleClose} disabled={sendMutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={() => sendMutation.mutate()}
            disabled={sendMutation.isPending || !preview}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {sendMutation.isPending ? `${mode === 'resend' ? 'Resending' : 'Sending'}...` : 'Send'}
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Template Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Email Template
          </label>
          {filteredTemplates.length === 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
              No active templates found. Please configure email templates in Company Settings.
            </div>
          ) : (
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              disabled={sendMutation.isPending}
              className="w-full border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {filteredTemplates.map((template) => (
                <option key={template.template_type} value={template.template_type}>
                  {TEMPLATE_LABELS[template.template_type] || template.template_type}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Preview Section */}
        {previewLoading ? (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-gray-600">
            Loading preview...
          </div>
        ) : preview ? (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="mb-4">
              <p className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-1">
                Subject
              </p>
              <p className="text-gray-900 font-medium break-words">{preview.subject}</p>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-2">
                Email Body Preview
              </p>
              <div className="bg-white border border-gray-200 rounded p-3 max-h-64 overflow-y-auto">
                <iframe
                  srcDoc={preview.body}
                  className="w-full h-48 border-none"
                  style={{ pointerEvents: 'none' }}
                  title="Email preview"
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            Failed to load template preview. The template may not exist or be inactive. Check the Company Settings to ensure the template is active.
          </div>
        )}

        {sendMutation.isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {sendMutation.error?.response?.data?.detail || 'Failed to send email'}
          </div>
        )}
      </div>
    </Modal>
  );
}
