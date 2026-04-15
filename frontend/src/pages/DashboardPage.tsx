import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/services/api';

interface PortfolioSummary {
  total_value: number;
  total_cost_basis: number;
  total_gain_loss: number;
  total_return_pct: number;
  holdings_count: number;
  currency: string;
}

export const DashboardPage = () => {
  const { user, logout } = useAuth();
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPortfolioSummary = async () => {
      try {
        setPortfolioLoading(true);
        const currency = user?.preferred_currency || 'USD';
        const response = await api.get(`/api/portfolio/summary?currency=${currency}`);
        setPortfolioSummary(response.data);
        setPortfolioError(null);
      } catch (error) {
        console.error('Failed to fetch portfolio summary:', error);
        setPortfolioError('Unable to load portfolio');
      } finally {
        setPortfolioLoading(false);
      }
    };

    if (user) {
      fetchPortfolioSummary();
    }
  }, [user]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-950 dark:via-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-6 py-12 max-w-6xl">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-12">
          <div>
            <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400 bg-clip-text text-transparent">
              Welcome back
            </h1>
            <p className="text-muted-foreground mt-1">{user?.email}</p>
          </div>
          <div className="flex gap-3">
            <Link to="/profile">
              <Button variant="outline" className="shadow-sm">Profile</Button>
            </Link>
            <Button onClick={logout} variant="outline" className="shadow-sm">
              Sign out
            </Button>
          </div>
        </div>

        {/* Cards Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Account Card */}
          <Card className="shadow-lg hover:shadow-xl transition-shadow duration-300 border-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-xl">Your Account</CardTitle>
              <CardDescription>Account details and preferences</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-800">
                  <span className="text-sm text-muted-foreground">Country</span>
                  <span className="text-sm font-medium">{user?.country || 'Not set'}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-800">
                  <span className="text-sm text-muted-foreground">Currency</span>
                  <span className="text-sm font-medium">{user?.preferred_currency}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-muted-foreground">Member since</span>
                  <span className="text-sm font-medium">
                    {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Chat Card */}
          <Card className="shadow-lg hover:shadow-xl transition-shadow duration-300 border-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-xl">Stock Analysis</CardTitle>
              <CardDescription>Chat with AI-powered assistant</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Get real-time stock analysis, company information, and market insights.
              </p>
              <Link to="/chat" className="block">
                <Button className="w-full shadow-md hover:shadow-lg transition-shadow">
                  <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  Start Chat
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Portfolio Card - Enhanced with Summary */}
          <Card className="shadow-lg hover:shadow-xl transition-shadow duration-300 border-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-xl flex items-center gap-2">
                <svg className="h-5 w-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                Portfolio Dashboard
              </CardTitle>
              <CardDescription>Your investment performance</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {portfolioLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-6 w-1/2" />
                </div>
              ) : portfolioError ? (
                <p className="text-sm text-muted-foreground">{portfolioError}</p>
              ) : portfolioSummary && portfolioSummary.holdings_count > 0 ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-800">
                    <span className="text-sm text-muted-foreground">Total Value</span>
                    <span className="text-lg font-semibold">
                      {new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: portfolioSummary.currency
                      }).format(portfolioSummary.total_value)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-800">
                    <span className="text-sm text-muted-foreground">Total Gain/Loss</span>
                    <span className={`text-lg font-semibold ${
                      portfolioSummary.total_gain_loss >= 0
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      {portfolioSummary.total_gain_loss >= 0 ? '+' : ''}
                      {new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: portfolioSummary.currency
                      }).format(portfolioSummary.total_gain_loss)}
                      <span className="text-sm font-medium ml-1">
                        ({portfolioSummary.total_return_pct >= 0 ? '+' : ''}{portfolioSummary.total_return_pct.toFixed(2)}%)
                      </span>
                    </span>
                  </div>
                  <div className="pt-1 text-center">
                    <p className="text-xs text-muted-foreground">
                      {portfolioSummary.holdings_count} holding{portfolioSummary.holdings_count !== 1 ? 's' : ''} tracked
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No holdings yet. Add your first stock to get started.
                </p>
              )}
              <Link to="/portfolio/dashboard" className="block">
                <Button className="w-full shadow-md hover:shadow-lg transition-shadow">
                  <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  {portfolioSummary && portfolioSummary.holdings_count > 0 ? 'View Dashboard' : 'Get Started'}
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
