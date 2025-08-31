/**
 * Chat First-Time Page Load Glitch Test Suite
 * 
 * This test suite is designed to detect and reproduce the container reload glitch
 * that occurs during first-time page load of the chat interface. The issue manifests
 * as multiple re-renders and container remounts, causing visual glitches.
 * 
 * EXPECTED FAILURES:
 * These tests are written to FAIL when the glitch is present and PASS when fixed.
 * 
 * @compliance testing.xml - Real world test scenarios
 * @compliance type_safety.xml - Strongly typed test implementations
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/context';
import { AuthGuard } from '@/components/AuthGuard';
import MainChat from '@/components/chat/MainChat';
import ChatPage from '@/app/chat/page';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useAuth } from '@/auth/context';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { logger } from '@/lib/logger';

// Mock modules
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/chat',
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => ({
    status: 'CONNECTING',
    messages: [],
    send: jest.fn(),
    disconnect: jest.fn(),
    isConnected: false
  }))
}));
jest.mock('@/hooks/useInitializationCoordinator', () => ({
  useInitializationCoordinator: () => ({
    state: {
      phase: 'ready',
      isReady: true,
      error: null,
      progress: 100
    },
    reset: jest.fn(),
    isInitialized: true
  })
}));
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
    trackError: jest.fn(),
    trackPageView: jest.fn(),
  }),
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: () => ({
    currentThreadId: null,
    isNavigating: false,
  }),
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: jest.fn(),
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => ({
    shouldShowLoading: false,
    shouldShowEmptyState: true,
    shouldShowExamplePrompts: false,
    loadingMessage: 'Loading...'
  })
}));

// Track component lifecycle events
interface LifecycleTracker {
  mounts: string[];
  unmounts: string[];
  renders: string[];
  authChecks: number;
  loadingStateChanges: string[];
  storeUpdates: string[];
}

const createLifecycleTracker = (): LifecycleTracker => ({
  mounts: [],
  unmounts: [],
  renders: [],
  authChecks: 0,
  loadingStateChanges: [],
  storeUpdates: [],
});

describe('Chat First-Time Page Load Glitch Detection', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let lifecycleTracker: LifecycleTracker;
  let mockWebSocket: any;
  let consoleErrorSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;

  beforeEach(() => {
    lifecycleTracker = createLifecycleTracker();
    
    // Suppress expected console errors/warnings
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
    
    // Setup WebSocket mock
    mockWebSocket = {
      status: 'CONNECTING',
      messages: [],
      send: jest.fn(),
      disconnect: jest.fn(),
      isConnected: false
    };
    // Update the mock implementation
    const useWebSocketMock = require('@/hooks/useWebSocket').useWebSocket;
    useWebSocketMock.mockImplementation(() => mockWebSocket);
    
    // Reset stores
    useUnifiedChatStore.setState({
      isConnected: false,
      activeThreadId: null,
      messages: [],
      isThreadLoading: false,
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      isProcessing: false,
      currentRunId: null,
    });
    
    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    jest.clearAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  /**
   * Test 1: Component should not remount multiple times during initial load
   * EXPECTED TO FAIL: Components currently remount 2-3 times
   */
  test('should not remount MainChat component multiple times on first load', async () => {
    const MainChatTracker = () => {
      React.useEffect(() => {
        lifecycleTracker.mounts.push('MainChat');
        return () => {
          lifecycleTracker.unmounts.push('MainChat');
        };
      }, []);
      
      lifecycleTracker.renders.push('MainChat');
      return <MainChat />;
    };

    const { rerender } = render(
      <AuthProvider>
        <AuthGuard>
          <MainChatTracker />
        </AuthGuard>
      </AuthProvider>
    );

    // Simulate WebSocket connection
    await act(async () => {
      mockWebSocket.status = 'OPEN';
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Simulate auth completion
    await act(async () => {
      localStorage.setItem('jwt_token', 'test-token');
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Wait for component to stabilize
    await waitFor(() => {
      expect(screen.queryByTestId('main-chat')).toBeInTheDocument();
    }, { timeout: 3000 });

    // ASSERTION: Component should mount exactly once
    expect(lifecycleTracker.mounts.filter(m => m === 'MainChat').length).toBe(1);
    expect(lifecycleTracker.unmounts.filter(m => m === 'MainChat').length).toBe(0);
  });

  /**
   * Test 2: Loading states should transition smoothly without cycling
   * EXPECTED TO FAIL: Loading states currently cycle multiple times
   */
  test('should transition through loading states without cycling', async () => {
    const loadingStates: string[] = [];
    
    const LoadingStateTracker = () => {
      const { loadingState } = useLoadingState();
      
      React.useEffect(() => {
        loadingStates.push(loadingState);
      }, [loadingState]);
      
      return <div data-testid="loading-state">{loadingState}</div>;
    };

    render(
      <AuthProvider>
        <LoadingStateTracker />
      </AuthProvider>
    );

    // Simulate initialization sequence
    await act(async () => {
      // Step 1: WebSocket connecting
      mockWebSocket.status = 'CONNECTING';
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Step 2: WebSocket connected
      mockWebSocket.status = 'OPEN';
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Step 3: Auth completed
      localStorage.setItem('jwt_token', 'test-token');
      await new Promise(resolve => setTimeout(resolve, 50));
    });

    // Analyze state transitions
    const uniqueStates = [...new Set(loadingStates)];
    const stateTransitions = loadingStates.join(' -> ');
    
    // ASSERTIONS:
    // 1. Should not cycle back to previous states
    const hasCycle = loadingStates.some((state, index) => {
      const previousIndex = loadingStates.indexOf(state);
      return previousIndex !== index; // State appeared before
    });
    expect(hasCycle).toBe(false);
    
    // 2. Should have a logical progression
    expect(uniqueStates.length).toBeLessThanOrEqual(5); // Max 5 unique states
    
    // 3. Should not have rapid state changes (more than 10 transitions)
    expect(loadingStates.length).toBeLessThanOrEqual(10);
  });

  /**
   * Test 3: Auth flow should not trigger multiple re-renders
   * EXPECTED TO FAIL: Auth currently triggers 3-4 re-renders
   */
  test('should not trigger excessive re-renders during auth flow', async () => {
    let renderCount = 0;
    let authCheckCount = 0;
    
    const AuthFlowTracker = () => {
      const { user, loading, initialized } = useAuth();
      
      React.useEffect(() => {
        if (!loading && initialized) {
          authCheckCount++;
        }
      }, [loading, initialized]);
      
      renderCount++;
      
      return (
        <div data-testid="auth-tracker">
          {loading ? 'Loading' : user ? 'Authenticated' : 'Not Authenticated'}
        </div>
      );
    };

    const { rerender } = render(
      <AuthProvider>
        <AuthFlowTracker />
      </AuthProvider>
    );

    // Simulate successful auth
    await act(async () => {
      localStorage.setItem('jwt_token', 'test-token');
      localStorage.setItem('refresh_token', 'test-refresh');
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    // Force a rerender to check stability
    rerender(
      <AuthProvider>
        <AuthFlowTracker />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-tracker')).toHaveTextContent('Authenticated');
    });

    // ASSERTIONS:
    // 1. Should not render more than 5 times during auth
    expect(renderCount).toBeLessThanOrEqual(5);
    
    // 2. Should check auth state at most twice
    expect(authCheckCount).toBeLessThanOrEqual(2);
  });

  /**
   * Test 4: Store updates should not cause cascading re-renders
   * EXPECTED TO FAIL: Store updates currently cascade
   */
  test('should not cascade store updates on initial load', async () => {
    const storeUpdates: string[] = [];
    
    const StoreUpdateTracker = () => {
      const store = useUnifiedChatStore();
      
      React.useEffect(() => {
        const updateType = determineUpdateType(store);
        if (updateType) {
          storeUpdates.push(updateType);
        }
      });
      
      return <div data-testid="store-tracker">Ready</div>;
    };
    
    function determineUpdateType(store: any): string | null {
      if (store.isConnected) return 'connection';
      if (store.activeThreadId) return 'thread';
      if (store.messages.length > 0) return 'messages';
      if (store.isProcessing) return 'processing';
      return null;
    }

    render(
      <AuthProvider>
        <StoreUpdateTracker />
      </AuthProvider>
    );

    // Simulate typical initialization sequence
    await act(async () => {
      // Connection established
      useUnifiedChatStore.setState({ isConnected: true });
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Thread selected
      useUnifiedChatStore.setState({ activeThreadId: 'test-thread' });
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Messages loaded
      useUnifiedChatStore.setState({ 
        messages: [{ id: '1', content: 'Test' }] 
      });
      await new Promise(resolve => setTimeout(resolve, 50));
    });

    // ASSERTIONS:
    // 1. Each update type should occur at most once
    const updateCounts = storeUpdates.reduce((acc, update) => {
      acc[update] = (acc[update] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    Object.entries(updateCounts).forEach(([type, count]) => {
      expect(count).toBe(1); // Each update should happen exactly once
    });
    
    // 2. Total updates should be minimal
    expect(storeUpdates.length).toBeLessThanOrEqual(3);
  });

  /**
   * Test 5: WebSocket reconnection should not cause full page reload
   * EXPECTED TO FAIL: WebSocket reconnection causes remounts
   */
  test('should handle WebSocket reconnection without remounting components', async () => {
    const mountTracker = { count: 0 };
    
    const WebSocketTracker = () => {
      React.useEffect(() => {
        mountTracker.count++;
      }, []);
      
      return <MainChat />;
    };

    render(
      <AuthProvider>
        <AuthGuard>
          <WebSocketTracker />
        </AuthGuard>
      </AuthProvider>
    );

    // Initial connection
    await act(async () => {
      mockWebSocket.status = 'OPEN';
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    const initialMountCount = mountTracker.count;

    // Simulate disconnect and reconnect
    await act(async () => {
      mockWebSocket.status = 'CLOSED';
      await new Promise(resolve => setTimeout(resolve, 100));
      
      mockWebSocket.status = 'RECONNECTING';
      await new Promise(resolve => setTimeout(resolve, 100));
      
      mockWebSocket.status = 'OPEN';
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // ASSERTION: Component should not remount on reconnection
    expect(mountTracker.count).toBe(initialMountCount);
  });

  /**
   * Test 6: Thread loading should not cause container flicker
   * EXPECTED TO FAIL: Thread loading causes visible flicker
   */
  test('should load thread without container flicker', async () => {
    const visibilityChanges: string[] = [];
    
    const ThreadLoadTracker = () => {
      const containerRef = React.useRef<HTMLDivElement>(null);
      
      React.useEffect(() => {
        const observer = new MutationObserver((mutations) => {
          mutations.forEach((mutation) => {
            if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
              const element = mutation.target as HTMLElement;
              visibilityChanges.push(element.style.display || 'block');
            }
          });
        });
        
        if (containerRef.current) {
          observer.observe(containerRef.current, {
            attributes: true,
            attributeFilter: ['style'],
          });
        }
        
        return () => observer.disconnect();
      }, []);
      
      return (
        <div ref={containerRef} data-testid="thread-container">
          <MainChat />
        </div>
      );
    };

    render(
      <AuthProvider>
        <ThreadLoadTracker />
      </AuthProvider>
    );

    // Simulate thread loading
    await act(async () => {
      useUnifiedChatStore.setState({ isThreadLoading: true });
      await new Promise(resolve => setTimeout(resolve, 50));
      
      useUnifiedChatStore.setState({ 
        isThreadLoading: false,
        messages: [{ id: '1', content: 'Loaded message' }]
      });
      await new Promise(resolve => setTimeout(resolve, 50));
    });

    // ASSERTION: Container should not flicker (hide/show)
    const hasFlicker = visibilityChanges.some((change, index) => {
      if (index === 0) return false;
      const prev = visibilityChanges[index - 1];
      return (prev === 'none' && change === 'block') || 
             (prev === 'block' && change === 'none');
    });
    
    expect(hasFlicker).toBe(false);
  });

  /**
   * Test 7: Performance - Initial render should be fast
   * EXPECTED TO FAIL: Initial render takes > 500ms
   */
  test('should complete initial render within performance budget', async () => {
    const startTime = performance.now();
    let firstRenderTime = 0;
    
    const PerformanceTracker = () => {
      React.useEffect(() => {
        if (firstRenderTime === 0) {
          firstRenderTime = performance.now() - startTime;
        }
      }, []);
      
      return <ChatPage />;
    };

    const { container } = render(
      <AuthProvider>
        <PerformanceTracker />
      </AuthProvider>
    );

    // Wait for initial render to complete
    await waitFor(() => {
      expect(container.querySelector('[data-testid="main-chat"], [data-testid="loading"]'))
        .toBeInTheDocument();
    }, { timeout: 1000 });

    const totalRenderTime = performance.now() - startTime;

    // ASSERTIONS:
    // 1. First render should be under 100ms
    expect(firstRenderTime).toBeLessThan(100);
    
    // 2. Total initial load should be under 500ms
    expect(totalRenderTime).toBeLessThan(500);
  });

  /**
   * Test 8: Memory leaks - Components should clean up properly
   * EXPECTED TO FAIL: Memory leaks from unmounted components
   */
  test('should not leak memory from unmounted components', async () => {
    const activeTimers: NodeJS.Timeout[] = [];
    const activeIntervals: NodeJS.Timeout[] = [];
    const activeListeners: Array<{ type: string; listener: Function }> = [];
    
    // Mock timers and track them
    const originalSetTimeout = global.setTimeout;
    const originalSetInterval = global.setInterval;
    const originalAddEventListener = window.addEventListener;
    
    global.setTimeout = jest.fn((fn, delay) => {
      const timer = originalSetTimeout(fn, delay);
      activeTimers.push(timer);
      return timer;
    }) as any;
    
    global.setInterval = jest.fn((fn, delay) => {
      const interval = originalSetInterval(fn, delay);
      activeIntervals.push(interval);
      return interval;
    }) as any;
    
    window.addEventListener = jest.fn((type, listener) => {
      activeListeners.push({ type, listener });
      return originalAddEventListener.call(window, type, listener);
    }) as any;

    const { unmount } = render(
      <AuthProvider>
        <AuthGuard>
          <MainChat />
        </AuthGuard>
      </AuthProvider>
    );

    // Let component initialize
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    const timersBeforeUnmount = activeTimers.length;
    const intervalsBeforeUnmount = activeIntervals.length;
    const listenersBeforeUnmount = activeListeners.length;

    // Unmount component
    unmount();

    // Check for cleanup
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Restore original functions
    global.setTimeout = originalSetTimeout;
    global.setInterval = originalSetInterval;
    window.addEventListener = originalAddEventListener;

    // ASSERTIONS:
    // 1. All timers should be cleared
    expect(activeTimers.filter(t => t._destroyed !== true).length).toBe(0);
    
    // 2. All intervals should be cleared
    expect(activeIntervals.filter(i => i._destroyed !== true).length).toBe(0);
    
    // 3. Event listeners should be minimal (some global ones are ok)
    expect(activeListeners.length).toBeLessThanOrEqual(5);
  });
});

/**
 * Integration Test Suite - Full Page Load Scenario
 */
describe('Chat Page Full Load Integration', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  /**
   * Test 9: Complete first-time user flow
   * EXPECTED TO FAIL: Multiple issues in complete flow
   */
  test('should handle complete first-time user flow smoothly', async () => {
    const flowEvents: string[] = [];
    
    // Track all major events
    const originalSetState = useUnifiedChatStore.setState;
    useUnifiedChatStore.setState = jest.fn((update) => {
      flowEvents.push('store-update');
      return originalSetState(update);
    }) as any;

    const { container } = render(
      <AuthProvider>
        <ChatPage />
      </AuthProvider>
    );

    // Step 1: Initial page load
    flowEvents.push('initial-render');
    
    // Step 2: Simulate OAuth callback with tokens
    await act(async () => {
      const searchParams = new URLSearchParams({
        token: 'oauth-token',
        refresh: 'oauth-refresh'
      });
      window.history.pushState({}, '', `/chat?${searchParams}`);
      flowEvents.push('oauth-redirect');
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Step 3: WebSocket connection
    await act(async () => {
      mockWebSocket.status = 'OPEN';
      flowEvents.push('websocket-open');
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Step 4: User types first message
    const input = container.querySelector('input, textarea');
    if (input) {
      await userEvent.type(input, 'Hello, Netra!');
      flowEvents.push('user-input');
    }

    // Analyze the flow
    const duplicateEvents = flowEvents.filter((event, index) => 
      flowEvents.indexOf(event) !== index
    );

    // ASSERTIONS:
    // 1. No duplicate major events
    expect(duplicateEvents.length).toBe(0);
    
    // 2. Events should follow logical order
    const expectedOrder = [
      'initial-render',
      'store-update',
      'oauth-redirect',
      'websocket-open',
      'user-input'
    ];
    
    const actualOrder = flowEvents.filter(e => expectedOrder.includes(e));
    expect(actualOrder).toEqual(expect.arrayContaining(expectedOrder));
    
    // 3. Total events should be reasonable
    expect(flowEvents.length).toBeLessThanOrEqual(15);
  });

  /**
   * Test 10: Concurrent operations should not cause race conditions
   * EXPECTED TO FAIL: Race conditions exist
   */
  test('should handle concurrent operations without race conditions', async () => {
    const raceConditions: string[] = [];
    let authCompleted = false;
    let wsConnected = false;
    let threadLoaded = false;

    const RaceConditionDetector = () => {
      const { user, loading } = useAuth();
      const { isConnected } = useUnifiedChatStore();
      const { activeThreadId } = useUnifiedChatStore();

      React.useEffect(() => {
        if (user && !loading && !authCompleted) {
          authCompleted = true;
          if (wsConnected && !isConnected) {
            raceConditions.push('auth-ws-race');
          }
        }
      }, [user, loading, isConnected]);

      React.useEffect(() => {
        if (isConnected && !wsConnected) {
          wsConnected = true;
          if (threadLoaded && !activeThreadId) {
            raceConditions.push('ws-thread-race');
          }
        }
      }, [isConnected, activeThreadId]);

      React.useEffect(() => {
        if (activeThreadId && !threadLoaded) {
          threadLoaded = true;
          if (!wsConnected && isConnected) {
            raceConditions.push('thread-ws-race');
          }
        }
      }, [activeThreadId, isConnected]);

      return <MainChat />;
    };

    render(
      <AuthProvider>
        <RaceConditionDetector />
      </AuthProvider>
    );

    // Trigger all operations concurrently
    await Promise.all([
      // Auth completion
      act(async () => {
        localStorage.setItem('jwt_token', 'test-token');
      }),
      // WebSocket connection
      act(async () => {
        mockWebSocket.status = 'OPEN';
        useUnifiedChatStore.setState({ isConnected: true });
      }),
      // Thread loading
      act(async () => {
        useUnifiedChatStore.setState({ 
          activeThreadId: 'test-thread',
          isThreadLoading: true 
        });
      })
    ]);

    // Wait for stabilization
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    // ASSERTION: No race conditions detected
    expect(raceConditions).toHaveLength(0);
  });
});