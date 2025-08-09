
import { create } from 'zustand';
import { Message, SubAgentStatus } from '@/types/chat';

interface ChatState {
  messages: Message[];
  subAgentName: string;
  subAgentStatus: SubAgentStatus | null;
  isProcessing: boolean;
  addMessage: (message: Message) => void;
  setSubAgentName: (name: string) => void;
  setSubAgentStatus: (status: SubAgentStatus) => void;
  setProcessing: (isProcessing: boolean) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  subAgentName: 'Netra Agent',
  subAgentStatus: null,
  isProcessing: false,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setSubAgentName: (name) => set({ subAgentName: name }),
  setSubAgentStatus: (status) => set({ subAgentStatus: status }),
  setProcessing: (isProcessing) => set({ isProcessing }),
  reset: () => set({ messages: [], subAgentName: 'Netra Agent', subAgentStatus: null, isProcessing: false }),
}));
