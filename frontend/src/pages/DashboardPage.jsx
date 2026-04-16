import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader } from '../components/ui/Card';

function formatCurrency(value) {
  const num = parseFloat(value) || 0;
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function Badge({ text, variant = 'default' }) {
  const variants = {
    default: 'bg-gray-100 text-gray-800',
    red: 'bg-red-100 text-red-800',
    amber: 'bg-amber-100 text-amber-800',
    blue: 'bg-blue-100 text-blue-800',
  };

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold ${variants[variant]}`}>
      {text}
    </span>
  );
}

function DaysOverdueBadge({ daysOverdue }) {
  let bgColor = 'bg-red-100 text-red-700';
  if (daysOverdue < 10) {
    bgColor = 'bg-yellow-100 text-yellow-700';
  } else if (daysOverdue < 30) {
    bgColor = 'bg-amber-100 text-amber-700';
  }

  return (
    <span className={`text-xs font-semibold px-2 py-1 rounded ${bgColor}`}>
      {daysOverdue}d
    </span>
  );
}

function InvoiceChip({ invoice, onClick }) {
  return (
    <div
      onClick={onClick}
      className="flex-shrink-0 w-40 bg-white border border-gray-200 rounded-md p-3 hover:shadow-md hover:border-gray-300 cursor-pointer transition-all"
    >
      <p className="text-sm font-medium text-gray-900 truncate">{invoice.client}</p>
      <p className="text-xs text-gray-500">Invoice {invoice.invoice_number}</p>
      <div className="flex justify-between items-center mt-2">
        <p className="text-sm font-bold text-red-600">${formatCurrency(invoice.balance)}</p>
        <DaysOverdueBadge daysOverdue={invoice.days_overdue} />
      </div>
    </div>
  );
}

function ClientChip({ client, amount, onClick, amountColor = 'text-gray-900' }) {
  return (
    <div
      onClick={onClick}
      className="flex-shrink-0 w-40 bg-white border border-gray-200 rounded-md p-3 hover:shadow-md hover:border-gray-300 cursor-pointer transition-all"
    >
      <p className="text-sm font-medium text-gray-900 truncate">{client.name}</p>
      <p className="text-xs text-gray-500">{client.subtitle}</p>
      {amount && <p className={`text-sm font-bold mt-2 ${amountColor}`}>${formatCurrency(amount)}</p>}
    </div>
  );
}

function SkeletonChip() {
  return (
    <div className="flex-shrink-0 w-40 bg-gray-100 rounded-md p-3 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-24 mb-2" />
      <div className="h-3 bg-gray-200 rounded w-32" />
    </div>
  );
}

function HorizontalScrollBar({ title, badge, metric, metricColor, subtitle, linkText, linkOnClick, children, isEmpty, isLoading }) {
  return (
    <Card className="mb-6">
      <CardContent className="p-0">
        <div className="flex">
          {/* Left Section */}
          <div className="w-72 flex-shrink-0 px-6 py-6 border-r border-gray-200">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              {badge && <Badge text={badge.text} variant={badge.variant} />}
            </div>
            {metric && (
              <>
                <p className={`text-3xl font-bold ${metricColor}`}>{metric}</p>
                <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
              </>
            )}
            <button
              onClick={linkOnClick}
              className="text-xs text-blue-600 font-medium hover:text-blue-800 mt-4 transition-colors"
            >
              {linkText}
            </button>
          </div>

          {/* Right Section - Scrollable */}
          <div className="flex-1 overflow-hidden relative">
            {isEmpty ? (
              <div className="flex items-center justify-center h-24 text-gray-400 text-sm">
                All clear
              </div>
            ) : isLoading ? (
              <div className="flex gap-3 px-6 py-6 overflow-x-auto">
                {[...Array(4)].map((_, i) => (
                  <SkeletonChip key={i} />
                ))}
              </div>
            ) : (
              <>
                <div className="flex gap-3 px-6 py-6 overflow-x-auto scrollbar-hide" style={{ scrollBehavior: 'smooth' }}>
                  {children}
                </div>
                {/* Right fade gradient */}
                <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white to-transparent pointer-events-none" />
              </>
            )}
          </div>
        </div>
      </CardContent>

      <style>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </Card>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const { data: recurringRevenue, isLoading: revenueLoading } = useQuery({
    queryKey: ['reports', 'recurring-revenue'],
    queryFn: async () => {
      const response = await apiClient.get('/reports/recurring-revenue');
      return response.data;
    },
  });

  const { data: dueBilling, isLoading: dueLoading } = useQuery({
    queryKey: ['invoices', 'due-for-billing'],
    queryFn: async () => {
      const response = await apiClient.get('/invoices/due-for-billing', {
        params: { days_ahead: 7 },
      });
      return response.data;
    },
  });

  const { data: dailyQueue, isLoading: queueLoading } = useQuery({
    queryKey: ['collections', 'daily-queue'],
    queryFn: async () => {
      const response = await apiClient.get('/collections/daily-queue');
      return response.data || {
        late_fee_candidates: [],
        suspension_candidates: [],
        deletion_candidates: [],
      };
    },
  });

  const isLoading = revenueLoading || dueLoading || queueLoading;

  // Extract invoice buckets from daily queue
  const invoicedAndDue = dailyQueue?.invoiced_and_due || [];
  const invoicedAndDueCount = invoicedAndDue.length;
  const invoicedAndDueAmount = invoicedAndDue.reduce((sum, inv) => sum + parseFloat(inv.balance_due || 0), 0);

  const pastDue = dailyQueue?.past_due || [];
  const pastDueCount = pastDue.length;
  const pastDueAmount = pastDue.reduce((sum, inv) => sum + parseFloat(inv.balance_due || 0), 0);

  const suspensionCandidates = dailyQueue?.suspension_candidates || [];
  const suspensionCount = suspensionCandidates.length;
  const suspensionAmount = suspensionCandidates.reduce((sum, inv) => sum + parseFloat(inv.balance_due || 0), 0);

  const terminationCandidates = dailyQueue?.termination_candidates || [];
  const terminationCount = terminationCandidates.length;
  const terminationAmount = terminationCandidates.reduce((sum, inv) => sum + parseFloat(inv.balance_due || 0), 0);

  // Due for billing
  const dueBillingList = dueBilling || [];
  const dueBillingCount = dueBillingList.length;

  return (
    <Layout title="Dashboard">
      {/* Bar 1: Invoiced and Due */}
      <HorizontalScrollBar
        title="Invoiced and due"
        badge={{ text: `${invoicedAndDueCount} invoices`, variant: 'blue' }}
        metric={`$${formatCurrency(invoicedAndDueAmount)}`}
        metricColor="text-blue-600"
        subtitle="due today"
        linkText="View all →"
        linkOnClick={() => navigate('/invoices')}
        isEmpty={invoicedAndDueCount === 0}
        isLoading={queueLoading}
      >
        {invoicedAndDue.map((invoice, idx) => (
          <InvoiceChip
            key={idx}
            invoice={{
              client: invoice.client_name,
              invoice_number: invoice.invoice_number,
              balance: invoice.balance_due,
              days_overdue: invoice.days_overdue,
            }}
            onClick={() => navigate(`/invoices`)}
          />
        ))}
      </HorizontalScrollBar>

      {/* Bar 2: Past Due */}
      <HorizontalScrollBar
        title="Past due"
        badge={{ text: `${pastDueCount} invoices`, variant: 'red' }}
        metric={`$${formatCurrency(pastDueAmount)}`}
        metricColor="text-red-600"
        subtitle="1–19 days overdue"
        linkText="View all →"
        linkOnClick={() => navigate('/invoices')}
        isEmpty={pastDueCount === 0}
        isLoading={queueLoading}
      >
        {pastDue.map((invoice, idx) => (
          <InvoiceChip
            key={idx}
            invoice={{
              client: invoice.client_name,
              invoice_number: invoice.invoice_number,
              balance: invoice.balance_due,
              days_overdue: invoice.days_overdue,
            }}
            onClick={() => navigate(`/invoices`)}
          />
        ))}
      </HorizontalScrollBar>

      {/* Bar 3: Suspension Candidates */}
      <HorizontalScrollBar
        title="Suspension candidates"
        badge={{ text: `${suspensionCount} invoices`, variant: 'amber' }}
        metric={`$${formatCurrency(suspensionAmount)}`}
        metricColor="text-amber-600"
        subtitle="20+ days overdue"
        linkText="View all →"
        linkOnClick={() => navigate('/invoices')}
        isEmpty={suspensionCount === 0}
        isLoading={queueLoading}
      >
        {suspensionCandidates.map((invoice, idx) => (
          <InvoiceChip
            key={idx}
            invoice={{
              client: invoice.client_name,
              invoice_number: invoice.invoice_number,
              balance: invoice.balance_due,
              days_overdue: invoice.days_overdue,
            }}
            onClick={() => navigate(`/invoices`)}
          />
        ))}
      </HorizontalScrollBar>

      {/* Bar 4: Termination Candidates */}
      <HorizontalScrollBar
        title="Termination candidates"
        badge={{ text: `${terminationCount} invoices`, variant: 'red' }}
        metric={`$${formatCurrency(terminationAmount)}`}
        metricColor="text-red-700"
        subtitle="due in prior month"
        linkText="View all →"
        linkOnClick={() => navigate('/invoices')}
        isEmpty={terminationCount === 0}
        isLoading={queueLoading}
      >
        {terminationCandidates.map((invoice, idx) => (
          <InvoiceChip
            key={idx}
            invoice={{
              client: invoice.client_name,
              invoice_number: invoice.invoice_number,
              balance: invoice.balance_due,
              days_overdue: invoice.days_overdue,
            }}
            onClick={() => navigate(`/invoices`)}
          />
        ))}
      </HorizontalScrollBar>

      {/* Bar 5: Due for Billing */}
      <HorizontalScrollBar
        title="Due for billing"
        badge={{ text: 'next 7 days', variant: 'blue' }}
        metric={dueBillingCount}
        metricColor="text-blue-600"
        subtitle="clients due soon"
        linkText="View all →"
        linkOnClick={() => navigate('/invoices?filter=due-billing')}
        isEmpty={dueBillingCount === 0}
        isLoading={dueLoading}
      >
        {dueBillingList.map((item, idx) => (
          <ClientChip
            key={idx}
            client={{
              name: item.client.company_name,
              subtitle: item.client.autocc_recurring ? 'Auto-charge' : 'Fixed recurring',
            }}
            amount={item.schedules && item.schedules.length > 0 ? item.schedules[0].amount : 0}
            onClick={() => navigate(`/clients/${item.client.id}`)}
          />
        ))}
      </HorizontalScrollBar>
    </Layout>
  );
}
