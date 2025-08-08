
const config = {
  api: {
    wsBaseUrl: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000',
  },
};

export default config;
