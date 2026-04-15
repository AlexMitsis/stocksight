import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface GainLossData {
  ticker: string;
  quantity: number;
  purchase_price: number;
  current_price: number;
  gain_loss: number;
  gain_loss_pct: number;
  current_value: number;
  cost_basis: number;
  currency: string;
}

interface GainsLossesChartProps {
  data: GainLossData[];
  currency?: string;
}

const GainsLossesChart: React.FC<GainsLossesChartProps> = ({ data, currency = 'USD' }) => {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Gains & Losses</CardTitle>
          <CardDescription>Unrealized gains and losses by holding</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64 text-muted-foreground">
            No holdings to display
          </div>
        </CardContent>
      </Card>
    );
  }

  // Format data for chart
  const chartData = data.map((item) => ({
    ticker: item.ticker,
    gainLoss: item.gain_loss,
    percentage: item.gain_loss_pct,
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const tickerData = payload[0].payload;
      const isGain = tickerData.gainLoss >= 0;
      const originalData = data.find((d: GainLossData) => d.ticker === tickerData.ticker);

      return (
        <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
          <p className="font-semibold mb-2">{tickerData.ticker}</p>
          {originalData && (
            <>
              <div className="space-y-1 mb-2 pb-2 border-b border-border">
                <p className="text-sm">
                  <span className="text-muted-foreground">Quantity: </span>
                  <span className="font-medium">{originalData.quantity.toFixed(2)}</span>
                </p>
                <p className="text-sm">
                  <span className="text-muted-foreground">Purchase Price: </span>
                  <span className="font-medium">
                    {getCurrencySymbol(currency)}
                    {originalData.purchase_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </p>
                <p className="text-sm">
                  <span className="text-muted-foreground">Current Price: </span>
                  <span className="font-medium">
                    {getCurrencySymbol(currency)}
                    {originalData.current_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </p>
              </div>
              <p className="text-sm">
                <span className="text-muted-foreground">Current Value: </span>
                <span className="font-medium">
                  {getCurrencySymbol(currency)}
                  {originalData.current_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </p>
              <p className="text-sm">
                <span className="text-muted-foreground">Cost Basis: </span>
                <span className="font-medium">
                  {getCurrencySymbol(currency)}
                  {originalData.cost_basis.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </p>
            </>
          )}
          <p className="text-sm mt-2 pt-2 border-t border-border">
            <span className="text-muted-foreground">Gain/Loss: </span>
            <span className={`font-medium ${isGain ? 'text-green-600 dark:text-green-500' : 'text-red-600 dark:text-red-500'}`}>
              {isGain ? '+' : ''}
              {getCurrencySymbol(currency)}
              {Math.abs(tickerData.gainLoss).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </p>
          <p className="text-sm">
            <span className="text-muted-foreground">Return: </span>
            <span className={`font-medium ${isGain ? 'text-green-600 dark:text-green-500' : 'text-red-600 dark:text-red-500'}`}>
              {isGain ? '+' : ''}{tickerData.percentage.toFixed(2)}%
            </span>
          </p>
        </div>
      );
    }
    return null;
  };

  // Custom bar color based on gain/loss
  const getBarColor = (value: number) => {
    return value >= 0 ? 'hsl(var(--chart-gain))' : 'hsl(var(--chart-loss))';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Gains & Losses</CardTitle>
        <CardDescription>Unrealized gains and losses by holding</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="ticker"
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <YAxis
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
              tickFormatter={(value) => {
                const absValue = Math.abs(value);
                if (absValue >= 1000) {
                  return `${getCurrencySymbol(currency)}${(value / 1000).toFixed(0)}k`;
                }
                return `${getCurrencySymbol(currency)}${value}`;
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="gainLoss" name="Gain/Loss" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.gainLoss)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

// Helper function to get currency symbol
function getCurrencySymbol(currency: string): string {
  const symbols: Record<string, string> = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    CHF: 'CHF ',
  };
  return symbols[currency] || currency;
}

export default GainsLossesChart;
