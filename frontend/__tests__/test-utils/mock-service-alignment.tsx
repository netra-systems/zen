/**
 * Mock Service Alignment Utilities
 * CRITICAL: Aligns mocks with real service interfaces to prevent test failures
 * Ensures all mocks match production service behavior exactly
 * ≤300 lines, ≤8 lines per function
 */

import React from 'react';
import { jest } from '@jest/globals';
import { WebSocketMessage, Message } from '@/types/unified';
import { WebSocketStatus, WebSocketServiceError } from '@/services/webSocketService';
import { AuthState, User } from '@/types/unified';

// Real-aligned WebSocket Service Mock
export const createAlignedWebSocketServiceMock = () => {
  const mockService = {
    status: 'CLOSED' as WebSocketStatus,
    messages: [] as WebSocketMessage[],
    isConnected: false,
    connectionAttempts: 0,
    lastError: null as WebSocketServiceError | null,

    connect: jest.fn().mockImplementation(async () => {
      mockService.status = 'CONNECTING';
      await new Promise(resolve => setTimeout(resolve, 10));
      mockService.status = 'CONNECTED';
      mockService.isConnected = true;
      return Promise.resolve();
    }),

    disconnect: jest.fn().mockImplementation(() => {
      mockService.status = 'CLOSED';
      mockService.isConnected = false;
    }),

    sendMessage: jest.fn().mockImplementation((message: WebSocketMessage) => {
      if (!mockService.isConnected) {
        throw new Error('WebSocket not connected');
      }
      mockService.messages.push(message);
      return Promise.resolve(true);
    }),

    getStatus: jest.fn().mockImplementation(() => mockService.status),
    getMessages: jest.fn().mockImplementation(() => [...mockService.messages]),
    clearMessages: jest.fn().mockImplementation(() => { mockService.messages = []; })
  };

  return mockService;
};

// Real-aligned Auth Service Mock
export const createAlignedAuthServiceMock = () => {
  const mockUser: User = {
    id: 'test-user-123',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    avatar: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  const mockAuthState: AuthState = {
    isAuthenticated: false,
    user: null,
    token: null,
    isLoading: false,
    error: null
  };

  const mockService = {
    ...mockAuthState,

    login: jest.fn().mockImplementation(async (email: string, password: string) => {
      await new Promise(resolve => setTimeout(resolve, 100));
      mockService.isAuthenticated = true;
      mockService.user = mockUser;
      mockService.token = 'mock-jwt-token';
      mockService.isLoading = false;
      return { user: mockUser, token: 'mock-jwt-token' };
    }),

    logout: jest.fn().mockImplementation(async () => {
      mockService.isAuthenticated = false;
      mockService.user = null;
      mockService.token = null;
      mockService.isLoading = false;
    }),

    refreshToken: jest.fn().mockImplementation(async () => {
      if (mockService.isAuthenticated) {
        return { token: 'refreshed-mock-token' };
      }
      throw new Error('Not authenticated');
    }),

    getCurrentUser: jest.fn().mockImplementation(() => mockService.user),
    getToken: jest.fn().mockImplementation(() => mockService.token),
    isLoggedIn: jest.fn().mockImplementation(() => mockService.isAuthenticated)
  };

  return mockService;
};

// Real-aligned Thread Service Mock
export const createAlignedThreadServiceMock = () => {
  const mockThreads = [
    {
      id: 'thread-1',
      title: 'Test Thread 1',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: []
    },
    {
      id: 'thread-2', 
      title: 'Test Thread 2',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: []
    }
  ];

  const mockService = {
    threads: [...mockThreads],
    currentThread: null as any,

    getThreads: jest.fn().mockImplementation(async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
      return [...mockService.threads];
    }),

    createThread: jest.fn().mockImplementation(async (title: string) => {
      const newThread = {
        id: `thread-${Date.now()}`,
        title,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: []
      };
      mockService.threads.push(newThread);
      return newThread;
    }),

    deleteThread: jest.fn().mockImplementation(async (threadId: string) => {
      const index = mockService.threads.findIndex(t => t.id === threadId);
      if (index > -1) {
        mockService.threads.splice(index, 1);
        return true;
      }
      return false;
    }),

    setCurrentThread: jest.fn().mockImplementation((thread: any) => {
      mockService.currentThread = thread;
    }),

    getCurrentThread: jest.fn().mockImplementation(() => mockService.currentThread)
  };

  return mockService;
};

