import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';

export default function CreditMemoListPage() {
  const [filters, setFilters] = useState({
    status: '',
    client: '',
    from_date: '',
    to_date: '',
  });
  const [sortBy, setSortBy] = useState('created_date');
  const [sortOrder, setSortOrder] = useState('desc');
  const navigate = useNavigate();

  const { data: clientsData } = useQuery({
    queryKey: ['clients-all'],
    queryFn: async () => {
      const response = await apiClient.get('/clients/', {
        params: { limit: 10000 },
      });
      return response.data;
    },
  });

  const { data: memoData, isLoading } = useQuery({
    queryKey: ['credit-memos', filters, sortBy, sortOrder],
    queryFn: async () => {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.client) {
        const selectedClient = clientsData?.items?.find(c => c.company_name === filters.client);
        if (selectedClient) {
          params.client_id = selectedClient.id;
        }
      }
      if (filters.from_date) params.from_date = filters.from_date;
      if (filters.to_date) params.to_date = filters.to_date;
      params.sort_by = sortBy;
      params.sort_order = sortOrder;

      const response = await apiClient.get('/credit-memos/', { params });
      return response.data;
    },
  });

  const memos = memoData?.items || [];

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const handleReset = () => {
    setFilters({
      status: '',
      client: '',
      from_date: '',
      to_date: '',
    });
  };

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const SortableHeader = ({ label, column }) => (
    <div
      onClick={() => handleSort(column)}
      className="cursor-pointer hover:text-blue-600 flex items-center gap-1 select-none"
    >
      {label}
      {sortBy === column && (
        <span className="text-xs">
          {sortOrder === 'asc' ? '↑' : '↓'}
        </span>
      )}
    </div>
  );

  const getStatusColor = (status) => {
    switch (status) {
      case 'sent':
        return 'bg-blue-100 text-blue-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'voided':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (isLoading) {
    return <Layout title="Credit Memos">Loading...</Layout>;
  }

  return (
    <Layout title="Credit Memos">
      <div className="mb-6 space-y-4">
        <div className="flex gap-4">
          <Button
            onClick={() => navigate('/credit-memos/new')}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            + New Credit Memo
          </Button>
          <Button
            onClick={handleReset}
            variant="outline"
          >
            Reset Filters
          </Button>
        </div>

        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="voided">Voided</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
            <Input
              type="date"
              value={filters.from_date}
              onChange={(e) => handleFilterChange('from_date', e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
            <Input
              type="date"
              value={filters.to_date}
              onChange={(e) => handleFilterChange('to_date', e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Client</label>
            <select
              value={filters.client}
              onChange={(e) => handleFilterChange('client', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Clients</option>
              {clientsData?.items?.map((client) => (
                <option key={client.id} value={client.company_name}>
                  {client.company_name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <SortableHeader label="Client" column="client_id" />
              </TableHead>
              <TableHead>
                <SortableHeader label="Amount" column="total" />
              </TableHead>
              <TableHead>
                <SortableHeader label="Status" column="status" />
              </TableHead>
              <TableHead>
                <SortableHeader label="Created Date" column="created_date" />
              </TableHead>
              <TableHead>
                <SortableHeader label="Reason" column="reason" />
              </TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {memos && memos.length > 0 ? (
              memos.map((memo) => (
                <TableRow key={memo.id}>
                  <TableCell>{memo.client?.company_name || 'N/A'}</TableCell>
                  <TableCell>${memo.total.toFixed(2)}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(memo.status)}`}>
                      {memo.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </TableCell>
                  <TableCell>
                    {new Date(memo.created_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="truncate max-w-xs">
                    {memo.reason || '-'}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => navigate(`/credit-memos/${memo.id}`)}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan="6" className="text-center py-8 text-gray-500">
                  No credit memos found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Layout>
  );
}
