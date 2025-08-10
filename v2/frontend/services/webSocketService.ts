import { WebSocketMessage } from '../types/backend_schema_auto_generated';
import { config } from '@/config';

export type WebSocketStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';
export type WebSocketState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

interface WebSocketOptions {
  onOpen?: () => void;
  onMessage?: (message: any) => void;
  onError?: (error: any) => void;
  onClose?: () => void;
  onReconnect?: () => void;
  onBinaryMessage?: (data: ArrayBuffer) => void;
  onRateLimit?: () => void;
  heartbeatInterval?: number;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private status: WebSocketStatus = 'CLOSED';
  private state: WebSocketState = 'disconnected';
  private options: WebSocketOptions = {};
  private messageQueue: any[] = [];
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private url: string = '';

  public onStatusChange: ((status: WebSocketStatus) => void) | null = null;
  public onMessage: ((message: WebSocketMessage) => void) | null = null;

  public connect(url: string, options: WebSocketOptions = {}) {
    this.url = url;
    this.options = options;
    
    if (this.state === 'connected' || this.state === 'connecting') {
      return;
    }

    this.state = 'connecting';
    this.status = 'CONNECTING';
    this.onStatusChange?.(this.status);

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.state = 'connected';
        this.status = 'OPEN';
        this.onStatusChange?.(this.status);
        
        // Send auth token
        const token = localStorage.getItem('authToken');
        if (token) {
          this.send({ type: 'auth', token });
        }
        
        // Send queued messages
        while (this.messageQueue.length > 0) {
          const msg = this.messageQueue.shift();
          this.send(msg);
        }
        
        // Start heartbeat if configured
        if (options.heartbeatInterval) {
          this.startHeartbeat(options.heartbeatInterval);
        }
        
        options.onOpen?.();
      };

      this.ws.onmessage = (event) => {
        // Handle binary data
        if (event.data instanceof ArrayBuffer) {
          options.onBinaryMessage?.(event.data);
          return;
        }
        
        try {
          const message = JSON.parse(event.data);
          this.onMessage?.(message as WebSocketMessage);
          options.onMessage?.(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          options.onError?.({ message: 'Failed to parse message' });
        }
      };

      this.ws.onclose = () => {
        this.state = 'disconnected';
        this.status = 'CLOSED';
        this.onStatusChange?.(this.status);
        this.stopHeartbeat();
        options.onClose?.();
        
        // Attempt reconnection
        if (this.options.onReconnect) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.status = 'CLOSED';
        this.state = 'disconnected';
        this.onStatusChange?.(this.status);
        options.onError?.(error);
      };
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      this.status = 'CLOSED';
      this.state = 'disconnected';
      this.onStatusChange?.(this.status);
      options.onError?.(error);
    }
  }
  
  private startHeartbeat(interval: number) {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, interval);
  }
  
  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
  
  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    
    this.state = 'reconnecting';
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.options.onReconnect?.();
      this.connect(this.url, this.options);
    }, 5000);
  }

  public send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Queue message for sending when connected
      this.messageQueue.push(message);
    }
  }

  public sendMessage(message: WebSocketMessage) {
    this.send(message);
  }
  
  public getState(): WebSocketState {
    return this.state;
  }

  public disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.stopHeartbeat();
    
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.ws.close();
    }
    
    this.state = 'disconnected';
    this.messageQueue = [];
  }
}

export const webSocketService = new WebSocketService();