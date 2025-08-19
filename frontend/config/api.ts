// API configuration exports for backward compatibility
// Uses secure-api-config to enforce HTTPS in production environments
import { getSecureApiConfig } from '../lib/secure-api-config';

const secureConfig = getSecureApiConfig();

export const API_BASE_URL = secureConfig.apiUrl;
export const WS_BASE_URL = secureConfig.wsUrl;

// Export the config object as well
export const config = {
  apiUrl: API_BASE_URL,
  wsUrl: WS_BASE_URL,
};

export default config;