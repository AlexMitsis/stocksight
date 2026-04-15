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
import { toNumber } from '@/utils/number';

type TabType = 'holdings' | 'transactions';

export const PortfolioPage = () => {
  const { user, logout } = useAuth();
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto p-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Portfolio</h1>
            <p className="text-muted-foreground mt-1">Manage your stock holdings and track performance</p>
          </div>
          <div className="flex gap-2">
            <Link to="/portfolio/dashboard">
              <Button variant="default">View Dashboard</Button>
            </Link>
            <Link to="/dashboard">
              <Button variant="outline">Home</Button>
            </Link>
            <Link to="/profile">
              <Button variant="outline">Profile</Button>
            </Link>
            <Button onClick={logout} variant="outline">
              Sign out
            </Button>
          </div>
        </div>

        {/* Portfolio Summary */}
        <div className="grid gap-6 md:grid-cols-4 mb-6">
          <Card>
            <CardHeader>
              <CardDescription>Total Value</CardDescription>
              <CardTitle className="text-2xl">
                {user?.preferred_currency === 'EUR' && '€'}
                {user?.preferred_currency === 'GBP' && '£'}
                {user?.preferred_currency === 'USD' && '$'}
                {user?.preferred_currency === 'CHF' && 'CHF '}
                {totalValue.toFixed(2)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Total Cost</CardDescription>
              <CardTitle className="text-2xl">
                {user?.preferred_currency === 'EUR' && '€'}
                {user?.preferred_currency === 'GBP' && '£'}
                {user?.preferred_currency === 'USD' && '$'}
                {user?.preferred_currency === 'CHF' && 'CHF '}
                {totalCostBasis.toFixed(2)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Total Gain/Loss</CardDescription>
              <CardTitle className={`text-2xl ${totalGain >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {totalGain >= 0 ? '+' : ''}
                {user?.preferred_currency === 'EUR' && '€'}
                {user?.preferred_currency === 'GBP' && '£'}
                {user?.preferred_currency === 'USD' && '$'}
                {user?.preferred_currency === 'CHF' && 'CHF '}
                {totalGain.toFixed(2)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Return</CardDescription>
              <CardTitle className={`text-2xl ${totalGainPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {totalGainPct >= 0 ? '+' : ''}
                {totalGainPct.toFixed(2)}%
              </CardTitle>
            </CardHeader>
          </Card>
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
                <p className="text-center text-muted-foreground py-8">Loading holdings...</p>
              ) : holdings.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground mb-4">No holdings yet</p>
                  <p className="text-sm text-muted-foreground mb-4">
                    Add positions using the Transactions tab or import from CSV.
                  </p>
                  <div className="flex gap-2 justify-center">
                    <CSVImportButton onSuccess={handleImportSuccess} />
                    <Button onClick={() => setActiveTab('transactions')}>
                      Add Transaction
                    </Button>
                  </div>
                </div>
              ) : (
                <HoldingsTable
                  holdings={holdings}
                  currency={user?.preferred_currency || 'USD'}
                />
              )}
            </CardContent>
          </Card>
        )}

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <TransactionHistory
            currency={user?.preferred_currency || 'USD'}
            onTransactionChange={fetchHoldings}
          />
        )}
      </div>
    </div>
  );
};
