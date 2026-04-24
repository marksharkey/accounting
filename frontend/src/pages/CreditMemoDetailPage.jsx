import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import Button from '../components/ui/Button';

export default function CreditMemoDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: memo, isLoading, refetch } = useQuery({
    queryKey: ['credit-memos', id],
    queryFn: async () => {
      const response = await apiClient.get(`/credit-memos/${id}`);
      return response.data;
    },
  });

  const sendMutation = useMutation({
    mutationFn: () => apiClient.post(`/credit-memos/${id}/send`),
    onSuccess: () => {
      refetch();
    },
    onError: (error) => alert(error.response?.data?.detail || 'Failed to send credit memo'),
  });

  const markSentMutation = useMutation({
    mutationFn: () => apiClient.post(`/credit-memos/${id}/mark-sent`),
    onSuccess: () => {
      refetch();
    },
    onError: (error) => alert(error.response?.data?.detail || 'Failed to mark credit memo as sent'),
  });

  const handleDownloadPDF = async () => {
    try {
      const response = await apiClient.get(`/credit-memos/${id}/pdf`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `credit-memo-${memo.id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Failed to download PDF');
    }
  };

  const isLoading_ = isLoading || sendMutation.isPending || markSentMutation.isPending;

  if (isLoading) {
    return <Layout title="Credit Memo">Loading...</Layout>;
  }

  if (!memo) {
    return <Layout title="Credit Memo">Credit memo not found</Layout>;
  }

  return (
    <Layout title="Credit Memo" onBack={() => navigate(-1)}>
      <div className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="text-3xl font-bold mb-2">Credit Memo</h2>
          <p className="text-gray-600">
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
              memo.status === 'sent' ? 'bg-blue-100 text-blue-800' :
              memo.status === 'draft' ? 'bg-gray-100 text-gray-800' :
              memo.status === 'voided' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {memo.status.replace('_', ' ').toUpperCase()}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end">
          {/* Status-specific action buttons */}
          {memo.status === 'draft' && (
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

          {/* Utility buttons */}
          <Button
            onClick={handleDownloadPDF}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            Download PDF
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Created Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {new Date(memo.created_date).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Total Credit</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">
              ${memo.total.toFixed(2)}
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
              <p className="text-lg">{memo.client?.company_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Display Name</p>
              <p className="text-lg">{memo.client?.display_name || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Email</p>
              <p className="text-lg">{memo.client?.email}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Phone</p>
              <p className="text-lg">{memo.client?.phone || 'N/A'}</p>
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
                  <th className="text-right py-2 px-4 font-medium">Amount</th>
                </tr>
              </thead>
              <tbody>
                {memo.line_items?.map((item) => (
                  <tr key={item.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4">{item.description}</td>
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
            <div className="flex justify-between border-b-2 border-gray-200 pb-3">
              <span className="font-bold text-lg">Total Credit:</span>
              <span className="font-bold text-lg text-green-600">${memo.total.toFixed(2)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {memo.reason && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Reason</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700">{memo.reason}</p>
          </CardContent>
        </Card>
      )}

      {memo.notes && (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700">{memo.notes}</p>
          </CardContent>
        </Card>
      )}
    </Layout>
  );
}
