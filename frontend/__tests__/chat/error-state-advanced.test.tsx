/**
 * Error Handling, State Management & Advanced UI Tests
 * ==================================================== 
 * Modular UI tests for error handling, state sync, and advanced features
 * Tests 20-23 (Error Handling), Tests 24-27 (State Management), Tests 28-30 (Advanced UI)
 * Complex UI behavior and edge case testing
 */

import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import shared utilities and test components
import {
  setupDefaultMocks,
  cleanupMocks,
  createChatStoreMock,
  createThreadStoreMock,
  createTestMessage,
  screen,
  fireEvent,
  userEvent,
  expectElementByText,
  expectElementByTestId,
  expectElementByRole
} from './ui-test-utilities';

// Import shared mock configurations
import { mockModuleConfigs } from './ui-test-utilities';

// Setup all mocks
mockModuleConfigs.authStore();
mockModuleConfigs.chatStore();
mockModuleConfigs.threadStore();
mockModuleConfigs.webSocket();

// Import components after mocks
import { ThreadSidebar } from '../../components/chat/ThreadSidebar';
import { MessageInput } from '../../components/chat/MessageInput';
import { MessageList } from '../../components/chat/MessageList';
import { MessageItem } from '../../components/chat/MessageItem';
import { ChatHeader } from '../../components/chat/ChatHeader';
import { useChatStore } from '../../store/chatStore';
import { useThreadStore } from '../../store/threadStore';

describe('Error Handling, State Management & Advanced UI Tests', () => {
  
  beforeEach(() => {
    setupDefaultMocks();
  });

  afterEach(() => {
    cleanupMocks();
  });

  // ============================================
  // Error Handling Tests (Tests 20-23)
  // ============================================
  describe('Error Handling', () => {
    
    test('20. Should display error message', () => {
      const mockThreadStore = createThreadStoreMock({
        error: new Error('Failed to load threads'),
        threads: []
      });
      
      (useThreadStore as jest.Mock).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      expectElementByText(/Failed to load threads/i).toBeInTheDocument();
    });

    test('21. Should show retry button on error', () => {
      const mockThreadStore = createThreadStoreMock({
        error: new Error('Network error'),
        threads: [],
        loadThreads: jest.fn()
      });
      
      (useThreadStore as jest.Mock).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      expectElementByRole('button', { name: /retry/i }).toBeInTheDocument();
    });

    test('22. Should handle rate limit errors', () => {
      const mockChatStore = createChatStoreMock({
        error: { code: 'RATE_LIMIT', message: 'Too many requests' }
      });
      
      (useChatStore as jest.Mock).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      expectElementByText(/Too many requests/i).toBeInTheDocument();
    });

    test('23. Should validate message before sending', async () => {
      const mockSendMessage = jest.fn();
      const mockChatStore = createChatStoreMock({
        sendMessage: mockSendMessage
      });
      
      (useChatStore as jest.Mock).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      // Try to send empty message
      const sendButton = expectElementByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      expect(mockSendMessage).not.toHaveBeenCalled();
    });
  });

  // ============================================
  // State Management Tests (Tests 24-27)
  // ============================================
  describe('State Management', () => {
    
    test('24. Should update message list when new message added', () => {
      const { rerender } = render(<MessageList />);
      
      // Update mock to return messages
      const mockChatStore = createChatStoreMock({
        messages: [createTestMessage({ id: '1', content: 'New message', role: 'user' })]
      });
      
      (useChatStore as jest.Mock).mockReturnValueOnce(mockChatStore);
      rerender(<MessageList />);
      
      expectElementByText('New message').toBeInTheDocument();
    });

    test('25. Should sync thread selection across components', () => {
      const mockThread = { id: '1', title: 'Selected Thread' };
      const mockThreadStore = createThreadStoreMock({
        currentThread: mockThread
      });
      
      (useThreadStore as jest.Mock).mockReturnValue(mockThreadStore);
      render(<ChatHeader />);
      
      expectElementByText('Selected Thread').toBeInTheDocument();
    });

    test('26. Should handle optimistic updates', () => {
      const mockSendMessageOptimistic = jest.fn();
      const mockChatStore = createChatStoreMock({
        sendMessageOptimistic: mockSendMessageOptimistic,
        messages: []
      });
      
      (useChatStore as jest.Mock).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText(/Type your message/i);
      fireEvent.change(input, { target: { value: 'Optimistic message' } });
      
      const sendButton = expectElementByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      
      expect(mockSendMessageOptimistic).toHaveBeenCalledWith(
        expect.objectContaining({ content: 'Optimistic message' })
      );
    });

    test('27. Should clear messages when switching threads', () => {
      const mockClearMessages = jest.fn();
      const mockChatStore = createChatStoreMock({
        clearMessages: mockClearMessages
      });
      
      const mockThreadStore = createThreadStoreMock({
        threads: [{ id: '1' }, { id: '2' }],
        setCurrentThreadId: jest.fn()
      });
      
      (useChatStore as jest.Mock).mockReturnValueOnce(mockChatStore);
      (useThreadStore as jest.Mock).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      // Switch thread
      const thread = expectElementByTestId('thread-2');
      fireEvent.click(thread);
      expect(mockClearMessages).toHaveBeenCalled();
    });
  });

  // ============================================
  // Advanced UI Features Tests (Tests 28-30)
  // ============================================
  describe('Advanced UI Features', () => {
    
    test('28. Should support markdown in messages', () => {
      const markdownMessage = createTestMessage({
        id: '1',
        content: '**Bold text** and *italic text*',
        role: 'assistant'
      });
      
      render(<MessageItem message={markdownMessage} />);
      
      const messageContent = expectElementByTestId('message-content');
      expect(messageContent.innerHTML).toContain('<strong>Bold text</strong>');
      expect(messageContent.innerHTML).toContain('<em>italic text</em>');
    });

    test('29. Should handle keyboard shortcuts', async () => {
      const mockSendMessage = jest.fn();
      const mockChatStore = createChatStoreMock({
        sendMessage: mockSendMessage
      });
      
      (useChatStore as jest.Mock).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText(/Type your message/i);
      await userEvent.type(input, 'Shortcut test');
      
      // Simulate Cmd/Ctrl+Enter
      fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true });
      expect(mockSendMessage).toHaveBeenCalledWith('Shortcut test');
    });

    test('30. Should show message timestamps', () => {
      const message = createTestMessage({
        id: '1',
        content: 'Timed message',
        role: 'user',
        timestamp: '2025-01-01T10:00:00Z'
      });
      
      render(<MessageItem message={message} />);
      expectElementByText(/10:00/).toBeInTheDocument();
    });
  });

  // ============================================
  // Integration Tests
  // ============================================
  describe('Integration Scenarios', () => {
    
    test('Should handle error recovery flow', async () => {
      const mockRetry = jest.fn();
      const mockThreadStore = createThreadStoreMock({
        error: new Error('Connection failed'),
        loadThreads: mockRetry
      });
      
      (useThreadStore as jest.Mock).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      const retryButton = expectElementByRole('button', { name: /retry/i });
      fireEvent.click(retryButton);
      expect(mockRetry).toHaveBeenCalled();
    });

    test('Should maintain state consistency', () => {
      const sharedState = {
        currentThreadId: 'thread-1',
        currentThread: { id: 'thread-1', title: 'Shared Thread' }
      };
      
      const mockThreadStore = createThreadStoreMock(sharedState);
      (useThreadStore as jest.Mock).mockReturnValue(mockThreadStore);
      
      render(<ChatHeader />);
      expectElementByText('Shared Thread').toBeInTheDocument();
    });
  });
});