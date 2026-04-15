import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/services/api';

interface CSVImportButtonProps {
  onSuccess: () => void;
}

interface ImportWarning {
  row: number;
  type: string;
  message: string;
  ticker?: string;
}

interface PreviewResponse {
  valid_rows: any[];
  warnings: ImportWarning[];
  duplicates: string[];
  total_rows: number;
  valid_count: number;
  warning_count: number;
}

export const CSVImportButton = ({ onSuccess }: CSVImportButtonProps) => {
  const [showPreview, setShowPreview] = useState(false);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError('');
    setLoading(true);

    try {
      const text = await file.text();

      // Send to preview endpoint
      const response = await api.post('/api/portfolio/import/preview', {
        csv_data: text,
        column_mapping: {
          ticker: 'ticker',
          quantity: 'quantity',
          purchase_price: 'purchase_price',
          purchase_date: 'purchase_date',
          currency: 'currency',
        },
      });

      setPreview(response.data);
      setShowPreview(true);
    } catch (err: any) {
      console.error('CSV preview failed:', err);
      setError(err.response?.data?.detail || 'Failed to parse CSV file');
    } finally {
      setLoading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleConfirmImport = async () => {
    if (!preview) return;

    setError('');
    setImporting(true);

    try {
      const response = await api.post('/api/portfolio/import/confirm', {
        holdings: preview.valid_rows,
      });

      if (response.data.success) {
        setShowPreview(false);
        setPreview(null);
        onSuccess();
      } else {
        setError(response.data.errors.join(', '));
      }
    } catch (err: any) {
      console.error('CSV import failed:', err);
      setError(err.response?.data?.detail || 'Failed to import holdings');
    } finally {
      setImporting(false);
    }
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={handleFileSelect}
        className="hidden"
      />
      <Button variant="outline" onClick={() => fileInputRef.current?.click()} disabled={loading}>
        {loading ? 'Loading...' : 'Import CSV'}
      </Button>

      {/* Preview Modal */}
      {showPreview && preview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>CSV Import Preview</CardTitle>
              <CardDescription>
                Review the import before confirming. {preview.valid_count} valid rows found.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 p-3 rounded">
                  {error}
                </div>
              )}

              {/* Summary */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Total Rows</p>
                  <p className="text-2xl font-bold">{preview.total_rows}</p>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Valid</p>
                  <p className="text-2xl font-bold text-green-600">{preview.valid_count}</p>
                </div>
                <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Warnings</p>
                  <p className="text-2xl font-bold text-yellow-600">{preview.warning_count}</p>
                </div>
              </div>

              {/* Duplicates Warning */}
              {preview.duplicates.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-3 rounded">
                  <p className="font-semibold text-yellow-800 dark:text-yellow-200">
                    Duplicate Tickers ({preview.duplicates.length})
                  </p>
                  <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                    The following tickers already exist in your portfolio. Importing will add shares to existing holdings:
                  </p>
                  <p className="text-sm font-mono mt-2">{preview.duplicates.join(', ')}</p>
                </div>
              )}

              {/* Warnings */}
              {preview.warnings.length > 0 && (
                <div className="space-y-2">
                  <p className="font-semibold">Warnings:</p>
                  <div className="max-h-40 overflow-y-auto space-y-1">
                    {preview.warnings.map((warning, idx) => (
                      <div
                        key={idx}
                        className="text-sm bg-gray-50 dark:bg-gray-800 p-2 rounded"
                      >
                        <span className="font-semibold">Row {warning.row}:</span> {warning.message}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Preview Table */}
              <div>
                <p className="font-semibold mb-2">Holdings to Import:</p>
                <div className="border rounded overflow-x-auto max-h-60 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                      <tr>
                        <th className="p-2 text-left">Ticker</th>
                        <th className="p-2 text-right">Quantity</th>
                        <th className="p-2 text-right">Price</th>
                        <th className="p-2 text-left">Date</th>
                        <th className="p-2 text-left">Currency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.valid_rows.map((row, idx) => (
                        <tr key={idx} className="border-t">
                          <td className="p-2 font-semibold">{row.ticker}</td>
                          <td className="p-2 text-right">{row.quantity}</td>
                          <td className="p-2 text-right">{row.purchase_price}</td>
                          <td className="p-2">{row.purchase_date}</td>
                          <td className="p-2">{row.currency}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-4">
                <Button
                  onClick={handleConfirmImport}
                  disabled={importing || preview.valid_count === 0}
                  className="flex-1"
                >
                  {importing ? 'Importing...' : `Import ${preview.valid_count} Holdings`}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowPreview(false);
                    setPreview(null);
                    setError('');
                  }}
                  disabled={importing}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
};
