import { act, renderHook } from '@testing-library/react';
import { useAppStore } from '@/store/app';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chat';
import { GlobalTestUtils } from './store-test-utils';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
foundation for all features and user data
 * - Revenue Impact: Store failures lose revenue - must be bulletproof
 * 
 * Tests: Store setup, middleware, persistence configuration
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { act, renderHook } from '@testing-library/react';
import { useAppStore } from '@/store/app';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chat';
import { GlobalTestUtils } from './store-test-utils';

describe('Store Configuration - Infrastructure Tests', () => {
    jest.setTimeout(10000);
  let mockStorage: ReturnType<typeof GlobalTestUtils.setupStoreTestEnvironment>['mockStorage'];

  beforeEach(() => {
    const env = GlobalTestUtils.setupStoreTestEnvironment();
    mockStorage = env.mockStorage;
    
    // Clear localStorage to ensure fresh state
    if (typeof window !== 'undefined') {
      window.localStorage.clear();
      window.sessionStorage.clear();
    }
  });

  afterEach(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Store Initialization', () => {
      jest.setTimeout(10000);
    it('should initialize app store with default state', () => {
      const { result } = renderHook(() => useAppStore());

      expect(result.current.isSidebarCollapsed).toBe(false);
      expect(typeof result.current.toggleSidebar).toBe('function');
    });

    it('should initialize auth store with secure defaults', () => {
      const { result } = renderHook(() => useAuthStore());

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should initialize chat store with empty state', () => {
      const { result } = renderHook(() => useChatStore());

      expect(result.current.messages).toEqual([]);
      expect(result.current.isProcessing).toBe(false);
      expect(result.current.activeThreadId).toBeNull();
      expect(result.current.subAgentName).toBe('Netra Agent');
    });

    it('should provide all required action methods', () => {
      const { result: appResult } = renderHook(() => useAppStore());
      const { result: authResult } = renderHook(() => useAuthStore());
      const { result: chatResult } = renderHook(() => useChatStore());

      // App store actions
      expect(typeof appResult.current.toggleSidebar).toBe('function');

      // Auth store actions
      expect(typeof authResult.current.login).toBe('function');
      expect(typeof authResult.current.logout).toBe('function');
      expect(typeof authResult.current.reset).toBe('function');

      // Chat store actions
      expect(typeof chatResult.current.addMessage).toBe('function');
      expect(typeof chatResult.current.clearMessages).toBe('function');
    });
  });

  describe('Middleware Configuration', () => {
      jest.setTimeout(10000);
    it('should configure persistence middleware for app store', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.toggleSidebar();
      });

      expect(mockStorage.setItem).toHaveBeenCalledWith(
        'app-storage',
        expect.stringContaining('"isSidebarCollapsed":true')
      );
    });

    it('should use immer middleware for auth store mutations', () => {
      const { result } = renderHook(() => useAuthStore());

      const user = {
        id: 'test-user',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        is_active: true,
        is_superuser: false
      };

      act(() => {
        result.current.login(user, 'test-token');
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(user);
      expect(result.current.token).toBe('test-token');
    });

    it('should handle state updates immutably', () => {
      const { result } = renderHook(() => useChatStore());
      const initialMessages = result.current.messages;

      const message = {
        id: 'msg-1',
        type: 'user' as const,
        content: 'Test message',
        created_at: new Date().toISOString(),
        displayed_to_user: true
      };

      act(() => {
        result.current.addMessage(message);
      });

      // Should be new array reference (immutable update)
      expect(result.current.messages).not.toBe(initialMessages);
      expect(result.current.messages).toHaveLength(1);
    });

    it('should maintain referential equality for unchanged state', () => {
      const { result } = renderHook(() => useChatStore());
      const initialMessages = result.current.messages;

      // Trigger an unrelated update
      act(() => {
        result.current.setProcessing(true);
      });

      // Messages array should remain the same reference
      expect(result.current.messages).toBe(initialMessages);
    });
  });

  describe('Persistence Configuration', () => {
      jest.setTimeout(10000);
    it('should persist app store state to localStorage', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.toggleSidebar();
      });

      expect(mockStorage.setItem).toHaveBeenCalledWith(
        'app-storage',
        expect.any(String)
      );
    });

    it('should partialize app store state correctly', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.toggleSidebar();
      });

      const persistedData = mockStorage.setItem.mock.calls[0][1];
      const parsed = JSON.parse(persistedData);

      expect(parsed.state).toHaveProperty('isSidebarCollapsed', true);
    });

    it('should handle localStorage unavailability gracefully', () => {
      // Mock localStorage to throw error
      mockStorage.setItem.mockImplementation(() => {
        throw new Error('localStorage not available');
      });

      const { result } = renderHook(() => useAppStore());

      expect(() => {
        act(() => {
          result.current.toggleSidebar();
        });
      }).not.toThrow();

      expect(result.current.isSidebarCollapsed).toBe(true);
    });

    it('should restore state from localStorage on initialization', () => {
      const persistedState = {
        state: { isSidebarCollapsed: true },
        version: 0
      };

      mockStorage.getItem.mockReturnValue(JSON.stringify(persistedState));

      const { result } = renderHook(() => useAppStore());

      expect(result.current.isSidebarCollapsed).toBe(true);
    });
  });

  describe('Store Isolation', () => {
      jest.setTimeout(10000);
    it('should maintain independent state between stores', () => {
      const { result: appResult } = renderHook(() => useAppStore());
      const { result: authResult } = renderHook(() => useAuthStore());
      const { result: chatResult } = renderHook(() => useChatStore());

      // Update app store
      act(() => {
        appResult.current.toggleSidebar();
      });

      // Other stores should be unaffected
      expect(authResult.current.isAuthenticated).toBe(false);
      expect(chatResult.current.messages).toEqual([]);
    });

    it('should handle concurrent store updates', async () => {
      const { result: appResult } = renderHook(() => useAppStore());
      const { result: authResult } = renderHook(() => useAuthStore());

      act(() => {
        appResult.current.toggleSidebar();
        authResult.current.setLoading(true);
      });

      expect(appResult.current.isSidebarCollapsed).toBe(true);
      expect(authResult.current.loading).toBe(true);
    });

    it('should provide stable selectors', () => {
      const { result } = renderHook(() => useAppStore());
      const toggleSidebar = result.current.toggleSidebar;

      act(() => {
        result.current.toggleSidebar();
      });

      // Action reference should remain stable
      expect(result.current.toggleSidebar).toBe(toggleSidebar);
    });
  });

  describe('Type Safety', () => {
      jest.setTimeout(10000);
    it('should enforce strong typing for store state', () => {
      const { result } = renderHook(() => useAppStore());

      // TypeScript should enforce boolean type for isSidebarCollapsed
      expect(typeof result.current.isSidebarCollapsed).toBe('boolean');
    });

    it('should enforce strong typing for action parameters', () => {
      const { result } = renderHook(() => useAuthStore());

      const user = {
        id: 'test',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        is_active: true,
        is_superuser: false
      };

      // Should accept valid user object without type errors
      expect(() => {
        act(() => {
          result.current.login(user, 'token');
        });
      }).not.toThrow();
    });

    it('should provide correct return types for selectors', () => {
      const { result } = renderHook(() => useAuthStore());

      expect(typeof result.current.hasPermission('test')).toBe('boolean');
      expect(typeof result.current.isAdminOrHigher()).toBe('boolean');
    });
  });
});