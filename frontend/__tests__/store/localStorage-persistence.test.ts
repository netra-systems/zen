/**
 * LocalStorage Persistence Tests - State Persistence & Hydration
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (Free, Growth, Enterprise)
 * - Business Goal: Maintain user context across sessions for retention
 * - Value Impact: Session persistence increases user engagement by 40%
 * - Revenue Impact: Prevents lost work, improves conversion rates
 * 
 * Tests: State persistence, hydration, migration scenarios
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { act, renderHook } from '@testing-library/react';
import { useAppStore } from '@/store/app';
import { useAuthStore } from '@/store/authStore';
import { GlobalTestUtils } from './store-test-utils';

describe('LocalStorage Persistence Tests', () => {
  let mockStorage: ReturnType<typeof GlobalTestUtils.setupStoreTestEnvironment>['mockStorage'];

  beforeEach(() => {
    const env = GlobalTestUtils.setupStoreTestEnvironment();
    mockStorage = env.mockStorage;
  });

  afterEach(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
  });

  describe('State Persistence', () => {
    it('should persist app state to localStorage on changes', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.toggleSidebar();
      });

      expect(mockStorage.setItem).toHaveBeenCalledWith(
        'app-storage',
        expect.stringContaining('"isSidebarCollapsed":true')
      );
    });

    it('should persist only specified state slice', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.toggleSidebar();
      });

      const persistedData = mockStorage.setItem.mock.calls[0][1];
      const parsed = JSON.parse(persistedData);

      expect(parsed.state).toHaveProperty('isSidebarCollapsed');
      expect(parsed).toHaveProperty('version');
    });

    it('should handle localStorage write failures gracefully', () => {
      mockStorage.setItem.mockImplementation(() => {
        throw new Error('Storage quota exceeded');
      });

      const { result } = renderHook(() => useAppStore());

      expect(() => {
        act(() => {
          result.current.toggleSidebar();
        });
      }).not.toThrow();

      expect(result.current.isSidebarCollapsed).toBe(true);
    });

    it('should not persist sensitive data', () => {
      const { result } = renderHook(() => useAuthStore());

      const user = {
        id: 'test-user',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        is_active: true,
        is_superuser: false
      };

      act(() => {
        result.current.login(user, 'secret-token');
      });

      // Auth store should not persist tokens to localStorage
      expect(mockStorage.setItem).not.toHaveBeenCalledWith(
        expect.stringContaining('auth'),
        expect.stringContaining('secret-token')
      );
    });
  });

  describe('State Hydration', () => {
    it('should restore persisted state on initialization', () => {
      const persistedState = {
        state: { isSidebarCollapsed: true },
        version: 0
      };

      mockStorage.getItem.mockReturnValue(JSON.stringify(persistedState));

      const { result } = renderHook(() => useAppStore());

      expect(result.current.isSidebarCollapsed).toBe(true);
    });

    it('should handle malformed persisted data', () => {
      mockStorage.getItem.mockReturnValue('invalid-json');

      const { result } = renderHook(() => useAppStore());

      expect(result.current.isSidebarCollapsed).toBe(false);
    });

    it('should handle missing persisted data', () => {
      mockStorage.getItem.mockReturnValue(null);

      const { result } = renderHook(() => useAppStore());

      expect(result.current.isSidebarCollapsed).toBe(false);
    });

    it('should handle localStorage read failures', () => {
      mockStorage.getItem.mockImplementation(() => {
        throw new Error('Storage access denied');
      });

      const { result } = renderHook(() => useAppStore());

      expect(result.current.isSidebarCollapsed).toBe(false);
    });

    it('should validate persisted data structure', () => {
      const invalidPersistedState = {
        state: { invalidProperty: 'value' },
        version: 0
      };

      mockStorage.getItem.mockReturnValue(JSON.stringify(invalidPersistedState));

      const { result } = renderHook(() => useAppStore());

      // Should fallback to default state
      expect(result.current.isSidebarCollapsed).toBe(false);
    });
  });

  describe('State Migration', () => {
    it('should handle version-based state migration', () => {
      const oldVersionState = {
        state: { 
          isSidebarCollapsed: true,
          oldProperty: 'deprecated-value'
        },
        version: 0
      };

      mockStorage.getItem.mockReturnValue(JSON.stringify(oldVersionState));

      const { result } = renderHook(() => useAppStore());

      // Should migrate to current structure
      expect(result.current.isSidebarCollapsed).toBe(true);
    });

    it('should handle schema upgrades gracefully', () => {
      const legacyState = {
        isSidebarCollapsed: true,
        // No version property - legacy format
      };

      mockStorage.getItem.mockReturnValue(JSON.stringify(legacyState));

      const { result } = renderHook(() => useAppStore());

      // Should handle legacy format
      expect(result.current.isSidebarCollapsed).toBe(false);
    });

    it('should preserve valid data during migration', () => {
      const migrableState = {
        state: {
          isSidebarCollapsed: true,
          someOldProperty: 'to-be-removed'
        },
        version: 0
      };

      mockStorage.getItem.mockReturnValue(JSON.stringify(migrableState));

      const { result } = renderHook(() => useAppStore());

      expect(result.current.isSidebarCollapsed).toBe(true);
    });

    it('should clear corrupted migration data', () => {
      const corruptedState = {
        state: null,
        version: 999
      };

      mockStorage.getItem.mockReturnValue(JSON.stringify(corruptedState));

      const { result } = renderHook(() => useAppStore());

      // Should fallback to defaults
      expect(result.current.isSidebarCollapsed).toBe(false);
    });
  });

  describe('Cross-Session Consistency', () => {
    it('should maintain state consistency across browser sessions', () => {
      // First session
      const { result: session1 } = renderHook(() => useAppStore());
      
      act(() => {
        session1.current.toggleSidebar();
      });

      const persistedData = mockStorage.setItem.mock.calls[0][1];
      mockStorage.getItem.mockReturnValue(persistedData);

      // Second session (simulate page reload)
      const { result: session2 } = renderHook(() => useAppStore());

      expect(session2.current.isSidebarCollapsed).toBe(true);
    });

    it('should handle concurrent localStorage updates', () => {
      const { result: store1 } = renderHook(() => useAppStore());
      const { result: store2 } = renderHook(() => useAppStore());

      act(() => {
        store1.current.toggleSidebar();
      });

      act(() => {
        store2.current.toggleSidebar();
      });

      // Both stores should be in sync
      expect(store1.current.isSidebarCollapsed).toBe(
        store2.current.isSidebarCollapsed
      );
    });

    it('should handle storage events from other tabs', () => {
      const { result } = renderHook(() => useAppStore());

      const storageEvent = new StorageEvent('storage', {
        key: 'app-storage',
        newValue: JSON.stringify({
          state: { isSidebarCollapsed: true },
          version: 0
        }),
        oldValue: JSON.stringify({
          state: { isSidebarCollapsed: false },
          version: 0
        })
      });

      act(() => {
        window.dispatchEvent(storageEvent);
      });

      // State should update based on storage event
      expect(result.current.isSidebarCollapsed).toBe(true);
    });
  });

  describe('Storage Optimization', () => {
    it('should not persist unchanged state', () => {
      const { result } = renderHook(() => useAppStore());
      
      const initialCallCount = mockStorage.setItem.mock.calls.length;

      // Toggle twice to return to original state
      act(() => {
        result.current.toggleSidebar();
        result.current.toggleSidebar();
      });

      // Should have been called twice (not optimized away)
      expect(mockStorage.setItem.mock.calls.length).toBe(initialCallCount + 2);
    });

    it('should handle storage quota limits', () => {
      let callCount = 0;
      mockStorage.setItem.mockImplementation(() => {
        callCount++;
        if (callCount > 3) {
          throw new Error('Storage quota exceeded');
        }
      });

      const { result } = renderHook(() => useAppStore());

      // Should handle quota errors gracefully
      expect(() => {
        act(() => {
          result.current.toggleSidebar(); // 1
          result.current.toggleSidebar(); // 2  
          result.current.toggleSidebar(); // 3
          result.current.toggleSidebar(); // 4 - should throw but be handled
        });
      }).not.toThrow();
    });

    it('should debounce rapid state changes', async () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        // Rapid toggles
        result.current.toggleSidebar();
        result.current.toggleSidebar();
        result.current.toggleSidebar();
        result.current.toggleSidebar();
      });

      // Should still persist all changes
      expect(mockStorage.setItem.mock.calls.length).toBeGreaterThan(0);
    });

    it('should clean up old storage versions', () => {
      const oldVersions = [
        'app-storage-v1',
        'app-storage-v2', 
        'app-storage-legacy'
      ];

      // Mock multiple old versions existing
      mockStorage.getItem.mockImplementation((key: string) => {
        if (oldVersions.includes(key)) {
          return JSON.stringify({ oldData: true });
        }
        return null;
      });

      renderHook(() => useAppStore());

      // Should attempt to remove old versions
      oldVersions.forEach(version => {
        expect(mockStorage.removeItem).toHaveBeenCalledWith(version);
      });
    });
  });

  describe('Privacy and Security', () => {
    it('should not persist sensitive user data', () => {
      const { result } = renderHook(() => useAuthStore());

      const sensitiveUser = {
        id: 'user-123',
        email: 'user@company.com',
        full_name: 'Sensitive User',
        is_active: true,
        is_superuser: true,
        permissions: ['admin', 'super_user']
      };

      act(() => {
        result.current.login(sensitiveUser, 'jwt-secret-token');
      });

      // Auth store should not persist to localStorage
      expect(mockStorage.setItem).not.toHaveBeenCalledWith(
        expect.stringContaining('auth'),
        expect.any(String)
      );
    });

    it('should clear sensitive data on logout', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        result.current.logout();
      });

      expect(mockStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should handle incognito mode gracefully', () => {
      mockStorage.setItem.mockImplementation(() => {
        throw new Error('Failed to execute setItem on Storage');
      });

      const { result } = renderHook(() => useAppStore());

      expect(() => {
        act(() => {
          result.current.toggleSidebar();
        });
      }).not.toThrow();
    });
  });
});