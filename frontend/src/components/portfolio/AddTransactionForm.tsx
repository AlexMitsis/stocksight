import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { api } from '@/services/api';
import { debounce } from '@/utils/debounce';
import { toNumber, formatCurrency } from '@/utils/number';
import type { Transaction, TransactionType } from '@/types/portfolio';

interface AddTransactionFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  editTransaction?: Transaction | null;
  currency?: string;
}

interface VWAPData {
  ticker: string;
  date: string;
  vwap: number;
  method: string;
  note?: string;
}

// Transaction type configurations
const TRANSACTION_TYPES: { value: TransactionType; label: string; color: string; description: string }[] = [
  { value: 'BUY', label: 'Buy', color: 'bg-green-600 hover:bg-green-700', description: 'Purchase shares' },
  { value: 'SELL', label: 'Sell', color: 'bg-red-600 hover:bg-red-700', description: 'Sell shares' },
  { value: 'TRANSFER_IN', label: 'Transfer In', color: 'bg-blue-600 hover:bg-blue-700', description: 'Import existing position' },
  { value: 'TRANSFER_OUT', label: 'Transfer Out', color: 'bg-orange-600 hover:bg-orange-700', description: 'Remove position' },
  { value: 'ADJUSTMENT', label: 'Adjustment', color: 'bg-gray-600 hover:bg-gray-700', description: 'Correct quantity' },
];

