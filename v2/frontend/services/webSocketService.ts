import { WebSocketMessage } from '../types/websockets';

import { WEBSOCKET_URL } from '@/config';

export type WebSocketStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';

class WebSocketService {
  private ws: WebSocket | null = null;
  private status: WebSocketStatus = 'CLOSED';
  private pingInterval: NodeJS.Timeout | null = null;

  public onStatusChange: ((status: WebSocketStatus) => void) | null = null;
  public onMessage: ((message: WebSocketMessage) => void) | null = null;

  public connect() {
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      return;
    }

    this.status = 'CONNECTING';
    this.onStatusChange?.(this.status);

    this.ws = new WebSocket(WEBSOCKET_URL);

    this.ws.onopen = () => {
      this.status = 'OPEN';
      this.onStatusChange?.(this.status);
      this.startPing();
    };

    this.ws.onmessage = (event) => {
      if (event.data === 'pong') {
        return;
      }
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        this.onMessage?.(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      this.status = 'CLOSED';
      this.onStatusChange?.(this.status);
      this.stopPing();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.ws?.close();
    };
  }

  public sendMessage(message: WebSocketMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not open. Cannot send message.');
    }
  }

  public disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }

  private startPing() {
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 30000);
  }

  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

export const webSocketService = new WebSocketService();
