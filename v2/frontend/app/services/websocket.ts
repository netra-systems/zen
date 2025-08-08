import { WebSocketMessage } from '@/app/types';

class WebSocketService {
  private static instance: WebSocketService;
  private socket: WebSocket | null = null;
  private messageListeners: Array<(message: WebSocketMessage) => void> = [];

  private constructor() {}

  public static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  public connect(url: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
    };

    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as WebSocketMessage;
      this.messageListeners.forEach(listener => listener(message));
    };

    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.socket = null;
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  public sendMessage(message: WebSocketMessage) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected.');
    }
  }

  public addMessageListener(listener: (message: WebSocketMessage) => void) {
    this.messageListeners.push(listener);
  }

  public removeMessageListener(listener: (message: WebSocketMessage) => void) {
    this.messageListeners = this.messageListeners.filter(l => l !== listener);
  }
}

export default WebSocketService.getInstance();