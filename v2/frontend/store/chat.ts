
import { create } from 'zustand';
import { Message, SubAgentStatus } from '@/types/chat';

interface ChatState {
  messages: Message[];
  subAgentName: string;
  currentSubAgent: string | null;
  subAgentStatus: SubAgentStatus | null;
  isProcessing: boolean;
  activeThreadId: string | null;
  addMessage: (message: Message) => void;
  updateMessage: (messageId: string, updates: Partial<Message>) => void;
  setSubAgentName: (name: string) => void;
  setSubAgentStatus: (status: SubAgentStatus) => void;
  setSubAgent: (name: string, status: string) => void;
  setProcessing: (isProcessing: boolean) => void;
  clearMessages: () => void;
  clearSubAgent: () => void;
  setActiveThread: (threadId: string) => void;
  loadThreadMessages: (messages: Message[]) => void;
  addError: (error: string) => void;
  addErrorMessage: (error: string) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  subAgentName: 'Netra Agent',
  currentSubAgent: null,
  subAgentStatus: null,
  isProcessing: false,
  activeThreadId: null,
  
  addMessage: (message) => set((state) => {
    // Ensure message has a unique ID and it's never an empty string
    const messageWithId = {
      ...message,
      id: (message.id && message.id.trim() !== '') ? message.id : `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
    return {
      messages: [...state.messages, messageWithId]
    };
  }),
  
  updateMessage: (messageId, updates) => set((state) => ({
    messages: state.messages.map(msg => 
      msg.id === messageId ? { ...msg, ...updates } : msg
    )
  })),
  
  setSubAgentName: (name) => set({ subAgentName: name, currentSubAgent: name }),
  
  setSubAgentStatus: (status) => set({ subAgentStatus: status }),
  
  setSubAgent: (name, status) => set({ 
    subAgentName: name, 
    currentSubAgent: name,
    subAgentStatus: status 
  }),
  
  setProcessing: (isProcessing) => set({ isProcessing }),
  
  clearMessages: () => set({ messages: [] }),
  
  clearSubAgent: () => set({ 
    subAgentName: 'Netra Agent', 
    currentSubAgent: null,
    subAgentStatus: null 
  }),
  
  setActiveThread: (threadId) => set({ 
    activeThreadId: threadId,
    messages: [] 
  }),
  
  loadThreadMessages: (messages) => set({ 
    messages: messages.map((msg, index) => ({
      ...msg,
      id: (msg.id && msg.id.trim() !== '') ? msg.id : `msg_${Date.now()}_${index}_${Math.random().toString(36).substr(2, 9)}`
    }))
  }),
  
  addError: (error) => set((state) => ({
    messages: [...state.messages, {
      id: `error-${Date.now()}`,
      type: 'error' as const,
      content: error,
      created_at: new Date().toISOString(),
      displayed_to_user: true,
      error: error,
    }]
  })),
  
  addErrorMessage: (error) => set((state) => ({
    messages: [...state.messages, {
      id: `error-${Date.now()}`,
      type: 'error' as const,
      content: error,
      created_at: new Date().toISOString(),
      displayed_to_user: true,
      error: error,
    }]
  })),
  
  reset: () => set({ 
    messages: [], 
    subAgentName: 'Netra Agent', 
    currentSubAgent: null,
    subAgentStatus: null, 
    isProcessing: false,
    activeThreadId: null 
  }),
}));
