import { getSecureApiConfig, getSecureApiConfigAsync } from './lib/secure-api-config';

const secureConfig = getSecureApiConfig();

export const config = {
  apiUrl: secureConfig.apiUrl,
  wsUrl: secureConfig.wsUrl,
};

// Dynamic configuration support
let dynamicConfig: { apiUrl: string; wsUrl: string; } | null = null;

/**
 * Initialize dynamic configuration (call during app startup)
 */
export async function initDynamicConfig(): Promise<void> {
  try {
    const dynamicApiConfig = await getSecureApiConfigAsync();
    dynamicConfig = {
      apiUrl: dynamicApiConfig.apiUrl,
      wsUrl: dynamicApiConfig.wsUrl,
    };
  } catch (error) {
    console.warn('Failed to initialize dynamic config, using static config:', error);
  }
}

/**
 * Get current configuration (dynamic if available, fallback to static)
 */
export function getConfig() {
  return dynamicConfig || config;
}

/**
 * Get API URL (dynamic if available)
 */
export function getApiUrl(): string {
  return dynamicConfig?.apiUrl || config.apiUrl;
}

/**
 * Get WebSocket URL (dynamic if available)
 */
export function getWsUrl(): string {
  return dynamicConfig?.wsUrl || config.wsUrl;
}
