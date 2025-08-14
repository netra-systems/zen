import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { Message } from '@/types/chat';

type AgentStatus = 'IDLE' | 'RUNNING' | 'COMPLETED' | 'ERROR';

interface SubAgentStatusData {
  status: string;
  tools?: string[];
  progress?: {
    current: number;
    total: number;
    message?: string;
  };
  error?: string;
  description?: string;
  executionTime?: number;
}

interface ChatState {
  messages: Message[];
  currentRunId: string | null;
  agentStatus: AgentStatus;
  agentProgress: number;
  isProcessing: boolean;
  currentSubAgent: string | null;
  subAgentName: string | null;
  subAgentStatus: string | null;
  subAgentTools: string[];
  subAgentProgress: { current: number; total: number; message?: string } | null;
  subAgentError: string | null;
  subAgentDescription: string | null;
  subAgentExecutionTime: number | null;
  queuedSubAgents: string[];
  
  // Actions
  addMessage: (message: Message) => void;
  updateAgentStatus: (status: AgentStatus, progress?: number) => void;
  setCurrentRunId: (runId: string | null) => void;
  setProcessing: (isProcessing: boolean) => void;
  setCurrentSubAgent: (subAgent: string | null) => void;
  setSubAgentName: (name: string | null) => void;
  setSubAgentStatus: (statusData: SubAgentStatusData | null) => void;
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
    subAgentName: null,
    subAgentStatus: null,
    subAgentTools: [],
    subAgentProgress: null,
    subAgentError: null,
    subAgentDescription: null,
    subAgentExecutionTime: null,
    queuedSubAgents: [],

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

    setSubAgentName: (name) =>
      set((state) => {
        state.subAgentName = name;
        // Also update currentSubAgent for backward compatibility
        state.currentSubAgent = name;
      }),

    setSubAgentStatus: (statusData) =>
      set((state) => {
        if (statusData) {
          state.subAgentStatus = statusData.status;
          state.subAgentTools = statusData.tools || [];
          state.subAgentProgress = statusData.progress || null;
          state.subAgentError = statusData.error || null;
          state.subAgentDescription = statusData.description || null;
          state.subAgentExecutionTime = statusData.executionTime || null;
        } else {
          // Clear all sub-agent status fields
          state.subAgentStatus = null;
          state.subAgentTools = [];
          state.subAgentProgress = null;
          state.subAgentError = null;
          state.subAgentDescription = null;
          state.subAgentExecutionTime = null;
        }
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
        state.subAgentName = null;
        state.subAgentStatus = null;
        state.subAgentTools = [];
        state.subAgentProgress = null;
        state.subAgentError = null;
        state.subAgentDescription = null;
        state.subAgentExecutionTime = null;
        state.queuedSubAgents = [];
      }),
  }))
);