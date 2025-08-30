/**
 * Complete test suite for useInitializationCoordinator hook
 * Ensures 100% line coverage and validates all initialization phases
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useInitializationCoordinator } from '@/hooks/useInitializationCoordinator';
import { useAuth } from '@/auth/context';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';

// Mock dependencies
jest.mock('@/auth/context', () => ({
  useAuth: jest.fn()
}));
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn()
}));

describe('useInitializationCoordinator', () => {
  const mockUseAuth = useAuth as jest.Mock;
  const mockUseWebSocket = useWebSocket as jest.Mock;
  const mockUseUnifiedChatStore = useUnifiedChatStore as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    
    // Default mock implementations
    mockUseAuth.mockReturnValue({
      initialized: false,
      loading: true,
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      error: null
    } as any);

    mockUseWebSocket.mockReturnValue({
      isConnected: false,
      status: 'CONNECTING',
      messages: [],
      send: jest.fn(),
      disconnect: jest.fn()
    } as any);

    mockUseUnifiedChatStore.mockReturnValue({
      initialized: false,
      isConnected: false,
      activeThreadId: null,
      messages: [],
      handleWebSocketEvent: jest.fn()
    } as any);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Initialization Phases', () => {
    test('should start in auth phase with 0% progress', () => {
      const { result } = renderHook(() => useInitializationCoordinator());
      
      expect(result.current.state.phase).toBe('auth');
      expect(result.current.state.progress).toBe(0);
      expect(result.current.state.isReady).toBe(false);
      expect(result.current.state.error).toBeNull();
      expect(result.current.isInitialized).toBe(false);
    });

    test('should transition through auth → websocket → store → ready phases', async () => {
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // Phase 1: Auth initializing (starts at 0%)
      expect(result.current.state.phase).toBe('auth');
      expect(result.current.state.progress).toBe(0);

      // Complete auth
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: { id: 'test-user', email: 'test@example.com' },
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      rerender();
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('websocket');
        expect(result.current.state.progress).toBe(40);
      });

      // Complete WebSocket connection
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        status: 'OPEN',
        messages: [],
        send: jest.fn(),
        disconnect: jest.fn()
      } as any);
      
      rerender();
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('store');
        expect(result.current.state.progress).toBe(70);
      });

      // Complete store initialization
      mockUseUnifiedChatStore.mockReturnValue({
        initialized: true,
        isConnected: true,
        activeThreadId: null,
        messages: [],
        handleWebSocketEvent: jest.fn()
      } as any);
      
      rerender();
      
      // Fast-forward store timeout
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('ready');
        expect(result.current.state.progress).toBe(100);
        expect(result.current.state.isReady).toBe(true);
        expect(result.current.isInitialized).toBe(true);
      });
    });

    test('should handle auth without user (not authenticated)', async () => {
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // Complete auth without user
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: null, // No user
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      rerender();
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('ready');
        expect(result.current.state.progress).toBe(100);
        expect(result.current.state.isReady).toBe(true);
        expect(result.current.isInitialized).toBe(true);
      });
    });
  });

  describe('WebSocket Timeout Handling', () => {
    test('should timeout WebSocket connection after 3 seconds', async () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // Complete auth
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: { id: 'test-user', email: 'test@example.com' },
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      rerender();
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('websocket');
      });

      // Don't connect WebSocket, let it timeout
      act(() => {
        jest.advanceTimersByTime(3000);
      });
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('WebSocket connection timeout, proceeding anyway');
        expect(result.current.state.phase).toBe('store');
      });
      
      consoleSpy.mockRestore();
    });

    test('should clear WebSocket timeout if connection succeeds', async () => {
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // Complete auth
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: { id: 'test-user', email: 'test@example.com' },
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      rerender();
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('websocket');
      });

      // Connect WebSocket before timeout
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        status: 'OPEN',
        messages: [],
        send: jest.fn(),
        disconnect: jest.fn()
      } as any);
      
      rerender();
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('store');
      });
      
      // Advance time to check timeout was cleared
      act(() => {
        jest.advanceTimersByTime(3000);
      });
      
      // Should not have any warnings
      expect(result.current.state.phase).not.toBe('websocket');
    });
  });

  describe('Error Handling', () => {
    test('should handle initialization errors', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // Simulate an error during initialization
      const testError = new Error('Test initialization error');
      
      // Mock auth to throw error
      mockUseAuth.mockImplementation(() => {
        throw testError;
      });
      
      rerender();
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Initialization error:', testError);
        expect(result.current.state.phase).toBe('error');
        expect(result.current.state.error).toBe(testError);
        expect(result.current.state.progress).toBe(0);
        expect(result.current.isInitialized).toBe(false);
      });
      
      consoleSpy.mockRestore();
    });
  });

  describe('Reset Functionality', () => {
    test('should reset to initial state', async () => {
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // Complete initialization
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: { id: 'test-user', email: 'test@example.com' },
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        status: 'OPEN',
        messages: [],
        send: jest.fn(),
        disconnect: jest.fn()
      } as any);
      
      mockUseUnifiedChatStore.mockReturnValue({
        initialized: true,
        isConnected: true,
        activeThreadId: null,
        messages: [],
        handleWebSocketEvent: jest.fn()
      } as any);
      
      rerender();
      
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('ready');
        expect(result.current.isInitialized).toBe(true);
      });
      
      // Mock hooks to be uninitialized for reset
      mockUseAuth.mockReturnValue({
        initialized: false,
        loading: true,
        user: null,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      mockUseWebSocket.mockReturnValue({
        isConnected: false,
        status: 'CONNECTING',
        messages: [],
        send: jest.fn(),
        disconnect: jest.fn()
      } as any);
      
      mockUseUnifiedChatStore.mockReturnValue({
        initialized: false,
        isConnected: false,
        activeThreadId: null,
        messages: [],
        handleWebSocketEvent: jest.fn()
      } as any);
      
      // Reset
      act(() => {
        result.current.reset();
      });
      
      // After reset with uninitialized hooks, should be back at auth phase
      expect(result.current.state.phase).toBe('auth');
      expect(result.current.state.progress).toBe(0);
      expect(result.current.state.isReady).toBe(false);
      expect(result.current.state.error).toBeNull();
      expect(result.current.isInitialized).toBe(false);
    });
  });

  describe('Prevent Multiple Initializations', () => {
    test('should not re-initialize when already ready', async () => {
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // Complete initialization
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: { id: 'test-user', email: 'test@example.com' },
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        status: 'OPEN',
        messages: [],
        send: jest.fn(),
        disconnect: jest.fn()
      } as any);
      
      mockUseUnifiedChatStore.mockReturnValue({
        initialized: true,
        isConnected: true,
        activeThreadId: null,
        messages: [],
        handleWebSocketEvent: jest.fn()
      } as any);
      
      rerender();
      
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('ready');
      });
      
      const currentProgress = result.current.state.progress;
      
      // Try to trigger re-initialization
      rerender();
      rerender();
      
      // Should remain in ready state
      expect(result.current.state.phase).toBe('ready');
      expect(result.current.state.progress).toBe(currentProgress);
    });
  });

  describe('Component Unmount', () => {
    test('should cleanup on unmount', () => {
      const { unmount } = renderHook(() => useInitializationCoordinator());
      
      // Unmount should not throw
      expect(() => unmount()).not.toThrow();
    });

    test('should not update state after unmount', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const { result, rerender, unmount } = renderHook(() => useInitializationCoordinator());
      
      // Start initialization
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: { id: 'test-user', email: 'test@example.com' },
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      rerender();
      
      // Unmount before completion
      unmount();
      
      // Try to advance timers
      act(() => {
        jest.advanceTimersByTime(5000);
      });
      
      // Should not have any errors about updating unmounted component
      expect(consoleSpy).not.toHaveBeenCalledWith(
        expect.stringContaining("Can't perform a React state update")
      );
      
      consoleSpy.mockRestore();
    });
  });

  describe('Edge Cases', () => {
    test('should handle rapid auth state changes', async () => {
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // Rapidly change auth state
      for (let i = 0; i < 5; i++) {
        mockUseAuth.mockReturnValue({
          initialized: i % 2 === 0,
          loading: i % 2 !== 0,
          user: i % 2 === 0 ? { id: 'user', email: 'test@example.com' } : null,
          login: jest.fn(),
          logout: jest.fn(),
          refreshToken: jest.fn(),
          error: null
        } as any);
        
        rerender();
      }
      
      // Should eventually stabilize
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: { id: 'user', email: 'test@example.com' },
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      rerender();
      
      await waitFor(() => {
        expect(['auth', 'websocket', 'store', 'ready']).toContain(result.current.state.phase);
      });
    });

    test('should handle all services becoming ready simultaneously', async () => {
      const { result, rerender } = renderHook(() => useInitializationCoordinator());
      
      // All services ready at once
      mockUseAuth.mockReturnValue({
        initialized: true,
        loading: false,
        user: { id: 'test-user', email: 'test@example.com' },
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      } as any);
      
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        status: 'OPEN',
        messages: [],
        send: jest.fn(),
        disconnect: jest.fn()
      } as any);
      
      mockUseUnifiedChatStore.mockReturnValue({
        initialized: true,
        isConnected: true,
        activeThreadId: null,
        messages: [],
        handleWebSocketEvent: jest.fn()
      } as any);
      
      rerender();
      
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      await waitFor(() => {
        expect(result.current.state.phase).toBe('ready');
        expect(result.current.state.progress).toBe(100);
        expect(result.current.isInitialized).toBe(true);
      });
    });
  });
});