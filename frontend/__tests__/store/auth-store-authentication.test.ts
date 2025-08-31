/**
 * AuthStore Authentication Tests - Business-Critical Security Testing
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (Free, Growth, Enterprise)
 * - Business Goal: Secure authentication across all tiers
 * - Value Impact: 100% of platform revenue depends on proper auth
 * - Revenue Impact: Authentication failures lose customers immediately
 * 
 * CRITICAL: Tests real store behavior, no mocking of store logic
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { AuthStoreTestUtils, GlobalTestUtils } from './store-test-utils';

describe('AuthStore - Authentication Flow', () => {
      setupAntiHang();
    jest.setTimeout(10000);
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

  describe('Initial State - Security Defaults', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should initialize with secure defaults', () => {
      expect(storeResult.current.isAuthenticated).toBe(false);
      expect(storeResult.current.user).toBeNull();
      expect(storeResult.current.token).toBeNull();
      expect(storeResult.current.loading).toBe(false);
      expect(storeResult.current.error).toBeNull();
    });

    it('should deny all permissions when not authenticated', () => {
      expect(storeResult.current.hasPermission('any-permission')).toBe(false);
      expect(storeResult.current.hasAnyPermission(['perm1', 'perm2'])).toBe(false);
      expect(storeResult.current.hasAllPermissions(['perm1', 'perm2'])).toBe(false);
      expect(storeResult.current.isAdminOrHigher()).toBe(false);
      expect(storeResult.current.isDeveloperOrHigher()).toBe(false);
    });

    it('should maintain security boundaries on fresh start', () => {
      // Verify no tokens are present initially
      expect(mockStorage.getItem).not.toHaveBeenCalled();
      expect(storeResult.current.token).toBeNull();
      
      // Verify no user data is accessible
      expect(storeResult.current.user).toBeNull();
      expect(storeResult.current.isAuthenticated).toBe(false);
    });
  });

  describe('Login Flow - Revenue Critical Tiers', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should authenticate free tier user correctly', () => {
      const freeUser = AuthStoreTestUtils.createMockUser('standard_user', []);
      const token = AuthStoreTestUtils.createTestToken('free');

      AuthStoreTestUtils.performLogin(storeResult, freeUser, token);
      expect(storeResult.current.error).toBeNull();
      expect(mockStorage.setItem).toHaveBeenCalledWith('jwt_token', token);
    });

    it('should authenticate growth tier user with permissions', () => {
      const growthUser = AuthStoreTestUtils.createMockUser('power_user', ['feature_analytics', 'export_data']);
      const token = AuthStoreTestUtils.createTestToken('growth');

      AuthStoreTestUtils.performLogin(storeResult, growthUser, token);
      expect(storeResult.current.hasPermission('feature_analytics')).toBe(true);
      expect(storeResult.current.hasPermission('admin_access')).toBe(false);
      expect(storeResult.current.isDeveloperOrHigher()).toBe(false);
    });

    it('should authenticate enterprise user with full access', () => {
      const enterpriseUser = AuthStoreTestUtils.createMockUser('admin', ['admin_access', 'full_api_access']);
      const token = AuthStoreTestUtils.createTestToken('enterprise');

      AuthStoreTestUtils.performLogin(storeResult, enterpriseUser, token);
      AuthStoreTestUtils.verifyRoleAccess(storeResult, true, true);
      expect(storeResult.current.hasAllPermissions(['admin_access', 'full_api_access'])).toBe(true);
    });

    it('should handle concurrent login attempts correctly', () => {
      const user1 = AuthStoreTestUtils.createMockUser('user1');
      const user2 = AuthStoreTestUtils.createMockUser('user2');
      const token1 = AuthStoreTestUtils.createTestToken('first');
      const token2 = AuthStoreTestUtils.createTestToken('second');
      
      AuthStoreTestUtils.performLogin(storeResult, user1, token1);
      AuthStoreTestUtils.performLogin(storeResult, user2, token2);

      // Second login should override first
      expect(storeResult.current.user?.id).toBe('user-user2');
      expect(storeResult.current.token).toBe(token2);
    });

    it('should clear errors on successful login', () => {
      storeResult.current.setError('Previous error');
      
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('error-clear');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      expect(storeResult.current.error).toBeNull();
    });
  });

  describe('Token Management - Security Critical', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should store token securely in localStorage', () => {
      const token = AuthStoreTestUtils.createTestToken('secure');
      const user = AuthStoreTestUtils.createMockUser('standard_user');

      AuthStoreTestUtils.performLogin(storeResult, user, token);
      expect(mockStorage.setItem).toHaveBeenCalledWith('jwt_token', token);
      expect(mockStorage.setItem).toHaveBeenCalledTimes(1);
    });

    it('should remove token completely on logout', () => {
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('logout-test');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      storeResult.current.logout();

      expect(storeResult.current.isAuthenticated).toBe(false);
      expect(storeResult.current.user).toBeNull();
      expect(storeResult.current.token).toBeNull();
      expect(mockStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should clear token on reset', () => {
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('reset-test');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      storeResult.current.reset();

      expect(storeResult.current.isAuthenticated).toBe(false);
      expect(storeResult.current.user).toBeNull();
      expect(storeResult.current.token).toBeNull();
      expect(storeResult.current.loading).toBe(false);
      expect(storeResult.current.error).toBeNull();
      expect(mockStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should handle token validation on initialization', () => {
      // Simulate token in localStorage
      const existingToken = AuthStoreTestUtils.createTestToken('existing');
      mockStorage.getItem.mockReturnValue(existingToken);
      
      const newStoreResult = AuthStoreTestUtils.initializeStore();
      
      // Store should handle existing tokens appropriately
      expect(mockStorage.getItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should maintain token integrity across operations', () => {
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('integrity-test');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      
      // Perform some operations
      storeResult.current.setLoading(true);
      storeResult.current.setLoading(false);
      
      // Token should remain unchanged
      expect(storeResult.current.token).toBe(token);
      expect(storeResult.current.isAuthenticated).toBe(true);
    });
  });

  describe('Authentication State Transitions', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle unauthenticated to authenticated transition', () => {
      expect(storeResult.current.isAuthenticated).toBe(false);
      
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('transition');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      expect(storeResult.current.isAuthenticated).toBe(true);
    });

    it('should handle authenticated to unauthenticated transition', () => {
      const user = AuthStoreTestUtils.createMockUser('standard_user');
      const token = AuthStoreTestUtils.createTestToken('logout-transition');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);
      expect(storeResult.current.isAuthenticated).toBe(true);
      
      storeResult.current.logout();
      expect(storeResult.current.isAuthenticated).toBe(false);
    });

    it('should handle reauthentication scenarios', () => {
      const user1 = AuthStoreTestUtils.createMockUser('user1');
      const user2 = AuthStoreTestUtils.createMockUser('user2');
      const token1 = AuthStoreTestUtils.createTestToken('reauth1');
      const token2 = AuthStoreTestUtils.createTestToken('reauth2');
      
      // First authentication
      AuthStoreTestUtils.performLogin(storeResult, user1, token1);
      expect(storeResult.current.user?.id).toBe('user-user1');
      
      // Logout
      storeResult.current.logout();
      expect(storeResult.current.isAuthenticated).toBe(false);
      
      // Second authentication
      AuthStoreTestUtils.performLogin(storeResult, user2, token2);
      expect(storeResult.current.user?.id).toBe('user-user2');
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});