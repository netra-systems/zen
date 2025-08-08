import { User } from '@/types';

export const devLogin = async (): Promise<User> => {
  const response = await fetch('/api/v3/auth/dev_login', {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to login as dev user');
  }
  return response.json();
};

export const logout = async (): Promise<void> => {
  const response = await fetch('/api/v3/auth/logout');
  if (!response.ok) {
    throw new Error('Failed to logout');
  }
};


export const getGoogleLoginUrl = async (): Promise<string> => {
  const response = await fetch('/api/v3/auth/login');
  if (!response.ok) {
    throw new Error('Failed to get Google login URL');
  }
  const data = await response.json();
  return data.url;
};

