/**
 * Ultra focused test to trace exactly where WebSocketProvider status is being set
 */

import React from 'react';
import { render } from '@testing-library/react';
import { WebSocketProvider, useWebSocketContext } from '../../providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';

// Mock webSocketService with detailed tracing
const mockWebSocketService = {
  connect: jest.fn((...args) => {
    console.log('🔥 webSocketService.connect called with:', args);
  }),
  updateToken: jest.fn(),
  disconnect: jest.fn(),
  sendMessage: jest.fn(),
  getSecureUrl: jest.fn((url) => url),
  onStatusChange: null,
  onMessage: null,
  getState: jest.fn(() => 'disconnected'),
  saveSessionState: jest.fn(),
};

jest.mock('../../services/webSocketService', () => ({
  webSocketService: mockWebSocketService
}));

// Mock other dependencies
jest.mock('@/lib/unified-auth-service');
jest.mock('@/config', () => ({ config: { apiUrl: 'http://localhost:8000', wsUrl: 'ws://localhost:8000/ws' } }));
jest.mock('../../services/reconciliation', () => ({ reconciliationService: { addOptimisticMessage: jest.fn((msg) => ({ ...msg, tempId: 'temp_123' })), processConfirmation: jest.fn((msg) => msg), getStats: jest.fn(() => ({})) } }));
jest.mock('../../services/chatStatePersistence', () => ({ chatStatePersistence: { getRestorableState: jest.fn(() => null), updateThread: jest.fn(), updateMessages: jest.fn(), destroy: jest.fn() } }));
jest.mock('@/lib/logger', () => ({ logger: { debug: jest.fn((...args) => console.log('🐛 LOGGER DEBUG:', ...args)), info: jest.fn(), warn: jest.fn(), error: jest.fn() } }));

// Track all status changes
let statusHistory: string[] = [];

const StatusTracker = () => {
  const context = useWebSocketContext();
  console.log('📊 STATUS CHANGE:', context.status);
  statusHistory.push(context.status);
  return <div data-testid="status">{context.status}</div>;
};

describe('WebSocketProvider Status Debugging', () => {
  beforeEach(() => {
    statusHistory = [];
    jest.clearAllMocks();
    
    // Reset global auth mock
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
    
    // Clear the onStatusChange to ensure we see when it gets set
    mockWebSocketService.onStatusChange = null;
  });

  it('should trace exactly where status OPEN comes from', () => {
    console.log('🚀 Starting status trace test...');
    
    const authContext = {
      token: null,
      initialized: false,
      user: null,
    };

    // Mock the handleStatusChange to see when it's called
    const originalHandleStatusChange = mockWebSocketService.onStatusChange;
    
    render(
      <AuthContext.Provider value={authContext}>
        <WebSocketProvider>
          <StatusTracker />
        </WebSocketProvider>
      </AuthContext.Provider>
    );

    console.log('📈 Status history:', statusHistory);
    console.log('🔌 onStatusChange set to:', mockWebSocketService.onStatusChange);
    console.log('⚡ webSocketService.connect called:', mockWebSocketService.connect.mock.calls.length);
    
    // This test exists just to trace what's happening
    console.log('🎯 Expected CLOSED, got:', statusHistory[statusHistory.length - 1]);
  });
});