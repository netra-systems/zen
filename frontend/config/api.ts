// API configuration exports for backward compatibility
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

// Export the config object as well
export const config = {
  apiUrl: API_BASE_URL,
  wsUrl: WS_BASE_URL,
};

export default config;