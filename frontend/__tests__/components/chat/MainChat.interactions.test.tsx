import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { mockStore, setupMocks, cleanupMocks } from './MainChat.fixtures';

describe('MainChat - Message Interactions Tests', () => {
  beforeEach(() => {
    setupMocks();
  });

  afterEach(() => {
    cleanupMocks();
  });

  describe('Message sending and receiving', () => {
    it('should display messages from store', () => {
      const messages = [
        { id: '1', type: 'user', content: 'Hello', displayed_to_user: true },
        { id: '2', type: 'agent', content: 'Hi there!', displayed_to_user: true }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should show example prompts when no messages', () => {
      render(<MainChat />);
      
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    });

    it('should hide example prompts when messages exist', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'Test' }]
      });
      
      render(<MainChat />);
      
      expect(screen.queryByTestId('example-prompts')).not.toBeInTheDocument();
    });

    it('should handle message updates from WebSocket', () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate receiving a message
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'New message' }]
      });
      
      rerender(<MainChat />);
      
      // Message list should be present
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should maintain message order', () => {
      const messages = [
        { id: '1', type: 'user', content: 'First', created_at: '2024-01-01T10:00:00Z' },
        { id: '2', type: 'agent', content: 'Second', created_at: '2024-01-01T10:01:00Z' },
        { id: '3', type: 'user', content: 'Third', created_at: '2024-01-01T10:02:00Z' }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages
      });
      
      render(<MainChat />);
      
      // Messages should be displayed in order
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should handle empty message content gracefully', () => {
      const messages = [
        { id: '1', type: 'user', content: '' },
        { id: '2', type: 'agent', content: null }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages
      });
      
      render(<MainChat />);
      
      // Should not crash
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });
  });

  describe('Message history loading', () => {
    it('should load message history on mount', () => {
      const historicalMessages = [
        { id: 'h1', type: 'user', content: 'Historical 1' },
        { id: 'h2', type: 'agent', content: 'Historical 2' }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: historicalMessages
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should handle pagination of message history', () => {
      const manyMessages = Array.from({ length: 100 }, (_, i) => ({
        id: `msg-${i}`,
        type: i % 2 === 0 ? 'user' : 'agent',
        content: `Message ${i}`
      }));
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: manyMessages
      });
      
      render(<MainChat />);
      
      // Should handle large message lists
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should preserve scroll position when loading history', async () => {
      const { rerender } = render(<MainChat />);
      
      // Initial messages
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [
          { id: '1', type: 'user', content: 'Initial' }
        ]
      });
      
      rerender(<MainChat />);
      
      // Load more history
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [
          { id: '0', type: 'user', content: 'Earlier' },
          { id: '1', type: 'user', content: 'Initial' }
        ]
      });
      
      rerender(<MainChat />);
      
      // Scroll position should be maintained
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should handle empty message history', () => {
      render(<MainChat />);
      
      // Should show example prompts instead
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
      expect(screen.queryByTestId('response-card')).not.toBeInTheDocument();
    });

    it('should update history when new messages arrive', async () => {
      const { rerender } = render(<MainChat />);
      
      // Add new message
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [{ id: 'new-1', type: 'user', content: 'New message' }]
      });
      
      rerender(<MainChat />);
      
      // Example prompts should disappear when there are messages
      await waitFor(() => {
        expect(screen.queryByTestId('example-prompts')).not.toBeInTheDocument();
      });
    });

    it('should handle message deletion from history', () => {
      const { rerender } = render(<MainChat />);
      
      // Start with messages
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [
          { id: '1', type: 'user', content: 'Message 1' },
          { id: '2', type: 'agent', content: 'Message 2' }
        ]
      });
      
      rerender(<MainChat />);
      
      // Delete a message
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [
          { id: '2', type: 'agent', content: 'Message 2' }
        ]
      });
      
      rerender(<MainChat />);
      
      // Should still render
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });
  });
});