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

export default function ClientsListPage() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [accountStatusFilter, setAccountStatusFilter] = useState('active');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [skip, setSkip] = useState(0);
  const [allClients, setAllClients] = useState([]);
  const navigate = useNavigate();

  const { data: clientData, isLoading } = useQuery({
    queryKey: ['clients', search, accountStatusFilter, skip],
    queryFn: async () => {
      const params = {
        skip,
        limit: 10000
      };

      if (search) {
        params.search = search;
      }

      if (accountStatusFilter === 'all') {
        params.active_only = false;
      } else {
        params.active_only = true;
        params.status = accountStatusFilter;
      }

      const response = await apiClient.get('/clients/', { params });
      return response.data;
    },
  });

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
  }, [search, accountStatusFilter]);

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
      <div className="mb-6">
        <div className="flex gap-4 mb-4">
          <Input
            type="text"
            placeholder="Search clients..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyPress={handleKeyPress}
          />
          <Button onClick={handleSearch}>Search</Button>
          <Button onClick={() => setIsAddModalOpen(true)}>
            + Add Client
          </Button>
        </div>
        <div className="flex gap-4 items-center">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={accountStatusFilter}
              onChange={(e) => setAccountStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="active">Active</option>
              <option value="overdue">Overdue</option>
              <option value="suspended">Suspended</option>
              <option value="all">All (including deleted)</option>
            </select>
          </div>
          {total > 0 && (
            <div className="text-sm text-gray-600 mt-6">
              Showing {allClients.length} of {total} clients
            </div>
          )}
        </div>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>AutoCC</TableHead>
              <TableHead>Balance</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
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
                      {client.company_name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    {client.autocc_recurring ? (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                        Yes
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">—</span>
                    )}
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
                    <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
                      {client.account_status || 'Active'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => navigate(`/clients/${client.id}`)}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan="6" className="text-center py-8 text-gray-500">
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
