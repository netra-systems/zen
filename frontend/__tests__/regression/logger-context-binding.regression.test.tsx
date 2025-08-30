/**
 * Regression Test: Logger Context Binding Issue
 * 
 * Issue: Uncaught TypeError: Cannot read properties of undefined (reading 'log')
 * Location: logger.ts:211:10 at warn method
 * 
 * Root Cause: When logger methods (warn, error, info, debug) were assigned to 
 * variables or passed as callbacks, they lost their 'this' context, causing
 * the internal this.log() call to fail.
 * 
 * Original Error Stack:
 * - WebSocketProvider.tsx:163 assigned logger.warn/error to a variable
 * - webSocketService.ts:930 called the onError callback
 * - The detached method tried to call this.log() with undefined 'this'
 * 
 * This test ensures the fix remains in place and prevents regression.
 */

import React from 'react';
import { render, waitFor, act } from '@testing-library/react';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { logger } from '@/lib/logger';
import { webSocketService } from '@/services/webSocketService';

// Mock the webSocketService
jest.mock('@/services/webSocketService', () => ({
  webSocketService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    send: jest.fn(),
    getStatus: jest.fn(() => 'CLOSED'),
    on: jest.fn(),
    off: jest.fn(),
    isConnected: jest.fn(() => false),
  }
}));

// Mock config
jest.mock('@/config', () => ({
  config: {
    wsUrl: 'ws://localhost:8000/ws',
    apiUrl: 'http://localhost:8000',
    isDevelopment: true,
    isProduction: false,
  }
}));

