import React from 'react';
import { render } from '@testing-library/react';
import { TestProviders } from '../../test-utils/providers';

// Mock dependencies with dynamic jest.Mock functions - DEFINE FIRST
const mockUseUnifiedChatStore = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseEventProcessor = jest.fn();
const mockUseThreadNavigation = jest.fn();

// Mock the modules
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: mockUseEventProcessor
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

// Export mock functions for test control
export { 
  mockUseUnifiedChatStore, 
  mockUseWebSocket, 
  mockUseLoadingState, 
  mockUseEventProcessor,
  mockUseThreadNavigation
};

// Export default mock store data for test use
export const mockStore = {
  isProcessing: false,
  messages: [],
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  currentRunId: null,
  activeThreadId: null,
  isThreadLoading: false,
  handleWebSocketEvent: jest.fn(),
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  updateLayerData: jest.fn(),
};
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => <div data-testid="chat-header">Chat Header</div>
}));
jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => <div data-testid="message-list">Message List</div>
}));
jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => <div data-testid="message-input">Message Input</div>
}));
jest.mock('@/components/chat/PersistentResponseCard', () => ({
  PersistentResponseCard: ({ isCollapsed, onToggleCollapse }: any) => (
    <div data-testid="response-card" data-collapsed={isCollapsed}>
      <button onClick={onToggleCollapse}>Toggle</button>
      Response Card
    </div>
  )
}));
jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>
}));
jest.mock('@/components/chat/OverflowPanel', () => ({
  OverflowPanel: () => <div data-testid="overflow-panel">Overflow Panel</div>
}));
jest.mock('@/components/chat/EventDiagnosticsPanel', () => ({
  EventDiagnosticsPanel: () => <div data-testid="event-diagnostics">Event Diagnostics</div>
}));

// Mock framer-motion to avoid animation issues
jest.mock('framer-motion', () => ({
  motion: {
    div: 'div',
  },
  AnimatePresence: ({ children }: any) => children,
}));

// Common test setup function
export const setupMocks = () => {
  // Clear all mocks first
  jest.clearAllMocks();
  
  // Mock fetch for config
  global.fetch = jest.fn().mockResolvedValue({
    json: jest.fn().mockResolvedValue({
      ws_url: 'ws://localhost:8000/ws'
    })
  });

  // Set up fresh default mock return values for each test
  mockUseUnifiedChatStore.mockReturnValue({
    isProcessing: false,
    messages: [],
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    currentRunId: null,
    activeThreadId: null,
    isThreadLoading: false,
    handleWebSocketEvent: jest.fn(),
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    clearMessages: jest.fn(),
    updateLayerData: jest.fn(),
  });
  
  mockUseWebSocket.mockReturnValue({
    messages: [],
    connected: true,
    error: null
  });
  
  mockUseLoadingState.mockReturnValue({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: ''
  });
  
  mockUseEventProcessor.mockReturnValue({
    processedEvents: [],
    isProcessing: false,
    stats: { processed: 0, failed: 0 }
  });
  
  mockUseThreadNavigation.mockReturnValue({
    currentThreadId: null,
    isNavigating: false,
    navigateToThread: jest.fn(),
    createNewThread: jest.fn()
  });

  jest.useFakeTimers();
};

// Common cleanup function
export const cleanupMocks = () => {
  jest.useRealTimers();
};