import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Button from '../components/ui/Button';
import AddExpenseModal from '../components/AddExpenseModal';

export default function ExpensesPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState(null);

  const { data: expensesData, isLoading } = useQuery({
    queryKey: ['expenses'],
    queryFn: async () => {
      const response = await apiClient.get('/expenses/');
      return response.data;
    },
  });

  const expenses = expensesData?.items || [];

  if (isLoading) {
    return <Layout title="Expenses">Loading...</Layout>;
  }

  const handleAddClick = () => {
    setSelectedExpense(null);
    setIsModalOpen(true);
  };

  const handleEditClick = (expense) => {
    setSelectedExpense(expense);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedExpense(null);
  };

  return (
    <Layout title="Expenses">
      <div className="mb-6">
        <Button onClick={handleAddClick}>+ Add Expense</Button>
      </div>

      <AddExpenseModal isOpen={isModalOpen} onClose={handleCloseModal} expense={selectedExpense} />

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Vendor</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {expenses && expenses.length > 0 ? (
              expenses.map((expense) => (
                <TableRow key={expense.id}>
                  <TableCell>{new Date(expense.expense_date).toLocaleDateString()}</TableCell>
                  <TableCell>{expense.vendor}</TableCell>
                  <TableCell>{expense.description || '-'}</TableCell>
                  <TableCell>${parseFloat(expense.amount).toFixed(2)}</TableCell>
                  <TableCell>{expense.category?.name || '-'}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="ghost" onClick={() => handleEditClick(expense)}>
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan="6" className="text-center py-8 text-gray-500">
                  No expenses found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Layout>
  );
}
