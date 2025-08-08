import { User } from '@/types/index';
import { api } from '@/services/api';

export const devLogin = async (): Promise<User> => {
  const response = await api.post('/auth/dev_login');
  return response.data;
};

export const logout = async (): Promise<void> => {
  await api.get('/auth/logout');
};
