import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
d input functionality
 * Tests 8-11 (Message Display) and Tests 12-15 (Message Input)
 * Core chat messaging experience components
 */

import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import shared utilities and test components
import {
  setupDefaultMocks,
  cleanupMocks,
  createChatStoreMock,
  createTestMessage,
  setupClipboardMock,
  screen,
  fireEvent,
  userEvent,
  expectElementByText,
  expectElementByTestId,
  expectElementByRole
} from './ui-test-utilities';

// Mock stores before importing components
jest.mock('../../store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
    token: 'test-token',
    isAuthenticated: true,
    setUser: jest.fn(),
    setToken: jest.fn(),
    logout: jest.fn(),
    checkAuth: jest.fn()
  }))
}));

jest.mock('../../store/chatStore', () => ({
  useChatStore: jest.fn(() => createChatStoreMock())
}));

jest.mock('../../store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({
    threads: [],
    currentThreadId: null,
    currentThread: null,
    setThreads: jest.fn(),
    setCurrentThread: jest.fn(),
    setCurrentThreadId: jest.fn(),
    addThread: jest.fn(),
    deleteThread: jest.fn(),
    updateThread: jest.fn(),
    loadThreads: jest.fn(),
    setError: jest.fn(),
    error: null
  }))
}));

jest.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => ({
    connectionState: 'connected',
    sendMessage: jest.fn(),
    subscribe: jest.fn(),
    unsubscribe: jest.fn(),
    reconnect: jest.fn(),
    disconnect: jest.fn()
  }))
}));

// Import components after mocks
import { MessageList } from '../../components/chat/MessageList';
import { MessageInput } from '../../components/chat/MessageInput';
import { MessageItem } from '../../components/chat/MessageItem';
import { ThinkingIndicator } from '../../components/chat/ThinkingIndicator';
import { useChatStore } from '../../store/chatStore';

describe('Message Display & Input Tests', () => {
  
    jest.setTimeout(10000);
  
  beforeEach(() => {
    setupDefaultMocks();
  });

  afterEach(() => {
    cleanupMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  // ============================================
  // Message Display Tests (Tests 8-11)
  // ============================================
  describe('Message Display and Interaction', () => {
    
      jest.setTimeout(10000);
    
    test('8. Should display messages in the list', () => {
      const mockMessages = [
        createTestMessage({ 
          id: '1', 
          content: 'Hello', 
          role: 'user', 
          timestamp: '2025-01-01T10:00:00Z' 
        }),
        createTestMessage({ 
          id: '2', 
          content: 'Hi there!', 
          role: 'assistant', 
          timestamp: '2025-01-01T10:01:00Z' 
        })
      ];
      
      const mockChatStore = createChatStoreMock({
        messages: mockMessages
      });
      
      jest.mocked(useChatStore).mockReturnValueOnce(mockChatStore);
      render(<MessageList />);
      
      expectElementByText('Hello');
      expectElementByText('Hi there!');
    });

    test('9. Should display message roles correctly', () => {
      const userMessage = createTestMessage({ 
        id: '1', 
        content: 'User message', 
        role: 'user' 
      });
      const assistantMessage = createTestMessage({ 
        id: '2', 
        content: 'Assistant message', 
        role: 'assistant' 
      });
      
      const { rerender } = render(<MessageItem message={userMessage} />);
      expectElementByTestId('message-user');
      
      rerender(<MessageItem message={assistantMessage} />);
      expectElementByTestId('message-assistant');
    });

    test('10. Should copy message to clipboard', async () => {
      const mockClipboard = setupClipboardMock();
      const message = createTestMessage({ 
        id: '1', 
        content: 'Copy this text', 
        role: 'user' 
      });
      
      render(<MessageItem message={message} />);
      
      const copyButton = expectElementByTestId('copy-message');
      fireEvent.click(copyButton);
      expect(mockClipboard.writeText).toHaveBeenCalledWith('Copy this text');
    });

    test('11. Should show thinking indicator when processing', () => {
      render(<ThinkingIndicator isThinking={true} agent="supervisor" />);
      
      expectElementByTestId('thinking-indicator');
      expectElementByText(/supervisor/i);
    });
  });

  // ============================================
  // Message Input Tests (Tests 12-15)
  // ============================================
  describe('Message Input Functionality', () => {
    
      jest.setTimeout(10000);
    
    test('12. Should handle text input', async () => {
      const user = userEvent.setup();
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText(/start typing your ai optimization request/i);
      await user.type(input, 'Test message');
      expect(input).toHaveValue('Test message');
    });

    test('13. Should send message on button click', async () => {
      const mockSendMessage = jest.fn();
      const mockChatStore = createChatStoreMock({
        sendMessage: mockSendMessage
      });
      
      jest.mocked(useChatStore).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText(/start typing your ai optimization request/i);
      await userEvent.type(input, 'Send this message');
      
      const sendButton = expectElementByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      expect(mockSendMessage).toHaveBeenCalledWith('Send this message');
    });

    test('14. Should clear input after sending', async () => {
      const mockSendMessage = jest.fn();
      const mockChatStore = createChatStoreMock({
        sendMessage: mockSendMessage
      });
      
      jest.mocked(useChatStore).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText(/start typing your ai optimization request/i);
      await userEvent.type(input, 'Message to clear');
      
      const sendButton = expectElementByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      expect(input).toHaveValue('');
    });

    test('15. Should disable input when loading', () => {
      const mockChatStore = createChatStoreMock({
        isLoading: true
      });
      
      jest.mocked(useChatStore).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText(/start typing your ai optimization request/i);
      expect(input).toBeDisabled();
    });
  });

  // ============================================
  // Message & Input Integration Tests
  // ============================================
  describe('Message & Input Integration', () => {
    
      jest.setTimeout(10000);
    
    test('Should handle empty message list', () => {
      const mockChatStore = createChatStoreMock({
        messages: []
      });
      
      jest.mocked(useChatStore).mockReturnValueOnce(mockChatStore);
      render(<MessageList />);
      
      expectElementByText(/No messages yet/i);
    });

    test('Should validate message content before sending', async () => {
      const mockSendMessage = jest.fn();
      const mockChatStore = createChatStoreMock({
        sendMessage: mockSendMessage
      });
      
      jest.mocked(useChatStore).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      // Try to send empty message
      const sendButton = expectElementByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    test('Should handle message timestamps display', () => {
      const message = createTestMessage({
        id: '1',
        content: 'Timed message',
        role: 'user',
        timestamp: '2025-01-01T10:00:00Z'
      });
      
      render(<MessageItem message={message} />);
      expectElementByText(/10:00/);
    });

    test('Should handle optimistic message updates', () => {
      const mockSendMessageOptimistic = jest.fn();
      const mockChatStore = createChatStoreMock({
        sendMessageOptimistic: mockSendMessageOptimistic,
        messages: []
      });
      
      jest.mocked(useChatStore).mockReturnValueOnce(mockChatStore);
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText(/start typing your ai optimization request/i);
      fireEvent.change(input, { target: { value: 'Optimistic message' } });
      
      const sendButton = expectElementByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      
      expect(mockSendMessageOptimistic).toHaveBeenCalledWith(
        expect.objectContaining({ content: 'Optimistic message' })
      );
    });
  });
});