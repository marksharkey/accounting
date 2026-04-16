import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import { formatLocalDate } from '../utils/dateFormat';

export default function InvoiceListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [invoiceNumberInput, setInvoiceNumberInput] = useState('');
  const [filters, setFilters] = useState({
    invoice_number: '',
    status: '',
    client: '',
    from_date: '',
    to_date: '',
    overdue: false,
    open: false,
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

  // Initialize filters from URL params
  useEffect(() => {
    const statusParam = searchParams.get('status');
    const filterParam = searchParams.get('filter');
    const clientIdParam = searchParams.get('client_id');
    const invoiceNumberParam = searchParams.get('invoice_number');

    if (invoiceNumberParam) {
      setInvoiceNumberInput(invoiceNumberParam);
      setFilters(prev => ({ ...prev, invoice_number: invoiceNumberParam }));
    }

    if (clientIdParam && clientsData?.items) {
      const client = clientsData.items.find(c => c.id === parseInt(clientIdParam));
      if (client) {
        setFilters(prev => ({ ...prev, client: client.company_name }));
      }
    }

    if (statusParam === 'overdue') {
      // For overdue, we'll use a special filter - don't set status
      setFilters(prev => ({ ...prev, status: '', overdue: true, open: false }));
    } else if (statusParam === 'open') {
      // For open, we'll use a special filter - don't set status
      setFilters(prev => ({ ...prev, status: '', overdue: false, open: true }));
    } else if (statusParam) {
      setFilters(prev => ({ ...prev, status: statusParam, overdue: false, open: false }));
    } else if (filterParam === 'due-billing') {
      // For due-billing filter, we'll just load and filter client-side
      // The status param remains empty
    }
  }, [searchParams, clientsData]);

  const { data: invoiceData, isLoading } = useQuery({
    queryKey: ['invoices', filters, sortBy, sortOrder],
    queryFn: async () => {
      const params = {};

      if (filters.invoice_number) {
        params.invoice_number = filters.invoice_number;
      }
      if (filters.status) {
        params.status = filters.status;
      }
      if (filters.overdue) {
        params.overdue = true;
      }
      if (filters.open) {
        params.is_open = true;
      }

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

      const response = await apiClient.get('/invoices/', { params });
      return response.data;
    },
  });

  const invoices = invoiceData?.items || [];

  const handleFilterChange = (field, value) => {
    if (field === 'invoice_number') {
      setInvoiceNumberInput(value);
      return;
    }
    if (field === 'status') {
      // Handle special statuses (overdue, open) vs regular statuses
      if (value === 'overdue') {
        setFilters(prev => ({ ...prev, status: '', overdue: true, open: false }));
      } else if (value === 'open') {
        setFilters(prev => ({ ...prev, status: '', overdue: false, open: true }));
      } else {
        setFilters(prev => ({ ...prev, status: value, overdue: false, open: false }));
      }
      // Update URL params
      const newParams = new URLSearchParams(searchParams);
      if (value) {
        newParams.set('status', value);
      } else {
        newParams.delete('status');
      }
      setSearchParams(newParams);
    } else {
      setFilters(prev => ({ ...prev, [field]: value }));
      // Update URL params
      const newParams = new URLSearchParams(searchParams);
      if (value) {
        newParams.set(field, value);
      } else {
        newParams.delete(field);
      }
      setSearchParams(newParams);
    }
  };

  const handleInvoiceNumberSearch = (value) => {
    setFilters(prev => ({ ...prev, invoice_number: value }));
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set('invoice_number', value);
    } else {
      newParams.delete('invoice_number');
    }
    setSearchParams(newParams);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleInvoiceNumberSearch(invoiceNumberInput);
    }
  };

  const handleReset = () => {
    setInvoiceNumberInput('');
    setFilters({
      invoice_number: '',
      status: '',
      client: '',
      from_date: '',
      to_date: '',
      overdue: false,
      open: false,
    });
    setSearchParams({});
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
      case 'paid':
        return 'bg-green-100 text-green-800';
      case 'partially_paid':
        return 'bg-yellow-100 text-yellow-800';
      case 'sent':
        return 'bg-blue-100 text-blue-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'voided':
        return 'bg-red-100 text-red-800';
      case 'overdue':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (isLoading) {
    return <Layout title="Invoices">Loading...</Layout>;
  }

  return (
    <Layout title="Invoices">
      <div className="mb-6 space-y-4">
        <div className="flex gap-4">
          <Button
            onClick={() => navigate('/invoices/new')}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            + New Invoice
          </Button>
          <Button
            onClick={handleReset}
            variant="outline"
          >
            Reset Filters
          </Button>
        </div>

        <div className="grid grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Invoice Number</label>
            <Input
              type="text"
              placeholder="Search..."
              value={invoiceNumberInput}
              onChange={(e) => handleFilterChange('invoice_number', e.target.value)}
              onKeyPress={handleKeyPress}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filters.open ? 'open' : filters.overdue ? 'overdue' : filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="overdue">Overdue</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="partially_paid">Partially Paid</option>
              <option value="paid">Paid</option>
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
                <SortableHeader label="Invoice Number" column="invoice_number" />
              </TableHead>
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
                <SortableHeader label="Due Date" column="due_date" />
              </TableHead>
              <TableHead>
                <SortableHeader label="Balance Due" column="balance_due" />
              </TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invoices && invoices.length > 0 ? (
              invoices.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell className="font-medium">
                    <Link
                      to={`/invoices/${invoice.id}`}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {invoice.invoice_number}
                    </Link>
                  </TableCell>
                  <TableCell>{invoice.client?.company_name || 'N/A'}</TableCell>
                  <TableCell>${invoice.total.toFixed(2)}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(invoice.status)}`}>
                      {invoice.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </TableCell>
                  <TableCell>
                    {formatLocalDate(invoice.due_date)}
                  </TableCell>
                  <TableCell>
                    <span className={invoice.balance_due > 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
                      ${invoice.balance_due.toFixed(2)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => navigate(`/invoices/${invoice.id}`)}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan="7" className="text-center py-8 text-gray-500">
                  No invoices found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Layout>
  );
}
