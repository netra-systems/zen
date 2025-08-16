import type { StateCreator } from 'zustand';
import type { AgentTrackingState, AgentExecution } from './types';

export const createAgentTrackingSlice: StateCreator<
  AgentTrackingState,
  [],
  [],
  AgentTrackingState
> = (set) => ({
  executedAgents: new Map<string, AgentExecution>(),
  agentIterations: new Map<string, number>(),
  isProcessing: false,
  currentRunId: null,

  setProcessing: (isProcessing) => set({ isProcessing })
});