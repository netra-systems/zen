
import { create } from 'zustand';

interface WebSocketState {
  isConnected: boolean;
  setWebSocketConnected: (isConnected: boolean) => void;
}

export const useWebSocketStore = create<WebSocketState>((set) => ({
  isConnected: false,
  setWebSocketConnected: (isConnected) => set({ isConnected }),
}));
