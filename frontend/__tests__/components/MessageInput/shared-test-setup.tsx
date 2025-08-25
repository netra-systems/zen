/**
 * Shared test setup for MessageInput component tests
 * Provides centralized mocking and utilities for consistent testing
 * 
 * BVJ: Reduces test maintenance overhead and ensures consistent test patterns.
 */

import React from 'react';
import { jest } from '@jest/globals';

// Mock utility modules with proper implementations
const mockUtils = {
  getPlaceholder: jest.fn((isAuth, isProc, msgLen) => {
    if (!isAuth) return 'Please sign in to send messages';
    if (isProc) return 'Agent is thinking...';
    if (msgLen > 9000) return `${10000 - msgLen} characters remaining`;
    return 'Start typing your AI optimization request... (Shift+Enter for new line)';
  }),
  getTextareaClassName: jest.fn(() => 'w-full resize-none rounded-2xl px-4 py-3 pr-12 bg-gray-50 border border-gray-200 focus:bg-white focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all duration-200 ease-in-out placeholder:text-gray-400 text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed'),
  getCharCountClassName: jest.fn(() => 'text-xs text-gray-500 absolute bottom-2 right-2'),
  shouldShowCharCount: jest.fn((len) => len > 8000),
  isMessageDisabled: jest.fn((isProc, isAuth, isSend) => isProc || !isAuth || isSend),
  canSendMessage: jest.fn((isDis, msg, len) => !isDis && !!msg.trim() && len <= 10000)
};

jest.mock('@/components/chat/utils/messageInputUtils', () => mockUtils);

jest.mock('@/components/chat/types', () => ({
  MESSAGE_INPUT_CONSTANTS: {
    MAX_ROWS: 5,
    CHAR_LIMIT: 10000,
    LINE_HEIGHT: 24
  }
}));

// Hook mocks
export const mockUseUnifiedChatStore = jest.fn();
export const mockUseThreadStore = jest.fn();
export const mockUseAuthStore = jest.fn();
export const mockUseMessageHistory = jest.fn();
export const mockUseTextareaResize = jest.fn();
export const mockUseMessageSending = jest.fn();

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: mockUseThreadStore
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: mockUseMessageHistory
}));

jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: mockUseTextareaResize
}));

jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: mockUseMessageSending
}));

// Component mocks
jest.mock('@/components/chat/components/MessageActionButtons', () => ({
  MessageActionButtons: ({ isDisabled, canSend, isSending, onSend }: any) => 
    React.createElement('div', {}, [
      React.createElement('button', {
        key: 'send',
        'data-testid': 'send-button',
        disabled: isDisabled || !canSend || isSending,
        onClick: onSend
      }, isSending ? 'Sending...' : 'Send'),
      React.createElement('button', {
        key: 'emoji',
        'data-testid': 'emoji-button'
      }, '😀'),
      React.createElement('button', {
        key: 'file',
        'data-testid': 'file-button'
      }, '📎')
    ])
}));

jest.mock('@/components/chat/components/KeyboardShortcutsHint', () => ({
  KeyboardShortcutsHint: ({ isAuthenticated, hasMessage }: any) => 
    React.createElement('div', {
      'data-testid': 'keyboard-hint'
    }, isAuthenticated && hasMessage ? 'Enter to send, Shift+Enter for new line' : 'Sign in to send')
}));

// Default mock setup
export const setupMessageInputMocks = () => {
  mockUseUnifiedChatStore.mockReturnValue({
    activeThreadId: 'thread-1',
    isProcessing: false
  });

  mockUseThreadStore.mockReturnValue({
    currentThreadId: 'thread-1'
  });

  mockUseAuthStore.mockReturnValue({
    isAuthenticated: true
  });

  mockUseMessageHistory.mockReturnValue({
    messageHistory: [],
    addToHistory: jest.fn(),
    navigateHistory: jest.fn(() => '')
  });

  mockUseTextareaResize.mockReturnValue({
    rows: 1
  });

  mockUseMessageSending.mockReturnValue({
    isSending: false,
    handleSend: jest.fn()
  });
};

// Consolidated mock hooks export
export const mockHooks = {
  mockUseUnifiedChatStore,
  mockUseThreadStore,
  mockUseAuthStore,
  mockUseMessageHistory,
  mockUseTextareaResize,
  mockUseMessageSending
};

// Mobile viewport simulation
export const simulateMobileViewport = () => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: 375,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: 667,
  });
  window.dispatchEvent(new Event('resize'));
};

// Reset viewport
export const resetViewport = () => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: 1024,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: 768,
  });
};

// Performance testing utility
export const measurePerformance = async (operation: () => Promise<void>) => {
  const startTime = performance.now();
  await operation();
  const endTime = performance.now();
  return endTime - startTime;
};

// Create mock clipboard data
export const createMockClipboardData = (data: { [key: string]: string }, types: string[]) => ({
  getData: jest.fn((type: string) => data[type] || ''),
  types
});