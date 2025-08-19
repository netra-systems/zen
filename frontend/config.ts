import { getSecureApiConfig } from './lib/secure-api-config';

const secureConfig = getSecureApiConfig();

export const config = {
  apiUrl: secureConfig.apiUrl,
  wsUrl: secureConfig.wsUrl,
};
