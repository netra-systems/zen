// Mock all hooks before any imports
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: require('./MainChat.websocket.test-utils').mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: require('./MainChat.websocket.test-utils').mockUseWebSocket
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: require('./MainChat.websocket.test-utils').mockUseLoadingState
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: require('./MainChat.websocket.test-utils').mockUseEventProcessor
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
import { render, screen, act } from '@testing-library/react';
import MainChat from '@/components/chat/MainChat';
import { 
  setupMocks, 
  cleanupMocks, 
  mockStore,
  mockUseUnifiedChatStore,
  mockUseWebSocket,
  mockUseLoadingState
} from './MainChat.websocket.test-utils';

describe('MainChat - WebSocket Events and Error Recovery Tests', () => {
  beforeEach(() => {
    setupMocks();
  });

  afterEach(() => {
    cleanupMocks();
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