import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/services/api';
import type { Transaction } from '@/types/portfolio';
import { toNumber, formatCurrency, formatQuantity } from '@/utils/number';
import { AddTransactionForm } from './AddTransactionForm';
import { toast } from 'sonner';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Loader2, Plus, Trash2, Filter, Pencil, Receipt } from 'lucide-react';

interface TransactionHistoryProps {
  currency?: string;
  onTransactionChange?: () => void;
}

export const TransactionHistory = ({
  currency = 'USD',
  onTransactionChange,
}: TransactionHistoryProps) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Filters
  const [filterType, setFilterType] = useState<string>('ALL');
  const [filterTicker, setFilterTicker] = useState<string>('');
  const [filterStartDate, setFilterStartDate] = useState<string>('');
  const [filterEndDate, setFilterEndDate] = useState<string>('');

  // Sorting
  const [sortColumn, setSortColumn] = useState<keyof Transaction>('transaction_date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Fetch transactions
  const fetchTransactions = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();

      if (filterType !== 'ALL') {
        params.append('type', filterType);
      }
      if (filterTicker.trim()) {
        params.append('ticker', filterTicker.trim().toUpperCase());
      }
      if (filterStartDate) {
        params.append('start_date', filterStartDate);
      }
      if (filterEndDate) {
        params.append('end_date', filterEndDate);
      }

      const url = `/api/portfolio/transactions${params.toString() ? '?' + params.toString() : ''}`;
      const response = await api.get(url);

      // Handle both array and object response formats
      const txnData = Array.isArray(response.data)
        ? response.data
        : response.data.transactions || [];

      setTransactions(txnData);
    } catch (error: any) {
      console.error('Failed to fetch transactions:', error);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [filterType, filterTicker, filterStartDate, filterEndDate]);

  const handleAddSuccess = () => {
    setShowAddForm(false);
    setEditingTransaction(null);
    fetchTransactions();
    onTransactionChange?.();
  };

  const handleEdit = (transaction: Transaction) => {
    setEditingTransaction(transaction);
    setShowAddForm(true);
  };

  const handleDelete = async (id: number, ticker: string, type: string) => {
    if (!confirm(`Are you sure you want to delete this ${type} transaction for ${ticker}?`)) {
      return;
    }

    try {
      setDeletingId(id);
      await api.delete(`/api/portfolio/transactions/${id}`);
      toast.success(`Deleted ${type} transaction for ${ticker}`);
      fetchTransactions();
      onTransactionChange?.();
    } catch (error: any) {
      console.error('Failed to delete transaction:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete transaction');
    } finally {
      setDeletingId(null);
    }
  };

  const handleSort = (column: keyof Transaction) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const clearFilters = () => {
    setFilterType('ALL');
    setFilterTicker('');
    setFilterStartDate('');
    setFilterEndDate('');
  };

  const hasActiveFilters = filterType !== 'ALL' || filterTicker || filterStartDate || filterEndDate;

  // Sort transactions
  const sortedTransactions = [...transactions].sort((a, b) => {
    const aVal = a[sortColumn];
    const bVal = b[sortColumn];

    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    // Handle numeric columns
    if (['quantity', 'price', 'fees', 'total_amount'].includes(sortColumn)) {
      const aNum = toNumber(aVal as string | number);
      const bNum = toNumber(bVal as string | number);
      return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
    }

    // Handle date columns
    if (sortColumn === 'transaction_date' || sortColumn === 'created_at') {
      const aDate = new Date(aVal as string).getTime();
      const bDate = new Date(bVal as string).getTime();
      return sortDirection === 'asc' ? aDate - bDate : bDate - aDate;
    }

    // Handle string columns
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    return 0;
  });

  const SortIcon = ({ column }: { column: keyof Transaction }) => {
    if (sortColumn !== column) {
      return <span className="ml-1 text-gray-400">↕</span>;
    }
    return <span className="ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>;
  };

  const getTypeBadgeStyles = (type: string) => {
    switch (type) {
      case 'BUY':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'SELL':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      case 'DIVIDEND':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
      case 'TRANSFER_IN':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      case 'TRANSFER_OUT':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400';
      case 'ADJUSTMENT':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
    }
  };

  // Helper to format transaction type for display
  const formatTypeName = (type: string) => {
    switch (type) {
      case 'TRANSFER_IN': return 'Transfer In';
      case 'TRANSFER_OUT': return 'Transfer Out';
      default: return type;
    }
  };

  // Check if transaction adds value (inflow) or removes value (outflow)
  const isInflow = (type: string) => ['BUY', 'TRANSFER_IN', 'DIVIDEND'].includes(type);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <CardTitle>Transaction History</CardTitle>
              <CardDescription>
                {loading ? 'Loading...' : `${transactions.length} transaction${transactions.length !== 1 ? 's' : ''}`}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
                className={hasActiveFilters ? 'border-primary' : ''}
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
                {hasActiveFilters && <span className="ml-1 text-primary">*</span>}
              </Button>
              <Button size="sm" onClick={() => setShowAddForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Transaction
              </Button>
            </div>
          </div>
        </CardHeader>

        {/* Filters */}
        {showFilters && (
          <CardContent className="border-t pt-4 pb-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
              {/* Type Filter */}
              <div className="space-y-1">
                <label className="text-sm font-medium">Type</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                >
                  <option value="ALL">All Types</option>
                  <option value="BUY">Buy</option>
                  <option value="SELL">Sell</option>
                  <option value="DIVIDEND">Dividend</option>
                  <option value="TRANSFER_IN">Transfer In</option>
                  <option value="TRANSFER_OUT">Transfer Out</option>
                  <option value="ADJUSTMENT">Adjustment</option>
                </select>
              </div>

              {/* Ticker Filter */}
              <div className="space-y-1">
                <label className="text-sm font-medium">Ticker</label>
                <Input
                  placeholder="e.g., AAPL"
                  value={filterTicker}
                  onChange={(e) => setFilterTicker(e.target.value)}
                  className="uppercase"
                />
              </div>

              {/* Start Date */}
              <div className="space-y-1">
                <label className="text-sm font-medium">From Date</label>
                <Input
                  type="date"
                  value={filterStartDate}
                  onChange={(e) => setFilterStartDate(e.target.value)}
                />
              </div>

              {/* End Date */}
              <div className="space-y-1">
                <label className="text-sm font-medium">To Date</label>
                <Input
                  type="date"
                  value={filterEndDate}
                  onChange={(e) => setFilterEndDate(e.target.value)}
                />
              </div>

              {/* Clear Button */}
              <div className="flex items-end">
                <Button
                  variant="outline"
                  onClick={clearFilters}
                  disabled={!hasActiveFilters}
                  className="w-full"
                >
                  Clear Filters
                </Button>
              </div>
            </div>
          </CardContent>
        )}

        <CardContent className="pt-6">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : transactions.length === 0 ? (
            hasActiveFilters ? (
              <EmptyState
                icon={Filter}
                title="No matching transactions"
                description="No transactions match your filters."
              >
                <Button variant="outline" onClick={clearFilters}>Clear Filters</Button>
              </EmptyState>
            ) : (
              <EmptyState
                icon={Receipt}
                title="No transactions yet"
                description="Record a buy, sell, transfer or dividend to start tracking your portfolio."
              >
                <Button onClick={() => setShowAddForm(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Record Your First Transaction
                </Button>
              </EmptyState>
            )
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th
                      className="text-left p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => handleSort('transaction_date')}
                    >
                      Date <SortIcon column="transaction_date" />
                    </th>
                    <th
                      className="text-left p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => handleSort('type')}
                    >
                      Type <SortIcon column="type" />
                    </th>
                    <th
                      className="text-left p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => handleSort('ticker')}
                    >
                      Ticker <SortIcon column="ticker" />
                    </th>
                    <th
                      className="text-right p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => handleSort('quantity')}
                    >
                      Quantity <SortIcon column="quantity" />
                    </th>
                    <th
                      className="text-right p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => handleSort('price')}
                    >
                      Price <SortIcon column="price" />
                    </th>
                    <th
                      className="text-right p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => handleSort('fees')}
                    >
                      Fees <SortIcon column="fees" />
                    </th>
                    <th
                      className="text-right p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => handleSort('total_amount')}
                    >
                      Total <SortIcon column="total_amount" />
                    </th>
                    <th className="p-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {sortedTransactions.map((txn) => (
                    <tr
                      key={txn.id}
                      className="border-b hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <td className="p-3">
                        {new Date(txn.transaction_date).toLocaleDateString()}
                      </td>
                      <td className="p-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTypeBadgeStyles(
                            txn.type
                          )}`}
                        >
                          {formatTypeName(txn.type)}
                        </span>
                      </td>
                      <td className="p-3 font-semibold">{txn.ticker}</td>
                      <td className="p-3 text-right">
                        {txn.quantity !== null ? formatQuantity(txn.quantity) : '-'}
                      </td>
                      <td className="p-3 text-right">
                        {formatCurrency(txn.price, currency)}
                      </td>
                      <td className="p-3 text-right">
                        {toNumber(txn.fees) > 0
                          ? formatCurrency(txn.fees, currency)
                          : '-'}
                      </td>
                      <td className="p-3 text-right font-medium">
                        <span className={isInflow(txn.type) ? 'text-green-600 dark:text-green-500' : 'text-red-600 dark:text-red-500'}>
                          {isInflow(txn.type) ? '+' : '-'}{formatCurrency(txn.total_amount, currency)}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(txn)}
                            className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(txn.id, txn.ticker, txn.type)}
                            disabled={deletingId === txn.id}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                          >
                            {deletingId === txn.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Transaction Form Modal */}
      {showAddForm && (
        <AddTransactionForm
          open={showAddForm}
          onClose={() => {
            setShowAddForm(false);
            setEditingTransaction(null);
          }}
          onSuccess={handleAddSuccess}
          editTransaction={editingTransaction}
          currency={currency}
        />
      )}
    </div>
  );
};
