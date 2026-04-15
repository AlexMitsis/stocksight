import { useState } from 'react';
import type { Holding } from '@/types/portfolio';
import { toNumber, formatCurrency as formatCurrencyUtil, formatQuantity } from '@/utils/number';

interface HoldingsTableProps {
  holdings: Holding[];
  onUpdate?: () => void;
  currency: string;
}

/**
 * HoldingsTable displays portfolio holdings in a read-only view.
 *
 * Holdings are managed through transactions (BUY, SELL, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT).
 * To modify holdings, use the Transactions tab.
 */
export const HoldingsTable = ({ holdings, currency }: HoldingsTableProps) => {
  const [sortColumn, setSortColumn] = useState<keyof Holding>('ticker');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const handleSort = (column: keyof Holding) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const sortedHoldings = [...holdings].sort((a, b) => {
    const aVal = a[sortColumn];
    const bVal = b[sortColumn];

    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    // Handle numeric columns (convert strings to numbers)
    if (['quantity', 'purchase_price', 'cost_basis', 'current_value'].includes(sortColumn)) {
      const aNum = toNumber(aVal);
      const bNum = toNumber(bVal);
      return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
    }

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    }

    return 0;
  });

  const SortIcon = ({ column }: { column: keyof Holding }) => {
    if (sortColumn !== column) {
      return <span className="ml-1 text-gray-400">⇅</span>;
    }
    return <span className="ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b">
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
              onClick={() => handleSort('purchase_price')}
            >
              Purchase Price <SortIcon column="purchase_price" />
            </th>
            <th
              className="text-right p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
              onClick={() => handleSort('cost_basis')}
            >
              Total Cost <SortIcon column="cost_basis" />
            </th>
            <th
              className="text-right p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
              onClick={() => handleSort('current_value')}
            >
              Current Value <SortIcon column="current_value" />
            </th>
            <th
              className="text-right p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
              onClick={() => handleSort('purchase_date')}
            >
              Purchase Date <SortIcon column="purchase_date" />
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedHoldings.map((holding) => (
            <tr key={holding.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
              <td className="p-3 font-semibold">{holding.ticker}</td>
              <td className="p-3 text-right">{formatQuantity(holding.quantity)}</td>
              <td className="p-3 text-right">{formatCurrencyUtil(holding.purchase_price, currency)}</td>
              <td className="p-3 text-right">{formatCurrencyUtil(holding.cost_basis, currency)}</td>
              <td className="p-3 text-right">
                {holding.current_value != null
                  ? formatCurrencyUtil(holding.current_value, currency)
                  : '-'}
              </td>
              <td className="p-3 text-right">{new Date(holding.purchase_date).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
