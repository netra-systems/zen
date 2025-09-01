/**
 * Auth Service Configuration V2
 * Wrapper for backward compatibility - delegates to unified configuration
 */

import { unifiedApiConfig, getUnifiedApiConfig, getOAuthRedirectUri } from './unified-api-config';
import { authServiceClient } from './auth-service-client';
import { logger } from './logger';

interface AuthServiceConfig {
  baseUrl: string;
  endpoints: {
    login: string;
    logout: string;
    callback: string;
    token: string;
    refresh: string;
    validate_token: string;
    config: string;
    session: string;
    me: string;
  };
  oauth: {
    googleClientId?: string;
    redirectUri: string;
    javascriptOrigins: string[];
  };
  dynamic?: boolean;
}

/**
 * Get auth service configuration based on environment (synchronous)
 * Now delegates to unified configuration
 */
export function getAuthServiceConfig(): AuthServiceConfig {
  const config = getUnifiedApiConfig();
  
  return {
    baseUrl: config.urls.auth,
    endpoints: {
      login: config.endpoints.authLogin,
      logout: config.endpoints.authLogout,
      callback: config.endpoints.authCallback,
      token: config.endpoints.authToken,
      refresh: config.endpoints.authRefresh,
      validate_token: config.endpoints.authValidate,
      config: config.endpoints.authConfig,
      session: config.endpoints.authSession,
      me: config.endpoints.authMe,
    },
    oauth: {
      // TOMBSTONE: NEXT_PUBLIC_GOOGLE_CLIENT_ID superseded by OAuth config from auth service
      googleClientId: undefined,
      redirectUri: getOAuthRedirectUri(),
      javascriptOrigins: [config.urls.frontend],
    },
    dynamic: config.features.dynamicDiscovery,
  };
}

/**
 * Get auth service configuration with dynamic discovery (async)
 * In unified config, dynamic discovery is only for development
 */
export async function getAuthServiceConfigAsync(): Promise<AuthServiceConfig> {
  // Just return synchronous config as dynamic discovery is handled internally
  return getAuthServiceConfig();
}

// Export singleton instance from the canonical implementation
// This is for backward compatibility - authServiceClient from auth-service-client.ts is the SSOT
export { authServiceClient as authService } from './auth-service-client';
// Re-export the class for type imports (but the class itself is in auth-service-client.ts)
export { AuthServiceClient } from './auth-service-client';