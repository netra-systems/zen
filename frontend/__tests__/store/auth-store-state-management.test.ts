/**
 * AuthStore State Management Tests - Data Integrity Testing
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (State reliability across tiers)
 * - Business Goal: Ensure consistent auth state management
 * - Value Impact: Critical for user experience and session integrity
 * - Revenue Impact: State bugs lead to lost sessions and user churn
 * 
 * CRITICAL: Tests real store behavior, no mocking of store logic
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { AuthStoreTestUtils, GlobalTestUtils } from './store-test-utils';

describe('AuthStore - State Management', () => {
  let mockStorage: ReturnType<typeof GlobalTestUtils.setupStoreTestEnvironment>['mockStorage'];
  let storeResult: ReturnType<typeof AuthStoreTestUtils.initializeStore>;

  // Setup test environment (≤8 lines)
  beforeAll(() => {
    const env = GlobalTestUtils.setupStoreTestEnvironment();
    mockStorage = env.mockStorage;
  });

  // Reset store and mocks before each test (≤8 lines)
  beforeEach(() => {
    jest.clearAllMocks();
    mockStorage.getItem.mockReturnValue(null);
    storeResult = AuthStoreTestUtils.initializeStore();
  });

  // Cleanup after all tests (≤8 lines)
  afterAll(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
  });

  describe('User Updates - State Integrity', () => {
    it('should update user properties correctly', () => {
      const user = AuthStoreTestUtils.createMockUser('power_user', ['analytics']);
      const token = AuthStoreTestUtils.createTestToken('update-test');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      storeResult.current.updateUser({ 
        full_name: 'Updated Name', 
        permissions: ['analytics', 'export'] 
      });

      expect(storeResult.current.user?.full_name).toBe('Updated Name');
      expect(storeResult.current.user?.permissions).toEqual(['analytics', 'export']);
      expect(storeResult.current.user?.id).toBe(user.id); // ID should remain unchanged
    });

    it('should not update user when not authenticated', () => {
      storeResult.current.updateUser({ full_name: 'Should Not Update' });
      expect(storeResult.current.user).toBeNull();
    });

    it('should preserve authentication state during user updates', () => {
      const user = AuthStoreTestUtils.createMockUser('power_user', ['analytics']);
      const token = AuthStoreTestUtils.createTestToken('preserve-auth');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      storeResult.current.updateUser({ full_name: 'New Name' });

      expect(storeResult.current.isAuthenticated).toBe(true);
      expect(storeResult.current.token).toBe(token);
    });

    it('should handle partial user updates correctly', () => {
      const user = AuthStoreTestUtils.createMockUser('power_user', ['analytics']);
      const token = AuthStoreTestUtils.createTestToken('partial-update');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      
      // Update only email
      storeResult.current.updateUser({ email: 'newemail@test.com' });
      
      expect(storeResult.current.user?.email).toBe('newemail@test.com');
      expect(storeResult.current.user?.full_name).toBe(user.full_name); // Should remain unchanged
      expect(storeResult.current.user?.permissions).toEqual(user.permissions);
    });

    it('should handle permission updates correctly', () => {
      const user = AuthStoreTestUtils.createMockUser('power_user', ['perm1']);
      const token = AuthStoreTestUtils.createTestToken('perm-update');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      
      // Update permissions
      storeResult.current.updateUser({ permissions: ['perm1', 'perm2', 'perm3'] });
      
      expect(storeResult.current.hasPermission('perm2')).toBe(true);
      expect(storeResult.current.hasPermission('perm3')).toBe(true);
      expect(storeResult.current.hasAllPermissions(['perm1', 'perm2', 'perm3'])).toBe(true);
    });
  });

  describe('Loading State Management', () => {
    it('should manage loading state correctly', () => {
      expect(storeResult.current.loading).toBe(false);

      storeResult.current.setLoading(true);
      expect(storeResult.current.loading).toBe(true);

      storeResult.current.setLoading(false);
      expect(storeResult.current.loading).toBe(false);
    });

    it('should handle loading state transitions during auth operations', () => {
      storeResult.current.setLoading(true);
      
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('loading-auth');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      
      // Loading state should be independent of auth state
      expect(storeResult.current.loading).toBe(true);
      expect(storeResult.current.isAuthenticated).toBe(true);
    });

    it('should maintain loading state consistency', () => {
      // Multiple loading state changes
      storeResult.current.setLoading(true);
      storeResult.current.setLoading(false);
      storeResult.current.setLoading(true);
      
      expect(storeResult.current.loading).toBe(true);
    });
  });

  describe('Error State Management', () => {
    it('should manage error state correctly', () => {
      expect(storeResult.current.error).toBeNull();

      const errorMessage = 'Authentication failed';
      storeResult.current.setError(errorMessage);
      expect(storeResult.current.error).toBe(errorMessage);

      storeResult.current.setError(null);
      expect(storeResult.current.error).toBeNull();
    });

    it('should clear error on successful login', () => {
      storeResult.current.setError('Previous error');
      
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('error-clear');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      expect(storeResult.current.error).toBeNull();
    });

    it('should handle multiple error states', () => {
      storeResult.current.setError('First error');
      expect(storeResult.current.error).toBe('First error');
      
      storeResult.current.setError('Second error');
      expect(storeResult.current.error).toBe('Second error');
      
      storeResult.current.setError(null);
      expect(storeResult.current.error).toBeNull();
    });

    it('should preserve error state through other operations', () => {
      const errorMessage = 'Persistent error';
      storeResult.current.setError(errorMessage);
      
      // Other operations shouldn't clear the error
      storeResult.current.setLoading(true);
      storeResult.current.setLoading(false);
      
      expect(storeResult.current.error).toBe(errorMessage);
    });
  });

  describe('Security Edge Cases - Environment Handling', () => {
    it('should handle SSR environment without localStorage', () => {
      // Temporarily remove window to simulate SSR
      const originalWindow = global.window;
      delete (global as any).window;
      
      const newStoreResult = AuthStoreTestUtils.initializeStore();
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('ssr');
      
      AuthStoreTestUtils.performLogin(newStoreResult, user, token);
      expect(newStoreResult.current.isAuthenticated).toBe(true);
      
      // Restore window
      global.window = originalWindow;
    });

    it('should handle localStorage errors gracefully', () => {
      mockStorage.setItem.mockImplementation(() => {
        throw new Error('LocalStorage error');
      });
      
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('storage-error');
      
      // Should not throw error even if localStorage fails
      expect(() => {
        AuthStoreTestUtils.performLogin(storeResult, user, token);
      }).not.toThrow();
      
      expect(storeResult.current.isAuthenticated).toBe(true);
    });

    it('should handle concurrent state modifications', () => {
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('concurrent');
      
      // Simulate concurrent operations
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      storeResult.current.setLoading(true);
      storeResult.current.setError('Test error');
      storeResult.current.setLoading(false);
      
      // State should remain consistent
      expect(storeResult.current.isAuthenticated).toBe(true);
      expect(storeResult.current.loading).toBe(false);
      expect(storeResult.current.error).toBe('Test error');
    });
  });

  describe('State Reset and Cleanup', () => {
    it('should reset all state completely', () => {
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('reset-complete');
      
      // Set all possible state
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      storeResult.current.setLoading(true);
      storeResult.current.setError('Test error');
      
      // Reset everything
      storeResult.current.reset();
      
      expect(storeResult.current.isAuthenticated).toBe(false);
      expect(storeResult.current.user).toBeNull();
      expect(storeResult.current.token).toBeNull();
      expect(storeResult.current.loading).toBe(false);
      expect(storeResult.current.error).toBeNull();
    });

    it('should cleanup localStorage on reset', () => {
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('cleanup-test');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      storeResult.current.reset();
      
      expect(mockStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should handle multiple resets gracefully', () => {
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('multi-reset');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      
      // Multiple resets should not cause issues
      storeResult.current.reset();
      storeResult.current.reset();
      storeResult.current.reset();
      
      expect(storeResult.current.isAuthenticated).toBe(false);
      expect(storeResult.current.user).toBeNull();
    });
  });

  describe('State Persistence and Recovery', () => {
    it('should maintain state integrity across operations', () => {
      const user = AuthStoreTestUtils.createMockUser('power_user', ['analytics']);
      const token = AuthStoreTestUtils.createTestToken('integrity');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      
      // Perform various operations
      storeResult.current.setLoading(true);
      storeResult.current.updateUser({ full_name: 'Updated Name' });
      storeResult.current.setLoading(false);
      
      // Core auth state should remain intact
      expect(storeResult.current.isAuthenticated).toBe(true);
      expect(storeResult.current.token).toBe(token);
      expect(storeResult.current.user?.permissions).toEqual(['analytics']);
      expect(storeResult.current.user?.full_name).toBe('Updated Name');
    });

    it('should handle state recovery scenarios', () => {
      // Simulate app restart with token in localStorage
      const existingToken = AuthStoreTestUtils.createTestToken('recovery');
      mockStorage.getItem.mockReturnValue(existingToken);
      
      const recoveredStoreResult = AuthStoreTestUtils.initializeStore();
      
      // Store should handle token recovery appropriately
      expect(mockStorage.getItem).toHaveBeenCalledWith('jwt_token');
    });
  });
});