import { AuthConfig, User } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export const getAuthConfig = async (): Promise<AuthConfig> => {
  const response = await fetch(`${API_BASE_URL}/api/v3/auth/endpoints`);
  if (!response.ok) {
    throw new Error('Failed to fetch auth config');
  }
  return response.json();
};

export const devLogin = async (email: string): Promise<User> => {
  const response = await fetch(`${API_BASE_URL}/api/v3/auth/dev-login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) {
    throw new Error('Dev login failed');
  }
  return response.json();
};

export const logout = async (): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/v3/auth/logout`);
  if (!response.ok) {
    throw new Error('Logout failed');
  }
};
