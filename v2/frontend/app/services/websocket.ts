import { create } from 'zustand';
import { WebSocketStatus } from '@/types';

const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000';

interface WebSocketState {
  ws: WebSocket | null;
  status: WebSocketStatus;
  lastJsonMessage: any;
  connect: (token: string) => void;
  disconnect: () => void;
  sendMessage: (message: object) => void;
}

const useWebSocketStore = create<WebSocketState>((set, get) => ({
  ws: null,
  status: WebSocketStatus.Closed,
  lastJsonMessage: null,
  connect: (token) => {
    const { ws } = get();
    if (ws && ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected.');
      return;
    }

    const url = `${WEBSOCKET_URL}/ws?token=${token}`;
    set({ status: WebSocketStatus.Connecting });
    console.log('WebSocket connecting to:', url);
    const newWs = new WebSocket(url);

    newWs.onopen = () => {
      console.log('WebSocket connection established.');
      set({ status: WebSocketStatus.Open });
    };

    newWs.onclose = () => {
      console.log('WebSocket connection closed.');
      set({ status: WebSocketStatus.Closed, ws: null });
    };

    newWs.onerror = (event) => {
      console.error('WebSocket error:', event);
      set({ status: WebSocketStatus.Error });
    };

    newWs.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        set({ lastJsonMessage: message });
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error, 'Received data:', event.data);
      }
    };

    set({ ws: newWs });
  },
  disconnect: () => {
    const { ws } = get();
    if (ws) {
      console.log('Disconnecting WebSocket.');
      ws.close();
    }
  },
  sendMessage: (message) => {
    const { ws } = get();
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not open. Cannot send message.');
    }
  },
}));

export const useWebSocket = useWebSocketStore;