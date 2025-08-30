/**
 * MainChat WebSocket Test Utils
 * Mock implementations for WebSocket-related testing
 */

import { jest } from '@jest/globals';

// Mock WebSocket connection state
export const mockWebSocketState = {
  isConnected: true,
  isConnecting: false,
  connectionStatus: 'connected' as const,
  lastError: null,
  reconnectCount: 0
};

// Mock unified chat store
export const mockUseUnifiedChatStore = jest.fn(() => ({
  // Chat state
  messages: [],
  isProcessing: false,
  activeThreadId: 'test-thread-1',
  isThreadLoading: false,
  
  // Fast layer data
  fastLayerData: {
    agentName: 'TestAgent',
    status: 'idle'
  },
  
  // Actions
  addMessage: jest.fn(),
  updateMessage: jest.fn(),
  setProcessing: jest.fn(),
  setActiveThread: jest.fn(),
  
  // WebSocket state
  ...mockWebSocketState
}));

// Mock WebSocket hook
export const mockUseWebSocket = jest.fn(() => ({
  sendMessage: jest.fn(),
  isConnected: mockWebSocketState.isConnected,
  isConnecting: mockWebSocketState.isConnecting,
  connectionStatus: mockWebSocketState.connectionStatus,
  lastError: mockWebSocketState.lastError,
  reconnectCount: mockWebSocketState.reconnectCount,
  connect: jest.fn(),
  disconnect: jest.fn(),
  reconnect: jest.fn()
}));

// Mock loading state
export const mockUseLoadingState = jest.fn(() => ({
  loadingState: 'idle',
  shouldShowLoading: false,
  shouldShowEmptyState: false,
  shouldShowExamplePrompts: true,
  loadingMessage: '',
  isInitialized: true,
  setLoadingState: jest.fn()
}));

// Mock event processor
export const mockUseEventProcessor = jest.fn(() => ({
  processEvent: jest.fn(),
  isProcessing: false,
  lastEventId: null,
  eventQueue: [],
  clearQueue: jest.fn()
}));

// Utility functions to update mock state
export const updateWebSocketState = (newState: Partial<typeof mockWebSocketState>) => {
  Object.assign(mockWebSocketState, newState);
};

export const resetAllMocks = () => {
  jest.clearAllMocks();
  updateWebSocketState({
    isConnected: true,
    isConnecting: false,
    connectionStatus: 'connected',
    lastError: null,
    reconnectCount: 0
  });
};