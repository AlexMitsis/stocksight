import { api } from './api';
import type { User, LoginResponse, RegisterResponse } from '@/types/auth';

export const authService = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/api/auth/login', {
      email,
      password,
    });
    return response.data;
  },

  async register(
    email: string,
    password: string,
    country: string = 'US',
    preferred_currency: string = 'USD'
  ): Promise<RegisterResponse> {
    const response = await api.post<RegisterResponse>('/api/auth/register', {
      email,
      password,
      country,
      preferred_currency,
    });
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/api/auth/me');
    return response.data;
  },

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/api/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async forgotPassword(email: string): Promise<{ message: string }> {
    const response = await api.post('/api/auth/forgot-password', { email });
    return response.data;
  },

  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    const response = await api.post('/api/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return response.data;
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    const response = await api.post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },

  async changeEmail(newEmail: string, password: string): Promise<{ message: string }> {
    const response = await api.post('/api/auth/change-email', {
      new_email: newEmail,
      password,
    });
    return response.data;
  },

  async changeCurrency(preferredCurrency: string): Promise<{ message: string }> {
    const response = await api.post('/api/auth/change-currency', {
      preferred_currency: preferredCurrency,
    });
    return response.data;
  },

  async changeCountry(country: string): Promise<{ message: string }> {
    const response = await api.post('/api/auth/change-country', {
      country,
    });
    return response.data;
  },

  async initiateGoogleOAuth(): Promise<{ auth_url: string }> {
    const response = await api.get('/api/auth/oauth/google');
    return response.data;
  },

  async initiateGitHubOAuth(): Promise<{ auth_url: string }> {
    const response = await api.get('/api/auth/oauth/github');
    return response.data;
  },

  async handleGoogleCallback(code: string): Promise<RegisterResponse> {
    const response = await api.get<RegisterResponse>(`/api/auth/oauth/google/callback?code=${code}`);
    return response.data;
  },

  async handleGitHubCallback(code: string): Promise<RegisterResponse> {
    const response = await api.get<RegisterResponse>(`/api/auth/oauth/github/callback?code=${code}`);
    return response.data;
  },
};
