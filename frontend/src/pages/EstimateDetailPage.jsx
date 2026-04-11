import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import Button from '../components/ui/Button';

export default function EstimateDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [isConverting, setIsConverting] = useState(false);

  const { data: estimate, isLoading, refetch } = useQuery({
    queryKey: ['estimates', id],
    queryFn: async () => {
      const response = await apiClient.get(`/estimates/${id}`);
      return response.data;
    },
  });

  const convertMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(`/estimates/${id}/convert-to-invoice`);
      return response.data;
    },
    onSuccess: (data) => {
      alert('Estimate converted to invoice successfully');
      navigate(`/invoices/${data.invoice.id}`);
    },
    onError: (error) => {
      alert('Error converting estimate: ' + (error.response?.data?.detail || error.message));
    },
  });

  const handleConvertToInvoice = async () => {
    if (!window.confirm('Convert this estimate to an invoice?')) {
      return;
    }
    setIsConverting(true);
    convertMutation.mutate();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'sent':
        return 'bg-blue-100 text-blue-800';
      case 'accepted':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (isLoading) {
    return <Layout title="Estimate Detail">Loading...</Layout>;
  }

  if (!estimate) {
    return <Layout title="Estimate Detail">Estimate not found</Layout>;
  }

  return (
    <Layout title={`Estimate ${estimate.estimate_number}`}>
      <div className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="text-3xl font-bold mb-2">{estimate.estimate_number}</h2>
          <p className="text-gray-600">
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(estimate.status)}`}>
              {estimate.status.toUpperCase()}
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          {estimate.status !== 'accepted' && estimate.status !== 'rejected' && (
            <Button
              onClick={handleConvertToInvoice}
              disabled={convertMutation.isPending}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {convertMutation.isPending ? 'Converting...' : 'Convert to Invoice'}
            </Button>
          )}
          <Button
            onClick={() => navigate('/estimates')}
            variant="outline"
          >
            Back to Estimates
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Created Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {new Date(estimate.created_date).toLocaleDateString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Expiry Date</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {estimate.expiry_date ? new Date(estimate.expiry_date).toLocaleDateString() : 'No expiry'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Total Amount</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-600">
              ${estimate.total.toFixed(2)}
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
              <p className="text-lg">{estimate.client?.company_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Contact Name</p>
              <p className="text-lg">{estimate.client?.contact_name || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Email</p>
              <p className="text-lg">{estimate.client?.email}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Phone</p>
              <p className="text-lg">{estimate.client?.phone || 'N/A'}</p>
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
                {estimate.line_items?.map((item) => (
                  <tr key={item.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4">{item.description}</td>
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
            <div className="flex justify-between border-t-2 border-gray-200 pt-3">
              <span className="font-bold text-lg">Total:</span>
              <span className="font-bold text-lg">${estimate.total.toFixed(2)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {estimate.notes && (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700">{estimate.notes}</p>
          </CardContent>
        </Card>
      )}
    </Layout>
  );
}
