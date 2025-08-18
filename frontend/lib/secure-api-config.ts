/**
 * Secure API Configuration
 * Ensures HTTPS URLs in production environments to prevent mixed content errors
 */

export interface ApiConfig {
  apiUrl: string;
  wsUrl: string;
  authUrl: string;
  environment: string;
  forceHttps: boolean;
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
 * Gets the API configuration with security enforcements
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
    ? 'http://localhost:8001' 
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
  };
};

// Export singleton instance
export const secureApiConfig = getSecureApiConfig();

// For backward compatibility
export const API_BASE_URL = secureApiConfig.apiUrl;
export const WS_BASE_URL = secureApiConfig.wsUrl;
export const AUTH_BASE_URL = secureApiConfig.authUrl;

export default secureApiConfig;