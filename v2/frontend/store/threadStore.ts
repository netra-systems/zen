import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface Thread {
  id: string;
  title?: string;
  created_at: number;
  updated_at?: number;
  metadata?: any;
  message_count?: number;
}

interface ThreadState {
  threads: Thread[];
  currentThreadId: string | null;
  currentThread: Thread | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  setThreads: (threads: Thread[]) => void;
  addThread: (thread: Thread) => void;
  updateThread: (threadId: string, updates: Partial<Thread>) => void;
  deleteThread: (threadId: string) => void;
  setCurrentThread: (threadId: string) => void;
  clearCurrentThread: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useThreadStore = create<ThreadState>()(
  immer((set) => ({
    threads: [],
    currentThreadId: null,
    currentThread: null,
    loading: false,
    error: null,

    setThreads: (threads) =>
      set((state) => {
        state.threads = threads;
      }),

    addThread: (thread) =>
      set((state) => {
        state.threads.push(thread);
      }),

    updateThread: (threadId, updates) =>
      set((state) => {
        const threadIndex = state.threads.findIndex((t) => t.id === threadId);
        if (threadIndex !== -1) {
          state.threads[threadIndex] = {
            ...state.threads[threadIndex],
            ...updates,
            updated_at: Date.now(),
          };
          
          // Update current thread if it's the one being updated
          if (state.currentThreadId === threadId) {
            state.currentThread = state.threads[threadIndex];
          }
        }
      }),

    deleteThread: (threadId) =>
      set((state) => {
        state.threads = state.threads.filter((t) => t.id !== threadId);
        if (state.currentThreadId === threadId) {
          state.currentThreadId = null;
          state.currentThread = null;
        }
      }),

    setCurrentThread: (threadId) =>
      set((state) => {
        const thread = state.threads.find((t) => t.id === threadId);
        state.currentThreadId = threadId;
        state.currentThread = thread || null;
      }),

    clearCurrentThread: () =>
      set((state) => {
        state.currentThreadId = null;
        state.currentThread = null;
      }),

    setLoading: (loading) =>
      set((state) => {
        state.loading = loading;
      }),

    setError: (error) =>
      set((state) => {
        state.error = error;
      }),

    reset: () =>
      set((state) => {
        state.threads = [];
        state.currentThreadId = null;
        state.currentThread = null;
        state.loading = false;
        state.error = null;
      }),
  }))
);