export const AddTransactionForm = ({
  open,
  onClose,
  onSuccess,
  editTransaction,
  currency = 'USD',
}: AddTransactionFormProps) => {
  const [type, setType] = useState<TransactionType>('BUY');
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [transactionDate, setTransactionDate] = useState('');
  const [fees, setFees] = useState('0.00');
  const [notes, setNotes] = useState('');
  const [costBasisKnown, setCostBasisKnown] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isLoadingVWAP, setIsLoadingVWAP] = useState(false);
  const [vwapData, setVwapData] = useState<VWAPData | null>(null);
  const [manualPriceOverride, setManualPriceOverride] = useState(false);
  const [availableQuantity, setAvailableQuantity] = useState<number | null>(null);
  const [checkingQuantity, setCheckingQuantity] = useState(false);

  // Pre-fill form when editing
  useEffect(() => {
    if (editTransaction) {
      setType(editTransaction.type);
      setTicker(editTransaction.ticker);
      setQuantity(toNumber(editTransaction.quantity).toString());
      setPrice(toNumber(editTransaction.price).toString());
      setTransactionDate(editTransaction.transaction_date);
      setFees(toNumber(editTransaction.fees).toString());
      setNotes(editTransaction.notes || '');
      setCostBasisKnown(editTransaction.cost_basis_known ?? true);
      setManualPriceOverride(true); // Don't auto-fill when editing
    }
  }, [editTransaction]);

  if (!open) return null;

  // Types that support VWAP auto-fill
  const supportsVWAP = type === 'BUY' || type === 'TRANSFER_IN';
  // Types that require quantity validation against holdings
  const requiresQuantityCheck = type === 'SELL' || type === 'TRANSFER_OUT';

  // Debounced VWAP fetch function
  const fetchVWAP = useCallback(
    debounce(async (tickerSymbol: string, date: string) => {
      if (!tickerSymbol || !date || !supportsVWAP) {
        return;
      }

      setIsLoadingVWAP(true);
      try {
        const response = await api.get(`/api/market-data/vwap/${tickerSymbol}?date=${date}`);
        const data = response.data;
        setVwapData(data);

        if (!manualPriceOverride) {
          setPrice(data.vwap.toString());
        }
      } catch (error: any) {
        console.error('Failed to fetch VWAP:', error);
        setVwapData(null);
      } finally {
        setIsLoadingVWAP(false);
      }
    }, 500),
    [manualPriceOverride, type]
  );

  // Check available quantity for SELL/TRANSFER_OUT transactions
  const checkAvailableQuantity = useCallback(
    debounce(async (tickerSymbol: string) => {
      if (!tickerSymbol || !requiresQuantityCheck) {
        setAvailableQuantity(null);
        return;
      }

      setCheckingQuantity(true);
      try {
        const response = await api.get('/api/portfolio/holdings');
        const holdings = response.data;
        const tickerHolding = holdings.find(
          (h: { ticker: string }) => h.ticker.toUpperCase() === tickerSymbol.toUpperCase()
        );
        setAvailableQuantity(tickerHolding ? toNumber(tickerHolding.quantity) : 0);
      } catch (error) {
        console.error('Failed to check available quantity:', error);
        setAvailableQuantity(null);
      } finally {
        setCheckingQuantity(false);
      }
    }, 300),
    [type]
  );

  // Handle type change
  const handleTypeChange = (newType: TransactionType) => {
    setType(newType);
    setAvailableQuantity(null);
    // Reset cost basis known when changing types
    if (newType !== 'TRANSFER_IN') {
      setCostBasisKnown(true);
    }
    // Check available quantity for types that remove shares
    if (ticker && (newType === 'SELL' || newType === 'TRANSFER_OUT')) {
      checkAvailableQuantity(ticker);
    }
    // Fetch VWAP for types that add shares
    if (ticker && transactionDate && (newType === 'BUY' || newType === 'TRANSFER_IN')) {
      fetchVWAP(ticker, transactionDate);
    }
  };

  // Handle ticker change
  const handleTickerChange = (value: string) => {
    const upperValue = value.toUpperCase();
    setTicker(upperValue);

    if (supportsVWAP && transactionDate) {
      fetchVWAP(upperValue, transactionDate);
    }
    if (requiresQuantityCheck) {
      checkAvailableQuantity(upperValue);
    }
  };

  // Handle date change
  const handleDateChange = (value: string) => {
    setTransactionDate(value);
    setManualPriceOverride(false);

    if (supportsVWAP && ticker) {
      fetchVWAP(ticker, value);
    }
  };

  // Handle manual price change
  const handlePriceChange = (value: string) => {
    setPrice(value);
    if (value && vwapData && parseFloat(value) !== vwapData.vwap) {
      setManualPriceOverride(true);
    }
  };

  // Calculate total amount
  const totalAmount = quantity && price
    ? (parseFloat(quantity) * parseFloat(price)) + parseFloat(fees || '0')
    : 0;

  // Validate quantity for types that remove shares
  const isQuantityValid = () => {
    if (!requiresQuantityCheck) return true;
    if (availableQuantity === null) return true; // Haven't checked yet
    const qty = Math.abs(parseFloat(quantity) || 0);
    return qty <= availableQuantity;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!ticker || !quantity || !transactionDate) {
      setError('Ticker, quantity, and date are required');
      return;
    }

    const parsedQuantity = parseFloat(quantity);
    const parsedPrice = parseFloat(price) || 0;

    // Quantity validation based on type
    if (type === 'ADJUSTMENT') {
      if (parsedQuantity === 0) {
        setError('Quantity must be non-zero for adjustments');
        return;
      }
    } else {
      if (parsedQuantity <= 0) {
        setError('Quantity must be positive');
        return;
      }
    }

    // Price validation (except for TRANSFER_IN with unknown cost basis)
    if (type === 'TRANSFER_IN' && !costBasisKnown) {
      // Price can be 0 for unknown cost basis
    } else if (['BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT'].includes(type)) {
      if (parsedPrice <= 0) {
        setError('Price must be positive');
        return;
      }
    }

    // Quantity validation for types that remove shares
    if (requiresQuantityCheck && availableQuantity !== null && Math.abs(parsedQuantity) > availableQuantity) {
      setError(`Insufficient quantity. Available: ${availableQuantity} shares`);
      return;
    }

    try {
      setLoading(true);

      const payload: Record<string, unknown> = {
        type,
        ticker: ticker.toUpperCase().trim(),
        quantity: parsedQuantity,
        price: parsedPrice,
        fees: parseFloat(fees || '0'),
        transaction_date: transactionDate,
        notes: notes.trim() || null,
      };

      // Include cost_basis_known for TRANSFER_IN
      if (type === 'TRANSFER_IN') {
        payload.cost_basis_known = costBasisKnown;
      }

      if (editTransaction) {
        await api.put(`/api/portfolio/transactions/${editTransaction.id}`, payload);
      } else {
        await api.post('/api/portfolio/transactions', payload);
      }

      onSuccess();
    } catch (err: any) {
      console.error('Failed to save transaction:', err);
      setError(err.response?.data?.detail || 'Failed to save transaction');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <Card className="w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>{editTransaction ? 'Edit Transaction' : 'Add Transaction'}</CardTitle>
          <CardDescription>
            Record a {type.toLowerCase()} transaction for your portfolio
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 p-3 rounded">
                {error}
              </div>
            )}

            {/* Transaction Type */}
            <div className="space-y-2">
              <Label>Transaction Type</Label>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {TRANSACTION_TYPES.map((txType) => (
                  <Button
                    key={txType.value}
                    type="button"
                    variant={type === txType.value ? 'default' : 'outline'}
                    className={`${type === txType.value ? txType.color : ''}`}
                    onClick={() => handleTypeChange(txType.value)}
                    disabled={loading}
                    title={txType.description}
                  >
                    {txType.label}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                {TRANSACTION_TYPES.find(t => t.value === type)?.description}
              </p>
            </div>

            {/* Ticker */}
            <div className="space-y-2">
              <Label htmlFor="ticker">Ticker Symbol</Label>
              <Input
                id="ticker"
                placeholder="AAPL"
                value={ticker}
                onChange={(e) => handleTickerChange(e.target.value)}
                disabled={loading}
                className="uppercase"
              />
              {requiresQuantityCheck && ticker && (
                <p className="text-sm text-muted-foreground">
                  {checkingQuantity ? (
                    'Checking available quantity...'
                  ) : availableQuantity !== null ? (
                    availableQuantity > 0 ? (
                      <span className="text-green-600 dark:text-green-500">
                        Available: {availableQuantity.toFixed(6).replace(/\.?0+$/, '')} shares
                      </span>
                    ) : (
                      <span className="text-red-600 dark:text-red-500">
                        You don't own any {ticker} shares
                      </span>
                    )
                  ) : null}
                </p>
              )}
            </div>

            {/* Quantity */}
            <div className="space-y-2">
              <Label htmlFor="quantity">
                Quantity {type === 'ADJUSTMENT' && '(negative to remove shares)'}
              </Label>
              <Input
                id="quantity"
                type="number"
                step="0.000001"
                placeholder={type === 'ADJUSTMENT' ? '-10 or 10' : '10'}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                disabled={loading}
              />
              {requiresQuantityCheck && !isQuantityValid() && (
                <p className="text-sm text-red-600 dark:text-red-500">
                  Quantity exceeds available shares ({availableQuantity})
                </p>
              )}
              {type === 'ADJUSTMENT' && (
                <p className="text-xs text-muted-foreground">
                  Use positive numbers to add shares, negative to remove.
                </p>
              )}
            </div>

            {/* Transaction Date */}
            <div className="space-y-2">
              <Label htmlFor="transactionDate">Transaction Date</Label>
              <Input
                id="transactionDate"
                type="date"
                value={transactionDate}
                onChange={(e) => handleDateChange(e.target.value)}
                disabled={loading}
                max={new Date().toISOString().split('T')[0]}
              />
            </div>

            {/* Cost Basis Known (for TRANSFER_IN) */}
            {type === 'TRANSFER_IN' && (
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="costBasisKnown"
                  checked={costBasisKnown}
                  onChange={(e) => setCostBasisKnown(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                  disabled={loading}
                />
                <Label htmlFor="costBasisKnown" className="text-sm font-normal cursor-pointer">
                  I know the cost basis (purchase price)
                </Label>
              </div>
            )}

            {/* Price */}
            <div className="space-y-2">
              <Label htmlFor="price">
                Price per Share
                {type === 'TRANSFER_IN' && !costBasisKnown && ' (optional)'}
              </Label>
              <div className="relative">
                <Input
                  id="price"
                  type="number"
                  step="0.01"
                  placeholder={type === 'TRANSFER_IN' && !costBasisKnown ? '0.00 (unknown)' : '150.00'}
                  value={price}
                  onChange={(e) => handlePriceChange(e.target.value)}
                  disabled={loading || isLoadingVWAP || (type === 'TRANSFER_IN' && !costBasisKnown)}
                />
                {isLoadingVWAP && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  </div>
                )}
              </div>
              {type === 'TRANSFER_IN' && !costBasisKnown && (
                <p className="text-xs text-amber-600 dark:text-amber-500">
                  Position will be tracked without cost basis. Gain/loss calculations won't be available.
                </p>
              )}
              {supportsVWAP && transactionDate && costBasisKnown && (
                <p className="text-xs text-muted-foreground mt-1">
                  {vwapData ? (
                    <>
                      Auto-filled with <span className="font-medium">VWAP</span> for{' '}
                      {new Date(vwapData.date).toLocaleDateString()}.
                      {vwapData.note && (
                        <span className="block mt-0.5 text-amber-600 dark:text-amber-500">
                          Note: {vwapData.note}
                        </span>
                      )}
                    </>
                  ) : (
                    'VWAP will auto-fill when ticker and date are entered'
                  )}
                </p>
              )}
            </div>

            {/* Fees */}
            <div className="space-y-2">
              <Label htmlFor="fees">Transaction Fees (optional)</Label>
              <Input
                id="fees"
                type="number"
                step="0.01"
                placeholder="0.00"
                value={fees}
                onChange={(e) => setFees(e.target.value)}
                disabled={loading}
              />
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <textarea
                id="notes"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Optional notes about this transaction..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={loading}
              />
            </div>

            {/* Total Amount */}
            <div className="bg-muted p-4 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-medium">Total Amount:</span>
                <span className={`text-lg font-bold ${
                  type === 'BUY' || type === 'TRANSFER_IN' ? 'text-green-600 dark:text-green-500' :
                  type === 'SELL' || type === 'TRANSFER_OUT' ? 'text-red-600 dark:text-red-500' :
                  'text-gray-600 dark:text-gray-400'
                }`}>
                  {formatCurrency(totalAmount, currency)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                ({Math.abs(parseFloat(quantity) || 0)} shares x {formatCurrency(parseFloat(price) || 0, currency)}/share + {formatCurrency(parseFloat(fees) || 0, currency)} fees)
              </p>
            </div>

            {/* Currency Info */}
            <p className="text-xs text-muted-foreground">
              Currency will be set automatically from your profile preferences.
            </p>

            {/* Actions */}
            <div className="flex gap-2 pt-4">
              <Button
                type="submit"
                disabled={loading || (requiresQuantityCheck && !isQuantityValid())}
                className={`flex-1 ${TRANSACTION_TYPES.find(t => t.value === type)?.color || ''}`}
              >
                {loading ? 'Saving...' : editTransaction ? 'Update Transaction' : `Record ${TRANSACTION_TYPES.find(t => t.value === type)?.label || type}`}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={loading}
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
