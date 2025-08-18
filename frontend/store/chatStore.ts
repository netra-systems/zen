import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { Message } from '@/types/registry';
import type { SubAgentStatusData } from '@/types/chat-store';
import { LegacyAgentStatus } from '@/types/agent-types';

// Keep legacy status for store compatibility during migration
type AgentStatus = LegacyAgentStatus;

interface ImmerChatState {
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

export const useChatStore = create<ImmerChatState>()(
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
          updateSubAgentFields(state, statusData);
        } else {
          clearSubAgentFields(state);
        }
      }),

    clearMessages: () =>
      set((state) => {
        state.messages = [];
      }),

    reset: () =>
      set((state) => {
        resetChatMessages(state);
        resetAgentState(state);
        clearSubAgentFields(state);
      }),
  }))
);

// Helper functions for state updates (≤8 lines each)
const updateSubAgentFields = (state: any, statusData: SubAgentStatusData): void => {
  state.subAgentStatus = statusData.status;
  state.subAgentTools = statusData.tools || [];
  state.subAgentProgress = statusData.progress || null;
  state.subAgentError = statusData.error || null;
  state.subAgentDescription = statusData.description || null;
  state.subAgentExecutionTime = statusData.executionTime || null;
};

const clearSubAgentFields = (state: any): void => {
  state.subAgentStatus = null;
  state.subAgentTools = [];
  state.subAgentProgress = null;
  state.subAgentError = null;
  state.subAgentDescription = null;
  state.subAgentExecutionTime = null;
};

const resetChatMessages = (state: any): void => {
  state.messages = [];
  state.currentRunId = null;
  state.queuedSubAgents = [];
};

const resetAgentState = (state: any): void => {
  state.agentStatus = 'IDLE';
  state.agentProgress = 0;
  state.isProcessing = false;
  state.currentSubAgent = null;
  state.subAgentName = null;
};