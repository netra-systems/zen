import { AuthConfigResponse } from '@/auth';
import { useContext } from 'react';
import { AuthContext, AuthContextType } from '@/auth';
import { config } from '@/config';

class AuthService {
  async getAuthConfig(): Promise<AuthConfigResponse> {
    const response = await fetch(`${config.apiUrl}/api/auth/config`);
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

  useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (context === undefined) {
      throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
  };
}

export const authService = new AuthService();