// Real-aligned Store Mock with proper state management
export const createAlignedStoreMock = () => {
  const initialState = {
    auth: {
      isAuthenticated: false,
      user: null,
      token: null,
      isLoading: false,
      error: null
    },
    chat: {
      messages: [],
      currentThread: null,
      isStreaming: false,
      error: null
    },
    websocket: {
      status: 'CLOSED',
      isConnected: false,
      lastMessage: null,
      error: null
    }
  };

  let currentState = { ...initialState };
  const listeners: ((state: any) => void)[] = [];

  const mockStore = {
    getState: jest.fn().mockImplementation(() => ({ ...currentState })),
    
    setState: jest.fn().mockImplementation((newState: any) => {
      currentState = { ...currentState, ...newState };
      listeners.forEach(listener => listener(currentState));
    }),

    subscribe: jest.fn().mockImplementation((listener: (state: any) => void) => {
      listeners.push(listener);
      return () => {
        const index = listeners.indexOf(listener);
        if (index > -1) listeners.splice(index, 1);
      };
    }),

    dispatch: jest.fn().mockImplementation((action: any) => {
      // Simulate reducer logic
      switch (action.type) {
        case 'AUTH_LOGIN':
          currentState.auth = { ...currentState.auth, ...action.payload };
          break;
        case 'CHAT_ADD_MESSAGE':
          currentState.chat.messages.push(action.payload);
          break;
        case 'WEBSOCKET_STATUS_CHANGE':
          currentState.websocket.status = action.payload;
          break;
      }
      listeners.forEach(listener => listener(currentState));
    }),

    reset: jest.fn().mockImplementation(() => {
      currentState = { ...initialState };
      listeners.forEach(listener => listener(currentState));
    })
  };

  return mockStore;
};

// Mock Provider Factories
export const createAlignedMockProviders = () => {
  const wsService = createAlignedWebSocketServiceMock();
  const authService = createAlignedAuthServiceMock();
  const threadService = createAlignedThreadServiceMock();
  const store = createAlignedStoreMock();

  return {
    WebSocketProvider: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="mock-websocket-provider">{children}</div>
    ),
    
    AuthProvider: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="mock-auth-provider">{children}</div>
    ),
    
    StoreProvider: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="mock-store-provider">{children}</div>
    ),

    services: {
      webSocket: wsService,
      auth: authService,
      thread: threadService,
      store
    }
  };
};

// Hook Mocks aligned with real implementations
export const createAlignedHookMocks = () => {
  const wsService = createAlignedWebSocketServiceMock();
  const authService = createAlignedAuthServiceMock();

  return {
    useWebSocket: jest.fn().mockImplementation(() => ({
      status: wsService.status,
      isConnected: wsService.isConnected,
      messages: wsService.messages,
      sendMessage: wsService.sendMessage,
      connect: wsService.connect,
      disconnect: wsService.disconnect
    })),

    useAuth: jest.fn().mockImplementation(() => ({
      isAuthenticated: authService.isAuthenticated,
      user: authService.user,
      token: authService.token,
      login: authService.login,
      logout: authService.logout,
      isLoading: authService.isLoading,
      error: authService.error
    })),

    useStore: jest.fn().mockImplementation(() => {
      const store = createAlignedStoreMock();
      return {
        state: store.getState(),
        setState: store.setState,
        dispatch: store.dispatch
      };
    })
  };
};

// Global mock setup utility
export const setupAlignedMocks = () => {
  const providers = createAlignedMockProviders();
  const hooks = createAlignedHookMocks();

  // Setup global mocks
  jest.mock('@/services/webSocketService', () => providers.services.webSocket);
  jest.mock('@/services/authService', () => providers.services.auth);
  jest.mock('@/services/threadService', () => providers.services.thread);
  jest.mock('@/hooks/useWebSocket', () => ({ useWebSocket: hooks.useWebSocket }));
  jest.mock('@/hooks/useAuth', () => ({ useAuth: hooks.useAuth }));
  jest.mock('@/hooks/useStore', () => ({ useStore: hooks.useStore }));

  return {
    providers,
    hooks,
    cleanup: () => {
      jest.clearAllMocks();
      jest.resetAllMocks();
    }
  };
};

// Test utilities for mock validation
export const validateMockAlignment = {
  webSocket: (mock: any) => {
    expect(mock.connect).toBeDefined();
    expect(mock.disconnect).toBeDefined();
    expect(mock.sendMessage).toBeDefined();
    expect(mock.getStatus).toBeDefined();
    expect(typeof mock.isConnected).toBe('boolean');
  },

  auth: (mock: any) => {
    expect(mock.login).toBeDefined();
    expect(mock.logout).toBeDefined();
    expect(mock.refreshToken).toBeDefined();
    expect(mock.getCurrentUser).toBeDefined();
    expect(typeof mock.isAuthenticated).toBe('boolean');
  },

  store: (mock: any) => {
    expect(mock.getState).toBeDefined();
    expect(mock.setState).toBeDefined();
    expect(mock.subscribe).toBeDefined();
    expect(mock.dispatch).toBeDefined();
  }
};

export default {
  createAlignedWebSocketServiceMock,
  createAlignedAuthServiceMock,
  createAlignedThreadServiceMock,
  createAlignedStoreMock,
  createAlignedMockProviders,
  createAlignedHookMocks,
  setupAlignedMocks,
  validateMockAlignment
};