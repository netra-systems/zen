import { AuthConfigResponse } from './types';
import { useContext } from 'react';
import { AuthContext, AuthContextType } from './context';
import { authService as authServiceClient } from '@/lib/auth-service-config';
import { logger } from '@/lib/logger';
import { jwtDecode } from 'jwt-decode';

const TOKEN_KEY = 'jwt_token';
const DEV_LOGOUT_FLAG = 'dev_logout_flag';
const REFRESH_THRESHOLD_MS = 5 * 60 * 1000; // Refresh 5 minutes before expiry

class AuthService {
  async getAuthConfig(retries = 3, delay = 1000): Promise<AuthConfigResponse> {
    for (let i = 0; i < retries; i++) {
      try {
        // Get config from auth service
        const authConfig = await authServiceClient.getConfig();
        
        // Get the auth service configuration
        const { getAuthServiceConfig } = await import('@/lib/auth-service-config');
        const config = getAuthServiceConfig();
        
        // Transform to expected format - use exact endpoints from auth config
        return {
          development_mode: authConfig.development_mode ?? process.env.NODE_ENV === 'development',
          google_client_id: authConfig.google_client_id || process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
          endpoints: {
            login: authConfig.endpoints?.login || config.endpoints.login,
            logout: authConfig.endpoints?.logout || config.endpoints.logout,
            callback: authConfig.endpoints?.callback || config.endpoints.callback,
            token: authConfig.endpoints?.token || config.endpoints.token,
            user: authConfig.endpoints?.user || config.endpoints.me,
            dev_login: authConfig.endpoints?.dev_login || `${config.baseUrl}/auth/dev/login`
          },
          authorized_javascript_origins: authConfig.authorized_javascript_origins || config.oauth?.javascriptOrigins || [],
          authorized_redirect_uris: authConfig.authorized_redirect_uris || [config.oauth?.redirectUri || window.location.origin + '/auth/callback']
        };
      } catch (error) {
        if (i < retries - 1) {
          logger.warn(`Auth config fetch error, retrying... (${i + 1}/${retries})`, {
            component: 'AuthService'
          });
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }
        throw error;
      }
    }
    throw new Error('Failed to fetch auth config after retries');
  }

  async handleDevLogin(authConfig: AuthConfigResponse): Promise<{ access_token: string, token_type: string } | null> {
    logger.info('Attempting dev login', { component: 'AuthService', action: 'dev_login' });
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
        logger.info('Dev login successful', { component: 'AuthService', action: 'dev_login_success' });
        localStorage.setItem(TOKEN_KEY, data.access_token);
        // Clear the logout flag on successful dev login
        this.clearDevLogoutFlag();
        return data;
      } else {
        logger.error('Dev login failed', undefined, { 
          component: 'AuthService', 
          action: 'dev_login_failed',
          metadata: { status: response.status }
        });
        return null;
      }
    } catch (error) {
      logger.error('Error during dev login', error as Error, { 
        component: 'AuthService', 
        action: 'dev_login_error'
      });
      return null;
    }
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  /**
   * Check if token needs refresh (within threshold)
   */
  needsRefresh(token?: string): boolean {
    const currentToken = token || this.getToken();
    if (!currentToken) return false;
    
    try {
      const decoded = jwtDecode(currentToken) as any;
      const expiryTime = decoded.exp * 1000; // Convert to milliseconds
      const currentTime = Date.now();
      
      return (expiryTime - currentTime) <= REFRESH_THRESHOLD_MS;
    } catch (error) {
      logger.error('Error checking token expiry', error as Error, {
        component: 'AuthService',
        action: 'needs_refresh_check'
      });
      return true; // Assume refresh needed if token is invalid
    }
  }

  /**
   * Refresh the current token
   */
  async refreshToken(): Promise<{ access_token: string; expires_in: number } | null> {
    try {
      const response = await authServiceClient.refreshToken();
      if (response.access_token) {
        this.setToken(response.access_token);
        logger.info('Token refreshed successfully', {
          component: 'AuthService',
          action: 'token_refresh_success'
        });
        return response;
      }
      return null;
    } catch (error) {
      logger.error('Token refresh failed', error as Error, {
        component: 'AuthService',
        action: 'token_refresh_failed'
      });
      return null;
    }
  }

  /**
   * Validate a token
   */
  async validateToken(token?: string): Promise<boolean> {
    const currentToken = token || this.getToken();
    if (!currentToken) return false;
    
    try {
      return await authServiceClient.validateToken(currentToken);
    } catch (error) {
      logger.error('Token validation failed', error as Error, {
        component: 'AuthService',
        action: 'token_validation_failed'
      });
      return false;
    }
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
    // Use the auth service client to initiate login
    authServiceClient.initiateLogin('google');
  }

  async handleLogout(authConfig: AuthConfigResponse) {
    try {
      await authServiceClient.logout();
      this.removeToken();
      window.location.href = '/';
    } catch (error) {
      logger.error('Error during logout', error as Error, { 
        component: 'AuthService', 
        action: 'logout_error'
      });
      // Still remove token and redirect on error
      this.removeToken();
      window.location.href = '/';
    }
  }

  useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (context === undefined || context === null) {
      throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
  };
}

// Create instance
const authServiceInstance = new AuthService();

// Export both the instance and the class
export { authServiceInstance as authService, AuthService };

// Also provide as default export for compatibility
export default AuthService;
