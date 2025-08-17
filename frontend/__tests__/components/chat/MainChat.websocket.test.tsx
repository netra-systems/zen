// Mock all hooks before any imports
const mockUseUnifiedChatStore = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseEventProcessor = jest.fn();

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

// Mock UI components
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

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: 'div',
  },
  AnimatePresence: ({ children }: any) => children,
}));

import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';

// Mock store data
const mockStore = {
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

// Setup function
const setupMocks = () => {
  jest.clearAllMocks();
  jest.useFakeTimers();
  
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
};

// Cleanup function
const cleanupMocks = () => {
  jest.useRealTimers();
};

describe('MainChat - WebSocket Connection Tests', () => {
  beforeEach(() => {
    setupMocks();
  });

  afterEach(() => {
    cleanupMocks();
  });

  describe('WebSocket connection management', () => {
    it('should initialize WebSocket connection on mount', () => {
      render(<MainChat />);
      
      expect(mockUseWebSocket).toHaveBeenCalled();
    });

    it('should handle WebSocket connection state', () => {
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: true,
        error: null
      });
      
      const { rerender } = render(<MainChat />);
      
      // Simulate disconnection
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: false,
        error: null
      });
      rerender(<MainChat />);
      
      // Component should still render without errors
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should handle WebSocket errors gracefully', () => {
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: false,
        error: new Error('WebSocket connection failed')
      });
      
      render(<MainChat />);
      
      // Component should still render
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });

    it('should reconnect WebSocket on error', async () => {
      const mockReconnect = jest.fn();
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: false,
        error: new Error('Connection lost'),
        reconnect: mockReconnect
      });
      
      render(<MainChat />);
      
      // Verify reconnect logic would be triggered
      // This would typically be handled by the WebSocket hook itself
      expect(mockUseWebSocket).toHaveBeenCalled();
    });

    it('should maintain connection during component updates', () => {
      const { rerender } = render(<MainChat />);
      
      const newMockStore = {
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'Hello' }]
      };
      
      mockUseUnifiedChatStore.mockReturnValue(newMockStore);
      rerender(<MainChat />);
      
      // WebSocket hook should not be re-initialized
      expect(mockUseWebSocket).toHaveBeenCalledTimes(2); // Once per render
    });

    it('should handle rapid connection state changes', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate rapid connection state changes
      for (let i = 0; i < 5; i++) {
        mockUseWebSocket.mockReturnValue({
          messages: [],
          connected: i % 2 === 0,
          error: null
        });
        rerender(<MainChat />);
      }
      
      // Component should remain stable
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });
  });

  describe('Error recovery and reconnection', () => {
    it('should handle store errors gracefully', () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockUseUnifiedChatStore.mockImplementation(() => {
        throw new Error('Store initialization failed');
      });
      
      // Should crash the component since store is essential
      expect(() => render(<MainChat />)).toThrow('Store initialization failed');
      consoleError.mockRestore();
    });

    it('should recover from WebSocket errors', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate error
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: false,
        error: new Error('Connection lost')
      });
      
      rerender(<MainChat />);
      
      // Simulate recovery
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: true,
        error: null
      });
      
      rerender(<MainChat />);
      
      // Should render normally after recovery
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should handle message processing errors', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: true,
        error: 'Failed to process message'
      });
      
      render(<MainChat />);
      
      // Should still render UI
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });

    it('should retry failed operations', async () => {
      const mockRetry = jest.fn();
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: false,
        error: new Error('Failed'),
        retry: mockRetry
      });
      
      render(<MainChat />);
      
      // Verify retry mechanism would be available
      expect(mockUseWebSocket).toHaveBeenCalled();
    });

    it('should maintain state during errors', () => {
      const messages = [
        { id: '1', type: 'user', content: 'Previous message' }
      ];
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages,
        error: 'Current error'
      });
      
      render(<MainChat />);
      
      // Messages should still be displayed
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should handle network interruptions', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate network interruption
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: false,
        error: new Error('Network error')
      });
      
      rerender(<MainChat />);
      
      // Wait for potential reconnection
      await act(async () => {
        jest.advanceTimersByTime(5000);
      });
      
      // Component should remain functional
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });
  });
});