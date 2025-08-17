import type { StateCreator } from 'zustand';
import type { ChatMessage } from '@/types/chat';
import type { MessageState } from './types';

export const createMessageSlice: StateCreator<
  MessageState,
  [],
  [],
  MessageState
> = (set) => ({
  messages: [],

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  clearMessages: () => set({
    messages: []
  }),

  loadMessages: (messages) => set({
    messages
  })
});