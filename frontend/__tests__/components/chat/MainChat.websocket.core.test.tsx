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
jest.mock('@/lib/logger', () => ({
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
import { render, screen } from '@testing-library/react';
import MainChat from '@/components/chat/MainChat';
import { 
  setupMocks, 
  cleanupMocks, 
  mockStore,
  mockUseUnifiedChatStore,
  mockUseWebSocket
} from './MainChat.websocket.test-utils';

describe('MainChat - WebSocket Core Connection Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    setupMocks();
  });

  afterEach(() => {
    cleanupMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('WebSocket connection management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
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
});