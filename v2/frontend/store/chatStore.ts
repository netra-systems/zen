import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { Message } from '@/types/chat';

type AgentStatus = 'IDLE' | 'RUNNING' | 'COMPLETED' | 'ERROR';

interface ChatState {
  messages: Message[];
  currentRunId: string | null;
  agentStatus: AgentStatus;
  agentProgress: number;
  isProcessing: boolean;
  currentSubAgent: string | null;
  
  // Actions
  addMessage: (message: any) => void;
  updateAgentStatus: (status: AgentStatus, progress?: number) => void;
  setCurrentRunId: (runId: string | null) => void;
  setProcessing: (isProcessing: boolean) => void;
  setCurrentSubAgent: (subAgent: string | null) => void;
  clearMessages: () => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>()(
  immer((set) => ({
    messages: [],
    currentRunId: null,
    agentStatus: 'IDLE',
    agentProgress: 0,
    isProcessing: false,
    currentSubAgent: null,

    addMessage: (message) =>
      set((state) => {
        state.messages.push(message);
        if (message.runId) {
          state.currentRunId = message.runId;
        }
      }),

    updateAgentStatus: (status, progress) =>
      set((state) => {
        state.agentStatus = status;
        if (progress !== undefined) {
          state.agentProgress = progress;
        }
      }),

    setCurrentRunId: (runId) =>
      set((state) => {
        state.currentRunId = runId;
      }),

    setProcessing: (isProcessing) =>
      set((state) => {
        state.isProcessing = isProcessing;
      }),

    setCurrentSubAgent: (subAgent) =>
      set((state) => {
        state.currentSubAgent = subAgent;
      }),

    clearMessages: () =>
      set((state) => {
        state.messages = [];
      }),

    reset: () =>
      set((state) => {
        state.messages = [];
        state.currentRunId = null;
        state.agentStatus = 'IDLE';
        state.agentProgress = 0;
        state.isProcessing = false;
        state.currentSubAgent = null;
      }),
  }))
);