import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { authService } from '@/services/auth';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

const changeCurrencySchema = z.object({
  preferredCurrency: z.enum(['EUR', 'GBP', 'CHF', 'USD'], {
    errorMap: () => ({ message: 'Please select a valid currency' }),
  }),
});

type ChangeCurrencyFormData = z.infer<typeof changeCurrencySchema>;

interface ChangeCurrencyFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

const CURRENCY_OPTIONS = [
  { value: 'EUR', label: 'EUR (€) - Euro', symbol: '€' },
  { value: 'GBP', label: 'GBP (£) - British Pound', symbol: '£' },
  { value: 'CHF', label: 'CHF - Swiss Franc', symbol: 'CHF' },
  { value: 'USD', label: 'USD ($) - US Dollar', symbol: '$' },
];

export const ChangeCurrencyForm = ({ onSuccess, onCancel }: ChangeCurrencyFormProps) => {
  const { user, refreshUser } = useAuth();
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCurrency, setSelectedCurrency] = useState<string>(user?.preferred_currency || 'EUR');

  const {
    handleSubmit,
    formState: { errors },
  } = useForm<ChangeCurrencyFormData>();

  const onSubmit = async () => {
    setError('');
    setSuccess(false);
    setIsLoading(true);

    try {
      await authService.changeCurrency(selectedCurrency);
      setSuccess(true);

      // Refresh user data to show new currency
      await refreshUser();

      setTimeout(() => {
        onSuccess();
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to change currency');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md border border-destructive/20">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-sm p-3 rounded-md border border-green-200 dark:border-green-800">
          Currency changed successfully!
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="preferredCurrency">Preferred Currency</Label>
        <select
          id="preferredCurrency"
          value={selectedCurrency}
          onChange={(e) => setSelectedCurrency(e.target.value)}
          disabled={isLoading}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {CURRENCY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {errors.preferredCurrency && (
          <p className="text-sm text-destructive">{errors.preferredCurrency.message}</p>
        )}
      </div>

      <div className="bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 text-sm p-3 rounded-md border border-blue-200 dark:border-blue-800">
        <p className="font-semibold mb-1">What changes:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>Stock prices will be displayed in {selectedCurrency}</li>
          <li>Historical data will be converted to {selectedCurrency}</li>
          <li>Financial statements will show values in {selectedCurrency}</li>
        </ul>
      </div>

      <div className="flex gap-4">
        <Button type="submit" disabled={isLoading} className="flex-1">
          {isLoading ? 'Updating Currency...' : 'Update Currency'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading} className="flex-1">
          Cancel
        </Button>
      </div>
    </form>
  );
};
