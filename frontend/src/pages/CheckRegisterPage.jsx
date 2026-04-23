import { useState, useEffect } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import { formatLocalDate } from '../utils/dateFormat';

export default function CheckRegisterPage() {
  const navigate = useNavigate();
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [addFormData, setAddFormData] = useState({
    transaction_date: new Date().toISOString().split('T')[0],
    transaction_type: 'other',
    amount: '',
    description: '',
    transaction_number: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingTransactionId, setEditingTransactionId] = useState(null);
  const [editFormData, setEditFormData] = useState(null);
  const queryClient = useQueryClient();

  const { data: accounts } = useQuery({
    queryKey: ['bank-accounts'],
    queryFn: async () => {
      const response = await apiClient.get('/bank/bank-accounts');
      return response.data;
    },
  });

  useEffect(() => {
    if (accounts && accounts.length > 0 && !selectedAccountId) {
      setSelectedAccountId(accounts[0].id);
    }
  }, [accounts]);

  const { data: register, isLoading } = useQuery({
    queryKey: ['check-register', selectedAccountId, fromDate, toDate],
    queryFn: async () => {
      if (!selectedAccountId) return null;
      const params = new URLSearchParams();
      if (fromDate) params.append('from_date', fromDate);
      if (toDate) params.append('to_date', toDate);

      const response = await apiClient.get(
        `/bank/check-register/${selectedAccountId}?${params.toString()}&limit=5000`
      );
      return response.data;
    },
    enabled: !!selectedAccountId,
  });

  const toggleReconcileMutation = useMutation({
    mutationFn: async ({ transactionId, reconciled }) => {
      await apiClient.put(
        `/bank/transactions/${transactionId}/reconcile`,
        null,
        { params: { reconciled: !reconciled } }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['check-register', selectedAccountId, fromDate, toDate] });
    },
    onError: (error) => {
      alert('Error updating reconciliation status: ' + (error.response?.data?.detail || error.message));
    }
  });

  const updateTransactionMutation = useMutation({
    mutationFn: async (data) => {
      await apiClient.put(`/bank/transactions/${editingTransactionId}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['check-register', selectedAccountId, fromDate, toDate] });
      setEditingTransactionId(null);
      setEditFormData(null);
    },
    onError: (error) => {
      alert('Error updating transaction: ' + (error.response?.data?.detail || error.message));
    }
  });

  const deleteTransactionMutation = useMutation({
    mutationFn: async (transactionId) => {
      await apiClient.delete(`/bank/transactions/${transactionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['check-register', selectedAccountId, fromDate, toDate] });
      setEditingTransactionId(null);
      setEditFormData(null);
    },
    onError: (error) => {
      alert('Error deleting transaction: ' + (error.response?.data?.detail || error.message));
    }
  });

  const handleEditTransaction = (txn) => {
    setEditingTransactionId(txn.id);
    setEditFormData({
      transaction_date: txn.transaction_date,
      transaction_type: txn.transaction_type,
      amount: txn.amount,
      description: txn.description || '',
      transaction_number: txn.transaction_number || ''
    });
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editFormData.transaction_date || !editFormData.transaction_type || !editFormData.amount) {
      alert('Please fill in required fields');
      return;
    }
    await updateTransactionMutation.mutate({
      transaction_date: editFormData.transaction_date,
      transaction_type: editFormData.transaction_type,
      amount: parseFloat(editFormData.amount),
      description: editFormData.description || null,
      transaction_number: editFormData.transaction_number || null
    });
  };

  const handleAddTransaction = async (e) => {
    e.preventDefault();
    if (!selectedAccountId || !addFormData.transaction_date || !addFormData.transaction_type || !addFormData.amount) {
      alert('Please fill in required fields');
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.post(`/bank/transactions/${selectedAccountId}`, {
        transaction_date: addFormData.transaction_date,
        transaction_type: addFormData.transaction_type,
        amount: parseFloat(addFormData.amount),
        description: addFormData.description || null,
        transaction_number: addFormData.transaction_number || null
      });

      // Reset form and refresh list
      setAddFormData({
        transaction_date: new Date().toISOString().split('T')[0],
        transaction_type: 'other',
        amount: '',
        description: '',
        transaction_number: ''
      });
      setShowAddForm(false);
      queryClient.invalidateQueries({ queryKey: ['check-register', selectedAccountId, fromDate, toDate] });
    } catch (error) {
      alert('Error creating transaction: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedAccount = accounts?.find(a => a.id === selectedAccountId);
  const transactions = register?.items || [];

  const endingBalance = transactions.length > 0
    ? transactions[0].balance
    : selectedAccount?.opening_balance || 0;

  return (
    <Layout title="Bank Register" onBack={() => navigate(-1)}>
      {/* Header section */}
      <div className="mb-6 flex justify-between items-start">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Bank Account</label>
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(parseInt(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select account...</option>
            {accounts?.map((account) => (
              <option key={account.id} value={account.id}>
                {account.account_name}
              </option>
            ))}
          </select>
        </div>

        <div className="text-right">
          <div className="text-sm font-medium text-gray-600 uppercase tracking-wide">ENDING BALANCE</div>
          <div className="text-4xl font-bold text-gray-900">
            ${endingBalance ? parseFloat(endingBalance).toFixed(2) : '0.00'}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
            <Input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
            <Input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="text-sm"
            />
          </div>

          <div className="flex items-end">
            <Button
              onClick={() => {
                setFromDate('');
                setToDate('');
              }}
              variant="outline"
              className="w-full"
            >
              Clear
            </Button>
          </div>

          <div className="flex items-end gap-2">
            <Button
              onClick={() => setShowAddForm(!showAddForm)}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white"
            >
              + Add
            </Button>
            <Button
              onClick={() => navigate(`/bank-reconciliation/${selectedAccountId}`)}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
            >
              Reconcile
            </Button>
          </div>
        </div>
      </div>

      {/* Edit Transaction Modal */}
      {editingTransactionId && editFormData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Edit Transaction</h3>
            <form onSubmit={handleSaveEdit}>
              <div className="space-y-3 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
                  <Input
                    type="date"
                    value={editFormData.transaction_date}
                    onChange={(e) => setEditFormData({...editFormData, transaction_date: e.target.value})}
                    className="text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
                  <select
                    value={editFormData.transaction_type}
                    onChange={(e) => setEditFormData({...editFormData, transaction_type: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="check">Check</option>
                    <option value="deposit">Deposit</option>
                    <option value="transfer">Transfer</option>
                    <option value="payment">Payment</option>
                    <option value="fee">Fee</option>
                    <option value="interest">Interest</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Amount *</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={editFormData.amount}
                    onChange={(e) => setEditFormData({...editFormData, amount: e.target.value})}
                    className="text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <Input
                    type="text"
                    value={editFormData.description}
                    onChange={(e) => setEditFormData({...editFormData, description: e.target.value})}
                    className="text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reference Number</label>
                  <Input
                    type="text"
                    value={editFormData.transaction_number}
                    onChange={(e) => setEditFormData({...editFormData, transaction_number: e.target.value})}
                    className="text-sm"
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end">
                <Button
                  type="button"
                  onClick={() => {
                    setEditingTransactionId(null);
                    setEditFormData(null);
                  }}
                  variant="outline"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={() => {
                    if (window.confirm('Are you sure you want to delete this transaction?')) {
                      deleteTransactionMutation.mutate(editingTransactionId);
                    }
                  }}
                  disabled={deleteTransactionMutation.isPending}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                >
                  Delete
                </Button>
                <Button
                  type="submit"
                  disabled={updateTransactionMutation.isPending}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                >
                  Save
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Transaction Form */}
      {showAddForm && (
        <div className="mb-6 p-6 bg-white rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Transaction</h3>
          <form onSubmit={handleAddTransaction}>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
                <Input
                  type="date"
                  value={addFormData.transaction_date}
                  onChange={(e) => setAddFormData({...addFormData, transaction_date: e.target.value})}
                  className="text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
                <select
                  value={addFormData.transaction_type}
                  onChange={(e) => setAddFormData({...addFormData, transaction_type: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="check">Check</option>
                  <option value="deposit">Deposit</option>
                  <option value="transfer">Transfer</option>
                  <option value="payment">Payment</option>
                  <option value="fee">Fee</option>
                  <option value="interest">Interest</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount * (negative for payments)</label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={addFormData.amount}
                  onChange={(e) => setAddFormData({...addFormData, amount: e.target.value})}
                  className="text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <Input
                  type="text"
                  placeholder="e.g., Bank fee, Check #1234"
                  value={addFormData.description}
                  onChange={(e) => setAddFormData({...addFormData, description: e.target.value})}
                  className="text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reference Number</label>
                <Input
                  type="text"
                  placeholder="e.g., Check number"
                  value={addFormData.transaction_number}
                  onChange={(e) => setAddFormData({...addFormData, transaction_number: e.target.value})}
                  className="text-sm"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {isSubmitting ? 'Creating...' : 'Create Transaction'}
              </Button>
              <Button
                type="button"
                onClick={() => setShowAddForm(false)}
                variant="outline"
              >
                Cancel
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Transactions */}
      <div className="bg-white rounded-lg border border-gray-200">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading transactions...</div>
        ) : transactions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No transactions found</div>
        ) : (
          <>
            {/* Header Row 1 */}
            <div className="border-b border-gray-300 bg-gray-100">
              <div className="flex px-6 py-3 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <div style={{ width: '90px' }}>DATE</div>
                <div style={{ width: '70px' }}>REF NO.</div>
                <div style={{ width: '150px' }}>PAYEE</div>
                <div style={{ flex: 1 }}>MEMO</div>
                <div style={{ width: '100px', textAlign: 'right' }}>PAYMENT</div>
                <div style={{ width: '100px', textAlign: 'right' }}>DEPOSIT</div>
                <div style={{ width: '40px', textAlign: 'center' }} title="Click to toggle reconciliation status">CLEARED</div>
                <div style={{ width: '120px', textAlign: 'right' }}>BALANCE</div>
              </div>
            </div>

            {/* Header Row 2 */}
            <div className="border-b-2 border-gray-300 bg-gray-50">
              <div className="flex px-6 py-2 text-xs font-semibold text-gray-600">
                <div style={{ width: '90px' }}></div>
                <div style={{ width: '70px' }}>TYPE</div>
                <div style={{ width: '150px' }}>ACCOUNT</div>
                <div style={{ flex: 1 }}></div>
                <div style={{ width: '100px' }}></div>
                <div style={{ width: '100px' }}></div>
                <div style={{ width: '40px' }}></div>
                <div style={{ width: '120px' }}></div>
              </div>
            </div>

            {/* Transactions */}
            <div className="divide-y divide-gray-200">
              {transactions.map((txn) => {
                const amount = parseFloat(txn.amount);
                const isPayment = amount < 0;
                const paymentAmount = isPayment ? Math.abs(amount).toFixed(2) : '';
                const depositAmount = !isPayment ? amount.toFixed(2) : '';

                return (
                  <div key={txn.id}>
                    {/* Row 1: Main Transaction Data */}
                    <div className="flex px-6 py-2 text-sm text-gray-900 hover:bg-blue-50">
                      <div style={{ width: '90px' }} className="font-mono text-gray-700">
                        {formatLocalDate(txn.transaction_date)}
                      </div>
                      <div style={{ width: '70px' }} className="font-mono text-gray-700">
                        {txn.transaction_number || ''}
                      </div>
                      <div style={{ width: '150px' }} className="truncate">
                        {txn.description || ''}
                      </div>
                      <div style={{ flex: 1 }}></div>
                      <div style={{ width: '100px', textAlign: 'right' }} className="font-mono">
                        {paymentAmount && <span className="text-red-600">{paymentAmount}</span>}
                      </div>
                      <div style={{ width: '100px', textAlign: 'right' }} className="font-mono">
                        {depositAmount && <span className="text-green-600">{depositAmount}</span>}
                      </div>
                      <div style={{ width: '40px', textAlign: 'center' }}>
                        <button
                          onClick={() => toggleReconcileMutation.mutate({ transactionId: txn.id, reconciled: txn.reconciled })}
                          disabled={toggleReconcileMutation.isPending}
                          className={`inline-block w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                            txn.reconciled
                              ? 'bg-blue-600 border-blue-600 text-white'
                              : 'border-gray-300 hover:border-blue-400'
                          }`}
                          title={txn.reconciled ? 'Click to unmark as cleared' : 'Click to mark as cleared'}
                        >
                          {txn.reconciled && <span className="text-xs">✓</span>}
                        </button>
                      </div>
                      <div style={{ width: '120px', textAlign: 'right' }} className="font-mono text-gray-900">
                        {txn.balance ? parseFloat(txn.balance).toFixed(2) : '—'}
                      </div>
                    </div>

                    {/* Row 2: Type and Account */}
                    <div className="flex px-6 py-2 text-xs text-gray-600 bg-gray-50 border-t border-gray-100 items-center justify-between">
                      <div className="flex" style={{ flex: 1 }}>
                        <div style={{ width: '90px' }}></div>
                        <div style={{ width: '70px' }} className="font-medium text-gray-600 capitalize">
                          {txn.transaction_type}
                        </div>
                        <div style={{ width: '150px' }} className="text-gray-600">
                          {txn.gl_account || '-'}
                        </div>
                      </div>
                      <button
                        onClick={() => handleEditTransaction(txn)}
                        className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                        title="Edit transaction"
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 px-6 py-3 bg-gray-50 text-xs text-gray-600">
              Showing {transactions.length} of {register?.total || 0} transactions
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
