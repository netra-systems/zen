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
