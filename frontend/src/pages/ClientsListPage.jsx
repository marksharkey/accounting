import { useState } from 'react';
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import AddClientModal from '../components/AddClientModal';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import { formatLocalDate } from '../utils/dateFormat';

export default function ClientsListPage() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [clientStatusFilter, setClientStatusFilter] = useState('active');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [skip, setSkip] = useState(0);
  const [allClients, setAllClients] = useState([]);
  const navigate = useNavigate();

  const { data: clientData, isLoading } = useQuery({
    queryKey: ['clients', search, clientStatusFilter, skip],
    queryFn: async () => {
      const params = {
        skip,
        limit: 10000
      };

      if (search) {
        params.search = search;
      }

      if (clientStatusFilter === 'all') {
        params.active_only = false;
      } else if (clientStatusFilter === 'inactive') {
        params.active_only = false;
        params.status = 'inactive';
      } else if (clientStatusFilter === 'active') {
        params.active_only = true;
      } else {
        params.active_only = true;
        params.status = clientStatusFilter;
      }

      const response = await apiClient.get('/clients/', { params });
      return response.data;
    },
  });

  const { data: invoiceData } = useQuery({
    queryKey: ['invoices-all'],
    queryFn: async () => {
      const response = await apiClient.get('/invoices/', { params: { limit: 10000 } });
      return response.data;
    },
  });

  const getEarliestDueDate = (clientId) => {
    if (!invoiceData?.items) return null;
    const unpaidStatuses = ['draft', 'sent', 'partially_paid', 'overdue'];
    const clientInvoices = invoiceData.items.filter(
      inv => inv.client_id === clientId && unpaidStatuses.includes(inv.status)
    );
    if (clientInvoices.length === 0) return null;
    const dates = clientInvoices.map(inv => new Date(inv.due_date));
    return new Date(Math.min(...dates));
  };

  const isOverdue = (dueDate) => {
    if (!dueDate) return false;
    return dueDate < new Date();
  };

  const handleSearch = () => {
    setSearch(searchInput);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  // When search or status filter changes, reset pagination
  React.useEffect(() => {
    setSkip(0);
    setAllClients([]);
  }, [search, clientStatusFilter]);

  // When clientData changes, update the all clients list
  React.useEffect(() => {
    if (clientData?.items) {
      if (skip === 0) {
        setAllClients(clientData.items);
      } else {
        setAllClients(prev => [...prev, ...clientData.items]);
      }
    }
  }, [clientData, skip]);


  const total = clientData?.total || 0;

  if (isLoading) {
    return <Layout title="Clients">Loading...</Layout>;
  }

  return (
    <Layout title="Clients">
      <AddClientModal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} />
      <div className="mb-4 flex gap-2 items-center">
        <Input
          type="text"
          placeholder="Search..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyPress={handleKeyPress}
          className="w-48"
        />
        <select
          value={clientStatusFilter}
          onChange={(e) => setClientStatusFilter(e.target.value)}
          className="px-2 py-1 h-7 border border-gray-300 rounded text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="active">Active</option>
          <option value="overdue">Overdue</option>
          <option value="inactive">Inactive</option>
          <option value="all">All</option>
        </select>
        <Button onClick={() => setIsAddModalOpen(true)} size="sm">
          + Add
        </Button>
        {total > 0 && (
          <div className="text-xs text-gray-500 ml-auto">
            {allClients.length} of {total}
          </div>
        )}
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>City</TableHead>
              <TableHead>Next Due Date</TableHead>
              <TableHead>Billing Type</TableHead>
              <TableHead>Balance</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {allClients && allClients.length > 0 ? (
              allClients.map((client) => (
                <TableRow key={client.id}>
                  <TableCell className="font-medium">
                    <Link
                      to={`/clients/${client.id}`}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {client.display_name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-gray-900">{client.email || '—'}</TableCell>
                  <TableCell className="text-gray-900">{client.city || '—'}</TableCell>
                  <TableCell>
                    {(() => {
                      const dueDate = getEarliestDueDate(client.id);
                      if (!dueDate) return '—';
                      return (
                        <span className={isOverdue(dueDate) ? 'text-red-600 font-medium' : ''}>
                          {formatLocalDate(dueDate.toISOString().split('T')[0])}
                        </span>
                      );
                    })()}
                  </TableCell>
                  <TableCell className="text-gray-900">
                    {client.autocc_recurring ? 'Auto-charge' : 'Fixed recurring'}
                  </TableCell>
                  <TableCell>
                    <span
                      className={
                        client.account_balance < 0
                          ? 'text-green-600 font-medium'
                          : 'text-red-600 font-medium'
                      }
                    >
                      ${Math.abs(client.account_balance).toFixed(2)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded">
                      {client.account_status || 'Active'}
                    </span>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan="7" className="text-center py-8 text-gray-500">
                  No clients found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

    </Layout>
  );
}
