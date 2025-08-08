import { AuthConfigResponse } from '@/types';

class AuthService {
  async getAuthConfig(): Promise<AuthConfigResponse> {
    const response = await fetch('/api/auth/config');
    if (!response.ok) {
      throw new Error('Failed to fetch auth config');
    }
    return response.json();
  }

  handleLogin(authConfig: AuthConfigResponse) {
    if (authConfig.development_mode) {
      window.location.href = authConfig.endpoints.dev_login;
    } else {
      window.location.href = authConfig.endpoints.login;
    }
  }

  handleLogout(authConfig: AuthConfigResponse) {
    window.location.href = authConfig.endpoints.logout;
  }
}

export const authService = new AuthService();