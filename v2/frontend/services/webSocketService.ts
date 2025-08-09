import { WebSocketMessage } from '../types/websocket';

export type WebSocketStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';

class WebSocketService {
  private ws: WebSocket | null = null;
  private status: WebSocketStatus = 'CLOSED';

  public onStatusChange: ((status: WebSocketStatus) => void) | null = null;
  public onMessage: ((message: WebSocketMessage) => void) | null = null;

  public connect(url: string) {
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      return;
    }

    this.status = 'CONNECTING';
    this.onStatusChange?.(this.status);

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
}

export const webSocketService = new WebSocketService();