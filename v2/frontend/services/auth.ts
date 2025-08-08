
import { AuthConfigResponse } from '@/types';
import { api } from './api';

export const getAuthConfig = async (): Promise<AuthConfigResponse> => {
  const response = await api.get('/api/auth/config');
  return response.data;
};
