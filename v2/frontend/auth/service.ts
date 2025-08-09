import { AuthConfigResponse } from '@/auth';
import { useContext } from 'react';
import { AuthContext, AuthContextType } from '@/auth';
import { config } from '@/config';

const TOKEN_KEY = 'jwt_token';

class AuthService {
  async getAuthConfig(): Promise<AuthConfigResponse> {
    const response = await fetch(`${config.apiUrl}/api/auth/config`);
    if (!response.ok) {
      throw new Error('Failed to fetch auth config');
    }
    return response.json();
  }

  async handleDevLogin(authConfig: AuthConfigResponse): Promise<{ access_token: string, token_type: string } | null> {
    try {
      const response = await fetch(authConfig.endpoints.dev_login, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: 'dev@example.com' }),
      });
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem(TOKEN_KEY, data.access_token);
        return data;
      } else {
        console.error('Dev login failed');
        return null;
      }
    } catch (error) {
      console.error('Error during dev login:', error);
      return null;
    }
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  handleLogin(authConfig: AuthConfigResponse) {
    if (authConfig.development_mode) {
      // In development mode, the login is handled by the AuthProvider
      return;
    } else {
      window.location.href = authConfig.endpoints.login;
    }
  }

  handleLogout(authConfig: AuthConfigResponse) {
    this.removeToken();
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