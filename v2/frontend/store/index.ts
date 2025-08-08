import { create } from 'zustand';
import { Message } from '@/types/chat';

interface ChatState {
  messages: Message[];
  subAgentName: string;
  subAgentStatus: string;
  addMessage: (message: Message) => void;
  setSubAgentName: (name: string) => void;
  setSubAgentStatus: (status: string) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  subAgentName: 'Idle',
  subAgentStatus: 'Not started',
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setSubAgentName: (name) => set({ subAgentName: name }),
  setSubAgentStatus: (status) => set({ subAgentStatus: status }),
}));