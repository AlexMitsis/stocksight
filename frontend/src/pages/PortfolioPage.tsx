import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { HoldingsTable } from '@/components/portfolio/HoldingsTable';
import { CSVImportButton } from '@/components/portfolio/CSVImportButton';
import { TransactionHistory } from '@/components/portfolio/TransactionHistory';
import { api } from '@/services/api';
import type { Holding } from '@/types/portfolio';
import { toNumber, formatCurrency } from '@/utils/number';
import { AnimatedNumber } from '@/components/ui/animated-number';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { Briefcase } from 'lucide-react';

type TabType = 'holdings' | 'transactions';

export const PortfolioPage = () => {
  const { user } = useAuth();
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('holdings');

  // Fetch holdings on mount
  useEffect(() => {
    fetchHoldings();
  }, []);

  const fetchHoldings = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/portfolio/holdings');
      setHoldings(response.data);
    } catch (error: any) {
      console.error('Failed to fetch holdings:', error);
      toast.error(error.response?.data?.detail || 'Failed to fetch holdings');
    } finally {
      setLoading(false);
    }
  };

  const handleImportSuccess = () => {
    fetchHoldings();
    toast.success('Holdings imported successfully');
  };

  // Calculate portfolio summary (convert strings to numbers)
  const totalValue = holdings.reduce((sum, h) => sum + (toNumber(h.current_value) || toNumber(h.cost_basis)), 0);
  const totalCostBasis = holdings.reduce((sum, h) => sum + toNumber(h.cost_basis), 0);
  const totalGain = totalValue - totalCostBasis;
  const totalGainPct = totalCostBasis > 0 ? (totalGain / totalCostBasis) * 100 : 0;

  const currency = user?.preferred_currency || 'USD';
  const gainColor = (v: number) => (v >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400');
  const summaryCards = [
    { label: 'Total Value', value: totalValue, format: (v: number) => formatCurrency(v, currency) },
    { label: 'Total Cost', value: totalCostBasis, format: (v: number) => formatCurrency(v, currency) },
    { label: 'Total Gain/Loss', value: totalGain, format: (v: number) => formatCurrency(v, currency, true), colored: true },
    { label: 'Return', value: totalGainPct, format: (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`, colored: true },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Portfolio</h1>
          <p className="text-muted-foreground mt-1">Manage your stock holdings and track performance</p>
        </div>
        <Link to="/portfolio/dashboard">
          <Button variant="default">View Dashboard</Button>
        </Link>
      </div>

      {/* Portfolio Summary */}
      <div className="grid gap-6 md:grid-cols-4 mb-6">
        {summaryCards.map((card) => (
          <Card key={card.label}>
            <CardHeader>
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className={`text-2xl ${card.colored ? gainColor(card.value) : ''}`}>
                <AnimatedNumber value={card.value} format={card.format} />
              </CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-4">
        <Button
          variant={activeTab === 'holdings' ? 'default' : 'outline'}
          onClick={() => setActiveTab('holdings')}
        >
          Holdings
        </Button>
        <Button
          variant={activeTab === 'transactions' ? 'default' : 'outline'}
          onClick={() => setActiveTab('transactions')}
        >
          Transactions
        </Button>
      </div>

      {/* Holdings Tab */}
      {activeTab === 'holdings' && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle>Holdings</CardTitle>
                <CardDescription>
                  {holdings.length} {holdings.length === 1 ? 'holding' : 'holdings'} — Holdings are managed through transactions
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <CSVImportButton onSuccess={handleImportSuccess} />
                <Button onClick={() => setActiveTab('transactions')}>
                  Add Position
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : holdings.length === 0 ? (
              <EmptyState
                icon={Briefcase}
                title="No holdings yet"
                description="Add positions using the Transactions tab or import from CSV."
              >
                <CSVImportButton onSuccess={handleImportSuccess} />
                <Button onClick={() => setActiveTab('transactions')}>Add Transaction</Button>
              </EmptyState>
            ) : (
              <HoldingsTable holdings={holdings} currency={currency} />
            )}
          </CardContent>
        </Card>
      )}

      {/* Transactions Tab */}
      {activeTab === 'transactions' && (
        <TransactionHistory
          currency={currency}
          onTransactionChange={fetchHoldings}
        />
      )}
    </div>
  );
};
