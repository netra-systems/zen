// API configuration exports for backward compatibility
// Uses secure-api-config to enforce HTTPS in production environments
// Now supports dynamic port discovery in development
import { getSecureApiConfig, getSecureApiConfigAsync, serviceDiscovery } from '../lib/secure-api-config';

const secureConfig = getSecureApiConfig();

export const API_BASE_URL = secureConfig.apiUrl;
export const WS_BASE_URL = secureConfig.wsUrl;

// Export the config object as well
export const config = {
  apiUrl: API_BASE_URL,
  wsUrl: WS_BASE_URL,
};

/**
 * Get dynamic API configuration (async)
 */
export async function getApiConfig() {
  try {
    const dynamicConfig = await getSecureApiConfigAsync();
    return {
      apiUrl: dynamicConfig.apiUrl,
      wsUrl: dynamicConfig.wsUrl,
    };
  } catch (error) {
    console.warn('Failed to get dynamic API config, using static:', error);
    return config;
  }
}

/**
 * Get dynamic API URL
 */
export async function getApiUrl(): Promise<string> {
  const dynamicConfig = await getApiConfig();
  return dynamicConfig.apiUrl;
}

/**
 * Get dynamic WebSocket URL
 */
export async function getWsUrl(): Promise<string> {
  const dynamicConfig = await getApiConfig();
  return dynamicConfig.wsUrl;
}

// Export service discovery for direct access
export { serviceDiscovery };

export default config;