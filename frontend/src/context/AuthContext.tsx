import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authService } from '@/services/auth';
import type { User } from '@/types/auth';

const isTokenExpired = (token: string): boolean => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
};

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, country?: string, currency?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  initiateOAuth: (provider: 'google' | 'github') => Promise<void>;
  handleOAuthCallback: (provider: 'google' | 'github', code: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch current user
  const fetchCurrentUser = useCallback(async (token: string) => {
    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
      setAccessToken(token);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      // Token is invalid, clear it
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setAccessToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      let token = localStorage.getItem('access_token');
      if (!token) {
        setIsLoading(false);
        return;
      }

      // If access token is expired, proactively refresh before calling /api/auth/me
      if (isTokenExpired(token)) {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken || isTokenExpired(refreshToken)) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          setIsLoading(false);
          return;
        }
        try {
          const data = await authService.refreshToken(refreshToken);
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          token = data.access_token;
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          setIsLoading(false);
          return;
        }
      }

      fetchCurrentUser(token);
    };

    initAuth();
  }, [fetchCurrentUser]);

  // Login function
  const login = async (email: string, password: string) => {
    try {
      const data = await authService.login(email, password);

      // Save tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      // Fetch user data
      await fetchCurrentUser(data.access_token);
    } catch (error: any) {
      console.error('Login error:', error);

      // Extract error message
      let errorMessage = 'Login failed';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        // Handle array of validation errors
        if (Array.isArray(detail)) {
          errorMessage = detail.map((err: any) => err.msg).join(', ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        }
      }
      throw new Error(errorMessage);
    }
  };

  // Signup function
  const signup = async (
    email: string,
    password: string,
    country: string = 'US',
    currency: string = 'USD'
  ) => {
    try {
      const data = await authService.register(email, password, country, currency);

      // Save tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      // Set user data (returned from signup)
      setUser(data.user);
      setAccessToken(data.access_token);
    } catch (error: any) {
      console.error('Signup error:', error);

      // Extract error message
      let errorMessage = 'Signup failed';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        // Handle array of validation errors
        if (Array.isArray(detail)) {
          errorMessage = detail.map((err: any) => err.msg).join(', ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        }
      }
      throw new Error(errorMessage);
    }
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setAccessToken(null);
    setUser(null);
  };

  // Refresh user data
  const refreshUser = async () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      await fetchCurrentUser(token);
    }
  };

  // Initiate OAuth flow
  const initiateOAuth = async (provider: 'google' | 'github') => {
    try {
      const response =
        provider === 'google'
          ? await authService.initiateGoogleOAuth()
          : await authService.initiateGitHubOAuth();

      // Redirect to OAuth provider
      window.location.href = response.auth_url;
    } catch (error: any) {
      console.error('OAuth initiation error:', error);
      throw new Error(`Failed to initiate ${provider} OAuth`);
    }
  };

  // Handle OAuth callback
  const handleOAuthCallback = async (provider: 'google' | 'github', code: string) => {
    try {
      const data =
        provider === 'google'
          ? await authService.handleGoogleCallback(code)
          : await authService.handleGitHubCallback(code);

      // Save tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      // Set user data
      setUser(data.user);
      setAccessToken(data.access_token);
    } catch (error: any) {
      console.error('OAuth callback error:', error);

      let errorMessage = `${provider} authentication failed`;
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      throw new Error(errorMessage);
    }
  };

  const value = {
    user,
    accessToken,
    isAuthenticated: !!user,
    isLoading,
    login,
    signup,
    logout,
    refreshUser,
    initiateOAuth,
    handleOAuthCallback,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
