/**
 * Secure API Configuration
 * Ensures HTTPS URLs in production environments to prevent mixed content errors
 * Now supports dynamic port discovery in development environments
 */

import { serviceDiscovery } from './service-discovery';
import { logger } from './logger';

export interface ApiConfig {
  apiUrl: string;
  wsUrl: string;
  authUrl: string;
  environment: string;
  forceHttps: boolean;
  dynamic: boolean; // Whether URLs were discovered dynamically
}

/**
 * Detects if we're in a secure environment that requires HTTPS
 */
const isSecureEnvironment = (): boolean => {
  // Server-side: check environment variables
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_ENVIRONMENT !== 'development';
  }
  
  // Client-side: check protocol and environment
  return (
    window.location.protocol === 'https:' ||
    process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' ||
    process.env.NEXT_PUBLIC_ENVIRONMENT === 'production' ||
    process.env.NEXT_PUBLIC_FORCE_HTTPS === 'true'
  );
};

/**
 * Forces URLs to use secure protocols in production environments
 */
const secureUrl = (url: string, isWebSocket = false): string => {
  if (!isSecureEnvironment()) {
    return url;
  }

  if (isWebSocket) {
    return url.replace(/^ws:\/\//, 'wss://');
  } else {
    return url.replace(/^http:\/\//, 'https://');
  }
};

/**
 * Gets the API configuration with security enforcements (synchronous fallback)
 */
export const getSecureApiConfig = (): ApiConfig => {
  const environment = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';
  const forceHttps = isSecureEnvironment();

  // Default URLs - properly handle production vs staging
  const defaultApiUrl = environment === 'development' 
    ? 'http://localhost:8000' 
    : environment === 'production'
    ? 'https://api.netrasystems.ai'
    : 'https://api.staging.netrasystems.ai';
  
  const defaultWsUrl = environment === 'development' 
    ? 'ws://localhost:8000/ws' 
    : environment === 'production'
    ? 'wss://api.netrasystems.ai/ws'
    : 'wss://api.staging.netrasystems.ai/ws';

  const defaultAuthUrl = environment === 'development' 
    ? 'http://localhost:8081' 
    : environment === 'production'
    ? 'https://auth.netrasystems.ai'
    : 'https://auth.staging.netrasystems.ai';

  // Get URLs from environment variables or use defaults
  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || defaultApiUrl;
  const rawWsUrl = process.env.NEXT_PUBLIC_WS_URL || defaultWsUrl;
  const rawAuthUrl = process.env.NEXT_PUBLIC_AUTH_URL || defaultAuthUrl;

  return {
    apiUrl: secureUrl(rawApiUrl),
    wsUrl: secureUrl(rawWsUrl, true),
    authUrl: secureUrl(rawAuthUrl),
    environment,
    forceHttps,
    dynamic: false,
  };
};

/**
 * Gets the API configuration with dynamic service discovery (async)
 */
export const getSecureApiConfigAsync = async (): Promise<ApiConfig> => {
  const environment = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';
  const forceHttps = isSecureEnvironment();

  try {
    // Only use service discovery in development
    if (environment === 'development') {
      logger.debug('Attempting dynamic service discovery for development environment');
      
      const discoveredUrls = await serviceDiscovery.discoverUrls();
      
      return {
        apiUrl: secureUrl(discoveredUrls.apiUrl),
        wsUrl: secureUrl(discoveredUrls.wsUrl, true),
        authUrl: secureUrl(discoveredUrls.authUrl),
        environment,
        forceHttps,
        dynamic: true,
      };
    }
  } catch (error) {
    logger.warn('Dynamic service discovery failed, falling back to static config:', error);
  }

  // Fall back to static config for production/staging or if discovery fails
  return getSecureApiConfig();
};

/**
 * Gets the base URL for the frontend application
 * Provides a centralized way to get the base URL that can be reused across the application
 */
export const getBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  // SSR context
  return process.env.NEXT_PUBLIC_APP_URL || 
         (process.env.NEXT_PUBLIC_ENVIRONMENT === 'production' 
           ? 'https://app.netrasystems.ai'
           : process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging'
           ? 'https://app.staging.netrasystems.ai'
           : 'http://localhost:3000');
};

// Export singleton instance (synchronous fallback)
export const secureApiConfig = getSecureApiConfig();

// For backward compatibility
export const API_BASE_URL = secureApiConfig.apiUrl;
export const WS_BASE_URL = secureApiConfig.wsUrl;
export const AUTH_BASE_URL = secureApiConfig.authUrl;

// Export service discovery for direct access
export { serviceDiscovery };

export default secureApiConfig;