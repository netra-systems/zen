
import { w3cwebsocket as W3CWebSocket } from 'websocket';
import { v4 as uuidv4 } from 'uuid';
import { WEBSOCKET_URL } from '@/config';
import { Message, WebSocketMessage } from '@/types';

class WebSocketService {
  private client: W3CWebSocket | null = null;
  private messageQueue: string[] = [];
  private onMessageCallback: ((message: Message) => void) | null = null;
  private connectionPromise: Promise<void> | null = null;

  public connect(): Promise<void> {
    if (this.client && this.client.readyState === this.client.OPEN) {
      return Promise.resolve();
    }

    if (this.connectionPromise) {
      return this.connectionPromise;
    }

    this.connectionPromise = new Promise((resolve, reject) => {
      this.client = new W3CWebSocket(WEBSOCKET_URL);

      this.client.onopen = () => {
        console.log('WebSocket Client Connected');
        this.messageQueue.forEach(message => this.client?.send(message));
        this.messageQueue = [];
        resolve();
      };

      this.client.onmessage = (message) => {
        if (typeof message.data === 'string') {
          try {
            const parsedMessage: Message = JSON.parse(message.data);
            if (this.onMessageCallback) {
              this.onMessageCallback(parsedMessage);
            }
          } catch (error) {
            console.error('Error parsing message data', error);
          }
        }
      };

      this.client.onerror = (error) => {
        console.error('WebSocket Error', error);
        reject(error);
        this.connectionPromise = null;
      };

      this.client.onclose = () => {
        console.log('WebSocket Client Closed');
        this.client = null;
        this.connectionPromise = null;
      };
    });

    return this.connectionPromise;
  }

  public sendMessage(payload: any): void {
    const message: WebSocketMessage = {
      id: uuidv4(),
      type: 'analysis_request',
      payload,
      timestamp: new Date().toISOString(),
    };
    const messageString = JSON.stringify(message);

    if (this.client && this.client.readyState === this.client.OPEN) {
      this.client.send(messageString);
    } else {
      this.messageQueue.push(messageString);
      this.connect();
    }
  }

  public onMessage(callback: (message: Message) => void): void {
    this.onMessageCallback = callback;
  }

  public close(): void {
    if (this.client) {
      this.client.close();
    }
  }
}

export const webSocketService = new WebSocketService();
