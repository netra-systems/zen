
import { w3cwebsocket as W3CWebSocket } from 'websocket';
import { useStore } from '@/store';

const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000/ws';

class WebSocketService {
  private client: W3CWebSocket | null = null;

  public connect = () => {
    if (this.client && this.client.readyState === this.client.OPEN) {
      return;
    }

    this.client = new W3CWebSocket(WEBSOCKET_URL);

    this.client.onopen = () => {
      console.log('WebSocket Client Connected');
      useStore.getState().setWebSocketConnected(true);
    };

    this.client.onmessage = (message) => {
      const data = JSON.parse(message.data.toString());
      // Handle incoming messages and update the store
    };

    this.client.onclose = () => {
      console.log('WebSocket Client Disconnected');
      useStore.getState().setWebSocketConnected(false);
    };

    this.client.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };
  };

  public sendMessage = (message: any) => {
    if (this.client && this.client.readyState === this.client.OPEN) {
      this.client.send(JSON.stringify(message));
    }
  };

  public disconnect = () => {
    if (this.client) {
      this.client.close();
    }
  };
}

export const webSocketService = new WebSocketService();
