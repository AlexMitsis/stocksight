import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface OAuthCallbackPageProps {
  provider: 'google' | 'github';
}

export const OAuthCallbackPage = ({ provider }: OAuthCallbackPageProps) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { handleOAuthCallback } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const code = searchParams.get('code');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setError(`OAuth error: ${errorParam}`);
      setTimeout(() => navigate('/login'), 3000);
      return;
    }

    if (!code) {
      setError('No authorization code received');
      setTimeout(() => navigate('/login'), 3000);
      return;
    }

    // Handle OAuth callback
    const completeOAuth = async () => {
      try {
        await handleOAuthCallback(provider, code);
        navigate('/dashboard');
      } catch (err: any) {
        console.error('OAuth callback error:', err);
        setError(err.message || `${provider} authentication failed`);
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    completeOAuth();
  }, [searchParams, navigate, provider, handleOAuthCallback]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            {error ? 'Authentication Failed' : 'Completing Sign In...'}
          </CardTitle>
          <CardDescription className="text-center">
            {error ? error : `Authenticating with ${provider === 'google' ? 'Google' : 'GitHub'}...`}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          {!error && (
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
