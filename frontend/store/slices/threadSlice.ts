import type { StateCreator } from 'zustand';
import type { ThreadState } from './types';

export const createThreadSlice: StateCreator<
  ThreadState,
  [],
  [],
  ThreadState
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