describe('Logger Context Binding Regression Test', () => {
  const mockAuthContextValue = {
    token: 'test-token',
    user: null,
    loading: false,
    initialized: true,
    login: jest.fn(),
    logout: jest.fn(),
    signup: jest.fn(),
    googleLogin: jest.fn(),
    refreshToken: jest.fn(),
    isDevMode: false,
    hasSession: jest.fn(() => true),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Spy on logger methods to track calls
    jest.spyOn(logger, 'warn');
    jest.spyOn(logger, 'error');
    jest.spyOn(logger, 'info');
    jest.spyOn(logger, 'debug');
    
    // Ensure console methods don't pollute test output
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'info').mockImplementation(() => {});
    jest.spyOn(console, 'debug').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('should handle WebSocket errors without losing logger context', async () => {
    let capturedOnError: ((error: any) => void) | undefined;
    
    // Capture the onError callback passed to webSocketService.connect
    (webSocketService.connect as jest.Mock).mockImplementation((url, token, options) => {
      capturedOnError = options?.onError;
      return Promise.resolve();
    });

    // Render the WebSocketProvider
    const { unmount } = render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <WebSocketProvider>
          <div>Test Child</div>
        </WebSocketProvider>
      </AuthContext.Provider>
    );

    // Wait for the connect to be called
    await waitFor(() => {
      expect(webSocketService.connect).toHaveBeenCalled();
    });

    expect(capturedOnError).toBeDefined();

    // Simulate recoverable error (should use logger.warn)
    const recoverableError = {
      code: 1006,
      message: 'Connection lost',
      timestamp: Date.now(),
      type: 'connection',
      recoverable: true
    };

    // This was the problematic code pattern that caused the error
    // The onError callback should NOT throw when it tries to log
    expect(() => {
      act(() => {
        capturedOnError?.(recoverableError);
      });
    }).not.toThrow();

    // Verify logger.warn was called correctly
    expect(logger.warn).toHaveBeenCalledWith(
      expect.stringContaining('WebSocket connection error'),
      expect.objectContaining({
        component: 'WebSocketProvider',
        action: 'connection_error',
        metadata: expect.objectContaining({
          error: 'Connection lost',
          type: 'connection',
          recoverable: true,
          code: 1006
        })
      })
    );

    // Simulate non-recoverable error (should use logger.error)
    const criticalError = {
      code: 1008,
      message: 'Authentication failed',
      timestamp: Date.now(),
      type: 'auth',
      recoverable: false
    };

    expect(() => {
      act(() => {
        capturedOnError?.(criticalError);
      });
    }).not.toThrow();

    // Verify logger.error was called correctly
    expect(logger.error).toHaveBeenCalledWith(
      expect.stringContaining('Authentication failed'),
      undefined,
      expect.objectContaining({
        component: 'WebSocketProvider',
        action: 'authentication_error',
        metadata: expect.objectContaining({
          error: 'Authentication failed',
          type: 'auth',
          recoverable: false,
          code: 1008
        })
      })
    );

    unmount();
  });

  it('should maintain logger context when methods are assigned to variables', () => {
    // This is the exact pattern that was causing the error
    const logFn = logger.warn;
    
    // Should not throw "Cannot read properties of undefined (reading 'log')"
    expect(() => {
      logFn('Test warning from detached method', { component: 'RegressionTest' });
    }).not.toThrow();
    
    expect(logger.warn).toHaveBeenCalledWith(
      'Test warning from detached method',
      { component: 'RegressionTest' }
    );
  });

  it('should handle conditional logger method assignment', () => {
    // This was the specific pattern in WebSocketProvider that failed
    const error = { recoverable: true };
    const logFn = error.recoverable ? logger.warn : logger.error;
    
    expect(() => {
      logFn('Conditional log message', { component: 'ConditionalTest' });
    }).not.toThrow();
    
    expect(logger.warn).toHaveBeenCalledWith(
      'Conditional log message',
      { component: 'ConditionalTest' }
    );
  });

  it('should work with all logger methods when detached', () => {
    const methods = [
      { method: logger.debug, name: 'debug', args: ['Debug message', { test: true }] },
      { method: logger.info, name: 'info', args: ['Info message', { test: true }] },
      { method: logger.warn, name: 'warn', args: ['Warn message', { test: true }] },
      { method: logger.error, name: 'error', args: ['Error message', undefined, { test: true }] },
    ];

    methods.forEach(({ method, name, args }) => {
      const detachedMethod = method;
      
      expect(() => {
        detachedMethod(...args);
      }).not.toThrow();
      
      expect(logger[name as keyof typeof logger]).toHaveBeenCalled();
    });
  });

  it('should handle logger methods in Promise chains', async () => {
    const failingPromise = Promise.reject(new Error('Test error'));
    
    // Common pattern in async error handling
    const handleError = logger.error;
    
    await expect(
      failingPromise.catch((err) => {
        // This should not throw
        handleError('Async operation failed', err, { component: 'AsyncTest' });
      })
    ).resolves.toBeUndefined();
    
    expect(logger.error).toHaveBeenCalledWith(
      'Async operation failed',
      expect.any(Error),
      { component: 'AsyncTest' }
    );
  });

  it('should handle logger methods in event handlers', () => {
    const mockWebSocket = {
      onerror: null as ((event: any) => void) | null,
      onclose: null as ((event: any) => void) | null,
    };
    
    // Simulate setting up error handlers with logger methods
    const setupHandlers = () => {
      // This pattern could lose context if not properly bound
      const logError = logger.error;
      const logWarn = logger.warn;
      
      mockWebSocket.onerror = (event) => {
        logError('WebSocket error event', undefined, { event });
      };
      
      mockWebSocket.onclose = (event) => {
        logWarn('WebSocket closed', { event });
      };
    };
    
    expect(() => {
      setupHandlers();
      mockWebSocket.onerror?.({ type: 'error', message: 'Connection failed' });
      mockWebSocket.onclose?.({ type: 'close', code: 1000 });
    }).not.toThrow();
    
    expect(logger.error).toHaveBeenCalled();
    expect(logger.warn).toHaveBeenCalled();
  });

  describe('Logger method binding verification', () => {
    it('should have all public methods bound in constructor', () => {
      // Create a new instance to test constructor binding
      const FrontendLogger = logger.constructor as any;
      const testInstance = new FrontendLogger();
      
      // List of methods that should be bound
      const methodsThatShouldBeBound = [
        'debug', 'info', 'warn', 'error',
        'performance', 'apiCall', 'websocketEvent',
        'userAction', 'errorBoundary', 'getLogBuffer',
        'clearLogBuffer', 'setLogLevel', 'isEnabled',
        'group', 'groupEnd'
      ];
      
      methodsThatShouldBeBound.forEach(methodName => {
        const method = testInstance[methodName];
        expect(method).toBeDefined();
        
        // Test that the method works when detached
        const detached = method;
        expect(() => {
          if (methodName === 'error') {
            detached('Test', new Error('test'), {});
          } else if (methodName === 'errorBoundary') {
            detached(new Error('test'), {}, 'Test');
          } else if (methodName === 'performance') {
            detached('operation', 100, {});
          } else if (methodName === 'apiCall') {
            detached('GET', '/api/test', 200, 100, {});
          } else if (methodName === 'websocketEvent') {
            detached('test_event', {}, {});
          } else if (methodName === 'userAction') {
            detached('click', {}, {});
          } else if (methodName === 'setLogLevel') {
            detached(2); // LogLevel.WARN
          } else if (methodName === 'isEnabled') {
            detached(1); // LogLevel.INFO
          } else if (methodName === 'group') {
            detached('Test Group');
          } else if (['getLogBuffer', 'clearLogBuffer', 'groupEnd'].includes(methodName)) {
            detached();
          } else {
            detached('Test message', {});
          }
        }).not.toThrow(`Method ${methodName} should not throw when detached`);
      });
    });
  });
});