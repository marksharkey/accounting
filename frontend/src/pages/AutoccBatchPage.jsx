import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Button from '../components/ui/Button';

export default function AutoccBatchPage() {
  const [phase, setPhase] = useState('checklist'); // 'checklist', 'summary', 'done'
  const [checkedItems, setCheckedItems] = useState({});
  const [summary, setSummary] = useState(null);
  const [selectedDate, setSelectedDate] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  const { data: autoccClients, isLoading } = useQuery({
    queryKey: ['autocc-batch', selectedDate.getFullYear(), selectedDate.getMonth() + 1],
    queryFn: async () => {
      const response = await apiClient.get('/invoices/autocc-batch', {
        params: {
          year: selectedDate.getFullYear(),
          month: selectedDate.getMonth() + 1,
        }
      });
      return response.data;
    },
  });

  const processMutation = useMutation({
    mutationFn: async () => {
      const items = (autoccClients || []).map(client => ({
        client_id: client.id,
        invoice_id: client.invoice_id,
        paid: checkedItems[client.id] === true,
      }));

      const response = await apiClient.post('/invoices/autocc-batch/process', {
        items,
        year: selectedDate.getFullYear(),
        month: selectedDate.getMonth() + 1,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setSummary(data);
      setPhase('done');
    },
  });

  const handleCheckChange = (clientId, value) => {
    setCheckedItems(prev => ({
      ...prev,
      [clientId]: value,
    }));
  };

  const handleGenerateSummary = () => {
    setPhase('summary');
  };

  const handleConfirmAndSend = () => {
    processMutation.mutate();
  };

  const handleBackToChecklist = () => {
    setPhase('checklist');
  };

  const handleRestart = () => {
    setPhase('checklist');
    setCheckedItems({});
    setSummary(null);
  };

  const handlePrevMonth = () => {
    setSelectedDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
    setPhase('checklist');
    setCheckedItems({});
    setSummary(null);
  };

  const handleNextMonth = () => {
    setSelectedDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
    setPhase('checklist');
    setCheckedItems({});
    setSummary(null);
  };

  if (isLoading) {
    return <Layout title="AutoCC Batch">Loading...</Layout>;
  }

  const monthYear = selectedDate.toLocaleString('default', { month: 'long', year: 'numeric' });

  // Phase 1: Checklist
  if (phase === 'checklist') {
    const clientsWithInvoices = (autoccClients || []).filter(c => c.invoice_total);

    return (
      <Layout title="AutoCC Batch">
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold">AutoCC Batch — {monthYear}</h1>
            <div className="flex items-center gap-3">
              <Button
                onClick={handlePrevMonth}
                variant="outline"
                className="px-3 py-2"
              >
                ← Previous
              </Button>
              <Button
                onClick={handleNextMonth}
                variant="outline"
                className="px-3 py-2"
              >
                Next →
              </Button>
            </div>
          </div>
          <p className="text-gray-600">Mark each client as paid or declined, then generate a summary.</p>
        </div>

        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client</TableHead>
                <TableHead>Invoice #</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Payment Received?</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {autoccClients && autoccClients.length > 0 ? (
                autoccClients.map((client) => (
                  <TableRow key={client.id} className={!client.invoice_id ? 'opacity-60' : ''}>
                    <TableCell className="font-medium">{client.display_name}</TableCell>
                    <TableCell>{client.invoice_number || '—'}</TableCell>
                    <TableCell>{client.invoice_total ? `$${client.invoice_total.toFixed(2)}` : '—'}</TableCell>
                    <TableCell>
                      {client.invoice_status ? (
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                          {client.invoice_status}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">No invoice</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {client.invoice_total ? (
                        <div className="flex gap-2">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={checkedItems[client.id] === true}
                              onChange={(e) => handleCheckChange(client.id, e.target.checked)}
                              className="w-4 h-4"
                            />
                            Yes
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="radio"
                              name={`client-${client.id}`}
                              checked={checkedItems[client.id] === false}
                              onChange={(e) => handleCheckChange(client.id, false)}
                              className="w-4 h-4"
                            />
                            No
                          </label>
                        </div>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan="5" className="text-center py-8 text-gray-500">
                    No AutoCC recurring clients found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>

        <div className="mt-6 flex gap-3">
          <Button
            onClick={handleGenerateSummary}
            className="bg-blue-600 hover:bg-blue-700 text-white"
            disabled={clientsWithInvoices.length === 0}
          >
            Generate Summary
          </Button>
        </div>
      </Layout>
    );
  }

  // Phase 2: Summary
  if (phase === 'summary') {
    const paidItems = (autoccClients || [])
      .filter(c => c.invoice_total && checkedItems[c.id] === true);
    const declinedItems = (autoccClients || [])
      .filter(c => c.invoice_total && checkedItems[c.id] === false);

    return (
      <Layout title="AutoCC Batch">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Summary</h1>
          <p className="text-gray-600">Review what will be sent, then confirm.</p>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <Card>
            <div className="p-6">
              <h3 className="text-lg font-bold mb-4 text-green-600">
                Will Send Invoices ({paidItems.length})
              </h3>
              {paidItems.length > 0 ? (
                <ul className="space-y-2">
                  {paidItems.map(item => (
                    <li key={item.id} className="text-sm">
                      <span className="font-medium">{item.company_name}</span>
                      <br />
                      <span className="text-gray-600">
                        Invoice {item.invoice_number} - ${item.invoice_total?.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-600 text-sm">No invoices to send</p>
              )}
            </div>
          </Card>

          <Card>
            <div className="p-6">
              <h3 className="text-lg font-bold mb-4 text-red-600">
                Will Send Decline Notices ({declinedItems.length})
              </h3>
              {declinedItems.length > 0 ? (
                <ul className="space-y-2">
                  {declinedItems.map(item => (
                    <li key={item.id} className="text-sm">
                      <span className="font-medium">{item.company_name}</span>
                      <br />
                      <span className="text-gray-600">
                        Invoice {item.invoice_number}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-600 text-sm">No decline notices to send</p>
              )}
            </div>
          </Card>
        </div>

        <div className="mt-6 flex gap-3">
          <Button
            onClick={handleConfirmAndSend}
            className="bg-green-600 hover:bg-green-700 text-white"
            disabled={processMutation.isPending}
          >
            {processMutation.isPending ? 'Sending...' : 'Confirm & Send'}
          </Button>
          <Button
            onClick={handleBackToChecklist}
            variant="outline"
          >
            Back to Checklist
          </Button>
        </div>
      </Layout>
    );
  }

  // Phase 3: Done
  if (phase === 'done') {
    return (
      <Layout title="AutoCC Batch">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Done!</h1>
        </div>

        <Card>
          <div className="p-8 text-center">
            <div className="mb-6">
              <div className="text-5xl mb-4">✓</div>
              <h2 className="text-2xl font-bold mb-4">Emails Sent Successfully</h2>
            </div>

            <div className="grid grid-cols-2 gap-6 my-8">
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="text-3xl font-bold text-green-600">{summary?.paid_count || 0}</div>
                <div className="text-sm text-gray-600 mt-2">Invoices Sent</div>
                {summary?.paid_invoices && summary.paid_invoices.length > 0 && (
                  <ul className="mt-3 text-left text-xs space-y-1">
                    {summary.paid_invoices.map(inv => (
                      <li key={inv} className="text-gray-700">{inv}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                <div className="text-3xl font-bold text-red-600">{summary?.declined_count || 0}</div>
                <div className="text-sm text-gray-600 mt-2">Decline Notices Sent</div>
                {summary?.declined_clients && summary.declined_clients.length > 0 && (
                  <ul className="mt-3 text-left text-xs space-y-1">
                    {summary.declined_clients.map(client => (
                      <li key={client} className="text-gray-700">{client}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="mt-8 flex gap-3 justify-center">
              <Button
                onClick={handleRestart}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                Process Another Batch
              </Button>
              <Button
                onClick={() => window.location.href = '/invoices'}
                variant="outline"
              >
                Go to Invoices
              </Button>
            </div>
          </div>
        </Card>
      </Layout>
    );
  }
}
