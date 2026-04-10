import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import AddClientModal from '../components/AddClientModal';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import { formatBillingType } from '../utils/formatting';

export default function ClientsListPage() {
  const [search, setSearch] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const navigate = useNavigate();

  const { data: clientData, isLoading } = useQuery({
    queryKey: ['clients', search],
    queryFn: async () => {
      const response = await apiClient.get('/clients/', {
        params: { search: search || undefined },
      });
      return response.data;
    },
  });

  const clients = clientData?.items || [];

  if (isLoading) {
    return <Layout title="Clients">Loading...</Layout>;
  }

  return (
    <Layout title="Clients">
      <AddClientModal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} />
      <div className="mb-6">
        <div className="flex gap-4">
          <div className="flex-1">
            <Input
              type="text"
              placeholder="Search clients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button onClick={() => setIsAddModalOpen(true)}>
            + Add Client
          </Button>
        </div>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Billing Type</TableHead>
              <TableHead>Balance</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {clients && clients.length > 0 ? (
              clients.map((client) => (
                <TableRow key={client.id}>
                  <TableCell className="font-medium">{client.company_name}</TableCell>
                  <TableCell>{formatBillingType(client.billing_type)}</TableCell>
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
                <TableCell colSpan="5" className="text-center py-8 text-gray-500">
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
