import React from 'react';

export interface AdminCommand {
  command: string;
  description: string;
  icon: React.ReactNode;
  category: 'corpus' | 'synthetic' | 'users' | 'config' | 'logs';
  template?: string;
}

export interface AdminTemplate {
  name: string;
  category: string;
  template: string;
  icon: React.ReactNode;
}

export interface MessageInputState {
  message: string;
  rows: number;
  isSending: boolean;
  messageHistory: string[];
  historyIndex: number;
}

export interface CommandPaletteState {
  showCommandPalette: boolean;
  showTemplates: boolean;
  selectedCommandIndex: number;
  filteredCommands: AdminCommand[];
}

export interface MessageHistoryActions {
  addToHistory: (message: string) => void;
  navigateHistory: (direction: 'up' | 'down') => string;
  resetHistory: () => void;
}

export interface MessageSendingParams {
  message: string;
  activeThreadId: string | null;
  currentThreadId: string | null;
  isAuthenticated: boolean;
}

export const MESSAGE_INPUT_CONSTANTS = {
  MAX_ROWS: 5,
  CHAR_LIMIT: 10000,
  LINE_HEIGHT: 24,
  MIN_HEIGHT: 48,
} as const;

// Re-export consolidated types from single source of truth
export type { MessageRole, ChatMessage } from '@/types/chat';