import React from 'react';
import { render } from '@testing-library/react';
import { TestProviders } from '../../test-utils/providers';

// Mock dependencies with implementations
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => ({
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
  })
}));

// Export mock store data for test use
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
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    messages: [],
    connected: true,
    error: null
  })
}));
jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => ({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: true,
    loadingMessage: ''
  })
}));
jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: () => ({
    processedEvents: [],
    isProcessing: false,
    stats: { processed: 0, failed: 0 }
  })
}));
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
  // Mock fetch for config
  global.fetch = jest.fn().mockResolvedValue({
    json: jest.fn().mockResolvedValue({
      ws_url: 'ws://localhost:8000/ws'
    })
  });

  jest.clearAllMocks();
  jest.useFakeTimers();
};

// Common cleanup function
export const cleanupMocks = () => {
  jest.useRealTimers();
};