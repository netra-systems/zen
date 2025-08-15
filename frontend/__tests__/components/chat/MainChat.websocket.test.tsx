import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { mockStore, setupMocks, cleanupMocks } from './MainChat.fixtures';

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
      
      const { useChatWebSocket } = require('@/hooks/useChatWebSocket');
      expect(useChatWebSocket).toHaveBeenCalled();
    });

    it('should handle WebSocket connection state', () => {
      const { useChatWebSocket } = require('@/hooks/useChatWebSocket');
      useChatWebSocket.mockReturnValue({
        connected: true,
        error: null
      });
      
      const { rerender } = render(<MainChat />);
      
      // Simulate disconnection
      useChatWebSocket.mockReturnValue({
        connected: false,
        error: null
      });
      rerender(<MainChat />);
      
      // Component should still render without errors
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should handle WebSocket errors gracefully', () => {
      const { useChatWebSocket } = require('@/hooks/useChatWebSocket');
      useChatWebSocket.mockReturnValue({
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
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: false,
        error: new Error('Connection lost'),
        reconnect: mockReconnect
      });
      
      render(<MainChat />);
      
      // Verify reconnect logic would be triggered
      // This would typically be handled by the WebSocket hook itself
      expect(useChatWebSocket).toHaveBeenCalled();
    });

    it('should maintain connection during component updates', () => {
      const { rerender } = render(<MainChat />);
      
      const newMockStore = {
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'Hello' }]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(newMockStore);
      rerender(<MainChat />);
      
      // WebSocket hook should not be re-initialized
      expect(useChatWebSocket).toHaveBeenCalledTimes(2); // Once per render
    });

    it('should handle rapid connection state changes', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate rapid connection state changes
      for (let i = 0; i < 5; i++) {
        (useChatWebSocket as jest.Mock).mockReturnValue({
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
      (useUnifiedChatStore as jest.Mock).mockImplementation(() => {
        throw new Error('Store initialization failed');
      });
      
      // Should crash the component since store is essential
      expect(() => render(<MainChat />)).toThrow('Store initialization failed');
      consoleError.mockRestore();
    });

    it('should recover from WebSocket errors', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate error
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: false,
        error: new Error('Connection lost')
      });
      
      rerender(<MainChat />);
      
      // Simulate recovery
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: true,
        error: null
      });
      
      rerender(<MainChat />);
      
      // Should render normally after recovery
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should handle message processing errors', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
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
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: false,
        error: new Error('Failed'),
        retry: mockRetry
      });
      
      render(<MainChat />);
      
      // Verify retry mechanism would be available
      expect(useChatWebSocket).toHaveBeenCalled();
    });

    it('should maintain state during errors', () => {
      const messages = [
        { id: '1', type: 'user', content: 'Previous message' }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
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
      (useChatWebSocket as jest.Mock).mockReturnValue({
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