import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AnimatedNumber } from '@/components/ui/animated-number';
import { formatCurrency } from '@/utils/number';

interface PortfolioSummary {
  total_value: number;
  total_cost_basis: number;
  total_gain_loss: number;
  total_return_pct: number;
  holdings_count: number;
  currency: string;
}

interface PerformanceMetricsProps {
  summary: PortfolioSummary | null;
  isLoading?: boolean;
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ summary, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                <div className="h-4 w-24 bg-muted animate-pulse rounded" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-8 w-32 bg-muted animate-pulse rounded mb-2" />
              <div className="h-3 w-20 bg-muted animate-pulse rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-muted-foreground">No portfolio data available</div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currency = summary.currency;
  const isGain = summary.total_gain_loss >= 0;
  const gainLossColor = isGain ? 'text-green-600 dark:text-green-500' : 'text-red-600 dark:text-red-500';

  const metrics = [
    {
      title: 'Total Value',
      value: summary.total_value,
      description: `${summary.holdings_count} holding${summary.holdings_count !== 1 ? 's' : ''}`,
    },
    {
      title: 'Cost Basis',
      value: summary.total_cost_basis,
      description: 'Total invested',
    },
    {
      title: 'Unrealized Gain/Loss',
      value: summary.total_gain_loss,
      showSign: true,
      description: `${isGain ? '+' : ''}${summary.total_return_pct.toFixed(2)}%`,
      valueColor: gainLossColor,
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {metrics.map((metric, index) => (
        <Card key={index}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${metric.valueColor || ''}`}>
              <AnimatedNumber value={metric.value} format={(v) => formatCurrency(v, currency, metric.showSign)} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">{metric.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default PerformanceMetrics;
