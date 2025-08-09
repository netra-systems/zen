import { WebSocketMessage } from '../types/backend_schema_auto_generated';
import { config } from '@/config';

export type WebSocketStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';

class WebSocketService {
  private ws: WebSocket | null = null;
  private status: WebSocketStatus = 'CLOSED';

  public onStatusChange: ((status: WebSocketStatus) => void) | null = null;
  public onMessage: ((message: WebSocketMessage) => void) | null = null;

  public async connect(url: string) {
    if (this.status === 'OPEN' || this.status === 'CONNECTING') {
      return;
    }

    this.status = 'CONNECTING';
    this.onStatusChange?.(this.status);

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.status = 'OPEN';
        this.onStatusChange?.(this.status);
      };

      this.ws.onmessage = (event) => {
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
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.status = 'CLOSED';
        this.onStatusChange?.(this.status);
      };
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      this.status = 'CLOSED';
      this.onStatusChange?.(this.status);
    }
  }

  public sendMessage(message: WebSocketMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not open. Cannot send message.');
    }
  }

  public disconnect() {
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.ws.close();
    }
  }
}

export const webSocketService = new WebSocketService();