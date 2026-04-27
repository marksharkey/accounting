import React, { useState } from 'react';
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
  const [drilldown, setDrilldown] = useState(null);
  const [balanceSheetDate, setBalanceSheetDate] = useState(new Date().toISOString().split('T')[0]);

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

  // Balance Sheet
  const { data: balanceSheetData, isLoading: balanceSheetLoading } = useQuery({
    queryKey: ['reports', 'balance-sheet', balanceSheetDate],
    queryFn: async () => {
      const response = await apiClient.get('/reports/balance-sheet', {
        params: { as_of: balanceSheetDate },
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

  // Profit & Loss Drilldown Transactions
  const { data: drilldownData, isLoading: drilldownLoading } = useQuery({
    queryKey: ['reports', 'profit-loss/transactions', fromDate, toDate, drilldown],
    queryFn: async () => {
      const params = new URLSearchParams({
        from_date: fromDate,
        to_date: toDate,
      });
      if (drilldown?.accountCode) {
        params.append('account_code', drilldown.accountCode);
      } else if (drilldown?.accountNamePrefix) {
        params.append('account_name_prefix', drilldown.accountNamePrefix);
      }
      const response = await apiClient.get('/reports/profit-loss/transactions', { params });
      return response.data;
    },
    enabled: !!drilldown,
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
            onClick={() => setSelectedReport('balance-sheet')}
          >
            <CardHeader>
              <CardTitle>Balance Sheet</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">Assets, liabilities, and equity snapshot</p>
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
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Client</TableHead>
                        <TableHead className="text-right">Current</TableHead>
                        <TableHead className="text-right">1-30 Days</TableHead>
                        <TableHead className="text-right">31-60 Days</TableHead>
                        <TableHead className="text-right">61-90 Days</TableHead>
                        <TableHead className="text-right">Over 90 Days</TableHead>
                        <TableHead className="text-right">Balance</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {arAgingData?.clients?.map((client, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{client.name}</TableCell>
                          <TableCell className="text-right">${client.current.toFixed(2)}</TableCell>
                          <TableCell className="text-right">${client['1_30'].toFixed(2)}</TableCell>
                          <TableCell className="text-right">${client['31_60'].toFixed(2)}</TableCell>
                          <TableCell className="text-right">${client['61_90'].toFixed(2)}</TableCell>
                          <TableCell className="text-right">${client.over_90.toFixed(2)}</TableCell>
                          <TableCell className="text-right font-semibold">${client.balance.toFixed(2)}</TableCell>
                        </TableRow>
                      ))}
                      <TableRow className="border-t-2 bg-gray-50 font-semibold">
                        <TableCell>Total</TableCell>
                        <TableCell className="text-right">${(arAgingData?.totals?.current || 0).toFixed(2)}</TableCell>
                        <TableCell className="text-right">${(arAgingData?.totals?.['1_30'] || 0).toFixed(2)}</TableCell>
                        <TableCell className="text-right">${(arAgingData?.totals?.['31_60'] || 0).toFixed(2)}</TableCell>
                        <TableCell className="text-right">${(arAgingData?.totals?.['61_90'] || 0).toFixed(2)}</TableCell>
                        <TableCell className="text-right">${(arAgingData?.totals?.over_90 || 0).toFixed(2)}</TableCell>
                        <TableCell className="text-right">${(arAgingData?.grand_total || 0).toFixed(2)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : selectedReport === 'pl' ? (
        <div>
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
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
            <Button
              onClick={() => {
                const params = new URLSearchParams({ from_date: fromDate, to_date: toDate });
                window.open(`/api/reports/profit-loss/pdf?${params.toString()}`, '_blank');
              }}
              disabled={plLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              📥 Download PDF
            </Button>
          </div>

          {/* Drilldown Modal */}
          {drilldown && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg shadow-lg w-full max-w-5xl mx-4 max-h-[90vh] flex flex-col overflow-hidden">
                <div className="flex justify-between items-center p-6 border-b border-gray-200 flex-shrink-0">
                  <h2 className="text-lg font-bold">{drilldown.title}</h2>
                  <button
                    onClick={() => setDrilldown(null)}
                    className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
                  >
                    ×
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-6">
                  {drilldownLoading ? (
                    <p>Loading transactions...</p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Date</TableHead>
                          <TableHead>Account</TableHead>
                          <TableHead>Description</TableHead>
                          <TableHead>Reference</TableHead>
                          <TableHead className="text-right">Debit</TableHead>
                          <TableHead className="text-right">Credit</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {drilldownData?.entries?.map((entry, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="whitespace-nowrap">{new Date(entry.date).toLocaleDateString()}</TableCell>
                            <TableCell className="font-mono text-sm">{entry.gl_account_code}</TableCell>
                            <TableCell>{entry.description}</TableCell>
                            <TableCell className="font-mono text-sm">{entry.reference_number}</TableCell>
                            <TableCell className="text-right font-mono">{entry.debit > 0 ? `$${entry.debit.toFixed(2)}` : '-'}</TableCell>
                            <TableCell className="text-right font-mono">{entry.credit > 0 ? `$${entry.credit.toFixed(2)}` : '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
                <div className="border-t border-gray-200 p-6 bg-gray-50 flex-shrink-0">
                  <div className="flex justify-end gap-4 font-semibold">
                    <span>Total Debits: ${(drilldownData?.entries?.reduce((sum, e) => sum + e.debit, 0) || 0).toFixed(2)}</span>
                    <span>Total Credits: ${(drilldownData?.entries?.reduce((sum, e) => sum + e.credit, 0) || 0).toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Profit & Loss Report</CardTitle>
            </CardHeader>
            <CardContent>
              {plLoading ? (
                <p>Loading...</p>
              ) : (
                <div>
                  <h3 className="text-lg font-semibold mb-4 text-gray-900">Income by Category</h3>
                  {plData?.income && plData.income.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Account</TableHead>
                          <TableHead>Amount</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {plData.income.map((item, idx) => (
                          <TableRow key={idx} className="cursor-pointer hover:bg-blue-50" onClick={() => setDrilldown({ title: item.name, accountCode: item.code })}>
                            <TableCell>{item.name}</TableCell>
                            <TableCell className="text-right font-mono">${item.amount.toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-gray-500 italic py-4">No income recorded for this period.</p>
                  )}

                  <div className="bg-blue-50 p-4 rounded my-6">
                    <div className="flex justify-between items-center">
                      <p className="text-sm text-gray-600">Total Income</p>
                      <p className="text-3xl font-bold text-blue-600">
                        ${(plData?.total_income || 0).toFixed(2)}
                      </p>
                    </div>
                  </div>

                  <h3 className="text-lg font-semibold mb-4 text-gray-900">Expenses by Category</h3>
                  {plData?.expenses && plData.expenses.length > 0 ? (
                    <table className="w-full border-collapse">
                      <thead>
                        <tr>
                          <th className="text-left font-semibold text-gray-900 py-2 px-0">Account</th>
                          <th className="text-right font-semibold text-gray-900 py-2 px-0">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {plData.expenses.map((expense, idx) =>
                          expense.type === 'category' ? (
                            <React.Fragment key={idx}>
                              <tr className="bg-gray-50 border-b border-gray-200 cursor-pointer hover:bg-orange-50" onClick={() => setDrilldown({ title: expense.name, accountNamePrefix: expense.name })}>
                                <td className="font-semibold text-gray-700 py-2 px-0">{expense.name}</td>
                                <td className="text-right text-gray-600 py-2 px-0"></td>
                              </tr>
                              {expense.items.map((item, itemIdx) => (
                                <tr key={`${idx}-${itemIdx}`} className="border-b border-gray-100 cursor-pointer hover:bg-blue-50" onClick={() => setDrilldown({ title: item.line_item || item.name, accountCode: item.code })}>
                                  <td className="text-gray-700 py-2 px-0 pl-6">{item.line_item || item.name}</td>
                                  <td className="text-right font-mono text-gray-700 py-2 px-0">${item.amount.toFixed(2)}</td>
                                </tr>
                              ))}
                              <tr className="bg-gray-100 border-b border-gray-300 font-semibold">
                                <td className="text-gray-800 py-2 px-0">Total for {expense.name}</td>
                                <td className="text-right font-mono text-gray-800 py-2 px-0">${expense.subtotal.toFixed(2)}</td>
                              </tr>
                            </React.Fragment>
                          ) : (
                            <tr key={idx} className="border-b border-gray-100 cursor-pointer hover:bg-blue-50" onClick={() => setDrilldown({ title: expense.name, accountCode: expense.code })}>
                              <td className="text-gray-900 py-2 px-0">{expense.name}</td>
                              <td className="text-right font-mono text-gray-700 py-2 px-0">${expense.amount.toFixed(2)}</td>
                            </tr>
                          )
                        )}
                      </tbody>
                    </table>
                  ) : (
                    <p className="text-gray-500 italic py-4">No expenses recorded for this period.</p>
                  )}

                  <div className="bg-gray-50 p-4 rounded my-6">
                    <div className="flex justify-between items-center">
                      <p className="text-sm text-gray-600">Total Expenses</p>
                      <p className="text-2xl font-bold text-gray-900">
                        ${(plData?.total_expenses || 0).toFixed(2)}
                      </p>
                    </div>
                  </div>

                  <div className={`p-6 rounded text-white text-center ${plData?.net_income >= 0 ? 'bg-green-600' : 'bg-red-600'}`}>
                    <p className="text-sm opacity-90 mb-2">NET INCOME</p>
                    <p className="text-4xl font-bold">
                      ${Math.abs(plData?.net_income || 0).toFixed(2)}
                    </p>
                    {plData?.net_income < 0 && <p className="text-sm opacity-90 mt-1">(Loss)</p>}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : selectedReport === 'balance-sheet' ? (
        <div>
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button size="sm" variant="ghost" onClick={closeDetail}>
                ← Back
              </Button>
              <label className="text-sm font-medium">As of:</label>
              <Input
                type="date"
                value={balanceSheetDate}
                onChange={(e) => setBalanceSheetDate(e.target.value)}
                className="w-40"
              />
            </div>
            <Button
              onClick={() => {
                const params = new URLSearchParams({ as_of: balanceSheetDate });
                window.open(`/api/reports/balance-sheet/pdf?${params.toString()}`, '_blank');
              }}
              disabled={balanceSheetLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              📥 Download PDF
            </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Balance Sheet</CardTitle>
            </CardHeader>
            <CardContent>
              {balanceSheetLoading ? (
                <p>Loading...</p>
              ) : (
                <div>
                  <h3 className="text-lg font-semibold mb-4 text-gray-900">Assets</h3>
                  {balanceSheetData?.assets && balanceSheetData.assets.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Code</TableHead>
                          <TableHead>Account</TableHead>
                          <TableHead className="text-right">Balance</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {balanceSheetData.assets.map((item, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-mono text-sm">{item.code}</TableCell>
                            <TableCell>{item.name}</TableCell>
                            <TableCell className="text-right font-mono">${item.balance.toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-gray-500 italic py-4">No asset accounts recorded.</p>
                  )}

                  <div className="bg-blue-50 p-4 rounded my-6">
                    <div className="flex justify-between items-center">
                      <p className="text-sm text-gray-600">Total Assets</p>
                      <p className="text-3xl font-bold text-blue-600">
                        ${(balanceSheetData?.total_assets || 0).toFixed(2)}
                      </p>
                    </div>
                  </div>

                  <h3 className="text-lg font-semibold mb-4 text-gray-900">Liabilities</h3>
                  {balanceSheetData?.liabilities && balanceSheetData.liabilities.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Code</TableHead>
                          <TableHead>Account</TableHead>
                          <TableHead className="text-right">Balance</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {balanceSheetData.liabilities.map((item, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-mono text-sm">{item.code}</TableCell>
                            <TableCell>{item.name}</TableCell>
                            <TableCell className="text-right font-mono">${item.balance.toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-gray-500 italic py-4">No liability accounts recorded.</p>
                  )}

                  <h3 className="text-lg font-semibold mb-4 text-gray-900">Equity</h3>
                  {balanceSheetData?.equity && balanceSheetData.equity.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Code</TableHead>
                          <TableHead>Account</TableHead>
                          <TableHead className="text-right">Balance</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {balanceSheetData.equity.map((item, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-mono text-sm">{item.code}</TableCell>
                            <TableCell>{item.name}</TableCell>
                            <TableCell className="text-right font-mono">${item.balance.toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-gray-500 italic py-4">No equity accounts recorded.</p>
                  )}

                  <div className="bg-gray-50 p-4 rounded my-6">
                    <div className="flex justify-between items-center">
                      <p className="text-sm text-gray-600">Total Liabilities & Equity</p>
                      <p className="text-2xl font-bold text-gray-900">
                        ${(balanceSheetData?.total_liabilities_and_equity || 0).toFixed(2)}
                      </p>
                    </div>
                  </div>

                  <div className={`p-6 rounded text-white text-center ${balanceSheetData?.balanced ? 'bg-green-600' : 'bg-red-600'}`}>
                    <p className="text-sm opacity-90 mb-2">BALANCE CHECK</p>
                    <p className="text-lg font-bold mb-2">
                      Assets: ${(balanceSheetData?.total_assets || 0).toFixed(2)} = Liabilities + Equity: ${(balanceSheetData?.total_liabilities_and_equity || 0).toFixed(2)}
                    </p>
                    <p className="text-sm opacity-90">
                      {balanceSheetData?.balanced ? '✓ Balance Sheet is Balanced' : '✗ Balance Sheet is NOT Balanced'}
                    </p>
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
