/**
 * Browser Context WebSocket Logger Error Tests
 * 
 * Tests specifically for the dual import context binding issue described in:
 * SPEC/learnings/websocket_logger_dual_import_context_binding_issue.xml
 * 
 * Critical Error Pattern: TypeError: Cannot read properties of undefined (reading 'log')
 * Root Cause: Dual logger imports causing context binding loss in browser environments
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { jest } from '@jest/globals';

// Mock WebSocket for browser environment simulation
class MockWebSocketWithErrors extends EventTarget {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocketWithErrors.CONNECTING;
  url: string;
  protocol: string;

  constructor(url: string, protocols?: string | string[]) {
    super();
    this.url = url;
    this.protocol = Array.isArray(protocols) ? protocols[0] : protocols || '';
  }

  send = jest.fn();
  close = jest.fn();

  // Simulate browser context error scenarios
  simulateError() {
    this.readyState = MockWebSocketWithErrors.CLOSED;
    const errorEvent = new Event('error') as any;
    errorEvent.code = 1006;
    errorEvent.reason = 'Connection failed';
    this.dispatchEvent(errorEvent);
  }

  simulateContextLossError() {
    // Simulate the specific error from the learning: "Cannot read properties of undefined (reading 'log')"
    const errorEvent = new Event('error') as any;
    errorEvent.code = 1011;
    errorEvent.reason = 'Context binding lost';
    errorEvent.contextLoss = true; // Custom property to trigger context-related errors
    this.dispatchEvent(errorEvent);
  }
}

// Replace global WebSocket
(global as any).WebSocket = MockWebSocketWithErrors;

// Test component that simulates the dual import pattern issue
const DualImportLoggerTestComponent: React.FC<{ triggerError?: boolean; triggerContextLoss?: boolean }> = ({ 
  triggerError = false, 
  triggerContextLoss = false 
}) => {
  const [error, setError] = React.useState<string>('');
  const [loggerState, setLoggerState] = React.useState<string>('');
  const wsRef = React.useRef<MockWebSocketWithErrors | null>(null);

  React.useEffect(() => {
    // Simulate the problematic dual import pattern that was causing issues
    const connectWithDelay = () => {
      try {
        // Import logger in the same way as the problematic code
        const { logger } = require('@/lib/logger');
        
        // Create WebSocket
        wsRef.current = new MockWebSocketWithErrors('ws://localhost:8001/ws') as MockWebSocketWithErrors;
        
        // Set up error handler that uses logger - this is where the context binding issue occurred
        wsRef.current.addEventListener('error', (event: any) => {
          try {
            // This line was failing with "Cannot read properties of undefined (reading 'log')"
            // when logger context was lost due to dual imports
            logger.error('WebSocket error occurred', new Error('Connection failed'), {
              component: 'WebSocketProvider',
              action: 'error_handler',
              metadata: {
                code: event.code,
                reason: event.reason,
                contextLoss: event.contextLoss || false
              }
            });
            
            setLoggerState('logger_method_executed');
          } catch (loggerError: any) {
            // Catch the specific error we're testing for
            if (loggerError.message.includes('Cannot read properties of undefined')) {
              setError('LOGGER_CONTEXT_BINDING_ERROR: ' + loggerError.message);
            } else {
              setError('UNEXPECTED_ERROR: ' + loggerError.message);
            }
          }
        });

        // Trigger different error scenarios
        if (triggerContextLoss) {
          setTimeout(() => wsRef.current?.simulateContextLossError(), 10);
        } else if (triggerError) {
          setTimeout(() => wsRef.current?.simulateError(), 10);
        }
        
      } catch (error: any) {
        setError('SETUP_ERROR: ' + error.message);
      }
    };

    connectWithDelay();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [triggerError, triggerContextLoss]);

  return (
    <div>
      <div data-testid="error-state">{error}</div>
      <div data-testid="logger-state">{loggerState}</div>
    </div>
  );
};

describe('WebSocket Logger Browser Context Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset any logger state
    jest.resetModules();
  });

  afterEach(() => {
    // Clean up any global state
    jest.restoreAllMocks();
  });

  it('should NOT have logger context binding errors in normal error scenarios', async () => {
    render(<DualImportLoggerTestComponent triggerError={true} />);
    
    await waitFor(() => {
      const errorState = screen.getByTestId('error-state').textContent;
      const loggerState = screen.getByTestId('logger-state').textContent;
      
      // Should execute logger method successfully without context binding errors
      expect(errorState).not.toContain('LOGGER_CONTEXT_BINDING_ERROR');
      expect(errorState).not.toContain('Cannot read properties of undefined');
      expect(loggerState).toBe('logger_method_executed');
    }, { timeout: 1000 });
  });

  it('should detect dual import context binding vulnerabilities', async () => {
    // This test simulates the browser environment where dual imports can cause context loss
    const TestComponentWithDualImports: React.FC = () => {
      const [testResult, setTestResult] = React.useState<string>('');

      React.useEffect(() => {
        // Simulate dual import pattern that was causing the original issue
        try {
          // First import
          const { logger } = require('@/lib/logger');
          
          // Second import with alias (the problematic pattern)
          const { logger: debugLogger } = require('@/lib/logger');
          
          // Test if context is preserved in both references
          const originalError = logger.error;
          const aliasedError = debugLogger.error;
          
          // Check if both references maintain proper 'this' binding
          if (typeof originalError === 'function' && typeof aliasedError === 'function') {
            // Test direct method access (this can lose context in some bundling scenarios)
            try {
              const unboundMethod = logger.error;
              // Try to call unbound method - this would fail with context loss
              unboundMethod('Test message', new Error('Test'));
              setTestResult('CONTEXT_PRESERVED');
            } catch (error: any) {
              if (error.message.includes('Cannot read properties of undefined')) {
                setTestResult('CONTEXT_BINDING_VULNERABILITY_DETECTED');
              } else {
                setTestResult('UNEXPECTED_BINDING_ERROR: ' + error.message);
              }
            }
          } else {
            setTestResult('IMPORT_METHOD_ERROR');
          }
        } catch (error: any) {
          setTestResult('DUAL_IMPORT_ERROR: ' + error.message);
        }
      }, []);

      return <div data-testid="dual-import-test">{testResult}</div>;
    };

    render(<TestComponentWithDualImports />);
    
    await waitFor(() => {
      const testResult = screen.getByTestId('dual-import-test').textContent;
      
      // Should NOT detect context binding vulnerabilities in the fixed code
      expect(testResult).not.toBe('CONTEXT_BINDING_VULNERABILITY_DETECTED');
      expect(testResult).toBe('CONTEXT_PRESERVED');
    }, { timeout: 1000 });
  });

  it('should handle WebSocket error callbacks with proper logger context', async () => {
    // Test the exact scenario from the learning file
    const WebSocketErrorCallbackTest: React.FC = () => {
      const [callbackResult, setCallbackResult] = React.useState<string>('');
      const [errorHandled, setErrorHandled] = React.useState<boolean>(false);

      React.useEffect(() => {
        const { logger } = require('@/lib/logger');
        
        const ws = new MockWebSocketWithErrors('ws://localhost:8001/ws');
        
        // Set up error handler exactly like in WebSocketProvider.tsx:165
        const onError = (event: any) => {
          try {
            // This is the exact line that was failing: logger.error(...) 
            // from WebSocketProvider.tsx:165 as mentioned in the stack trace
            logger.error('WebSocket error occurred', new Error('Connection failed'), {
              component: 'WebSocketProvider',
              action: 'onError_callback',
              metadata: {
                code: event.code,
                reason: event.reason
              }
            });
            
            setCallbackResult('ERROR_LOGGED_SUCCESSFULLY');
            setErrorHandled(true);
          } catch (loggerError: any) {
            if (loggerError.message.includes('Cannot read properties of undefined')) {
              setCallbackResult('LOGGER_CONTEXT_LOST_IN_CALLBACK');
            } else {
              setCallbackResult('CALLBACK_ERROR: ' + loggerError.message);
            }
            setErrorHandled(false);
          }
        };

        ws.addEventListener('error', onError);
        
        // Trigger error after setup
        setTimeout(() => ws.simulateError(), 10);

        return () => {
          ws.removeEventListener('error', onError);
          ws.close();
        };
      }, []);

      return (
        <div>
          <div data-testid="callback-result">{callbackResult}</div>
          <div data-testid="error-handled">{errorHandled.toString()}</div>
        </div>
      );
    };

    render(<WebSocketErrorCallbackTest />);
    
    await waitFor(() => {
      const callbackResult = screen.getByTestId('callback-result').textContent;
      const errorHandled = screen.getByTestId('error-handled').textContent;
      
      // Should handle the error properly without context binding issues
      expect(callbackResult).toBe('ERROR_LOGGED_SUCCESSFULLY');
      expect(errorHandled).toBe('true');
      expect(callbackResult).not.toContain('LOGGER_CONTEXT_LOST_IN_CALLBACK');
    }, { timeout: 1000 });
  });

  it('should preserve logger context in WebSocket service method calls', async () => {
    // Test that covers webSocketService.ts:930 mentioned in the stack trace
    const WebSocketServiceMethodTest: React.FC = () => {
      const [serviceResult, setServiceResult] = React.useState<string>('');

      React.useEffect(() => {
        const testWebSocketServiceLoggerContext = () => {
          try {
            const { logger } = require('@/lib/logger');
            
            // Simulate the call pattern from webSocketService.ts:930
            const ws = new MockWebSocketWithErrors('ws://localhost:8001/ws');
            
            // Set onerror handler like in webSocketService.ts
            ws.addEventListener('error', (event: any) => {
              try {
                // This mirrors the pattern at webSocketService.ts:930
                logger.error('WebSocket service error', new Error('Service error'), {
                  component: 'webSocketService',
                  action: 'onerror_handler',
                  metadata: { 
                    eventType: 'websocket_error',
                    timestamp: Date.now()
                  }
                });
                setServiceResult('SERVICE_LOGGER_SUCCESS');
              } catch (loggerError: any) {
                setServiceResult('SERVICE_LOGGER_CONTEXT_ERROR: ' + loggerError.message);
              }
            });
            
            // Trigger error
            setTimeout(() => ws.simulateError(), 10);
            
          } catch (error: any) {
            setServiceResult('SERVICE_TEST_SETUP_ERROR: ' + error.message);
          }
        };

        testWebSocketServiceLoggerContext();
      }, []);

      return <div data-testid="service-result">{serviceResult}</div>;
    };

    render(<WebSocketServiceMethodTest />);
    
    await waitFor(() => {
      const serviceResult = screen.getByTestId('service-result').textContent;
      
      // Should execute logger successfully without context errors
      expect(serviceResult).toBe('SERVICE_LOGGER_SUCCESS');
      expect(serviceResult).not.toContain('SERVICE_LOGGER_CONTEXT_ERROR');
      expect(serviceResult).not.toContain('Cannot read properties of undefined');
    }, { timeout: 1000 });
  });

  it('should prevent logger method binding loss when assigned to variables', async () => {
    // Test specific vulnerability: logger methods losing 'this' context when assigned to variables
    const LoggerBindingTest: React.FC = () => {
      const [bindingResult, setBindingResult] = React.useState<string>('');

      React.useEffect(() => {
        try {
          const { logger } = require('@/lib/logger');
          
          // The problematic pattern: assigning logger methods to variables
          const errorMethod = logger.error;
          const warnMethod = logger.warn;
          const infoMethod = logger.info;
          
          // Test if methods maintain context when called as variables
          try {
            errorMethod('Test error message', new Error('Test error'));
            warnMethod('Test warn message');
            infoMethod('Test info message');
            setBindingResult('ALL_METHODS_BOUND_CORRECTLY');
          } catch (bindingError: any) {
            if (bindingError.message.includes('Cannot read properties of undefined')) {
              setBindingResult('LOGGER_BINDING_LOST');
            } else {
              setBindingResult('BINDING_ERROR: ' + bindingError.message);
            }
          }
        } catch (error: any) {
          setBindingResult('BINDING_TEST_ERROR: ' + error.message);
        }
      }, []);

      return <div data-testid="binding-result">{bindingResult}</div>;
    };

    render(<LoggerBindingTest />);
    
    await waitFor(() => {
      const bindingResult = screen.getByTestId('binding-result').textContent;
      
      // Should maintain binding (methods are bound in constructor lines 73-87)
      expect(bindingResult).toBe('ALL_METHODS_BOUND_CORRECTLY');
      expect(bindingResult).not.toBe('LOGGER_BINDING_LOST');
    }, { timeout: 1000 });
  });

  it('should handle webpack bundling scenarios that might affect logger context', async () => {
    // Test browser-specific bundling scenarios
    const WebpackBundlingTest: React.FC = () => {
      const [bundlingResult, setBundlingResult] = React.useState<string>('');

      React.useEffect(() => {
        const testWebpackBundlingScenarios = async () => {
          try {
            // Simulate webpack module resolution patterns
            const module1 = require('@/lib/logger');
            const module2 = await import('@/lib/logger');
            
            // Test that both import methods provide the same logger instance
            const logger1 = module1.logger;
            const logger2 = module2.logger;
            
            if (logger1 === logger2) {
              // Test method binding on both references
              try {
                logger1.error('Test from require import');
                logger2.error('Test from dynamic import');
                setBundlingResult('WEBPACK_BUNDLING_CONSISTENT');
              } catch (error: any) {
                setBundlingResult('WEBPACK_CONTEXT_ERROR: ' + error.message);
              }
            } else {
              setBundlingResult('WEBPACK_DIFFERENT_INSTANCES');
            }
          } catch (error: any) {
            setBundlingResult('WEBPACK_TEST_ERROR: ' + error.message);
          }
        };

        testWebpackBundlingScenarios();
      }, []);

      return <div data-testid="bundling-result">{bundlingResult}</div>;
    };

    render(<WebpackBundlingTest />);
    
    await waitFor(() => {
      const bundlingResult = screen.getByTestId('bundling-result').textContent;
      
      // Should handle webpack bundling consistently
      expect(bundlingResult).toBe('WEBPACK_BUNDLING_CONSISTENT');
      expect(bundlingResult).not.toContain('WEBPACK_CONTEXT_ERROR');
    }, { timeout: 1000 });
  });

  it('should reproduce and verify the exact error scenario from the learning', async () => {
    // Reproduce the exact error pattern from lines 13-17 of the learning file
    const ExactErrorReproductionTest: React.FC = () => {
      const [reproductionResult, setReproductionResult] = React.useState<string>('');
      const [stackTraceMatches, setStackTraceMatches] = React.useState<boolean>(false);

      React.useEffect(() => {
        const reproduceExactScenario = () => {
          try {
            // Import exactly as in the original problematic code (before fix)
            const { logger } = require('@/lib/logger');
            
            // Create WebSocket like in WebSocketProvider
            const ws = new MockWebSocketWithErrors('ws://localhost:8001/ws');
            
            // Set up error handler exactly like WebSocketProvider.tsx:165
            const connectWithDelay = {
              connectToWebSocket: {
                onError: (event: any) => {
                  try {
                    // This is the exact line from the stack trace: "at error (logger.ts:215:10)"
                    logger.error('WebSocket error occurred'); // Line that was failing
                    setReproductionResult('EXACT_SCENARIO_HANDLED');
                  } catch (error: any) {
                    // Check if we get the exact error from the learning
                    if (error.message === "Cannot read properties of undefined (reading 'log')") {
                      setReproductionResult('EXACT_ERROR_REPRODUCED');
                      // Check stack trace pattern
                      if (error.stack && error.stack.includes('logger.ts')) {
                        setStackTraceMatches(true);
                      }
                    } else {
                      setReproductionResult('DIFFERENT_ERROR: ' + error.message);
                    }
                  }
                }
              }
            };
            
            // Trigger via the same path: WebSocketProvider.useEffect.connectWithDelay.connectToWebSocket.onError
            ws.addEventListener('error', connectWithDelay.connectToWebSocket.onError);
            setTimeout(() => ws.simulateError(), 10);
            
          } catch (error: any) {
            setReproductionResult('REPRODUCTION_SETUP_ERROR: ' + error.message);
          }
        };

        reproduceExactScenario();
      }, []);

      return (
        <div>
          <div data-testid="reproduction-result">{reproductionResult}</div>
          <div data-testid="stack-trace-matches">{stackTraceMatches.toString()}</div>
        </div>
      );
    };

    render(<ExactErrorReproductionTest />);
    
    await waitFor(() => {
      const reproductionResult = screen.getByTestId('reproduction-result').textContent;
      
      // After the fix, this should handle the scenario without the exact error
      expect(reproductionResult).toBe('EXACT_SCENARIO_HANDLED');
      expect(reproductionResult).not.toBe('EXACT_ERROR_REPRODUCED');
    }, { timeout: 1000 });
  });

  it('should validate logger constructor binding prevents context loss', async () => {
    // Test that the constructor binding (lines 73-87 in logger.ts) actually works
    const ConstructorBindingTest: React.FC = () => {
      const [bindingResults, setBindingResults] = React.useState<Record<string, string>>({});

      React.useEffect(() => {
        const testConstructorBinding = () => {
          try {
            const { logger } = require('@/lib/logger');
            
            // Test all bound methods from constructor (lines 73-87)
            const boundMethods = [
              'debug', 'info', 'warn', 'error', 'performance', 
              'apiCall', 'websocketEvent', 'userAction', 'errorBoundary',
              'getLogBuffer', 'clearLogBuffer', 'setLogLevel', 'isEnabled', 
              'group', 'groupEnd'
            ];
            
            const results: Record<string, string> = {};
            
            boundMethods.forEach(methodName => {
              try {
                const method = (logger as any)[methodName];
                if (typeof method === 'function') {
                  // Test that method maintains 'this' context when extracted
                  const extractedMethod = method;
                  
                  // For non-logging methods, just check they exist and are bound
                  if (['getLogBuffer', 'clearLogBuffer', 'setLogLevel', 'isEnabled'].includes(methodName)) {
                    // These can be called safely
                    if (methodName === 'isEnabled') {
                      extractedMethod(0); // Test with LogLevel.DEBUG
                    }
                    results[methodName] = 'BOUND_OK';
                  } else if (['group', 'groupEnd'].includes(methodName)) {
                    // Console methods
                    extractedMethod('test');
                    results[methodName] = 'BOUND_OK';
                  } else {
                    // Logging methods - test with minimal args to avoid side effects
                    if (methodName === 'error') {
                      extractedMethod('Test message');
                    } else if (methodName === 'performance') {
                      extractedMethod('test', 100);
                    } else if (methodName === 'apiCall') {
                      extractedMethod('GET', '/test');
                    } else if (methodName === 'websocketEvent') {
                      extractedMethod('test');
                    } else if (methodName === 'userAction') {
                      extractedMethod('test');
                    } else if (methodName === 'errorBoundary') {
                      extractedMethod(new Error('test'), {});
                    } else {
                      extractedMethod('Test message');
                    }
                    results[methodName] = 'BOUND_OK';
                  }
                } else {
                  results[methodName] = 'NOT_FUNCTION';
                }
              } catch (error: any) {
                if (error.message.includes('Cannot read properties of undefined')) {
                  results[methodName] = 'CONTEXT_LOST';
                } else {
                  results[methodName] = 'ERROR: ' + error.message;
                }
              }
            });
            
            setBindingResults(results);
          } catch (error: any) {
            setBindingResults({ testError: 'CONSTRUCTOR_BINDING_TEST_ERROR: ' + error.message });
          }
        };

        testConstructorBinding();
      }, []);

      return (
        <div>
          <div data-testid="binding-results">{JSON.stringify(bindingResults)}</div>
        </div>
      );
    };

    render(<ConstructorBindingTest />);
    
    await waitFor(() => {
      const bindingResults = JSON.parse(screen.getByTestId('binding-results').textContent || '{}');
      
      // All methods should be properly bound
      const contextLostMethods = Object.entries(bindingResults)
        .filter(([method, result]) => result === 'CONTEXT_LOST')
        .map(([method]) => method);
      
      expect(contextLostMethods).toHaveLength(0);
      
      // Verify specific methods that were in the error are bound
      expect(bindingResults.error).toBe('BOUND_OK');
      expect(bindingResults.warn).toBe('BOUND_OK');
      expect(bindingResults.info).toBe('BOUND_OK');
    }, { timeout: 1000 });
  });
});