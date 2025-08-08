import create from 'zustand';
import { WebSocketMessage } from '../types';

interface ChatState {
  subAgentName: string;
  subAgentStatus: string;
  messages: WebSocketMessage[];
  setSubAgentName: (name: string) => void;
  setSubAgentStatus: (status: string) => void;
  addMessage: (message: WebSocketMessage) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  subAgentName: 'Idle',
  subAgentStatus: 'Not running',
  messages: [],
  setSubAgentName: (name) => set({ subAgentName: name }),
  setSubAgentStatus: (status) => set({ subAgentStatus: status }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] }))
}));