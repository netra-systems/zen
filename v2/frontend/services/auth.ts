
import { AuthConfigResponse } from '@/types';
import { api } from './api';

export const getAuthConfig = async (): Promise<AuthConfigResponse> => {
  const response = await api.get('/api/auth/config');
  return response.data;
};

export const login = (authConfig: AuthConfigResponse) => {
  if (authConfig.development_mode) {
    window.location.href = authConfig.endpoints.dev_login;
  } else {
    window.location.href = authConfig.endpoints.login;
  }
};

export const logout = (authConfig: AuthConfigResponse) => {
  window.location.href = authConfig.endpoints.logout;
};
