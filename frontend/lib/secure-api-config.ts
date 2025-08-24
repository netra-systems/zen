/**
 * Secure API Configuration V2
 * Wrapper for backward compatibility - delegates to unified configuration
 */

import { unifiedApiConfig, getUnifiedApiConfig, getOAuthRedirectUri, isSecureEnvironment as isSecure } from './unified-api-config';
import { logger } from './logger';

export interface ApiConfig {
  apiUrl: string;
  wsUrl: string;
  authUrl: string;
  environment: string;
  forceHttps: boolean;
  dynamic: boolean;
}

/**
 * Gets the API configuration with security enforcements (synchronous fallback)
 * Now delegates to unified configuration
 */
export const getSecureApiConfig = (): ApiConfig => {
  const config = getUnifiedApiConfig();
  
  return {
    apiUrl: config.urls.api,
    wsUrl: config.endpoints.websocket,
    authUrl: config.urls.auth,
    environment: config.environment,
    forceHttps: config.features.useHttps,
    dynamic: config.features.dynamicDiscovery,
  };
};

/**
 * Gets the API configuration with dynamic service discovery (async)
 * In unified config, dynamic discovery is only for development
 */
export const getSecureApiConfigAsync = async (): Promise<ApiConfig> => {
  // Just return synchronous config as dynamic discovery is handled internally
  return getSecureApiConfig();
};

/**
 * Detects if we're in a secure environment that requires HTTPS
 */
export const isSecureEnvironment = (): boolean => {
  return isSecure();
};

/**
 * Gets the base URL for the frontend application
 */
export const getBaseUrl = (): string => {
  return unifiedApiConfig.urls.frontend;
};

// Export singleton instance (synchronous fallback)
export const secureApiConfig = getSecureApiConfig();

// For backward compatibility
export const API_BASE_URL = secureApiConfig.apiUrl;
export const WS_BASE_URL = secureApiConfig.wsUrl;
export const AUTH_BASE_URL = secureApiConfig.authUrl;

// Export service discovery for backward compatibility
export { serviceDiscovery } from './service-discovery';

export default secureApiConfig;