import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import JournalEntryModal from '../components/JournalEntryModal';

export default function JournalEntriesPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [filters, setFilters] = useState({
    from_date: '',
    to_date: '',
    account_code: '',
    source: '',
  });
  const queryClient = useQueryClient();

  const queryParams = new URLSearchParams();
  if (filters.from_date) queryParams.append('from_date', filters.from_date);
  if (filters.to_date) queryParams.append('to_date', filters.to_date);
  if (filters.account_code) queryParams.append('account_code', filters.account_code);
  if (filters.source) queryParams.append('source', filters.source);

  const { data: entriesData, isLoading, refetch } = useQuery({
    queryKey: ['journal-entries', filters],
    queryFn: async () => {
      const response = await apiClient.get(`/journal-entries/?${queryParams.toString()}`);
      return response.data;
    },
  });

  const entries = entriesData?.items || [];

  const deleteMutation = useMutation({
    mutationFn: async (entryId) => {
      await apiClient.delete(`/journal-entries/${entryId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal-entries'] });
      refetch();
    },
  });

  if (isLoading) {
    return <Layout title="Journal Entries">Loading...</Layout>;
  }

  const handleAddClick = () => {
    setSelectedEntry(null);
    setIsModalOpen(true);
  };

  const handleEditClick = (entry) => {
    setSelectedEntry(entry);
    setIsModalOpen(true);
  };

  const handleDeleteClick = (entry) => {
    if (confirm(`Are you sure you want to delete this journal entry? This action cannot be undone.`)) {
      deleteMutation.mutate(entry.id);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEntry(null);
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleClearFilters = () => {
    setFilters({
      from_date: '',
      to_date: '',
      account_code: '',
      source: '',
    });
  };

  return (
    <Layout title="Journal Entries">
      <div className="mb-6 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold">Journal Entries</h2>
          <Button onClick={handleAddClick}>+ Add Entry</Button>
        </div>

        {/* Filters */}
        <Card className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                From Date
              </label>
              <Input
                type="date"
                name="from_date"
                value={filters.from_date}
                onChange={handleFilterChange}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                To Date
              </label>
              <Input
                type="date"
                name="to_date"
                value={filters.to_date}
                onChange={handleFilterChange}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                GL Account Code
              </label>
              <Input
                type="text"
                name="account_code"
                value={filters.account_code}
                onChange={handleFilterChange}
                placeholder="e.g., 4100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Source
              </label>
              <select
                name="source"
                value={filters.source}
                onChange={handleFilterChange}
                className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                <option value="">All Sources</option>
                <option value="manual">Manual Entry</option>
                <option value="qbo_journal">QuickBooks Online</option>
                <option value="bank_import">Bank Import</option>
              </select>
            </div>
            <div className="flex items-end">
              <Button
                variant="secondary"
                onClick={handleClearFilters}
                className="w-full"
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <JournalEntryModal isOpen={isModalOpen} onClose={handleCloseModal} entry={selectedEntry} />

      <Card>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>GL Account Code</TableHead>
                <TableHead>GL Account Name</TableHead>
                <TableHead className="text-right">Debit</TableHead>
                <TableHead className="text-right">Credit</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Ref #</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries && entries.length > 0 ? (
                entries.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell>{new Date(entry.transaction_date).toLocaleDateString()}</TableCell>
                    <TableCell className="font-mono text-sm">{entry.gl_account_code}</TableCell>
                    <TableCell>{entry.gl_account_name}</TableCell>
                    <TableCell className="text-right">
                      {parseFloat(entry.debit) > 0 ? `$${parseFloat(entry.debit).toFixed(2)}` : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      {parseFloat(entry.credit) > 0 ? `$${parseFloat(entry.credit).toFixed(2)}` : '-'}
                    </TableCell>
                    <TableCell className="max-w-xs truncate">{entry.description || '-'}</TableCell>
                    <TableCell className="text-sm">{entry.reference_number || '-'}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                        {entry.source === 'manual' && 'Manual'}
                        {entry.source === 'qbo_journal' && 'QBO'}
                        {entry.source === 'bank_import' && 'Bank'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEditClick(entry)}
                        >
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-600 hover:text-red-800"
                          onClick={() => handleDeleteClick(entry)}
                          disabled={deleteMutation.isPending}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan="9" className="text-center py-8 text-gray-500">
                    No journal entries found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      {entriesData && (
        <div className="mt-4 text-sm text-gray-600">
          Total: {entriesData.total} entries
        </div>
      )}
    </Layout>
  );
}
