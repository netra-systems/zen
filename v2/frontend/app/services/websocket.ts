import { w3cwebsocket as W3CWebSocket } from 'websocket';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

let client: W3CWebSocket | null = null;

export const getWebSocketClient = (token: string) => {
  if (!client) {
    client = new W3CWebSocket(`${WS_URL}?token=${token}`);

    client.onopen = () => {
      console.log('WebSocket Client Connected');
    };

    client.onclose = () => {
      console.log('WebSocket Client Disconnected');
      client = null;
    };

    client.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };
  }
  return client;
};
