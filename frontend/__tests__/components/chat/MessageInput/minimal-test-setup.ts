/**
 * Minimal MessageInput Test Setup
 * Only mocks external APIs, allows real component behavior
 * BVJ: Reduces test maintenance while ensuring real functionality is tested
 */

import { jest } from '@jest/globals';

// Mock only external WebSocket API
export const mockSendMessage = jest.fn();
export const mockUseWebSocket = jest.fn(() => ({
  sendMessage: mockSendMessage,
}));

// Mock only external stores (these would make HTTP calls)
export const mockChatStore = {
  activeThreadId: 'thread-1',
  isProcessing: false,
  setProcessing: jest.fn(),
  addMessage: jest.fn(),
  addOptimisticMessage: jest.fn(),
  updateOptimisticMessage: jest.fn(),
};

export const mockThreadStore = {
  currentThreadId: 'thread-1',
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
};

export const mockAuthStore = {
  isAuthenticated: true,
};

// Apply minimal mocks
export const setupMinimalMocks = () => {
  jest.doMock('@/hooks/useWebSocket', () => ({
    useWebSocket: mockUseWebSocket
  }));
  
  jest.doMock('@/store/unified-chat', () => ({
    useUnifiedChatStore: jest.fn(() => mockChatStore)
  }));
  
  jest.doMock('@/store/threadStore', () => ({
    useThreadStore: jest.fn(() => mockThreadStore)
  }));
  
  jest.doMock('@/store/authStore', () => ({
    useAuthStore: jest.fn(() => mockAuthStore)
  }));
};

// Reset function
export const resetMocks = () => {
  jest.clearAllMocks();
  mockChatStore.isProcessing = false;
  mockAuthStore.isAuthenticated = true;
};

// Quick overrides for test scenarios
export const setProcessing = (processing: boolean) => {
  mockChatStore.isProcessing = processing;
};

export const setAuthenticated = (auth: boolean) => {
  mockAuthStore.isAuthenticated = auth;
};

export const setThreadId = (id: string) => {
  mockChatStore.activeThreadId = id;
  mockThreadStore.currentThreadId = id;
};