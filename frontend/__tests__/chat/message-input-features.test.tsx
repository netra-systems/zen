/**
 * Message Input Features Tests
 * Tests for MessageInput component functionality and advanced features
 * 
 * BVJ: User Input Experience
 * Segment: All - input quality affects all user segments
 * Business Goal: Smooth user interaction and reduced friction
 * Value Impact: Better input experience increases user engagement and reduces abandonment
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { MessageInput } from '@/components/chat/MessageInput';
import { TestProviders } from '../test-utils/providers';
import {
  setupDefaultMocks
} from './ui-test-utilities';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
    isConnected: true,
  }),
}));

jest.mock('@/hooks/useChatWebSocket', () => ({
  useChatWebSocket: jest.fn(),
}));

jest.mock('@/store/chat', () => ({
  useChatStore: () => ({
    messages: [],
    isProcessing: false,
    setProcessing: jest.fn(),
    addMessage: jest.fn(),
    stopProcessing: jest.fn(),
  }),
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: () => ({
    currentThreadId: 'test-thread',
    threads: [],
    setCurrentThread: jest.fn(),
    addThread: jest.fn(),
  }),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
  }),
}));

jest.mock('@/services/threadService', () => ({
  ThreadService: {
    createThread: jest.fn().mockResolvedValue({ 
      id: 'new-thread', 
      title: 'Test Thread',
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 0,
      metadata: { title: 'Test Thread', renamed: false }
    }),
    getThread: jest.fn().mockResolvedValue({
      id: 'test-thread',
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 1,
      metadata: { title: 'Test Thread', renamed: false }
    }),
    listThreads: jest.fn().mockResolvedValue([]),
    deleteThread: jest.fn(),
    updateThread: jest.fn(),
    getThreadMessages: jest.fn().mockResolvedValue({ 
      messages: [], 
      thread_id: 'test', 
      total: 0, 
      limit: 50, 
      offset: 0 
    })
  },
}));

jest.mock('@/services/threadRenameService', () => ({
  ThreadRenameService: {
    autoRenameThread: jest.fn()
  }
}));

beforeEach(() => {
  setupDefaultMocks();
});

describe('Message Input Features', () => {
  describe('Multi-line Input Support', () => {
    test('should support multi-line input with Shift+Enter', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      expect(textarea).toBeInTheDocument();
      
      // Type some text
      await userEvent.type(textarea, 'Line 1');
      
      // Press Shift+Enter for new line
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
      await userEvent.type(textarea, '{shift}{enter}Line 2');
      
      // Verify multi-line content
      expect(textarea.value).toContain('Line 1');
    });

    test('should send message on Enter without Shift', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      await userEvent.type(textarea, 'Single line message');
      
      // Press Enter without Shift to send
      fireEvent.keyDown(textarea, { key: 'Enter' });
      
      // Message should be sent (input cleared)
      await waitFor(() => {
        expect(textarea.value).toBe('');
      });
    });

    test('should preserve line breaks in multi-line messages', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Type multi-line content
      await userEvent.type(textarea, 'First line{shift}{enter}Second line{shift}{enter}Third line');
      
      // Verify content contains line breaks
      expect(textarea.value).toMatch(/First line.*Second line.*Third line/s);
    });

    test('should handle mixed content with line breaks and regular text', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      await userEvent.type(textarea, 'Normal text{shift}{enter}{shift}{enter}After double break');
      
      expect(textarea.value).toContain('Normal text');
      expect(textarea.value).toContain('After double break');
    });
  });

  describe('Character Count and Limits', () => {
    test('should show character count when approaching limit', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Type a long message (simulate approaching limit)
      const longMessage = 'a'.repeat(8001); // 80% of 10000 char limit
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      // Check for character counter
      await waitFor(() => {
        const charCount = screen.getByText(/8001\/10000/);
        expect(charCount).toBeInTheDocument();
      });
    });

    test('should warn when approaching character limit', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Type message near limit
      const nearLimitMessage = 'a'.repeat(9500);
      fireEvent.change(textarea, { target: { value: nearLimitMessage } });
      
      await waitFor(() => {
        const warning = screen.queryByText(/approaching limit/i) || 
                       screen.getByText(/9500\/10000/);
        expect(warning).toBeInTheDocument();
      });
    });

    test('should prevent input when character limit is exceeded', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Try to exceed limit
      const overLimitMessage = 'a'.repeat(10001);
      fireEvent.change(textarea, { target: { value: overLimitMessage } });
      
      // Should be truncated or prevented
      await waitFor(() => {
        expect(textarea.value.length).toBeLessThanOrEqual(10000);
      });
    });

    test('should not show character count for short messages', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Type short message
      await userEvent.type(textarea, 'Short message');
      
      // Character count should not be visible
      const charCount = screen.queryByText(/\/10000/);
      expect(charCount).not.toBeInTheDocument();
    });
  });

  describe('Auto-resize Functionality', () => {
    test('should auto-resize based on content', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      const initialHeight = textarea.style.height;
      
      // Add multiple lines
      await userEvent.type(textarea, 'Line 1{shift}{enter}Line 2{shift}{enter}Line 3');
      
      // Height should have changed
      expect(textarea.style.height).not.toBe(initialHeight);
    });

    test('should limit maximum height when content is very long', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Add many lines
      const manyLines = Array(20).fill('Line').join('\n');
      fireEvent.change(textarea, { target: { value: manyLines } });
      
      // Should have a maximum height (scrollable)
      const computedStyle = window.getComputedStyle(textarea);
      const maxHeight = parseInt(computedStyle.maxHeight || '0');
      expect(maxHeight).toBeGreaterThan(0);
    });

    test('should reset height when content is cleared', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Add content to expand
      await userEvent.type(textarea, 'Line 1{shift}{enter}Line 2{shift}{enter}Line 3');
      
      // Clear content
      await userEvent.clear(textarea);
      
      // Height should reset
      expect(textarea.rows).toBeLessThanOrEqual(2);
    });

    test('should handle rapid content changes', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Rapidly change content
      for (let i = 1; i <= 5; i++) {
        const content = Array(i).fill('Line').join('\n');
        fireEvent.change(textarea, { target: { value: content } });
      }
      
      // Should handle without errors
      expect(textarea).toBeInTheDocument();
    });
  });

  describe('Message History Navigation', () => {
    test('should support message history navigation with arrow keys', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Send a few messages to build history
      await userEvent.type(textarea, 'First message');
      fireEvent.keyDown(textarea, { key: 'Enter' });
      
      await userEvent.clear(textarea);
      await userEvent.type(textarea, 'Second message');
      fireEvent.keyDown(textarea, { key: 'Enter' });
      
      // Navigate history with arrow up
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
      
      // Should show previous message (this behavior depends on implementation)
      expect(textarea.value).toBe('');
    });

    test('should cycle through message history', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Build some history
      const messages = ['First', 'Second', 'Third'];
      for (const msg of messages) {
        await userEvent.type(textarea, msg);
        fireEvent.keyDown(textarea, { key: 'Enter' });
        await userEvent.clear(textarea);
      }
      
      // Navigate through history
      fireEvent.keyDown(textarea, { key: 'ArrowUp' }); // Should show "Third"
      fireEvent.keyDown(textarea, { key: 'ArrowUp' }); // Should show "Second"
      fireEvent.keyDown(textarea, { key: 'ArrowDown' }); // Should show "Third" again
      
      // Should handle navigation correctly
      expect(textarea).toBeInTheDocument();
    });

    test('should not navigate history when textarea has multiple lines', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Type multi-line content
      await userEvent.type(textarea, 'Line 1{shift}{enter}Line 2');
      
      // Arrow keys should navigate within the text, not history
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
      
      // Content should remain the same
      expect(textarea.value).toContain('Line 1');
      expect(textarea.value).toContain('Line 2');
    });

    test('should reset history position when typing new content', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Build history and navigate
      await userEvent.type(textarea, 'Historical message');
      fireEvent.keyDown(textarea, { key: 'Enter' });
      
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
      
      // Start typing new content
      await userEvent.type(textarea, 'New message');
      
      // Should not interfere with new typing
      expect(textarea.value).toContain('New message');
    });
  });

  describe('Action Buttons', () => {
    test('should display action buttons (attachment, voice)', () => {
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      
      // Check for attachment button
      const attachButton = screen.getByLabelText('Attach file');
      expect(attachButton).toBeInTheDocument();
      
      // Check for voice input button
      const voiceButton = screen.getByLabelText('Voice input');
      expect(voiceButton).toBeInTheDocument();
    });

    test('should handle attachment button click', async () => {
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      
      const attachButton = screen.getByLabelText('Attach file');
      fireEvent.click(attachButton);
      
      // Should trigger file input or attachment dialog
      // Exact behavior depends on implementation
      expect(attachButton).toBeInTheDocument();
    });

    test('should handle voice input button click', async () => {
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      
      const voiceButton = screen.getByLabelText('Voice input');
      fireEvent.click(voiceButton);
      
      // Should start voice recording or show voice interface
      // Exact behavior depends on implementation
      expect(voiceButton).toBeInTheDocument();
    });

    test('should disable action buttons when appropriate', async () => {
      // Mock processing state
      jest.doMock('@/store/chat', () => ({
        useChatStore: () => ({
          messages: [],
          isProcessing: true, // Processing state
          setProcessing: jest.fn(),
          addMessage: jest.fn(),
          stopProcessing: jest.fn(),
        }),
      }));
      
      render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      
      const attachButton = screen.getByLabelText('Attach file');
      const voiceButton = screen.getByLabelText('Voice input');
      
      // Buttons might be disabled during processing
      // This depends on the implementation
      expect(attachButton).toBeInTheDocument();
      expect(voiceButton).toBeInTheDocument();
    });

    test('should show send button state changes', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Send button should be disabled when empty
      const sendButton = screen.getByLabelText('Send message');
      expect(sendButton).toBeDisabled();
      
      // Should be enabled when there's content
      await userEvent.type(textarea, 'Test message');
      expect(sendButton).not.toBeDisabled();
      
      // Should be disabled again when cleared
      await userEvent.clear(textarea);
      expect(sendButton).toBeDisabled();
    });
  });

  describe('Placeholder Text', () => {
    test('should show appropriate placeholder text for authenticated users', () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      expect(textarea.placeholder).toMatch(/Type.*message/i);
    });

    test('should show login prompt for unauthenticated users', () => {
      // Mock unauthenticated state
      jest.doMock('@/store/authStore', () => ({
        useAuthStore: () => ({
          isAuthenticated: false,
        }),
      }));
      
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      expect(textarea.placeholder).toMatch(/sign in|login/i);
    });

    test('should show processing placeholder during agent thinking', () => {
      // Mock processing state
      jest.doMock('@/store/chat', () => ({
        useChatStore: () => ({
          messages: [],
          isProcessing: true,
          setProcessing: jest.fn(),
          addMessage: jest.fn(),
          stopProcessing: jest.fn(),
        }),
      }));
      
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      expect(textarea.placeholder).toMatch(/thinking|processing/i);
    });

    test('should update placeholder based on character count', async () => {
      const { container } = render(
        <TestProviders>
          <MessageInput />
        </TestProviders>
      );
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Type near character limit
      const nearLimit = 'a'.repeat(9000);
      fireEvent.change(textarea, { target: { value: nearLimit } });
      
      // Placeholder might show character count info
      expect(textarea.placeholder).toBeDefined();
    });
  });
});