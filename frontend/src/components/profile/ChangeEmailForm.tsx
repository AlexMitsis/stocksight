import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { authService } from '@/services/auth';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const changeEmailSchema = z.object({
  newEmail: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

type ChangeEmailFormData = z.infer<typeof changeEmailSchema>;

interface ChangeEmailFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

export const ChangeEmailForm = ({ onSuccess, onCancel }: ChangeEmailFormProps) => {
  const { refreshUser } = useAuth();
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ChangeEmailFormData>();

  const onSubmit = async (data: ChangeEmailFormData) => {
    setError('');
    setSuccess(false);
    setIsLoading(true);

    try {
      await authService.changeEmail(data.newEmail, data.password);
      setSuccess(true);
      reset();

      // Refresh user data to show new email
      await refreshUser();

      setTimeout(() => {
        onSuccess();
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to change email');
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
          Email changed successfully!
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="newEmail">New Email Address</Label>
        <Input
          id="newEmail"
          type="email"
          placeholder="you@example.com"
          {...register('newEmail')}
          disabled={isLoading}
        />
        {errors.newEmail && (
          <p className="text-sm text-destructive">{errors.newEmail.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Confirm Password</Label>
        <Input
          id="password"
          type="password"
          placeholder="Enter your password"
          {...register('password')}
          disabled={isLoading}
        />
        {errors.password && (
          <p className="text-sm text-destructive">{errors.password.message}</p>
        )}
      </div>

      <div className="flex gap-4">
        <Button type="submit" disabled={isLoading} className="flex-1">
          {isLoading ? 'Changing Email...' : 'Change Email'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading} className="flex-1">
          Cancel
        </Button>
      </div>
    </form>
  );
};
