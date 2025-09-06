/**
 * Test to trace exactly what useWebSocketContext returns and when
 */

import React, { useEffect, useState, useRef } from 'react';
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

// Component that traces useWebSocketContext updates with memory leak prevention
const ContextTracer = () => {
  const context = useWebSocketContext();
  const [renderCount, setRenderCount] = useState(0);
  const renderCountRef = useRef(0);
  
  // Use ref to prevent infinite re-renders and memory leaks
  useEffect(() => {
    renderCountRef.current = renderCountRef.current + 1;
    setRenderCount(renderCountRef.current);
  }, [context.status, context.messages.length]); // Only update on actual context changes
  
  // Limit console logging to prevent memory exhaustion in tests
  useEffect(() => {
    if (renderCountRef.current <= 10) { // Limit to first 10 renders
      console.log(`🔍 Render ${renderCountRef.current}: useWebSocketContext returned:`, {
        status: context.status,
        messagesLength: context.messages.length,
        contextKeys: Object.keys(context)
      });
    }
  }, [context.status, context.messages.length]);
  
  return (
    <div>
      <div data-testid="status">{context.status}</div>
      <div data-testid="messages-count">{context.messages.length}</div>
      <div data-testid="render-count">{renderCount}</div>
    </div>
  );
};

describe('WebSocketProvider Context Trace', () => {
  let cleanup: (() => void) | null = null;
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Clear any existing timers to prevent memory leaks
    jest.clearAllTimers();
    
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
  
  afterEach(() => {
    // Comprehensive cleanup to prevent memory leaks
    if (cleanup) {
      cleanup();
      cleanup = null;
    }
    
    // Clear all timers
    jest.clearAllTimers();
    
    // Force garbage collection if available (test environment)
    if (global.gc) {
      global.gc();
    }
  });

  it('should trace context values from WebSocketProvider without memory leaks', () => {
    console.log('🚀 Starting context trace test...');
    
    const authContext = {
      token: null,
      initialized: false,
      user: null,
    };

    const { unmount } = render(
      <AuthContext.Provider value={authContext}>
        <WebSocketProvider>
          <ContextTracer />
        </WebSocketProvider>
      </AuthContext.Provider>
    );
    
    // Store cleanup function for afterEach
    cleanup = () => {
      try {
        unmount();
      } catch (error) {
        console.warn('Error during cleanup:', error);
      }
    };
    
    console.log('✅ Context trace complete');
  });
});