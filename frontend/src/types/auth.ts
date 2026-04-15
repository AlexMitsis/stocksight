export interface User {
  id: number;
  email: string;
  country: string | null;
  preferred_currency: string;
  created_at: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface AuthError {
  detail: string;
}
