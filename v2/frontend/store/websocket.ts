
import { create } from 'zustand';
import { WebSocketStatus } from '@/types';
import webSocketService from '@/app/services/websocket';

interface WebSocketState {
  status: WebSocketStatus;
  lastJsonMessage: any;
  connect: (token: string) => void;
  disconnect: () => void;
  sendMessage: (message: object) => void;
}

export const useWebSocketStore = create<WebSocketState>((set) => ({
  status: WebSocketStatus.Closed,
  lastJsonMessage: null,
  connect: (token) => {
    webSocketService.connect(token);
  },
  disconnect: () => {
    webSocketService.disconnect();
  },
  sendMessage: (message) => {
    webSocketService.sendMessage(message);
  },
}));

webSocketService.onStatusChange((status) => {
  useWebSocketStore.setState({ status });
});

webSocketService.onMessage((message) => {
  useWebSocketStore.setState({ lastJsonMessage: message });
});
