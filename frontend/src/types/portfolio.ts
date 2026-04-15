export interface Holding {
  id: number;
  ticker: string;
  quantity: string | number;  // Comes as string from Decimal type
  cost_basis: string | number;  // Comes as string from Decimal type
  purchase_price: string | number;  // Comes as string from Decimal type
  purchase_date: string;
  currency: string;
  current_price?: string | number | null;
  current_value?: string | number | null;
  unrealized_gain?: string | number | null;
  unrealized_gain_pct?: string | number | null;
  created_at: string;
  updated_at: string;
}

export type TransactionType = 'BUY' | 'SELL' | 'DIVIDEND' | 'TRANSFER_IN' | 'TRANSFER_OUT' | 'ADJUSTMENT';

export interface Transaction {
  id: number;
  user_id: number;
  ticker: string;
  type: TransactionType;
  quantity: string | number | null;  // Nullable for dividends, can be negative for ADJUSTMENT
  price: string | number;
  fees: string | number;
  total_amount: string | number;
  transaction_date: string;
  currency: string;
  notes?: string | null;
  cost_basis_known?: boolean;  // For TRANSFER_IN with unknown cost basis
  created_at: string;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total_count: number;
  filters_applied: Record<string, string>;
}

export type { Holding, Transaction, TransactionListResponse };
