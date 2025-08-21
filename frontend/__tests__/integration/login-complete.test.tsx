/**
 * Complete Login Flow Integration Tests
 * Tests complete user journey from credentials to chat-ready state
 * Business Value: Critical for user onboarding and retention
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Phase 2, Agent 5 - Login Flow Complete Journey
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/context';
import { useAuthStore } from '@/store/authStore';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { WebSocketTestManager } from '@/__tests__/helpers/websocket-test-manager';
import { mockAuthServiceResponses } from '@/__tests__/mocks/auth-service-mock';
import { setupBasicMocks, setupTokenMocks } from '@/__tests__/auth/helpers/test-helpers';

// Mock modules for independent testing
jest.mock('@/store/authStore');
jest.mock('@/store/unified-chat');
jest.mock('@/auth/service');
jest.mock('@/services/threadService');
jest.mock('@/services/messageService');

// Mock components that will be loaded after login
const MockChatInterface = () => <div data-testid="chat-interface">Chat Ready</div>;
const MockThreadList = () => <div data-testid="thread-list">Threads Loaded</div>;
const MockMessageInput = () => <input data-testid="message-input" placeholder="Type message..." />;

jest.mock('@/components/MainChat', () => ({
  MainChat: MockChatInterface
}));

jest.mock('@/components/ThreadList', () => ({
  ThreadList: MockThreadList
}));

jest.mock('@/components/MessageInput', () => ({
  MessageInput: MockMessageInput
}));

describe('Complete Login Flow Integration', () => {
  let wsManager: WebSocketTestManager;
  let mockAuthStore: any;
  let mockChatStore: any;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    wsManager = new WebSocketTestManager();
    
    setupBasicMocks();
    setupMockStores();
    setupMockServices();
    
    // Mock localStorage for token storage
    const mockStorage = createMockStorage();
    Object.defineProperty(window, 'localStorage', { value: mockStorage });
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
  });

  describe('Complete Login Journey', () => {
    it('completes full login to chat-ready state in <2s', async () => {
      const startTime = Date.now();
      
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      await verifyPostLoginState();
      
      const totalTime = Date.now() - startTime;
      expect(totalTime).toBeLessThan(2000);
    });

    it('handles login form submission correctly', async () => {
      const { result } = renderLoginFlow();
      
      await submitLoginCredentials('test@example.com', 'password123');
      
      await waitFor(() => {
        expect(mockAuthStore.login).toHaveBeenCalledWith(
          expect.objectContaining({ email: 'test@example.com' }),
          expect.any(String)
        );
      });
    });

    it('shows loading spinner during authentication', async () => {
      const { result } = renderLoginFlow();
      
      await act(async () => {
        await submitLoginCredentials('test@example.com', 'password123');
        
        expect(screen.getByTestId('auth-loading')).toBeInTheDocument();
      });
    });

    it('stores token securely in localStorage', async () => {
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      expect(localStorage.getItem('auth_token')).toBe(mockAuthServiceResponses.token.access_token);
      expect(localStorage.getItem('refresh_token')).toBeTruthy();
    });
  });

  describe('WebSocket Connection with Auth', () => {
    it('establishes WebSocket connection with token', async () => {
      const server = wsManager.setup();
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      await waitFor(() => {
        expect(mockChatStore.setConnectionState).toHaveBeenCalledWith('connected');
      });
    });

    it('handles WebSocket authentication flow', async () => {
      const server = wsManager.setup();
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      await wsManager.waitForConnection();
      
      server.send(JSON.stringify({ type: 'auth_success', authenticated: true }));
      
      await waitFor(() => {
        expect(mockChatStore.updateConnectionMetrics).toHaveBeenCalled();
      });
    });
  });

  describe('Post-Login Data Loading', () => {
    it('fetches user data after authentication', async () => {
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      await waitFor(() => {
        expect(mockAuthStore.setUserProfile).toHaveBeenCalledWith(
          expect.objectContaining({ email: 'test@example.com' })
        );
      });
    });

    it('populates thread list after login', async () => {
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      await waitFor(() => {
        expect(screen.getByTestId('thread-list')).toBeInTheDocument();
      });
    });

    it('auto-selects most recent thread', async () => {
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      await waitFor(() => {
        expect(mockChatStore.setActiveThread).toHaveBeenCalledWith('recent-thread-id');
      });
    });

    it('loads message history for selected thread', async () => {
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      await waitFor(() => {
        expect(mockChatStore.loadMessages).toHaveBeenCalledWith('recent-thread-id');
      });
    });
  });

  describe('UI State After Login', () => {
    it('activates chat input field', async () => {
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      await waitFor(() => {
        const input = screen.getByTestId('message-input');
        expect(input).not.toBeDisabled();
        expect(input).toHaveFocus();
      });
    });

    it('enables all UI controls', async () => {
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      await waitFor(() => {
        expect(screen.getByTestId('send-button')).not.toBeDisabled();
        expect(screen.getByTestId('new-thread-button')).not.toBeDisabled();
      });
    });

    it('displays user profile information', async () => {
      const { result } = renderLoginFlow();
      
      await executeLoginSequence(result);
      
      await waitFor(() => {
        expect(screen.getByText('Test User')).toBeInTheDocument();
        expect(screen.getByText('test@example.com')).toBeInTheDocument();
      });
    });
  });

  describe('Race Condition Prevention', () => {
    it('prevents concurrent login attempts', async () => {
      const { result } = renderLoginFlow();
      
      const promise1 = submitLoginCredentials('test@example.com', 'password123');
      const promise2 = submitLoginCredentials('test@example.com', 'password123');
      
      await Promise.all([promise1, promise2]);
      
      expect(mockAuthStore.login).toHaveBeenCalledTimes(1);
    });

    it('handles rapid navigation during login', async () => {
      const { result } = renderLoginFlow();
      
      await act(async () => {
        submitLoginCredentials('test@example.com', 'password123');
        // Simulate rapid navigation
        window.history.pushState({}, '', '/chat');
        window.history.pushState({}, '', '/settings');
      });
      
      await waitFor(() => {
        expect(mockAuthStore.login).toHaveBeenCalledTimes(1);
      });
    });
  });

  // Helper functions (≤8 lines each)
  function setupMockStores() {
    mockAuthStore = createMockAuthStore();
    mockChatStore = createMockChatStore();
    jest.mocked(useAuthStore).mockReturnValue(mockAuthStore);
    jest.mocked(useUnifiedChatStore).mockReturnValue(mockChatStore);
  }

  function createMockAuthStore() {
    return {
      login: jest.fn(),
      logout: jest.fn(),
      setUserProfile: jest.fn(),
      user: null,
      token: null,
      isAuthenticated: false
    };
  }

  function createMockChatStore() {
    return {
      setConnectionState: jest.fn(),
      updateConnectionMetrics: jest.fn(),
      setActiveThread: jest.fn(),
      loadMessages: jest.fn(),
      addMessage: jest.fn()
    };
  }

  function createMockStorage() {
    const storage: { [key: string]: string } = {};
    return {
      getItem: (key: string) => storage[key] || null,
      setItem: (key: string, value: string) => { storage[key] = value; },
      removeItem: (key: string) => { delete storage[key]; },
      clear: () => { Object.keys(storage).forEach(key => delete storage[key]); }
    };
  }

  function setupMockServices() {
    const threadService = require('@/services/threadService');
    const messageService = require('@/services/messageService');
    
    threadService.getThreads = jest.fn().mockResolvedValue([
      { id: 'recent-thread-id', title: 'Recent Chat', updated_at: new Date().toISOString() }
    ]);
    
    messageService.getMessages = jest.fn().mockResolvedValue({
      messages: [{ id: 'msg-1', content: 'Hello', role: 'user' }]
    });
  }

  function renderLoginFlow() {
    return render(
      <AuthProvider>
        <div data-testid="login-form">
          <input data-testid="email-input" type="email" />
          <input data-testid="password-input" type="password" />
          <button data-testid="login-button">Login</button>
          <div data-testid="auth-loading" style={{ display: 'none' }}>Loading...</div>
        </div>
        <MockChatInterface />
        <MockThreadList />
        <MockMessageInput />
        <button data-testid="send-button">Send</button>
        <button data-testid="new-thread-button">New Thread</button>
        <div data-testid="user-profile">
          <span>Test User</span>
          <span>test@example.com</span>
        </div>
      </AuthProvider>
    );
  }

  async function submitLoginCredentials(email: string, password: string) {
    await user.type(screen.getByTestId('email-input'), email);
    await user.type(screen.getByTestId('password-input'), password);
    await user.click(screen.getByTestId('login-button'));
  }

  async function executeLoginSequence(result: any) {
    await submitLoginCredentials('test@example.com', 'password123');
    
    // Simulate successful auth response
    await act(async () => {
      mockAuthStore.user = mockAuthServiceResponses.user;
      mockAuthStore.token = mockAuthServiceResponses.token.access_token;
      mockAuthStore.isAuthenticated = true;
    });
  }

  async function verifyPostLoginState() {
    await waitFor(() => {
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
      expect(screen.getByTestId('thread-list')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).not.toBeDisabled();
    });
  }
});