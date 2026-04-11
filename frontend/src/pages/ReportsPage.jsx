import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';

const months = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"];

export default function ReportsPage() {
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [fromDate, setFromDate] = useState(new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0]);
  const [toDate, setToDate] = useState(new Date().toISOString().split('T')[0]);

  // Revenue by Period
  const { data: revenueData, isLoading: revenueLoading } = useQuery({
    queryKey: ['reports', 'revenue-by-period', selectedYear],
    queryFn: async () => {
      const response = await apiClient.get('/reports/revenue-by-period', {
        params: { year: selectedYear },
      });
      return response.data;
    },
  });

  // AR Aging
  const { data: arAgingData, isLoading: arAgingLoading } = useQuery({
    queryKey: ['reports', 'ar-aging'],
    queryFn: async () => {
      const response = await apiClient.get('/reports/ar-aging');
      return response.data;
    },
  });

  // Profit & Loss
  const { data: plData, isLoading: plLoading } = useQuery({
    queryKey: ['reports', 'profit-loss', fromDate, toDate],
    queryFn: async () => {
      const response = await apiClient.get('/reports/profit-loss', {
        params: { from_date: fromDate, to_date: toDate },
      });
      return response.data;
    },
  });

  // Collections Queue
  const { data: collectionsData, isLoading: collectionsLoading } = useQuery({
    queryKey: ['collections', 'daily-queue'],
    queryFn: async () => {
      const response = await apiClient.get('/collections/daily-queue');
      return response.data;
    },
  });

  const closeDetail = () => setSelectedReport(null);

  return (
    <Layout title="Reports">
      {!selectedReport ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card
            className="cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => setSelectedReport('revenue')}
          >
            <CardHeader>
              <CardTitle>Revenue by Period</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">Detailed revenue breakdown by time period</p>
              <p className="text-sm text-gray-500 mt-2">Click to view report</p>
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => setSelectedReport('araging')}
          >
            <CardHeader>
              <CardTitle>Accounts Receivable Aging</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">Outstanding invoices grouped by aging period</p>
              <p className="text-sm text-gray-500 mt-2">Click to view report</p>
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => setSelectedReport('pl')}
          >
            <CardHeader>
              <CardTitle>Profit & Loss</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">Income and expense summary by category</p>
              <p className="text-sm text-gray-500 mt-2">Click to view report</p>
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => setSelectedReport('collections')}
          >
            <CardHeader>
              <CardTitle>Collections</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">Collections events and overdue account tracking</p>
              <p className="text-sm text-gray-500 mt-2">Click to view report</p>
            </CardContent>
          </Card>
        </div>
      ) : selectedReport === 'revenue' ? (
        <div>
          <div className="mb-6 flex items-center gap-4">
            <Button size="sm" variant="ghost" onClick={closeDetail}>
              ← Back
            </Button>
            <label className="text-sm font-medium">Year:</label>
            <Input
              type="number"
              value={selectedYear}
              onChange={(e) => setSelectedYear(parseInt(e.target.value))}
              className="w-32"
            />
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Revenue by Period - {selectedYear}</CardTitle>
            </CardHeader>
            <CardContent>
              {revenueLoading ? (
                <p>Loading...</p>
              ) : (
                <div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Month</TableHead>
                        <TableHead>Revenue</TableHead>
                        <TableHead>Invoice Count</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {months.map((month) => {
                        const data = revenueData?.months?.[month] || { total: 0, count: 0 };
                        return (
                          <TableRow key={month}>
                            <TableCell>{month}</TableCell>
                            <TableCell>${data.total.toFixed(2)}</TableCell>
                            <TableCell>{data.count}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-lg font-semibold">
                      Annual Total: ${(revenueData?.annual_total || 0).toFixed(2)}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : selectedReport === 'araging' ? (
        <div>
          <div className="mb-6">
            <Button size="sm" variant="ghost" onClick={closeDetail}>
              ← Back
            </Button>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Accounts Receivable Aging</CardTitle>
            </CardHeader>
            <CardContent>
              {arAgingLoading ? (
                <p>Loading...</p>
              ) : (
                <div>
                  <div className="grid grid-cols-5 gap-4 mb-6">
                    <div className="p-3 bg-green-50 rounded">
                      <p className="text-xs text-gray-600">Current</p>
                      <p className="text-lg font-bold">${(arAgingData?.totals?.current || 0).toFixed(2)}</p>
                    </div>
                    <div className="p-3 bg-yellow-50 rounded">
                      <p className="text-xs text-gray-600">1-30 Days</p>
                      <p className="text-lg font-bold">${(arAgingData?.totals?.['1_30'] || 0).toFixed(2)}</p>
                    </div>
                    <div className="p-3 bg-orange-50 rounded">
                      <p className="text-xs text-gray-600">31-60 Days</p>
                      <p className="text-lg font-bold">${(arAgingData?.totals?.['31_60'] || 0).toFixed(2)}</p>
                    </div>
                    <div className="p-3 bg-red-50 rounded">
                      <p className="text-xs text-gray-600">61-90 Days</p>
                      <p className="text-lg font-bold">${(arAgingData?.totals?.['61_90'] || 0).toFixed(2)}</p>
                    </div>
                    <div className="p-3 bg-red-100 rounded">
                      <p className="text-xs text-gray-600">Over 90 Days</p>
                      <p className="text-lg font-bold">${(arAgingData?.totals?.over_90 || 0).toFixed(2)}</p>
                    </div>
                  </div>

                  {['current', '1_30', '31_60', '61_90', 'over_90'].map((bucket) => {
                    const bucketData = arAgingData?.buckets?.[bucket] || [];
                    if (bucketData.length === 0) return null;

                    const bucketLabels = {
                      'current': 'Current',
                      '1_30': '1-30 Days Overdue',
                      '31_60': '31-60 Days Overdue',
                      '61_90': '61-90 Days Overdue',
                      'over_90': 'Over 90 Days Overdue'
                    };

                    return (
                      <div key={bucket} className="mb-6">
                        <h3 className="text-lg font-semibold mb-3">{bucketLabels[bucket]}</h3>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Invoice</TableHead>
                              <TableHead>Client</TableHead>
                              <TableHead>Due Date</TableHead>
                              <TableHead>Days Overdue</TableHead>
                              <TableHead>Balance</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {bucketData.map((invoice, idx) => (
                              <TableRow key={idx}>
                                <TableCell>{invoice.invoice_number}</TableCell>
                                <TableCell>{invoice.client}</TableCell>
                                <TableCell>{new Date(invoice.due_date).toLocaleDateString()}</TableCell>
                                <TableCell>{invoice.days_overdue}</TableCell>
                                <TableCell>${invoice.balance.toFixed(2)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    );
                  })}

                  <div className="mt-6 pt-4 border-t">
                    <p className="text-lg font-semibold">
                      Grand Total: ${(arAgingData?.grand_total || 0).toFixed(2)}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : selectedReport === 'pl' ? (
        <div>
          <div className="mb-6 flex items-center gap-4">
            <Button size="sm" variant="ghost" onClick={closeDetail}>
              ← Back
            </Button>
            <label className="text-sm font-medium">From:</label>
            <Input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-40"
            />
            <label className="text-sm font-medium">To:</label>
            <Input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-40"
            />
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Profit & Loss Report</CardTitle>
            </CardHeader>
            <CardContent>
              {plLoading ? (
                <p>Loading...</p>
              ) : (
                <div>
                  <div className="bg-blue-50 p-4 rounded mb-6">
                    <p className="text-sm text-gray-600">Total Income</p>
                    <p className="text-3xl font-bold text-blue-600">
                      ${(plData?.total_income || 0).toFixed(2)}
                    </p>
                  </div>

                  <h3 className="text-lg font-semibold mb-3">Expenses by Category</h3>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Code</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead>Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {plData?.expenses?.map((expense, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{expense.code}</TableCell>
                          <TableCell>{expense.name}</TableCell>
                          <TableCell>${expense.total.toFixed(2)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  <div className="mt-6 pt-4 border-t space-y-2">
                    <div className="flex justify-between">
                      <span>Total Expenses:</span>
                      <span className="font-semibold">${(plData?.total_expenses || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-lg font-bold">
                      <span>Net Income:</span>
                      <span className={plData?.net_income >= 0 ? 'text-green-600' : 'text-red-600'}>
                        ${(plData?.net_income || 0).toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        <div>
          <div className="mb-6">
            <Button size="sm" variant="ghost" onClick={closeDetail}>
              ← Back
            </Button>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Collections Report - {collectionsData?.date ? new Date(collectionsData.date).toLocaleDateString() : 'Today'}</CardTitle>
            </CardHeader>
            <CardContent>
              {collectionsLoading ? (
                <p>Loading...</p>
              ) : (
                <div className="space-y-6">
                  {/* Overdue Summary */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-red-50 rounded-lg">
                      <p className="text-sm text-gray-600">Total Overdue</p>
                      <p className="text-2xl font-bold text-red-600">{collectionsData?.overdue_count || 0}</p>
                    </div>
                    <div className="p-4 bg-orange-50 rounded-lg">
                      <p className="text-sm text-gray-600">Late Fee Candidates</p>
                      <p className="text-2xl font-bold text-orange-600">{collectionsData?.late_fee_candidates?.length || 0}</p>
                    </div>
                    <div className="p-4 bg-red-100 rounded-lg">
                      <p className="text-sm text-gray-600">Suspension Candidates</p>
                      <p className="text-2xl font-bold text-red-700">{collectionsData?.suspension_candidates?.length || 0}</p>
                    </div>
                  </div>

                  {/* Late Fee Candidates */}
                  {collectionsData?.late_fee_candidates && collectionsData.late_fee_candidates.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Late Fee Candidates (10+ days overdue)</h3>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Invoice</TableHead>
                            <TableHead>Client</TableHead>
                            <TableHead>Due Date</TableHead>
                            <TableHead>Days Overdue</TableHead>
                            <TableHead>Balance</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {collectionsData.late_fee_candidates.map((inv, idx) => (
                            <TableRow key={idx}>
                              <TableCell>{inv.invoice_number}</TableCell>
                              <TableCell>{inv.client_name}</TableCell>
                              <TableCell>{new Date(inv.due_date).toLocaleDateString()}</TableCell>
                              <TableCell>{inv.days_overdue}</TableCell>
                              <TableCell>${inv.balance_due.toFixed(2)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  {/* Suspension Candidates */}
                  {collectionsData?.suspension_candidates && collectionsData.suspension_candidates.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Suspension Candidates (20+ days overdue)</h3>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Invoice</TableHead>
                            <TableHead>Client</TableHead>
                            <TableHead>Due Date</TableHead>
                            <TableHead>Days Overdue</TableHead>
                            <TableHead>Balance</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {collectionsData.suspension_candidates.map((inv, idx) => (
                            <TableRow key={idx}>
                              <TableCell>{inv.invoice_number}</TableCell>
                              <TableCell>{inv.client_name}</TableCell>
                              <TableCell>{new Date(inv.due_date).toLocaleDateString()}</TableCell>
                              <TableCell>{inv.days_overdue}</TableCell>
                              <TableCell>${inv.balance_due.toFixed(2)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  {/* No action needed message */}
                  {(!collectionsData?.late_fee_candidates || collectionsData.late_fee_candidates.length === 0) &&
                    (!collectionsData?.suspension_candidates || collectionsData.suspension_candidates.length === 0) && (
                    <div className="p-4 bg-green-50 rounded-lg text-center">
                      <p className="text-green-700 font-medium">✓ No collections actions needed today</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </Layout>
  );
}
