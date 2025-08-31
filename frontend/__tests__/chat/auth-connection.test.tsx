import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
tion flow and WebSocket connection
 * Tests 1-3 (Authentication) and Tests 16-19 (WebSocket Connection)
 * Part of split from chatUIUXCore.test.tsx (570 lines → ≤300 lines)
 */

import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import shared utilities and test components
import {
  setupDefaultMocks,
  cleanupMocks,
  createAuthStoreMock,
  createWebSocketMock,
  screen,
  fireEvent,
  expectElementByText,
  expectElementByTestId,
  expectElementByRole
} from './ui-test-utilities';

// Mock stores before importing components
jest.mock('../../store/authStore', () => ({
  useAuthStore: jest.fn(() => createAuthStoreMock())
}));

jest.mock('../../store/chatStore', () => ({
  useChatStore: jest.fn(() => ({
    messages: [],
    addMessage: jest.fn(),
    clearMessages: jest.fn(),
    sendMessage: jest.fn(),
    sendMessageOptimistic: jest.fn(),
    updateMessage: jest.fn(),
    deleteMessage: jest.fn(),
    setMessages: jest.fn(),
    isLoading: false,
    setLoading: jest.fn()
  }))
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
  useWebSocket: jest.fn(() => createWebSocketMock())
}));

// Import components after mocks
import { ChatHeader } from '../../components/chat/ChatHeader';
import { useAuthStore } from '../../store/authStore';
import { useWebSocket } from '../../hooks/useWebSocket';

describe('Authentication & Connection Tests', () => {
  
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
  // Authentication Flow Tests (Tests 1-3)
  // ============================================
  describe('Authentication Flow', () => {
    
      jest.setTimeout(10000);
    
    test('1. Should display user information when authenticated', () => {
      render(<ChatHeader />);
      expectElementByText('Test User');
    });

    test('2. Should show login prompt when not authenticated', () => {
      const mockAuthStore = createAuthStoreMock({
        user: null,
        token: null,
        isAuthenticated: false
      });
      
      jest.mocked(useAuthStore).mockReturnValueOnce(mockAuthStore);
      render(<ChatHeader />);
      expectElementByText(/Please log in/i);
    });

    test('3. Should handle logout action', async () => {
      const mockLogout = jest.fn();
      const mockAuthStore = createAuthStoreMock({
        user: { name: 'Test User' },
        isAuthenticated: true,
        logout: mockLogout
      });
      
      jest.mocked(useAuthStore).mockReturnValueOnce(mockAuthStore);
      render(<ChatHeader />);
      
      const logoutButton = expectElementByRole('button', { name: /logout/i });
      fireEvent.click(logoutButton);
      expect(mockLogout).toHaveBeenCalled();
    });
  });

  // ============================================
  // WebSocket Connection Tests (Tests 16-19)  
  // ============================================
  describe('WebSocket Connection', () => {
    
      jest.setTimeout(10000);
    
    test('16. Should show connected status', () => {
      const mockWebSocket = createWebSocketMock({
        connectionState: 'connected'
      });
      
      (useWebSocket as jest.Mock).mockReturnValueOnce(mockWebSocket);
      render(<ChatHeader />);
      
      const status = expectElementByTestId('connection-status');
      expect(status).toHaveClass('connected');
    });

    test('17. Should show disconnected status', () => {
      const mockWebSocket = createWebSocketMock({
        connectionState: 'disconnected'
      });
      
      (useWebSocket as jest.Mock).mockReturnValueOnce(mockWebSocket);
      render(<ChatHeader />);
      
      const status = expectElementByTestId('connection-status');
      expect(status).toHaveClass('disconnected');
    });

    test('18. Should handle reconnection', async () => {
      const mockReconnect = jest.fn();
      const mockWebSocket = createWebSocketMock({
        connectionState: 'disconnected',
        reconnect: mockReconnect
      });
      
      (useWebSocket as jest.Mock).mockReturnValueOnce(mockWebSocket);
      render(<ChatHeader />);
      
      const reconnectButton = expectElementByRole('button', { name: /reconnect/i });
      fireEvent.click(reconnectButton);
      expect(mockReconnect).toHaveBeenCalled();
    });

    test('19. Should subscribe to WebSocket events', () => {
      const mockSubscribe = jest.fn();
      const mockWebSocket = createWebSocketMock({
        connectionState: 'connected',
        subscribe: mockSubscribe
      });
      
      (useWebSocket as jest.Mock).mockReturnValueOnce(mockWebSocket);
      
      // Import MessageList here to avoid early import issues
      const { MessageList } = require('../../components/chat/MessageList');
      render(<MessageList />);
      
      expect(mockSubscribe).toHaveBeenCalledWith(
        expect.any(String), 
        expect.any(Function)
      );
    });
  });

  // ============================================
  // Connection State Integration Tests
  // ============================================
  describe('Connection State Integration', () => {
    
      jest.setTimeout(10000);
    
    test('Should sync authentication and connection states', () => {
      const mockAuthStore = createAuthStoreMock({
        isAuthenticated: true,
        user: { name: 'Connected User' }
      });
      
      const mockWebSocket = createWebSocketMock({
        connectionState: 'connected'
      });
      
      jest.mocked(useAuthStore).mockReturnValueOnce(mockAuthStore);
      (useWebSocket as jest.Mock).mockReturnValueOnce(mockWebSocket);
      
      render(<ChatHeader />);
      
      expectElementByText('Connected User');
      const status = expectElementByTestId('connection-status');
      expect(status).toHaveClass('connected');
    });

    test('Should handle unauthenticated with disconnected state', () => {
      const mockAuthStore = createAuthStoreMock({
        isAuthenticated: false,
        user: null
      });
      
      const mockWebSocket = createWebSocketMock({
        connectionState: 'disconnected'
      });
      
      jest.mocked(useAuthStore).mockReturnValueOnce(mockAuthStore);
      (useWebSocket as jest.Mock).mockReturnValueOnce(mockWebSocket);
      
      render(<ChatHeader />);
      
      expectElementByText(/Please log in/i);
      const status = expectElementByTestId('connection-status');
      expect(status).toHaveClass('disconnected');
    });
  });
});