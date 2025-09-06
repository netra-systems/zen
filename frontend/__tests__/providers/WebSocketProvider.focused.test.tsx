/**
 * Very focused test to understand WebSocketProvider status behavior
 */

import React from 'react';
import { render } from '@testing-library/react';
// Use proper import paths for mocking
import { WebSocketProvider, useWebSocketContext } from '../../providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';

// Mock all dependencies to isolate the issue
const mockConnect = jest.fn();

jest.mock('../../services/webSocketService', () => ({
  webSocketService: {
    connect: mockConnect,
    updateToken: jest.fn().mockResolvedValue(undefined),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    getSecureUrl: jest.fn((url) => url),
    onStatusChange: null,
    onMessage: null,
    getState: jest.fn(() => 'disconnected'),
    saveSessionState: jest.fn(),
  }
}));

jest.mock('@/lib/unified-auth-service', () => ({
  unifiedAuthService: {
    getWebSocketAuthConfig: jest.fn(() => ({
      refreshToken: jest.fn().mockResolvedValue('refreshed_token')
    }))
  }
}));

jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws'
  }
}));

jest.mock('../../services/reconciliation', () => ({
  reconciliationService: {
    addOptimisticMessage: jest.fn((msg) => ({ ...msg, tempId: 'temp_123' })),
    processConfirmation: jest.fn((msg) => msg),
    getStats: jest.fn(() => ({}))
  }
}));

jest.mock('../../services/chatStatePersistence', () => ({
  chatStatePersistence: {
    getRestorableState: jest.fn(() => null),
    updateThread: jest.fn(),
    updateMessages: jest.fn(),
    destroy: jest.fn()
  }
}));

jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn((...args) => console.log('LOGGER DEBUG:', ...args)),
    info: jest.fn((...args) => console.log('LOGGER INFO:', ...args)),
    warn: jest.fn((...args) => console.log('LOGGER WARN:', ...args)),
    error: jest.fn((...args) => console.log('LOGGER ERROR:', ...args)),
  }
}));

// Simple test component
const StatusDisplay = () => {
  const context = useWebSocketContext();
  return <div data-testid="status">{context.status}</div>;
};

describe('WebSocketProvider Status Investigation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set global auth mock state to unauthenticated
    (global as any).mockAuthState = {
      token: null,
      initialized: false,
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,
      authConfig: {},
      login: jest.fn(),
      logout: jest.fn()
    };
  });

  it('should start with CLOSED status and never change without connection', () => {
    console.log('=== Starting status test ===');
    
    const authContext = {
      token: null,
      initialized: false,
      user: null,
    };

    const { container } = render(
      <AuthContext.Provider value={authContext}>
        <WebSocketProvider>
          <StatusDisplay />
        </WebSocketProvider>
      </AuthContext.Provider>
    );

    const statusElement = container.querySelector('[data-testid="status"]');
    console.log('Initial status:', statusElement?.textContent);

    // With no auth and no connection, status should be CLOSED
    expect(statusElement?.textContent).toBe('CLOSED');
    expect(mockConnect).not.toHaveBeenCalled();
  });
});