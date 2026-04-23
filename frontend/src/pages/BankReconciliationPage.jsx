import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { formatLocalDate } from '../utils/dateFormat';

export default function BankReconciliationPage() {
  const { accountId, reconciliationId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [statementBalance, setStatementBalance] = useState('');
  const [reconciliationDate, setReconciliationDate] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [showNewReconciliation, setShowNewReconciliation] = useState(!reconciliationId);
  const [notes, setNotes] = useState('');

  const { data: account } = useQuery({
    queryKey: ['bank-account', accountId],
    queryFn: async () => {
      const response = await apiClient.get(`/bank/bank-accounts`);
      return response.data.find(a => a.id === parseInt(accountId));
    },
  });

  const { data: reconciliation, isLoading: reconcilLoading } = useQuery({
    queryKey: ['reconciliation', reconciliationId],
    queryFn: async () => {
      if (!reconciliationId) return null;
      const response = await apiClient.get(`/bank/reconciliations/${reconciliationId}/summary`);
      return response.data;
    },
    enabled: !!reconciliationId,
  });

  const createReconciliationMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(`/bank/reconciliations/${accountId}`, null, {
        params: {
          statement_balance: statementBalance,
          reconciliation_date: reconciliationDate,
          notes: notes || undefined,
        }
      });
      return response.data;
    },
    onSuccess: (data) => {
      setShowNewReconciliation(false);
      queryClient.invalidateQueries({ queryKey: ['reconciliation', data.id] });
      navigate(`/bank-reconciliation/${accountId}/${data.id}`);
    },
  });

  const toggleReconcileMutation = useMutation({
    mutationFn: async (transactionId) => {
      const response = await apiClient.put(
        `/bank/transactions/${transactionId}/reconcile`,
        null,
        {
          params: { reconciled: true }
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reconciliation'] });
    },
  });

  const completeReconciliationMutation = useMutation({
    mutationFn: async () => {
      await apiClient.put(`/bank/reconciliations/${reconciliationId}/complete`);
      return true;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reconciliation'] });
      alert('Reconciliation completed!');
      navigate(`/check-register`);
    },
  });

  if (showNewReconciliation) {
    return (
      <Layout title="New Bank Reconciliation" onBack={() => navigate(-1)}>
        <Card className="max-w-2xl mx-auto">
          <div className="p-6 space-y-4">
            <h2 className="text-xl font-bold text-gray-900">{account?.account_name}</h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Statement Date
              </label>
              <Input
                type="date"
                value={reconciliationDate}
                onChange={(e) => setReconciliationDate(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Statement Balance
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-gray-600">$</span>
                <Input
                  type="number"
                  value={statementBalance}
                  onChange={(e) => setStatementBalance(e.target.value)}
                  placeholder="0.00"
                  step="0.01"
                  className="pl-7"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Enter reconciliation notes..."
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
              <Button
                onClick={() => navigate(-1)}
                variant="secondary"
              >
                Cancel
              </Button>
              <Button
                onClick={() => createReconciliationMutation.mutate()}
                disabled={!statementBalance || createReconciliationMutation.isPending}
              >
                {createReconciliationMutation.isPending ? 'Creating...' : 'Start Reconciliation'}
              </Button>
            </div>
          </div>
        </Card>
      </Layout>
    );
  }

  if (reconcilLoading) {
    return <Layout title="Bank Reconciliation">Loading...</Layout>;
  }

  if (!reconciliation) {
    return <Layout title="Bank Reconciliation">Reconciliation not found</Layout>;
  }

  const rec = reconciliation.reconciliation;
  const cleared = reconciliation.cleared_transactions;
  const uncleared = reconciliation.uncleared_transactions;

  return (
    <Layout title="Bank Reconciliation" onBack={() => navigate(-1)}>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="text-xs font-semibold text-gray-600 uppercase">Statement Balance</div>
            <div className="text-2xl font-bold text-gray-900">
              ${rec.statement_balance.toFixed(2)}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-xs font-semibold text-gray-600 uppercase">Cleared Amount</div>
            <div className="text-2xl font-bold text-green-600">
              ${cleared.amount.toFixed(2)}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-xs font-semibold text-gray-600 uppercase">Uncleared Amount</div>
            <div className="text-2xl font-bold text-amber-600">
              ${uncleared.amount.toFixed(2)}
            </div>
          </Card>
          <Card className={`p-4 ${rec.difference === 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className="text-xs font-semibold text-gray-600 uppercase">Difference</div>
            <div className={`text-2xl font-bold ${rec.difference === 0 ? 'text-green-600' : 'text-red-600'}`}>
              ${rec.difference.toFixed(2)}
            </div>
          </Card>
        </div>

        {rec.difference === 0 && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
            ✓ Account reconciles! You can complete the reconciliation.
          </div>
        )}

        {rec.difference !== 0 && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-800">
            ⚠ Difference of ${Math.abs(rec.difference).toFixed(2)}. Mark more transactions as reconciled or adjust the statement balance.
          </div>
        )}

        {/* Cleared Transactions */}
        <Card>
          <div className="border-b border-gray-200 px-6 py-4 bg-gray-50">
            <h3 className="text-lg font-semibold text-gray-900">
              Cleared Transactions ({cleared.count})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-white border-b border-gray-200">
                <tr>
                  <th className="text-left px-6 py-3 font-semibold text-gray-600">Date</th>
                  <th className="text-left px-6 py-3 font-semibold text-gray-600">Description</th>
                  <th className="text-right px-6 py-3 font-semibold text-gray-600">Amount</th>
                  <th className="text-center px-6 py-3 font-semibold text-gray-600">Action</th>
                </tr>
              </thead>
              <tbody>
                {cleared.items.map((txn) => (
                  <tr key={txn.id} className="border-b border-gray-200 hover:bg-green-50">
                    <td className="px-6 py-3">{formatLocalDate(txn.transaction_date)}</td>
                    <td className="px-6 py-3 text-gray-700">{txn.description}</td>
                    <td className="px-6 py-3 text-right font-mono">
                      ${parseFloat(txn.amount).toFixed(2)}
                    </td>
                    <td className="px-6 py-3 text-center">
                      <span className="inline-block px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium">
                        ✓ Cleared
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Uncleared Transactions */}
        <Card>
          <div className="border-b border-gray-200 px-6 py-4 bg-gray-50">
            <h3 className="text-lg font-semibold text-gray-900">
              Uncleared Transactions ({uncleared.count})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-white border-b border-gray-200">
                <tr>
                  <th className="text-left px-6 py-3 font-semibold text-gray-600">Date</th>
                  <th className="text-left px-6 py-3 font-semibold text-gray-600">Description</th>
                  <th className="text-right px-6 py-3 font-semibold text-gray-600">Amount</th>
                  <th className="text-center px-6 py-3 font-semibold text-gray-600">Action</th>
                </tr>
              </thead>
              <tbody>
                {uncleared.items.map((txn) => (
                  <tr key={txn.id} className="border-b border-gray-200 hover:bg-amber-50">
                    <td className="px-6 py-3">{formatLocalDate(txn.transaction_date)}</td>
                    <td className="px-6 py-3 text-gray-700">{txn.description}</td>
                    <td className="px-6 py-3 text-right font-mono">
                      ${parseFloat(txn.amount).toFixed(2)}
                    </td>
                    <td className="px-6 py-3 text-center">
                      <Button
                        size="sm"
                        onClick={() => toggleReconcileMutation.mutate(txn.id)}
                        disabled={toggleReconcileMutation.isPending}
                      >
                        Mark Cleared
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <Button
            onClick={() => navigate(-1)}
            variant="secondary"
          >
            Cancel
          </Button>
          <Button
            onClick={() => completeReconciliationMutation.mutate()}
            disabled={rec.difference !== 0 || completeReconciliationMutation.isPending}
            className="bg-green-600 hover:bg-green-700"
          >
            {completeReconciliationMutation.isPending ? 'Completing...' : 'Complete Reconciliation'}
          </Button>
        </div>
      </div>
    </Layout>
  );
}
