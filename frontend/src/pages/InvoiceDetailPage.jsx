import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import Button from '../components/ui/Button';
import RecordPaymentModal from '../components/RecordPaymentModal';
import SendInvoiceModal from '../components/SendInvoiceModal';
import { formatLocalDate } from '../utils/dateFormat';

export default function InvoiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [voidReason, setVoidReason] = useState('');
  const [isVoidModalOpen, setIsVoidModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isSendModalOpen, setIsSendModalOpen] = useState(false);
  const [sendModalMode, setSendModalMode] = useState('send'); // 'send' or 'resend'

  const { data: invoice, isLoading, refetch } = useQuery({
    queryKey: ['invoices', id],
    queryFn: async () => {
      const response = await apiClient.get(`/invoices/${id}`);
      return response.data;
    },
  });

  const markSentMutation = useMutation({
    mutationFn: () => apiClient.post(`/invoices/${id}/mark-sent`),
    onSuccess: () => refetch(),
    onError: (error) => alert(error.response?.data?.detail || 'Failed to mark invoice as sent'),
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

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.delete(`/invoices/${id}`),
    onSuccess: () => {
      navigate('/invoices');
    },
    onError: (error) => alert(error.response?.data?.detail || 'Failed to delete invoice'),
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

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'sent':
      case 'ready':
        return 'bg-blue-100 text-blue-800';
      case 'partially_paid':
        return 'bg-yellow-100 text-yellow-800';
      case 'paid':
        return 'bg-green-100 text-green-800';
      case 'voided':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const isLoading_ = isLoading || markSentMutation.isPending || voidMutation.isPending || deleteMutation.isPending;

  if (isLoading) {
    return <Layout title="Invoice Detail">Loading...</Layout>;
  }

  if (!invoice) {
    return <Layout title="Invoice Detail">Invoice not found</Layout>;
  }

  return (
    <Layout title={`Invoice ${invoice.invoice_number}`} onBack={() => navigate(-1)}>
      {/* Action Buttons */}
      <div className="mb-6 flex flex-wrap gap-2 justify-end">
        {invoice.status === 'draft' && (
          <>
            <Button
              onClick={() => {
                setSendModalMode('send');
                setIsSendModalOpen(true);
              }}
              disabled={isLoading_}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Send
            </Button>
            <Button
              onClick={() => markSentMutation.mutate()}
              disabled={isLoading_}
              className="bg-gray-600 hover:bg-gray-700 text-white"
            >
              {markSentMutation.isPending ? 'Marking...' : 'Mark as Sent'}
            </Button>
            <Button
              onClick={() => setIsDeleteModalOpen(true)}
              disabled={isLoading_}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Delete
            </Button>
          </>
        )}

        {(invoice.status === 'sent' || invoice.status === 'ready') && (
          <>
            <Button
              onClick={() => {
                setSendModalMode('resend');
                setIsSendModalOpen(true);
              }}
              disabled={isLoading_}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Resend
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

        {invoice.status !== 'paid' && invoice.balance_due > 0 && (
          <Button
            onClick={() => setIsPaymentModalOpen(true)}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            Record Payment
          </Button>
        )}

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

      <RecordPaymentModal
        isOpen={isPaymentModalOpen}
        onClose={() => setIsPaymentModalOpen(false)}
        invoiceId={invoice.id}
        balanceDue={invoice.balance_due}
        onSuccess={() => refetch()}
      />

      <SendInvoiceModal
        isOpen={isSendModalOpen}
        onClose={() => setIsSendModalOpen(false)}
        invoiceId={invoice.id}
        mode={sendModalMode}
        onSuccess={() => refetch()}
      />

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

      {isDeleteModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">Delete Invoice</h3>
            <p className="text-gray-600 mb-4">Are you sure you want to delete this invoice? This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <Button
                onClick={() => setIsDeleteModalOpen(false)}
                variant="secondary"
                disabled={deleteMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={() => deleteMutation.mutate()}
                className="bg-red-600 hover:bg-red-700 text-white"
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete Invoice'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* PDF-like Invoice Document */}
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-md relative overflow-hidden">
        {/* Watermark stamp for paid/voided invoices */}
        {invoice.status === 'paid' && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10" style={{ top: '20%' }}>
            <div style={{
              transform: 'rotate(-35deg)',
              fontSize: '96px',
              fontWeight: '900',
              color: 'rgba(22, 163, 74, 0.15)',
              letterSpacing: '0.05em',
              userSelect: 'none',
              whiteSpace: 'nowrap',
              textTransform: 'uppercase',
              border: '12px solid rgba(22, 163, 74, 0.15)',
              padding: '0 24px',
              lineHeight: 1.1,
            }}>
              PAID
            </div>
          </div>
        )}
        {invoice.status === 'voided' && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10" style={{ top: '20%' }}>
            <div style={{
              transform: 'rotate(-35deg)',
              fontSize: '96px',
              fontWeight: '900',
              color: 'rgba(220, 38, 38, 0.15)',
              letterSpacing: '0.05em',
              userSelect: 'none',
              whiteSpace: 'nowrap',
              textTransform: 'uppercase',
              border: '12px solid rgba(220, 38, 38, 0.15)',
              padding: '0 24px',
              lineHeight: 1.1,
            }}>
              VOID
            </div>
          </div>
        )}
        {/* Header */}
        <div className="border-b-4 border-[#1a3a52] p-8 flex justify-between">
          <div>
            <div className="text-2xl font-bold text-[#1a3a52] mb-1">PrecisionPros</div>
            <div className="text-xs text-gray-600 mb-3">Professional Web Hosting & IT Services</div>
            <div className="text-xs text-gray-600 space-y-0.5">
              <p>6543 East Omega Street</p>
              <p>Mesa, AZ 85215</p>
              <p>480-329-6176 | billing@precisionpros.com</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-[#1a3a52] mb-3">INVOICE</div>
            <div className="text-sm text-gray-600 space-y-1 mb-3 ml-auto w-fit">
              <div className="grid grid-cols-[auto_auto] gap-x-3">
                <span className="font-semibold text-gray-800 text-right">Invoice #:</span>
                <span className="text-right">{invoice.invoice_number}</span>
              </div>
              <div className="grid grid-cols-[auto_auto] gap-x-3">
                <span className="font-semibold text-gray-800 text-right">Date:</span>
                <span className="text-right">{formatLocalDate(invoice.created_date)}</span>
              </div>
              <div className="grid grid-cols-[auto_auto] gap-x-3">
                <span className="font-semibold text-gray-800 text-right">Due:</span>
                <span className="text-right">{formatLocalDate(invoice.due_date)}</span>
              </div>
            </div>
            <span className={`inline-block px-2 py-1 rounded text-xs font-bold uppercase tracking-wider ${getStatusBadgeClass(invoice.status)}`}>
              {invoice.status === 'voided' ? 'VOIDED' : getStatusDisplay(invoice.status).replace('_', ' ')}
            </span>
          </div>
        </div>

        {/* Bill To */}
        <div className="px-8 pt-6 pb-3">
          <div className="text-xs font-bold uppercase text-gray-500 tracking-wider mb-2">Bill To</div>
          <div className="text-sm text-gray-700 space-y-0.5">
            <div className="font-semibold text-[#1a3a52]">{invoice.client?.display_name}</div>
            {invoice.client?.display_name && <div>{invoice.client.display_name}</div>}
            {invoice.client?.address_line1 && <div>{invoice.client.address_line1}</div>}
            {invoice.client?.address_line2 && <div>{invoice.client.address_line2}</div>}
            {(invoice.client?.city || invoice.client?.state || invoice.client?.zip_code) && (
              <div>
                {invoice.client?.city}{invoice.client?.state ? ', ' + invoice.client.state : ''}{' '}
                {invoice.client?.zip_code}
              </div>
            )}
            {invoice.client?.email && <div>{invoice.client.email}</div>}
            {invoice.client?.phone && <div>{invoice.client.phone}</div>}
          </div>
        </div>

        {/* Line Items Table */}
        <table className="w-full text-sm my-4">
          <thead>
            <tr className="bg-[#1a3a52] text-white">
              <th className="text-left py-2 px-8 font-semibold text-xs uppercase tracking-wider">Description</th>
              <th className="text-center py-2 px-4 font-semibold text-xs uppercase tracking-wider w-16">Qty</th>
              <th className="text-right py-2 px-4 font-semibold text-xs uppercase tracking-wider w-24">Unit Price</th>
              <th className="text-right py-2 px-8 font-semibold text-xs uppercase tracking-wider w-24">Amount</th>
            </tr>
          </thead>
          <tbody>
            {invoice.line_items?.map((item, idx) => (
              <tr key={item.id} className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                <td className="py-3 px-8 text-gray-700">
                  <div className="font-medium">{item.description}</div>
                  {item.is_prorated && item.prorate_note && (
                    <div className="text-xs text-gray-500 italic">{item.prorate_note}</div>
                  )}
                </td>
                <td className="py-3 px-4 text-center text-gray-700">{item.quantity.toFixed(2)}</td>
                <td className="py-3 px-4 text-right text-gray-700">${item.unit_amount.toFixed(2)}</td>
                <td className="py-3 px-8 text-right font-medium text-gray-900">${item.amount.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Totals and Summary */}
        <div className="px-8 py-4 flex justify-end">
          <div className="w-64">
            {invoice.late_fee_amount > 0 && (
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-700">Subtotal:</span>
                <span>${invoice.subtotal.toFixed(2)}</span>
              </div>
            )}
            {invoice.late_fee_amount > 0 && (
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-700">Late Fee:</span>
                <span>${invoice.late_fee_amount.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm font-bold border-t-2 border-b-2 border-[#1a3a52] py-2 mb-2 bg-gray-50">
              <span className="text-[#1a3a52]">Total:</span>
              <span className="text-[#1a3a52]">${invoice.total.toFixed(2)}</span>
            </div>
            {invoice.amount_paid > 0 && (
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-700">Amount Paid:</span>
                <span>${invoice.amount_paid.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm font-bold">
              <span className={invoice.balance_due > 0 ? 'text-red-600' : 'text-green-600'}>Balance Due:</span>
              <span className={invoice.balance_due > 0 ? 'text-red-600' : 'text-green-600'}>${invoice.balance_due.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Payment History */}
        {invoice.payments && invoice.payments.length > 0 && (
          <div className="px-8 py-4 border-t border-gray-200">
            <h3 className="text-sm font-bold text-gray-800 mb-3 uppercase tracking-wider">Payment History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-300">
                    <th className="text-left py-2 px-2 font-semibold text-gray-600">Date Paid</th>
                    <th className="text-right py-2 px-2 font-semibold text-gray-600">Amount</th>
                    <th className="text-left py-2 px-2 font-semibold text-gray-600">Method</th>
                    <th className="text-left py-2 px-2 font-semibold text-gray-600">Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {[...invoice.payments].sort((a, b) => new Date(b.payment_date) - new Date(a.payment_date)).map((payment) => (
                    <tr key={payment.id} className="border-b border-gray-200">
                      <td className="py-2 px-2">{formatLocalDate(payment.payment_date)}</td>
                      <td className="py-2 px-2 text-right font-medium">${payment.amount.toFixed(2)}</td>
                      <td className="py-2 px-2 capitalize">{payment.method.replace('_', ' ')}</td>
                      <td className="py-2 px-2">{payment.reference_number || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Notes */}
        {invoice.notes && (
          <div className="px-8 py-4 border-t border-gray-200 border-l-4 border-l-[#1a3a52] bg-gray-50 mx-8 mb-4">
            <h3 className="text-xs font-bold text-[#1a3a52] mb-2 uppercase tracking-wider">Notes</h3>
            <p className="text-sm text-gray-700">{invoice.notes}</p>
          </div>
        )}

        {/* Footer */}
        <div className="px-8 py-6 border-t border-gray-200 text-center text-xs text-gray-500">
          <p>Thank you for your business!</p>
        </div>
      </div>
    </Layout>
  );
}
