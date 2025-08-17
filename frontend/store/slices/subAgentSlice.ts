import type { StateCreator } from 'zustand';
import type { SubAgentUIState } from './types';

export const createSubAgentSlice: StateCreator<
  SubAgentUIState,
  [],
  [],
  SubAgentUIState
> = (set, get) => ({
  subAgentName: null,
  subAgentStatus: null,
  subAgentTools: [],
  subAgentProgress: null,
  subAgentError: null,
  subAgentDescription: null,
  subAgentExecutionTime: null,
  queuedSubAgents: [],

  setSubAgentName: (name) => set({
    subAgentName: name
  }),

  setSubAgentStatus: (statusData) => set({
    subAgentStatus: statusData?.status || null,
    subAgentTools: statusData?.tools || [],
    subAgentProgress: statusData?.progress || null,
    subAgentError: statusData?.error || null,
    subAgentDescription: statusData?.description || null,
    subAgentExecutionTime: statusData?.executionTime || null
  })
});