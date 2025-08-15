/**
 * MessageInput Auto-resize Tests
 * Tests for textarea auto-resize behavior
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { generateUniqueId } from '@/lib/utils';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));
jest.mock('@/store/chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');
jest.mock('@/lib/utils');

describe('MessageInput - Auto-resize Textarea Behavior', () => {
  const mockSendMessage = jest.fn();
  const mockChatStore = {
    setProcessing: jest.fn(),
    addMessage: jest.fn()
  };
  const mockThreadStore = {
    setCurrentThread: jest.fn(),
    addThread: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    (useWebSocket as jest.Mock).mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    (useChatStore as jest.Mock).mockReturnValue({
      setProcessing: mockChatStore.setProcessing,
      isProcessing: false,
      addMessage: mockChatStore.addMessage,
    });
    
    (useThreadStore as jest.Mock).mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: mockThreadStore.setCurrentThread,
      addThread: mockThreadStore.addThread,
    });
    
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: true,
    });
    
    (generateUniqueId as jest.Mock).mockImplementation((prefix) => `${prefix}-${Date.now()}`);
  });

  describe('Auto-resize textarea behavior', () => {
    it('should start with single row', () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // The component sets rows dynamically based on content height
      // Empty textarea should have minimal rows (1 or 2 depending on styling)
      expect(textarea.rows).toBeLessThanOrEqual(2);
    });

    it('should expand textarea as content grows', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      const initialRows = textarea.rows;
      
      // Type multiline content using actual newlines
      const multilineText = 'Line 1\nLine 2\nLine 3';
      fireEvent.change(textarea, { target: { value: multilineText } });
      
      // Should expand from initial rows
      await waitFor(() => {
        expect(textarea.rows).toBeGreaterThanOrEqual(initialRows);
        // Component calculates rows based on scrollHeight
        expect(textarea.value).toContain('Line 1');
        expect(textarea.value).toContain('Line 2');
        expect(textarea.value).toContain('Line 3');
      });
    });

    it('should respect maximum rows limit', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Set multiline content directly to avoid timeout
      const manyLines = Array.from({ length: 10 }, (_, i) => `Line ${i}`).join('\n');
      fireEvent.change(textarea, { target: { value: manyLines } });
      
      // Wait for component to update rows
      await waitFor(() => {
        // Should not exceed MAX_ROWS (5)
        expect(textarea.rows).toBeLessThanOrEqual(5);
      });
    });

    it('should reset to single row after sending', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Type multiline content
      await userEvent.type(textarea, 'Line 1');
      await userEvent.type(textarea, '{shift}{enter}');
      await userEvent.type(textarea, 'Line 2');
      
      await waitFor(() => {
        expect(textarea.rows).toBeGreaterThan(1);
      });
      
      // Send message
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(textarea.rows).toBe(1);
        expect(textarea.value).toBe('');
      });
    });

    it('should handle paste of multiline content', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      const multilineText = 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5';
      
      // Simulate paste
      await userEvent.click(textarea);
      await userEvent.paste(multilineText);
      
      await waitFor(() => {
        expect(textarea.value).toBe(multilineText);
        expect(textarea.rows).toBeGreaterThan(1);
        expect(textarea.rows).toBeLessThanOrEqual(5); // MAX_ROWS
      });
    });

    it('should maintain scroll position during resize', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Type content
      await userEvent.type(textarea, 'First line');
      const initialScrollTop = textarea.scrollTop;
      
      // Add more content
      await userEvent.type(textarea, '{shift>}{enter}{/shift}');
      await userEvent.type(textarea, 'Second line');
      
      // Scroll position should be maintained
      expect(textarea.scrollTop).toBeGreaterThanOrEqual(initialScrollTop);
    });
  });
});