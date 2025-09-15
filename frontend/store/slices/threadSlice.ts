import type { StateCreator } from 'zustand';
import type { ThreadSliceState } from './types';

export const createThreadSlice: StateCreator<
  ThreadSliceState,
  [],
  [],
  ThreadSliceState
> = (set) => ({
  activeThreadId: null,
  threads: new Map(),
  isThreadLoading: false,

  setActiveThread: (threadId) => set({ 
    activeThreadId: threadId 
  }),

  setThreadLoading: (isLoading) => set({
    isThreadLoading: isLoading
  })
});