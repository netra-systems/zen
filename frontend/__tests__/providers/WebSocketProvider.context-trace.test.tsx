/**
 * Test to trace exactly what useWebSocketContext returns and when
 */

import React, { useEffect, useState } from 'react';
import { render } from '@testing-library/react';
import { WebSocketProvider, useWebSocketContext } from '../../providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';

// Mock all dependencies minimally
jest.mock('../../services/webSocketService', () => ({
  webSocketService: {
    connect: jest.fn(),
    updateToken: jest.fn(),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    getSecureUrl: jest.fn((url) => url),
    onStatusChange: null,
    onMessage: null,
    getState: jest.fn(() => 'disconnected'),
    saveSessionState: jest.fn(),
  }
}));

jest.mock('@/lib/unified-auth-service');
jest.mock('@/config', () => ({ config: { apiUrl: 'http://localhost:8000', wsUrl: 'ws://localhost:8000/ws' } }));
jest.mock('../../services/reconciliation', () => ({ reconciliationService: { addOptimisticMessage: jest.fn((msg) => ({ ...msg, tempId: 'temp_123' })), processConfirmation: jest.fn((msg) => msg), getStats: jest.fn(() => ({})) } }));
jest.mock('../../services/chatStatePersistence', () => ({ chatStatePersistence: { getRestorableState: jest.fn(() => null), updateThread: jest.fn(), updateMessages: jest.fn(), destroy: jest.fn() } }));
jest.mock('@/lib/logger', () => ({ logger: { debug: jest.fn(), info: jest.fn(), warn: jest.fn(), error: jest.fn() } }));

// Component that traces useWebSocketContext updates
const ContextTracer = () => {
  const context = useWebSocketContext();
  const [renderCount, setRenderCount] = useState(0);
  
  useEffect(() => {
    setRenderCount(prev => prev + 1);
  });
  
  console.log(`🔍 Render ${renderCount + 1}: useWebSocketContext returned:`, {
    status: context.status,
    messagesLength: context.messages.length,
    contextKeys: Object.keys(context)
  });
  
  return (
    <div>
      <div data-testid="status">{context.status}</div>
      <div data-testid="messages-count">{context.messages.length}</div>
      <div data-testid="render-count">{renderCount + 1}</div>
    </div>
  );
};

describe('WebSocketProvider Context Trace', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set controlled auth state
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

  it('should trace context values from WebSocketProvider', () => {
    console.log('🚀 Starting context trace test...');
    
    const authContext = {
      token: null,
      initialized: false,
      user: null,
    };

    render(
      <AuthContext.Provider value={authContext}>
        <WebSocketProvider>
          <ContextTracer />
        </WebSocketProvider>
      </AuthContext.Provider>
    );
    
    console.log('✅ Context trace complete');
  });
});