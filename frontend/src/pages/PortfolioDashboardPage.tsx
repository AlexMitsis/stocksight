import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/services/api';
import PortfolioValueChart from '@/components/portfolio/PortfolioValueChart';
import AllocationPieChart from '@/components/portfolio/AllocationPieChart';
import GainsLossesChart from '@/components/portfolio/GainsLossesChart';
import PerformanceMetrics from '@/components/portfolio/PerformanceMetrics';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface PortfolioSummary {
  total_value: number;
  total_cost_basis: number;
  total_gain_loss: number;
  total_return_pct: number;
  holdings_count: number;
  holdings: any[];
  currency: string;
}

interface AllocationData {
  ticker: string;
  value: number;
  percentage: number;
  currency: string;
}

interface GainLossData {
  ticker: string;
  gain_loss: number;
  gain_loss_pct: number;
  current_value: number;
  cost_basis: number;
  currency: string;
}

interface HistoricalDataPoint {
  date: string;
  value: number;
  cost_basis: number;
  currency: string;
}

const PortfolioDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [allocation, setAllocation] = useState<AllocationData[]>([]);
  const [gainsLosses, setGainsLosses] = useState<GainLossData[]>([]);
  const [historicalValue, setHistoricalValue] = useState<HistoricalDataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const currency = user?.preferred_currency || 'USD';

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch all data in parallel
      const [summaryRes, allocationRes, gainsLossesRes, historicalRes] = await Promise.all([
        api.get(`/api/portfolio/summary?currency=${currency}`),
        api.get(`/api/portfolio/allocation?currency=${currency}`),
        api.get(`/api/portfolio/gains-losses?currency=${currency}`),
        api.get(`/api/portfolio/historical-value?currency=${currency}`),
      ]);

      setSummary(summaryRes.data);
      setAllocation(allocationRes.data);
      setGainsLosses(gainsLossesRes.data);
      setHistoricalValue(historicalRes.data);
    } catch (err: any) {
      console.error('Error fetching dashboard data:', err);
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [currency]);

  if (isLoading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold">Portfolio Dashboard</h1>
        </div>
        <PerformanceMetrics summary={null} isLoading={true} />
        <div className="grid gap-6 mt-6 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-6 w-48 bg-muted animate-pulse rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-64 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Card>
          <CardHeader>
            <CardTitle>Error Loading Dashboard</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={fetchDashboardData}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/portfolio')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Portfolio Dashboard</h1>
            <p className="text-muted-foreground">
              Real-time performance metrics and analytics
            </p>
          </div>
        </div>
      </div>

      {/* Performance Metrics Cards */}
      <PerformanceMetrics summary={summary} />

      {/* Charts Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Portfolio Value Over Time */}
        <div className="md:col-span-2">
          <PortfolioValueChart data={historicalValue} currency={currency} />
        </div>

        {/* Allocation Pie Chart */}
        <AllocationPieChart data={allocation} currency={currency} />

        {/* Gains & Losses Bar Chart */}
        <GainsLossesChart data={gainsLosses} currency={currency} />
      </div>

      {/* Additional Info Card */}
      {summary && summary.holdings_count === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Get Started</CardTitle>
            <CardDescription>Add holdings to see your portfolio dashboard</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              You haven't added any holdings yet. Add your first holding or import a CSV file to get started.
            </p>
            <Button onClick={() => navigate('/portfolio')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Go to Portfolio
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Historical Data Info */}
      {summary && summary.holdings_count > 0 && historicalValue.length === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Track Your Performance Over Time</CardTitle>
            <CardDescription>Create daily snapshots to see historical charts</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              Currently showing today's portfolio value only. Create daily snapshots to track your portfolio's performance over time and see trend lines.
            </p>
            <p className="text-sm text-muted-foreground">
              Tip: Set up a daily schedule to automatically create snapshots and track your portfolio's growth.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PortfolioDashboardPage;
