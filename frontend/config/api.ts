// API configuration exports for backward compatibility
// Force HTTPS URLs in production environments to prevent mixed content errors
const getApiUrl = () => {
  const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  // If we're in production/staging and URL starts with http://, force https://
  if (typeof window !== 'undefined' && window.location.protocol === 'https:' && url.startsWith('http://')) {
    return url.replace('http://', 'https://');
  }
  return url;
};

const getWsUrl = () => {
  const url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
  // If we're in production/staging and URL starts with ws://, force wss://
  if (typeof window !== 'undefined' && window.location.protocol === 'https:' && url.startsWith('ws://')) {
    return url.replace('ws://', 'wss://');
  }
  return url;
};

export const API_BASE_URL = getApiUrl();
export const WS_BASE_URL = getWsUrl();

// Export the config object as well
export const config = {
  apiUrl: API_BASE_URL,
  wsUrl: WS_BASE_URL,
};

export default config;