import { AuthConfigResponse } from '@/auth';
import { useContext } from 'react';
import { AuthContext, AuthContextType } from '@/auth';
import { config } from '@/config';

const TOKEN_KEY = 'jwt_token';
const DEV_LOGOUT_FLAG = 'dev_logout_flag';

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
        // Clear the logout flag on successful dev login
        this.clearDevLogoutFlag();
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

  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  getDevLogoutFlag(): boolean {
    return localStorage.getItem(DEV_LOGOUT_FLAG) === 'true';
  }

  setDevLogoutFlag(): void {
    localStorage.setItem(DEV_LOGOUT_FLAG, 'true');
  }

  clearDevLogoutFlag(): void {
    localStorage.removeItem(DEV_LOGOUT_FLAG);
  }

  handleLogin(authConfig: AuthConfigResponse) {
    // Always redirect to OAuth login endpoint
    // The backend will handle whether it's dev mode or production
    window.location.href = authConfig.endpoints.login;
  }

  async handleLogout(authConfig: AuthConfigResponse) {
    try {
      const response = await fetch(authConfig.endpoints.logout, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
      });
      
      if (response.ok) {
        this.removeToken();
        window.location.href = '/';
      } else {
        console.error('Logout failed');
        // Still remove token and redirect on error
        this.removeToken();
        window.location.href = '/';
      }
    } catch (error) {
      console.error('Error during logout:', error);
      // Still remove token and redirect on error
      this.removeToken();
      window.location.href = '/';
    }
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