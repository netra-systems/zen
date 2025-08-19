import { getSecureApiConfig } from '../lib/secure-api-config';

const secureConfig = getSecureApiConfig();
export const API_BASE_URL = secureConfig.apiUrl;