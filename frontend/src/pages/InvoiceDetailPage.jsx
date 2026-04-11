import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import Button from '../components/ui/Button';
import RecordPaymentModal from '../components/RecordPaymentModal';

export default function InvoiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [voidReason, setVoidReason] = useState('');
  const [isVoidModalOpen, setIsVoidModalOpen] = useState(false);

  const { data: invoice, isLoading, refetch } = useQuery({
    queryKey: ['invoices', id],
    queryFn: async () => {
      const response = await apiClient.get(`/invoices/${id}`);
      return response.data;
    },
  });

  const sendMutation = useMutation({
    mutationFn: () => apiClient.post(`/invoices/${id}/send`),
    onSuccess: () => refetch(),
    onError: (error) => alert(error.response?.data?.detail || 'Failed to send invoice'),
  });

  const markSentMutation = useMutation({
    mutationFn: () => apiClient.post(`/invoices/${id}/mark-sent`),
    onSuccess: () => refetch(),
    onError: (error) => alert(error.response?.data?.detail || 'Failed to mark invoice as sent'),
  });

  const resendMutation = useMutation({
    mutationFn: () => apiClient.post(`/invoices/${id}/resend`),
    onSuccess: () => refetch(),
    onError: (error) => alert(error.response?.data?.detail || 'Failed to resend invoice'),
  });

  const voidMutation = useMutation({
    mutationFn: (reason) => apiClient.post(`/invoices/${id}/void?reason=${encodeURIComponent(reason)}`),
    onSuccess: () => {
      refetch();
      setIsVoidModalOpen(false);
      setVoidReason('');
    },
    onError: (error) => alert(error.response?.data?.detail || 'Failed to void invoice'),
  });

  const handleDownloadPDF = async () => {
    try {
      const response = await apiClient.get(`/invoices/${id}/pdf`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${invoice.invoice_number}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Failed to download PDF');
    }
  };

  const getStatusDisplay = (status) => {
    if (status === 'ready') return 'sent';
    return status;
  };

  const isLoading_ = isLoading || sendMutation.isPending || markSentMutation.isPending || resendMutation.isPending || voidMutation.isPending;

  if (isLoading) {
    return <Layout title="Invoice Detail">Loading...</Layout>;
  }

  if (!invoice) {
    return <Layout title="Invoice Detail">Invoice not found</Layout>;
  }

  return (
    <Layout title={`Invoice ${invoice.invoice_number}`}>
      <div className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="text-3xl font-bold mb-2">{invoice.invoice_number}</h2>
          <p className="text-gray-600">
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
              invoice.status === 'paid' ? 'bg-green-100 text-green-800' :
              invoice.status === 'sent' || invoice.status === 'ready' ? 'bg-blue-100 text-blue-800' :
              invoice.status === 'draft' ? 'bg-gray-100 text-gray-800' :
              invoice.status === 'partially_paid' ? 'bg-yellow-100 text-yellow-800' :
              invoice.status === 'voided' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {invoice.status === 'voided' ? 'VOIDED' : getStatusDisplay(invoice.status).replace('_', ' ').toUpperCase()}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end">
          {/* Status-specific action buttons */}
          {invoice.status === 'draft' && (
            <>
              <Button
                onClick={() => sendMutation.mutate()}
                disabled={isLoading_}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {sendMutation.isPending ? 'Sending...' : 'Send'}
              </Button>
              <Button
                onClick={() => markSentMutation.mutate()}
                disabled={isLoading_}
                className="bg-gray-600 hover:bg-gray-700 text-white"
              >
                {markSentMutation.isPending ? 'Marking...' : 'Mark as Sent'}
              </Button>
            </>
          )}

          {(invoice.status === 'sent' || invoice.status === 'ready') && (
            <>
              <Button
                onClick={() => resendMutation.mutate()}
                disabled={isLoading_}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {resendMutation.isPending ? 'Resending...' : 'Resend'}
              </Button>
            </>
          )}

          {(invoice.status === 'sent' || invoice.status === 'ready' || invoice.status === 'partially_paid') && (
            <Button
              onClick={() => setIsVoidModalOpen(true)}
              disabled={isLoading_}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Void
            </Button>
          )}

          {/* Payment recording */}
          {invoice.status !== 'paid' && invoice.balance_due > 0 && (
            <Button
              onClick={() => setIsPaymentModalOpen(true)}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              Record Payment
            </Button>
          )}

          {/* Utility buttons */}
          <Button
            onClick={() => navigate('/credit-memos/new')}
            className="bg-orange-600 hover:bg-orange-700 text-white"
          >
            Create Credit Memo
          </Button>
          <Button
            onClick={handleDownloadPDF}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            Download PDF
          </Button>
        </div>
      </div>

      <RecordPaymentModal
        isOpen={isPaymentModalOpen}
        onClose={() => setIsPaymentModalOpen(false)}
        invoiceId={invoice.id}
        balanceDue={invoice.balance_due}
        onSuccess={() => refetch()}
      />

      {/* Void Invoice Modal */}
      {isVoidModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">Void Invoice</h3>
            <p className="text-gray-600 mb-4">Are you sure you want to void this invoice? Please provide a reason.</p>
            <textarea
              value={voidReason}
              onChange={(e) => setVoidReason(e.target.value)}
              placeholder="Reason for voiding..."
              rows="3"
              className="w-full border border-gray-300 rounded-lg p-2 mb-4 focus:outline-none focus:ring-2 focus:ring-red-500"
            />
            <div className="flex gap-2 justify-end">
              <Button
                onClick={() => {
                  setIsVoidModalOpen(false);
                  setVoidReason('');
                }}
                variant="secondary"
                disabled={voidMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={() => voidMutation.mutate(voidReason)}
                className="bg-red-600 hover:bg-red-700 text-white"
                disabled={voidMutation.isPending || !voidReason.trim()}
              >
                {voidMutation.isPending ? 'Voiding...' : 'Void Invoice'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Created Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {new Date(invoice.created_date).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Due Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {new Date(invoice.due_date).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Balance Due</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${
              invoice.balance_due <= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              ${invoice.balance_due.toFixed(2)}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Client Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-sm font-medium text-gray-600">Company Name</p>
              <p className="text-lg">{invoice.client?.company_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Contact Name</p>
              <p className="text-lg">{invoice.client?.contact_name || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Email</p>
              <p className="text-lg">{invoice.client?.email}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Phone</p>
              <p className="text-lg">{invoice.client?.phone || 'N/A'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Line Items</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-4 font-medium">Description</th>
                  <th className="text-center py-2 px-4 font-medium">Qty</th>
                  <th className="text-right py-2 px-4 font-medium">Unit Price</th>
                  <th className="text-right py-2 px-4 font-medium">Amount</th>
                </tr>
              </thead>
              <tbody>
                {invoice.line_items?.map((item) => (
                  <tr key={item.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div>{item.description}</div>
                      {item.is_prorated && item.prorate_note && (
                        <div className="text-xs text-gray-500 italic">{item.prorate_note}</div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">{item.quantity.toFixed(4)}</td>
                    <td className="py-3 px-4 text-right">${item.unit_amount.toFixed(2)}</td>
                    <td className="py-3 px-4 text-right font-medium">${item.amount.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 max-w-md ml-auto">
            <div className="flex justify-between">
              <span className="font-medium">Subtotal:</span>
              <span>${invoice.subtotal.toFixed(2)}</span>
            </div>
            {invoice.late_fee_amount > 0 && (
              <div className="flex justify-between">
                <span className="font-medium">Late Fee:</span>
                <span>${invoice.late_fee_amount.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between border-t-2 border-gray-200 pt-3">
              <span className="font-bold text-lg">Total:</span>
              <span className="font-bold text-lg">${invoice.total.toFixed(2)}</span>
            </div>
            <div className="flex justify-between pt-2">
              <span className="font-medium">Amount Paid:</span>
              <span>${invoice.amount_paid.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-red-600 font-bold">
              <span>Balance Due:</span>
              <span>${invoice.balance_due.toFixed(2)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {invoice.notes && (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700">{invoice.notes}</p>
          </CardContent>
        </Card>
      )}
    </Layout>
  );
}
