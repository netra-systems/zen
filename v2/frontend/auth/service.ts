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

  async handleDevLogin(authConfig: AuthConfigResponse): Promise<User | null> {
    try {
      const response = await fetch(authConfig.endpoints.dev_login, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const user = await response.json();
        console.log('Dev login successful', user);
        return user;
      } else {
        console.error('Dev login failed');
        return null;
      }
    } catch (error) {
      console.error('Error during dev login:', error);
      return null;
    }
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
