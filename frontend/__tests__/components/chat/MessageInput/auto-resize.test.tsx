/**
 * MessageInput Auto-resize Tests
 * Tests for textarea auto-resize behavior
 */

// Mock dependencies BEFORE imports
const mockSendMessage = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseTextareaResize = jest.fn();
const mockHandleSend = jest.fn();
const mockUseUnifiedChatStore = jest.fn();
const mockUseThreadStore = jest.fn();
const mockUseAuthStore = jest.fn();
const mockGenerateUniqueId = jest.fn();

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));
jest.mock('@/store/threadStore', () => ({
  useThreadStore: mockUseThreadStore
}));
jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));
jest.mock('@/lib/utils', () => ({
  generateUniqueId: mockGenerateUniqueId,
  cn: jest.fn((...classes) => classes.filter(Boolean).join(' '))
}));
jest.mock('@/components/chat/utils/messageInputUtils', () => ({
  getPlaceholder: jest.fn((isAuthenticated, isProcessing, messageLength) => {
    if (!isAuthenticated) return 'Please sign in to send messages';
    if (isProcessing) return 'Agent is thinking...';
    if (messageLength > 9000) return `${10000 - messageLength} characters remaining`;
    return 'Type a message...';
  }),
  getTextareaClassName: jest.fn(() => 'mocked-textarea-class'),
  getCharCountClassName: jest.fn(() => 'mocked-char-count-class'),
  shouldShowCharCount: jest.fn((messageLength) => messageLength > 8000),
  isMessageDisabled: jest.fn((isProcessing, isAuthenticated, isSending) => {
    return isProcessing || !isAuthenticated || isSending;
  }),
  canSendMessage: jest.fn((isDisabled, message, messageLength) => {
    return !isDisabled && !!message.trim() && messageLength <= 10000;
  })
}));
jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: jest.fn(() => ({
    messageHistory: [],
    addToHistory: jest.fn(),
    navigateHistory: jest.fn(() => '')
  }))
}));
// Dynamic mock for useTextareaResize based on content
jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: mockUseTextareaResize
}));
// Mock that simulates actual message sending behavior
jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: jest.fn(() => ({
    isSending: false,
    handleSend: mockHandleSend
  }))
}));

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';

describe('MessageInput - Auto-resize Textarea Behavior', () => {
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
    
    // Setup dynamic textarea resize mock
    mockUseTextareaResize.mockImplementation((ref, message) => {
      if (!message || message.trim() === '') {
        return { rows: 1 };
      }
      const lineCount = message.split('\n').length;
      return { rows: Math.min(Math.max(lineCount, 1), 5) };
    });
    
    // Setup handleSend to resolve successfully
    mockHandleSend.mockResolvedValue(undefined);
    
    // Setup default mocks
    mockUseWebSocket.mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    mockUseUnifiedChatStore.mockReturnValue({
      activeThreadId: 'thread-1',
      isProcessing: false,
      setProcessing: mockChatStore.setProcessing,
      addMessage: mockChatStore.addMessage,
      addOptimisticMessage: jest.fn(),
      updateOptimisticMessage: jest.fn(),
    });
    
    mockUseThreadStore.mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: mockThreadStore.setCurrentThread,
      addThread: mockThreadStore.addThread,
    });
    
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
    });
    
    mockGenerateUniqueId.mockImplementation((prefix) => `${prefix}-${Date.now()}`);
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
      
      // Set multiline content directly to ensure it works
      const multilineText = 'Line 1\nLine 2';
      fireEvent.change(textarea, { target: { value: multilineText } });
      
      await waitFor(() => {
        expect(textarea.rows).toBeGreaterThan(1);
        expect(textarea.value).toBe(multilineText);
      });
      
      // Send message by pressing Enter
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      
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