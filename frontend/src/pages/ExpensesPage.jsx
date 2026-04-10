import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Button from '../components/ui/Button';

export default function ExpensesPage() {
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

  return (
    <Layout title="Expenses">
      <div className="mb-6">
        <Button>+ Add Expense</Button>
      </div>

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
                    <Button size="sm" variant="ghost">
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
