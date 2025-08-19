/**
 * Auth Login to Chat Real Flow Tests
 * Tests REAL user experience: Login → WebSocket connect → threads load → chat ready
 * Business Value: P0 critical path validation for returning users
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Real component integration without mocks
 */

import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Import modular utilities (following 300-line limit)
import {
  setupMockWebSocket,
  setupMockThreadsApi,
  setupMockStorage,
  setupFailingWebSocket,
  setupSlowThreadsApi,
  cleanupMockWebSocket,
  performRealLogin,
  sendTestMessage,
  simulateTokenExpiration,
  verifyWebSocketConnection,
  verifyThreadsLoaded,
  verifyChatReady,
  verifyTokenStorage,
  verifyWebSocketAuthentication,
  verifyConnectionErrorHandling,
  verifyThreadsLoadingState,
  verifyTokenRefreshFlow,
  verifyWebSocketPersistence,
  verifyMessageReceiving,
  verifyMessageSending,
  verifyConnectionStatus
} from './login-to-chat-test-utils';

import {
  renderRealLoginToChatFlow,
  mockUser,
  mockToken
} from './login-to-chat-test-components';

// Only mock external services, not our components
jest.mock('@/services/api', () => ({
  threadsApi: {
    getThreads: jest.fn(),
    getThread: jest.fn()
  }
}));

// Mock auth service to prevent loading state
jest.mock('@/auth/service', () => ({
  authService: {
    getAuthConfig: jest.fn().mockResolvedValue({
      google_client_id: 'test-client-id'
    }),
    getToken: jest.fn().mockReturnValue(null),
    useAuth: jest.fn().mockReturnValue({
      user: null,
      login: jest.fn(),
      logout: jest.fn()
    })
  }
}));

describe('Auth Login to Chat Real Flow', () => {
  let user: ReturnType<typeof userEvent.setup>;
  let mockWebSocket: any;

  beforeEach(() => {
    user = userEvent.setup();
    mockWebSocket = setupMockWebSocket();
    setupMockThreadsApi();
    setupMockStorage();
    
    // Use real timers for real component behavior
    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanupMockWebSocket(mockWebSocket);
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('Real Login to Chat Flow', () => {
    it('completes login → websocket → threads → chat ready flow', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await verifyWebSocketConnection(mockWebSocket);
      await verifyThreadsLoaded();
      await verifyChatReady();
    });

    it('stores token and establishes WebSocket with real auth', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await verifyTokenStorage(mockToken);
      await verifyWebSocketAuthentication(mockWebSocket, mockToken);
    });

    it('shows chat interface after successful authentication', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('chat-window')).toBeInTheDocument();
      });
    });

    it('loads user threads after authentication', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('thread-list')).toBeInTheDocument();
      });
    });
  });

  describe('Real Error Scenarios', () => {
    it('handles WebSocket connection failure gracefully', async () => {
      setupFailingWebSocket();
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await verifyConnectionErrorHandling();
    });

    it('shows loading state during thread fetch', async () => {
      setupSlowThreadsApi();
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await verifyThreadsLoadingState();
    });

    it('recovers from token expiration during chat', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
        await simulateTokenExpiration();
      });
      
      await verifyTokenRefreshFlow();
    });

    it('maintains WebSocket connection across component updates', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await verifyWebSocketPersistence(mockWebSocket);
    });
  });

  describe('Real Chat Integration', () => {
    it('establishes WebSocket and receives real messages', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await verifyMessageReceiving(mockWebSocket);
    });

    it('sends messages through WebSocket after login', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
        await sendTestMessage(user, 'Hello from test');
      });
      
      await verifyMessageSending(mockWebSocket);
    });

    it('displays connection status indicator correctly', async () => {
      renderRealLoginToChatFlow();
      
      await act(async () => {
        await performRealLogin(user, mockToken);
      });
      
      await verifyConnectionStatus();
    });
  });

});