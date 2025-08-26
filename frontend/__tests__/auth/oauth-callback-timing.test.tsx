/**
 * OAuth Callback Timing Tests - Challenging Edge Cases
 * 
 * Tests the critical OAuth callback improvements:
 * 1. Storage event dispatch after token save
 * 2. 50ms delay before redirect
 * 3. Error recovery scenarios
 * 
 * These tests are designed to fail if the implementation doesn't handle
 * complex async timing, Next.js router mocking, and storage event edge cases correctly.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';

// Import the component to test
import AuthCallbackClient from '@/app/auth/callback/client';

// Mock Next.js navigation hooks
const mockPush = jest.fn();
const mockSearchParams = {
  get: jest.fn(),
};

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => mockSearchParams,
}));

// Mock the debug logger
jest.mock('@/utils/debug-logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
  },
}));

// Enhanced localStorage mock with event tracking
const mockLocalStorage = (() => {
  const store: { [key: string]: string } = {};
  const listeners: Array<(event: StorageEvent) => void> = [];
  
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      const oldValue = store[key];
      store[key] = value;
      
      // Simulate real localStorage behavior - don't auto-dispatch storage events
      // for same-window operations (this is what makes the test challenging)
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach(key => delete store[key]);
    }),
    addEventListener: jest.fn((type: string, listener: (event: StorageEvent) => void) => {
      if (type === 'storage') {
        listeners.push(listener);
      }
    }),
    removeEventListener: jest.fn((type: string, listener: (event: StorageEvent) => void) => {
      if (type === 'storage') {
        const index = listeners.indexOf(listener);
        if (index > -1) {
          listeners.splice(index, 1);
        }
      }
    }),
    _triggerStorageEvent: (key: string, newValue: string) => {
      const event = new StorageEvent('storage', {
        key,
        newValue,
        url: 'http://localhost:3000',
        storageArea: localStorage
      });
      listeners.forEach(listener => listener(event));
    },
    _store: store,
    _listeners: listeners,
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// Enhanced window.dispatchEvent mock to track storage events
const originalDispatchEvent = window.dispatchEvent;
const mockDispatchEvent = jest.fn((event: Event) => {
  if (event instanceof StorageEvent && event.type === 'storage') {
    // This is the critical part - the component should dispatch storage events
    return originalDispatchEvent.call(window, event);
  }
  return originalDispatchEvent.call(window, event);
});
window.dispatchEvent = mockDispatchEvent;

// Store original setTimeout before mocking
const originalSetTimeout = global.setTimeout;

// Mock setTimeout with precise timing control
let mockSetTimeoutId = 0;
const mockSetTimeoutCallbacks = new Map<number, { callback: () => void; delay: number }>();

const mockSetTimeout = jest.fn((callback: () => void, delay: number): NodeJS.Timeout => {
  const id = ++mockSetTimeoutId;
  mockSetTimeoutCallbacks.set(id, { callback, delay });
  
  // Return a real timeout that won't cause infinite recursion
  const realTimeoutId = originalSetTimeout(() => {
    const storedCallback = mockSetTimeoutCallbacks.get(id);
    if (storedCallback) {
      storedCallback.callback();
      mockSetTimeoutCallbacks.delete(id);
    }
  }, delay);
  
  return realTimeoutId;
}) as unknown as typeof setTimeout;

describe('OAuth Callback Timing - Challenging Edge Cases', () => {
  // Set timeout for all tests in this suite
  jest.setTimeout(30000);
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    mockLocalStorage.clear();
    mockSetTimeoutCallbacks.clear();
    mockSetTimeoutId = 0;
    mockPush.mockReset();
    mockSearchParams.get.mockReset();
    mockDispatchEvent.mockClear();
    
    // Reset setTimeout to our mock
    global.setTimeout = mockSetTimeout;
  });

  afterEach(() => {
    // Clean up any pending timeouts
    mockSetTimeoutCallbacks.clear();
  });

  afterAll(() => {
    // Restore original setTimeout
    global.setTimeout = originalSetTimeout;
  });

  /**
   * TEST 1: Storage Event Dispatch Verification
   * 
   * This test verifies that storage events are properly dispatched with correct data
   * CHALLENGING ASPECTS:
   * - Must distinguish between automatic localStorage events vs manual dispatch
   * - Verifies exact StorageEvent properties
   * - Tests timing of event dispatch relative to localStorage.setItem
   */
  test('CHALLENGE 1: Storage event dispatch verification with exact timing and data validation', async () => {
    // Setup successful OAuth callback scenario
    const testToken = 'test_jwt_token_12345';
    const testRefreshToken = 'test_refresh_token_67890';
    
    mockSearchParams.get.mockImplementation((key: string) => {
      if (key === 'token') return testToken;
      if (key === 'refresh') return testRefreshToken;
      return null;
    });

    // Track storage event dispatches with precise validation
    const storageEventsSpy = jest.fn();
    window.addEventListener('storage', storageEventsSpy);

    // Render the component
    await act(async () => {
      render(<AuthCallbackClient />);
    });

    // Wait for the callback to complete
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken);
    }, { timeout: 5000 });

    // CRITICAL ASSERTION 1: Verify dispatchEvent was called with StorageEvent
    await waitFor(() => {
      expect(mockDispatchEvent).toHaveBeenCalled();
    }, { timeout: 2000 });
    
    const dispatchedEvent = mockDispatchEvent.mock.calls[0][0] as StorageEvent;
    expect(dispatchedEvent).toBeInstanceOf(StorageEvent);
    expect(dispatchedEvent.type).toBe('storage');
    
    // CRITICAL ASSERTION 2: Verify StorageEvent has exact properties
    expect(dispatchedEvent.key).toBe('jwt_token');
    expect(dispatchedEvent.newValue).toBe(testToken);
    expect(dispatchedEvent.url).toBe(window.location.href);
    expect(dispatchedEvent.storageArea).toBe(localStorage);

    // CRITICAL ASSERTION 3: Verify both tokens are stored
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('refresh_token', testRefreshToken);
    expect(mockLocalStorage.setItem).toHaveBeenCalledTimes(2);

    // Cleanup
    window.removeEventListener('storage', storageEventsSpy);
  });

  /**
   * TEST 2: Redirect Timing Test
   * 
   * This test verifies the exact 50ms delay occurs and router.push happens after delay
   * CHALLENGING ASPECTS:
   * - Tests precise timing with setTimeout mocking
   * - Verifies router.push doesn't happen immediately
   * - Tests async timing coordination
   * - Ensures redirect happens to correct route
   */
  test('CHALLENGE 2: Exact 50ms redirect timing with precise async control', async () => {
    const testToken = 'timing_test_token';
    
    mockSearchParams.get.mockImplementation((key: string) => {
      if (key === 'token') return testToken;
      return null;
    });

    // Track the exact timing of operations
    const operationTimestamps: Array<{ operation: string; timestamp: number }> = [];
    
    // Wrap localStorage.setItem to track timing
    const originalSetItem = mockLocalStorage.setItem;
    mockLocalStorage.setItem.mockImplementation((key: string, value: string) => {
      operationTimestamps.push({ operation: `setItem_${key}`, timestamp: Date.now() });
      return originalSetItem(key, value);
    });

    // Wrap dispatchEvent to track timing
    const originalMockDispatchEvent = mockDispatchEvent;
    mockDispatchEvent.mockImplementation((event: Event) => {
      if (event instanceof StorageEvent) {
        operationTimestamps.push({ operation: 'dispatchEvent', timestamp: Date.now() });
      }
      return originalMockDispatchEvent(event);
    });

    // Wrap router.push to track timing
    mockPush.mockImplementation((route: string) => {
      operationTimestamps.push({ operation: `router_push_${route}`, timestamp: Date.now() });
    });

    const startTime = Date.now();

    // Render component
    await act(async () => {
      render(<AuthCallbackClient />);
    });

    // CRITICAL ASSERTION 1: Router.push should NOT be called immediately
    expect(mockPush).not.toHaveBeenCalled();
    
    // CRITICAL ASSERTION 2: setTimeout should be called with exactly 50ms delay
    expect(mockSetTimeout).toHaveBeenCalledWith(expect.any(Function), 50);
    
    // Verify callback sequence before timeout
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken);
      expect(mockDispatchEvent).toHaveBeenCalled();
    });

    // CRITICAL ASSERTION 3: Router.push should still not be called before timeout
    expect(mockPush).not.toHaveBeenCalled();

    // Wait for timeout to complete (we need to wait slightly more than 50ms)
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 60));
    });

    // CRITICAL ASSERTION 4: Router.push should now be called with correct route
    expect(mockPush).toHaveBeenCalledWith('/chat');
    expect(mockPush).toHaveBeenCalledTimes(1);

    // CRITICAL ASSERTION 5: Verify operation sequence and timing
    const setItemOp = operationTimestamps.find(op => op.operation === 'setItem_jwt_token');
    const dispatchOp = operationTimestamps.find(op => op.operation === 'dispatchEvent');
    const routerOp = operationTimestamps.find(op => op.operation === 'router_push_/chat');

    expect(setItemOp).toBeDefined();
    expect(dispatchOp).toBeDefined();
    expect(routerOp).toBeDefined();

    // Verify sequence: setItem -> dispatchEvent -> (delay) -> router.push
    expect(setItemOp!.timestamp).toBeLessThan(dispatchOp!.timestamp);
    expect(dispatchOp!.timestamp).toBeLessThan(routerOp!.timestamp);
    
    // Verify minimum delay between dispatch and router push (should be ~50ms)
    const delayMs = routerOp!.timestamp - dispatchOp!.timestamp;
    expect(delayMs).toBeGreaterThanOrEqual(45); // Allow 5ms tolerance for timing precision
  });

  /**
   * TEST 3: Error Recovery During Redirect
   * 
   * This test verifies error handling when storage event dispatch or redirect fails
   * CHALLENGING ASPECTS:
   * - Tests multiple failure scenarios in sequence
   * - Verifies graceful degradation
   * - Tests error boundary behavior
   * - Ensures no memory leaks from failed operations
   */
  test('CHALLENGE 3: Complex error recovery scenarios with multiple failure points', async () => {
    const testToken = 'error_recovery_token';
    
    // Test Case 3A: Storage event dispatch failure
    const storageDispatchError = new Error('Storage event dispatch failed');
    mockDispatchEvent.mockImplementationOnce(() => {
      throw storageDispatchError;
    });

    mockSearchParams.get.mockImplementation((key: string) => {
      if (key === 'token') return testToken;
      return null;
    });

    // Track error handling
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    // Render component with dispatch error
    await act(async () => {
      render(<AuthCallbackClient />);
    });

    // CRITICAL ASSERTION 3A: Token should still be stored despite dispatch error
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken);
    });

    // CRITICAL ASSERTION 3A: Component should recover and still attempt redirect
    // Even if storage event fails, the redirect should still work
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 60));
    });
    
    expect(mockPush).toHaveBeenCalledWith('/chat');

    // Reset for next test case
    jest.clearAllMocks();
    mockSetTimeoutCallbacks.clear();

    // Test Case 3B: Router.push failure
    const routerError = new Error('Router navigation failed');
    mockPush.mockImplementationOnce(() => {
      throw routerError;
    });

    mockSearchParams.get.mockImplementation((key: string) => {
      if (key === 'token') return testToken + '_router_fail';
      return null;
    });

    // Render component with router error
    await act(async () => {
      render(<AuthCallbackClient />);
    });

    // Wait for operations to complete
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken + '_router_fail');
    });

    // Wait for timeout and router call
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 60));
    });

    // CRITICAL ASSERTION 3B: Router.push should have been attempted despite error
    expect(mockPush).toHaveBeenCalledWith('/chat');

    // Reset for next test case  
    jest.clearAllMocks();
    mockSetTimeoutCallbacks.clear();

    // Test Case 3C: localStorage failure with recovery
    const localStorageError = new Error('LocalStorage quota exceeded');
    mockLocalStorage.setItem.mockImplementationOnce(() => {
      throw localStorageError;
    });

    mockSearchParams.get.mockImplementation((key: string) => {
      if (key === 'token') return testToken + '_storage_fail';
      return null;
    });

    // Render component with localStorage error
    await act(async () => {
      render(<AuthCallbackClient />);
    });

    // CRITICAL ASSERTION 3C: Should handle localStorage error gracefully
    // The component should not crash and should display error state
    await waitFor(() => {
      // Should show error state instead of successful authentication
      const errorElement = screen.queryByText(/Authentication Failed/);
      expect(errorElement || screen.queryByText(/No authentication token received/)).toBeInTheDocument();
    });

    // CRITICAL ASSERTION 3C: Router should redirect to error page, not /chat
    expect(mockPush).not.toHaveBeenCalledWith('/chat');

    // Test Case 3D: Multiple simultaneous failures
    jest.clearAllMocks();
    mockSetTimeoutCallbacks.clear();

    // Set up multiple failures
    mockDispatchEvent.mockImplementation(() => { throw new Error('Dispatch failed'); });
    mockPush.mockImplementation(() => { throw new Error('Router failed'); });
    
    mockSearchParams.get.mockImplementation((key: string) => {
      if (key === 'token') return testToken + '_multi_fail';
      return null;
    });

    // This should not crash the component
    let componentErrored = false;
    const ErrorBoundary = ({ children }: { children: React.ReactNode }) => {
      try {
        return <>{children}</>;
      } catch (error) {
        componentErrored = true;
        return <div>Component crashed</div>;
      }
    };

    await act(async () => {
      render(
        <ErrorBoundary>
          <AuthCallbackClient />
        </ErrorBoundary>
      );
    });

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 60));
    });

    // CRITICAL ASSERTION 3D: Component should not crash despite multiple failures  
    expect(componentErrored).toBe(false);
    expect(screen.queryByText('Component crashed')).not.toBeInTheDocument();

    // Cleanup
    consoleErrorSpy.mockRestore();
  });

  // Additional challenging edge case: Rapid successive callback attempts
  test('BONUS CHALLENGE: Rapid successive OAuth callbacks with race condition protection', async () => {
    const testToken1 = 'race_token_1';
    const testToken2 = 'race_token_2';

    // Mock multiple rapid renders (simulating browser back/forward or multiple tabs)
    mockSearchParams.get
      .mockImplementationOnce((key: string) => key === 'token' ? testToken1 : null)
      .mockImplementationOnce((key: string) => key === 'token' ? testToken2 : null);

    // Render first instance
    const { rerender } = render(<AuthCallbackClient />);
    
    // Immediately render second instance (race condition)
    await act(async () => {
      rerender(<AuthCallbackClient />);
    });

    // Wait for all operations to complete
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // CRITICAL ASSERTION: Should handle race condition gracefully
    // Only one redirect should occur, storage should be consistent
    expect(mockPush).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledWith('/chat');
    
    // Last token should win
    expect(mockLocalStorage.setItem).toHaveBeenLastCalledWith('jwt_token', testToken2);
  });
});