
import { create } from 'zustand';
import { generateUniqueId } from '@/lib/utils';
import { Message } from '@/types/registry';
import type { SubAgentState as BackendSubAgentState } from '@/types/backend_schema_base';
import type { SubAgentStatusData } from '@/types/chat-store';

interface SimpleChatState {
  messages: Message[];
  subAgentName: string;
  currentSubAgent: string | null;
  subAgentStatus: BackendSubAgentState | string | null;
  subAgentTools: string[];
  subAgentProgress: { current: number; total: number; message?: string } | null;
  subAgentError: string | null;
  subAgentDescription: string | null;
  subAgentExecutionTime: number | null;
  queuedSubAgents: string[];
  isProcessing: boolean;
  activeThreadId: string | null;
  addMessage: (message: Message) => void;
  updateMessage: (messageId: string, updates: Partial<Message>) => void;
  setSubAgentName: (name: string) => void;
  setSubAgentStatus: (status: BackendSubAgentState | SubAgentStatusData) => void;
  setSubAgent: (name: string, status: string) => void;
  setProcessing: (isProcessing: boolean) => void;
  clearMessages: () => void;
  clearSubAgent: () => void;
  setActiveThread: (threadId: string) => void;
  loadThreadMessages: (messages: Message[]) => void;
  loadMessages: (messages: Message[]) => void;
  addError: (error: string) => void;
  addErrorMessage: (error: string) => void;
  reset: () => void;
}

export const useChatStore = create<SimpleChatState>((set) => ({
  messages: [],
  subAgentName: 'Netra Agent',
  currentSubAgent: null,
  subAgentStatus: null,
  subAgentTools: [],
  subAgentProgress: null,
  subAgentError: null,
  subAgentDescription: null,
  subAgentExecutionTime: null,
  queuedSubAgents: [],
  isProcessing: false,
  activeThreadId: null,
  
  addMessage: (message) => set((state) => {
    // Ensure message has a unique ID and it's never an empty string
    const messageWithId = {
      ...message,
      id: (message.id && message.id.trim() !== '') ? message.id : generateUniqueId('msg')
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
  
  setSubAgentStatus: (status) => set((state) => {
    // Handle both SubAgentStatus object and SubAgentStatusData object formats
    if (typeof status === 'object' && status !== null && 'status' in status) {
      // SubAgentStatusData format
      const statusData = status as SubAgentStatusData;
      return {
        subAgentStatus: statusData.status,
        subAgentTools: statusData.tools || [],
        subAgentProgress: statusData.progress || null,
        subAgentError: statusData.error || null,
        subAgentDescription: statusData.description || null,
        subAgentExecutionTime: statusData.executionTime || null
      };
    } else {
      // Simple status or SubAgentStatus object
      return { 
        subAgentStatus: status,
        subAgentTools: [],
        subAgentProgress: null,
        subAgentError: null,
        subAgentDescription: null,
        subAgentExecutionTime: null
      };
    }
  }),
  
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
    subAgentStatus: null,
    subAgentTools: [],
    subAgentProgress: null,
    subAgentError: null,
    subAgentDescription: null,
    subAgentExecutionTime: null,
    queuedSubAgents: []
  }),
  
  setActiveThread: (threadId) => set({ 
    activeThreadId: threadId,
    messages: [] 
  }),
  
  loadThreadMessages: (messages) => set({ 
    messages: messages.map((msg, index) => ({
      ...msg,
      id: (msg.id && msg.id.trim() !== '') ? msg.id : generateUniqueId('msg')
    }))
  }),

  loadMessages: (messages) => set({
    messages: messages.map((msg, index) => {
      const { id: msgId, ...restMsg } = msg;
      return {
        ...restMsg,
        id: (msgId && msgId.trim() !== '') ? msgId : generateUniqueId('msg'),
        type: msg.role === 'user' ? 'user' : 'ai',
        content: msg.content,
        created_at: msg.created_at || new Date().toISOString(),
        displayed_to_user: true
      };
    })
  }),
  
  addError: (error) => set((state) => ({
    messages: [...state.messages, {
      id: generateUniqueId('error'),
      type: 'error' as const,
      content: error,
      created_at: new Date().toISOString(),
      displayed_to_user: true,
      error: error,
    }]
  })),
  
  addErrorMessage: (error) => set((state) => ({
    messages: [...state.messages, {
      id: generateUniqueId('error'),
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
    subAgentTools: [],
    subAgentProgress: null,
    subAgentError: null,
    subAgentDescription: null,
    subAgentExecutionTime: null,
    queuedSubAgents: [],
    isProcessing: false,
    activeThreadId: null 
  }),
}));
