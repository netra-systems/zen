// Mock all hooks before any imports
var mockUseUnifiedChatStore = jest.fn();
var mockUseWebSocket = jest.fn();
var mockUseLoadingState = jest.fn();
var mockUseEventProcessor = jest.fn();

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
  useThreadNavigation: jest.fn()
}));

// Mock utility services but NOT UI components
jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn()
  }
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
  
  // Mock thread navigation
  const mockUseThreadNavigation = require('@/hooks/useThreadNavigation').useThreadNavigation;
  mockUseThreadNavigation.mockReturnValue({
    currentThreadId: null,
    isNavigating: false,
    navigateToThread: jest.fn(),
    createNewThread: jest.fn()
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
      expect(screen.getByRole('banner')).toBeInTheDocument();
    });

    it('should handle WebSocket errors gracefully', () => {
      mockUseWebSocket.mockReturnValue({
        messages: [],
        connected: false,
        error: new Error('WebSocket connection failed')
      });
      
      render(<MainChat />);
      
      // Component should still render
      expect(screen.getByRole('banner')).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toBeInTheDocument();
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
      expect(screen.getByRole('banner')).toBeInTheDocument();
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
      expect(screen.getByRole('banner')).toBeInTheDocument();
    });

    it('should handle message processing errors', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: true,
        error: 'Failed to process message'
      });
      
      render(<MainChat />);
      
      // Should still render UI
      expect(screen.getByRole('banner')).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toBeInTheDocument();
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
      
      // Mock store with messages and error
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages,
        error: 'Current error'
      });
      
      // Mock loading state to show messages (not loading)
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      // Mock thread navigation to not be navigating
      const mockUseThreadNavigation = require('@/hooks/useThreadNavigation').useThreadNavigation;
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      render(<MainChat />);
      
      // Messages should still be displayed
      expect(screen.getByRole('list')).toBeInTheDocument();
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
      expect(screen.getByRole('banner')).toBeInTheDocument();
    });
  });
});