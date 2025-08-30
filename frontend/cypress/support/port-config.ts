/**
 * Dynamic Port Configuration for Cypress Tests
 * Provides centralized port discovery for test environments
 */

export class PortConfig {
  /**
   * Get the current test environment
   */
  static getEnvironment(): string {
    return Cypress.env('ENVIRONMENT') || 
           (Cypress.env('TESTING') === '1' || Cypress.env('TESTING') === 'true' ? 'test' : 'development');
  }

  /**
   * Get port for a specific service
   */
  static getPort(service: 'backend' | 'auth' | 'frontend'): number {
    const env = this.getEnvironment();
    
    // Check for Cypress environment variable overrides
    const envVarMap = {
      backend: 'BACKEND_PORT',
      auth: env === 'test' ? 'TEST_AUTH_PORT' : 'AUTH_SERVICE_PORT',
      frontend: 'FRONTEND_PORT'
    };
    
    const envPort = Cypress.env(envVarMap[service]);
    if (envPort) {
      return parseInt(envPort, 10);
    }
    
    // Default ports based on environment
    const defaultPorts = {
      development: {
        backend: 8001,
        auth: 8081,
        frontend: 3000
      },
      test: {
        backend: 8001,
        auth: 8082,  // Test environment uses different auth port
        frontend: 3001
      }
    };
    
    return defaultPorts[env]?.[service] || defaultPorts.development[service];
  }

  /**
   * Get full URL for a service
   */
  static getServiceUrl(service: 'backend' | 'auth' | 'frontend', path: string = ''): string {
    const port = this.getPort(service);
    const host = Cypress.env('DOCKER_HOST') || 'localhost';
    const protocol = Cypress.env('USE_HTTPS') === 'true' ? 'https' : 'http';
    
    return `${protocol}://${host}:${port}${path}`;
  }

  /**
   * Get auth configuration endpoint
   */
  static getAuthConfigUrl(): string {
    return this.getServiceUrl('auth', '/auth/config');
  }

  /**
   * Get dev login endpoint
   */
  static getDevLoginUrl(): string {
    return this.getServiceUrl('auth', '/auth/dev/login');
  }

  /**
   * Get backend API URL
   */
  static getBackendUrl(path: string = ''): string {
    return this.getServiceUrl('backend', path);
  }

  /**
   * Get WebSocket URL for backend
   */
  static getWebSocketUrl(path: string = '/ws'): string {
    const port = this.getPort('backend');
    const host = Cypress.env('DOCKER_HOST') || 'localhost';
    const protocol = Cypress.env('USE_HTTPS') === 'true' ? 'wss' : 'ws';
    
    return `${protocol}://${host}:${port}${path}`;
  }

  /**
   * Log current port configuration (for debugging)
   */
  static logConfiguration(): void {
    cy.log('Port Configuration', {
      environment: this.getEnvironment(),
      backend: this.getPort('backend'),
      auth: this.getPort('auth'),
      frontend: this.getPort('frontend'),
      authConfigUrl: this.getAuthConfigUrl(),
      devLoginUrl: this.getDevLoginUrl()
    });
  }
}

// Export convenience functions
export const getAuthConfigUrl = () => PortConfig.getAuthConfigUrl();
export const getDevLoginUrl = () => PortConfig.getDevLoginUrl();
export const getBackendUrl = (path?: string) => PortConfig.getBackendUrl(path);
export const getWebSocketUrl = (path?: string) => PortConfig.getWebSocketUrl(path);