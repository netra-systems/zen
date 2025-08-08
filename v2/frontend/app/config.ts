export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
    wsBaseUrl: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000',
  },
};