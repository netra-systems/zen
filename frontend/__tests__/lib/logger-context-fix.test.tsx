/**
 * Test to verify logger context binding fix
 * Ensures logger methods maintain proper 'this' context when passed as callbacks
 */

import { logger } from '@/lib/logger';

describe('Logger Context Binding', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should maintain context when logger methods are assigned to variables', () => {
    // This was the problematic pattern that caused the error
    const warnFn = logger.warn;
    const errorFn = logger.error;
    const infoFn = logger.info;
    const debugFn = logger.debug;
    
    // These should not throw "Cannot read properties of undefined"
    expect(() => {
      warnFn('Test warning message', { component: 'Test' });
    }).not.toThrow();
    
    expect(() => {
      errorFn('Test error message', undefined, { component: 'Test' });
    }).not.toThrow();
    
    expect(() => {
      infoFn('Test info message', { component: 'Test' });
    }).not.toThrow();
    
    expect(() => {
      debugFn('Test debug message', { component: 'Test' });
    }).not.toThrow();
  });

  it('should work when passed as callbacks to other functions', () => {
    const executeCallback = (fn: Function, ...args: any[]) => {
      return fn(...args);
    };
    
    // Should not throw when passed as callback
    expect(() => {
      executeCallback(logger.warn, 'Callback warning', { component: 'CallbackTest' });
    }).not.toThrow();
    
    expect(() => {
      executeCallback(logger.error, 'Callback error', undefined, { component: 'CallbackTest' });
    }).not.toThrow();
  });

  it('should work in Promise error handlers', async () => {
    const testPromise = Promise.reject(new Error('Test error'));
    
    // This pattern is common in error handlers
    const handleError = logger.error;
    
    await expect(
      testPromise.catch((err) => {
        handleError('Promise rejected', err, { component: 'PromiseTest' });
      })
    ).resolves.toBeUndefined();
  });

  it('should work when used in WebSocket-like error callbacks', () => {
    interface MockError {
      message: string;
      recoverable: boolean;
    }
    
    const simulateWebSocketError = (onError: (error: MockError) => void) => {
      const error: MockError = {
        message: 'Connection failed',
        recoverable: true
      };
      onError(error);
    };
    
    const onError = (error: MockError) => {
      // This is the pattern that was failing in WebSocketProvider
      const logFn = error.recoverable ? logger.warn : logger.error;
      
      // This should not throw
      expect(() => {
        logFn('WebSocket error', { metadata: { error: error.message } });
      }).not.toThrow();
    };
    
    simulateWebSocketError(onError);
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});