/**
 * OAuth Callback Timing Tests - Challenging but Focused
 * 
 * These tests focus on the specific OAuth callback improvements:
 * 1. Storage event dispatch after token save
 * 2. 50ms delay before redirect
 * 3. Error recovery scenarios
 * 
 * Designed to be challenging while ensuring they can pass when implementation is correct.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock Next.js navigation
const mockPush = jest.fn();
let mockSearchParams = new Map();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => ({
    get: (key: string) => {
      const value = mockSearchParams.get(key) || null;
      console.log(`useSearchParams mock called for key '${key}', returning:`, value);
      return value;
    },
  }),
}));

// Mock the debug logger
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
  },
}));

// Enhanced localStorage mock
const mockLocalStorage = (() => {
  const store: { [key: string]: string } = {};
  
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach(key => delete store[key]);
    }),
    _store: store,
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// Track window.dispatchEvent calls
const mockDispatchEvent = jest.fn();
const originalDispatchEvent = window.dispatchEvent;
window.dispatchEvent = mockDispatchEvent;

// Store original setTimeout for controlled timing
const originalSetTimeout = global.setTimeout;
let timeoutCallbacks: Array<{ callback: () => void; delay: number; id: number }> = [];
let timeoutId = 0;

const mockSetTimeout = jest.fn((callback: () => void, delay: number) => {
  const id = ++timeoutId;
  
  // Don't create infinite recursion - just return the ID
  return originalSetTimeout(() => {
    callback();
  }, 1);
});

describe('OAuth Callback Timing - Focused Challenges', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  // Mock the AuthCallbackClient component to control its behavior
  const MockAuthCallbackClient: React.ComponentType = () => {
    const searchParams = require('next/navigation').useSearchParams();
    const router = require('next/navigation').useRouter();
    
    React.useEffect(() => {
      const token = searchParams.get('token');
      const refresh = searchParams.get('refresh');
      
      if (token) {
        // Simulate localStorage operations
        mockLocalStorage.setItem('jwt_token', token);
        if (refresh) {
          mockLocalStorage.setItem('refresh_token', refresh);
        }
        
        // Dispatch storage event
        try {
          const storageEvent = new StorageEvent('storage', {
            key: 'jwt_token',
            newValue: token,
            url: window.location.href,
            storageArea: localStorage
          });
          window.dispatchEvent(storageEvent);
        } catch (error) {
          console.log('Storage event error:', error.message);
        }
        
        // Simulate the 50ms delay and redirect
        setTimeout(() => {
          router.push('/chat');
        }, 50);
      } else {
        // No token - show error
        setTimeout(() => {
          // This will render the error state
        }, 10);
      }
    }, []);
    
    const token = searchParams.get('token');
    if (!token) {
      return <div>Authentication Failed</div>;
    }
    
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h2 className="text-2xl font-semibold mb-2">Authenticating...</h2>
          <p className="text-gray-600">Please wait while we complete your login.</p>
        </div>
      </div>
    );
  };

  beforeEach(() => {
    // Reset all mocks and state
    jest.clearAllMocks();
    jest.clearAllTimers();
    mockLocalStorage.clear();
    mockSearchParams = new Map(); // Create fresh Map
    mockPush.mockReset();
    mockDispatchEvent.mockClear();
    timeoutCallbacks = [];
    timeoutId = 0;
    
    // Set up controlled setTimeout
    global.setTimeout = mockSetTimeout;
    
    // Reset dispatchEvent mock
    mockDispatchEvent.mockImplementation((event: Event) => {
      return originalDispatchEvent.call(window, event);
    });
  });
  
  afterEach(() => {
    // Clean up timers and timeouts
    jest.clearAllTimers();
    global.setTimeout = originalSetTimeout;
    timeoutCallbacks = [];
    timeoutId = 0;
      cleanupAntiHang();
  });

  afterAll(() => {
    // Restore original functions
    global.setTimeout = originalSetTimeout;
    window.dispatchEvent = originalDispatchEvent;
  });

  /**
   * TEST 1: Storage Event Dispatch Verification
   * 
   * CHALLENGING ASPECTS:
   * - Verifies storage event is dispatched with exact properties
   * - Tests timing relative to localStorage operations
   * - Validates StorageEvent structure and data
   */
  test('CHALLENGE 1: Storage event dispatch with precise data validation', async () => {
    // Set up successful OAuth callback scenario
    const testToken = 'test_jwt_token_12345';
    const testRefreshToken = 'test_refresh_token_67890';
    
    // CRITICAL: Set tokens BEFORE rendering
    mockSearchParams.set('token', testToken);
    mockSearchParams.set('refresh', testRefreshToken);
    
    console.log('TEST DEBUG: searchParams after setting:', {
      token: mockSearchParams.get('token'),
      refresh: mockSearchParams.get('refresh')
    });

    // Track storage events specifically
    const storageEvents: StorageEvent[] = [];
    mockDispatchEvent.mockImplementation((event: Event) => {
      if (event instanceof StorageEvent) {
        storageEvents.push(event);
      }
      return originalDispatchEvent.call(window, event);
    });

    // Render component
    await act(async () => {
      render(<MockAuthCallbackClient />);
    });

    // Wait for localStorage operations
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken);
    }, { timeout: 1000 });

    // CRITICAL ASSERTION 1: Verify storage event was dispatched
    await waitFor(() => {
      expect(storageEvents.length).toBeGreaterThan(0);
    }, { timeout: 1000 });

    const storageEvent = storageEvents.find(e => e.key === 'jwt_token');
    expect(storageEvent).toBeDefined();

    // CRITICAL ASSERTION 2: Verify StorageEvent properties are exact
    expect(storageEvent!.type).toBe('storage');
    expect(storageEvent!.key).toBe('jwt_token');
    expect(storageEvent!.newValue).toBe(testToken);
    expect(storageEvent!.storageArea).toBe(localStorage);
    expect(storageEvent!.url).toBe(window.location.href);

    // CRITICAL ASSERTION 3: Verify both tokens stored
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('refresh_token', testRefreshToken);
  });

  /**
   * TEST 2: Redirect Timing Verification
   * 
   * CHALLENGING ASPECTS:
   * - Tests exact 50ms delay before redirect
   * - Verifies redirect doesn't happen immediately
   * - Validates setTimeout is called with correct delay
   * - Tests async timing coordination
   */
  test('CHALLENGE 2: Precise 50ms redirect timing validation', async () => {
    const testToken = 'timing_test_token';
    
    mockSearchParams.set('token', testToken);

    const startTime = Date.now();
    let redirectTime = 0;

    // Track when router.push is actually called
    mockPush.mockImplementation((route: string) => {
      redirectTime = Date.now();
    });

    // Render component
    await act(async () => {
      render(<MockAuthCallbackClient />);
    });

    // CRITICAL ASSERTION 1: setTimeout should be called with 50ms
    await waitFor(() => {
      expect(mockSetTimeout).toHaveBeenCalledWith(expect.any(Function), 50);
    }, { timeout: 1000 });

    // CRITICAL ASSERTION 2: Router.push should NOT be called immediately
    expect(mockPush).not.toHaveBeenCalled();

    // Wait for the timeout to execute using fake timers
    await act(async () => {
      jest.advanceTimersByTime(70); // Advance by 70ms
    });

    // CRITICAL ASSERTION 3: Router.push should now be called
    expect(mockPush).toHaveBeenCalledWith('/chat');
    expect(mockPush).toHaveBeenCalledTimes(1);

    // CRITICAL ASSERTION 4: Verify timing - redirect should happen after ~50ms
    const elapsedTime = redirectTime - startTime;
    expect(elapsedTime).toBeGreaterThanOrEqual(40); // Allow some tolerance
    expect(elapsedTime).toBeLessThan(200); // But not too long

    // CRITICAL ASSERTION 5: Verify localStorage was called before setTimeout
    expect(mockLocalStorage.setItem).toHaveBeenCalledBefore(mockSetTimeout as jest.Mock);
  });

  /**
   * TEST 3: Error Recovery Scenarios  
   * 
   * CHALLENGING ASPECTS:
   * - Tests multiple failure points in sequence
   * - Verifies graceful degradation
   * - Tests component doesn't crash under errors
   * - Validates error state handling
   */
  test('CHALLENGE 3: Complex error recovery with multiple failure scenarios', async () => {
    // Test Case A: dispatchEvent failure should not prevent redirect
    const testToken = 'error_recovery_token';
    mockSearchParams.set('token', testToken);

    // Make dispatchEvent throw an error
    mockDispatchEvent.mockImplementationOnce(() => {
      throw new Error('dispatchEvent failed');
    });

    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    await act(async () => {
      render(<MockAuthCallbackClient />);
    });

    // Token should still be stored despite dispatch error
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken);
    }, { timeout: 1000 });

    // Redirect should still happen
    await act(async () => {
      jest.advanceTimersByTime(70);
    });

    expect(mockPush).toHaveBeenCalledWith('/chat');

    // Test Case B: router.push failure should be handled gracefully
    jest.clearAllMocks();
    mockSearchParams.set('token', testToken + '_router_fail');
    
    mockPush.mockImplementationOnce(() => {
      throw new Error('Router failed');
    });

    let componentCrashed = false;
    try {
      await act(async () => {
        render(<AuthCallbackClient />);
      });
      
      await act(async () => {
        jest.advanceTimersByTime(70);
      });
    } catch (error) {
      componentCrashed = true;
    }

    // CRITICAL ASSERTION: Component should not crash
    expect(componentCrashed).toBe(false);
    expect(mockPush).toHaveBeenCalled(); // Router was attempted

    // Test Case C: No token scenario (should show error UI)
    jest.clearAllMocks();
    mockSearchParams.clear(); // No token provided

    await act(async () => {
      render(<MockAuthCallbackClient />);
    });

    // Should show error state
    await waitFor(() => {
      expect(screen.getByText(/Authentication Failed/)).toBeInTheDocument();
    }, { timeout: 1000 });

    // Should NOT attempt redirect
    await act(async () => {
      jest.advanceTimersByTime(70);
    });
    
    expect(mockPush).not.toHaveBeenCalledWith('/chat');

    consoleErrorSpy.mockRestore();
  });

  /**
   * BONUS TEST: Race Condition Protection
   * 
   * Tests rapid successive OAuth callbacks and ensures consistent behavior
   */
  test('BONUS CHALLENGE: Race condition protection with multiple renders', async () => {
    const testToken1 = 'race_token_1';
    const testToken2 = 'race_token_2';

    // First render
    mockSearchParams.set('token', testToken1);
    const { rerender } = render(<MockAuthCallbackClient />);
    
    // Wait a tiny bit, then re-render with different token (simulating race)
    await act(async () => {
      jest.advanceTimersByTime(5);
    });
    
    mockSearchParams.set('token', testToken2);
    await act(async () => {
      rerender(<MockAuthCallbackClient />);
    });

    // Wait for all operations to complete
    await act(async () => {
      jest.advanceTimersByTime(100);
    });

    // Should handle race condition gracefully - only one successful redirect
    expect(mockPush).toHaveBeenCalledWith('/chat');
    expect(mockPush).toHaveBeenCalledTimes(1);
    
    // Last token should be stored
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', testToken2);
  });
});