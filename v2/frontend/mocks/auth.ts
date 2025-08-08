import { AuthConfigResponse, User } from '@/types';

export const mockAuthConfig: AuthConfigResponse = {
  development_mode: false,
  user: null,
  google_login_url: '/api/auth/login/google',
  logout_url: '/api/auth/logout',
  endpoints: {
    login: '/api/auth/login/google',
    logout: '/api/auth/logout',
    user: '/api/auth/user',
  },
};

export const mockUser: User = {
  id: '1',
  email: 'test@example.com',
  full_name: 'Test User',
  is_active: true,
  is_superuser: false,
  picture: '',
};
