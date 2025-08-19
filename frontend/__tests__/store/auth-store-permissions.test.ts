/**
 * AuthStore Permissions Tests - Revenue Protection Testing
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (Tier-based feature access)
 * - Business Goal: Enforce proper tier boundaries and prevent revenue leakage
 * - Value Impact: Critical for monetization model integrity
 * - Revenue Impact: Permission failures allow free access to paid features
 * 
 * CRITICAL: Tests real store behavior, no mocking of store logic
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { AuthStoreTestUtils, GlobalTestUtils } from './store-test-utils';

describe('AuthStore - Permission System', () => {
  let storeResult: ReturnType<typeof AuthStoreTestUtils.initializeStore>;

  // Setup test environment (≤8 lines)
  beforeAll(() => {
    GlobalTestUtils.setupStoreTestEnvironment();
  });

  // Reset store before each test (≤8 lines)
  beforeEach(() => {
    jest.clearAllMocks();
    storeResult = AuthStoreTestUtils.initializeStore();
  });

  // Cleanup after all tests (≤8 lines)
  afterAll(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
  });

  describe('Free Tier Limitations - Revenue Protection', () => {
    it('should enforce free tier limitations strictly', () => {
      const freeUser = AuthStoreTestUtils.createMockUser('standard_user', []);
      const token = AuthStoreTestUtils.createTestToken('free');
      
      AuthStoreTestUtils.performLogin(storeResult, freeUser, token);

      // Free tier should not have paid features
      AuthStoreTestUtils.verifyPermissions(storeResult, [], [
        'advanced_analytics',
        'bulk_export', 
        'priority_support',
        'admin_access',
        'developer_tools'
      ]);
      
      expect(storeResult.current.hasAnyPermission(['admin_access', 'developer_tools'])).toBe(false);
    });

    it('should deny all premium permissions for free users', () => {
      const freeUser = AuthStoreTestUtils.createMockUser('standard_user', []);
      const token = AuthStoreTestUtils.createTestToken('free-premium-check');
      
      AuthStoreTestUtils.performLogin(storeResult, freeUser, token);

      const premiumFeatures = [
        'advanced_analytics', 'bulk_export', 'priority_support',
        'custom_integrations', 'white_label', 'enterprise_sso'
      ];
      
      AuthStoreTestUtils.verifyPermissions(storeResult, [], premiumFeatures);
    });

    it('should prevent free tier escalation attempts', () => {
      const freeUser = AuthStoreTestUtils.createMockUser('standard_user', []);
      const token = AuthStoreTestUtils.createTestToken('escalation-test');
      
      AuthStoreTestUtils.performLogin(storeResult, freeUser, token);
      
      // Even if somehow permissions were added, role checks should still fail
      AuthStoreTestUtils.verifyRoleAccess(storeResult, false, false);
    });
  });

  describe('Growth Tier Permissions - Controlled Access', () => {
    it('should validate growth tier permissions correctly', () => {
      const growthUser = AuthStoreTestUtils.createMockUser('power_user', ['analytics', 'export']);
      const token = AuthStoreTestUtils.createTestToken('growth');
      
      AuthStoreTestUtils.performLogin(storeResult, growthUser, token);

      AuthStoreTestUtils.verifyPermissions(storeResult, ['analytics', 'export'], ['admin_access']);
      expect(storeResult.current.hasAnyPermission(['analytics', 'admin_access'])).toBe(true);
      expect(storeResult.current.hasAllPermissions(['analytics', 'export'])).toBe(true);
      expect(storeResult.current.hasAllPermissions(['analytics', 'admin_access'])).toBe(false);
    });

    it('should enforce growth tier boundaries', () => {
      const growthUser = AuthStoreTestUtils.createMockUser('power_user', ['feature_analytics', 'export_data']);
      const token = AuthStoreTestUtils.createTestToken('growth-boundary');
      
      AuthStoreTestUtils.performLogin(storeResult, growthUser, token);

      // Should have growth features but not enterprise features
      AuthStoreTestUtils.verifyPermissions(storeResult, 
        ['feature_analytics', 'export_data'], 
        ['admin_access', 'full_api_access', 'white_label']
      );
      
      AuthStoreTestUtils.verifyRoleAccess(storeResult, false, false);
    });

    it('should handle partial permission grants for growth tier', () => {
      const growthUser = AuthStoreTestUtils.createMockUser('power_user', ['analytics']);
      const token = AuthStoreTestUtils.createTestToken('partial-growth');
      
      AuthStoreTestUtils.performLogin(storeResult, growthUser, token);

      expect(storeResult.current.hasPermission('analytics')).toBe(true);
      expect(storeResult.current.hasPermission('export')).toBe(false);
      expect(storeResult.current.hasAnyPermission(['analytics', 'export'])).toBe(true);
      expect(storeResult.current.hasAllPermissions(['analytics', 'export'])).toBe(false);
    });
  });

  describe('Enterprise Tier Permissions - Full Access', () => {
    it('should grant enterprise full permissions correctly', () => {
      const enterpriseUser = AuthStoreTestUtils.createMockUser('super_admin', ['admin_access', 'dev_tools']);
      enterpriseUser.is_superuser = true;
      const token = AuthStoreTestUtils.createTestToken('enterprise');
      
      AuthStoreTestUtils.performLogin(storeResult, enterpriseUser, token);

      AuthStoreTestUtils.verifyRoleAccess(storeResult, true, true);
      expect(storeResult.current.hasAllPermissions(['admin_access', 'dev_tools'])).toBe(true);
    });

    it('should validate admin hierarchy correctly', () => {
      const adminUser = AuthStoreTestUtils.createMockUser('admin');
      const token = AuthStoreTestUtils.createTestToken('admin-hierarchy');
      
      AuthStoreTestUtils.performLogin(storeResult, adminUser, token);

      // Admin should have admin access and developer access
      AuthStoreTestUtils.verifyRoleAccess(storeResult, true, true);
    });

    it('should handle super admin privileges', () => {
      const superAdmin = AuthStoreTestUtils.createMockUser('super_admin');
      superAdmin.is_superuser = true;
      const token = AuthStoreTestUtils.createTestToken('super-admin');
      
      AuthStoreTestUtils.performLogin(storeResult, superAdmin, token);

      expect(storeResult.current.isAdminOrHigher()).toBe(true);
      expect(storeResult.current.isDeveloperOrHigher()).toBe(true);
      expect(storeResult.current.user?.is_superuser).toBe(true);
    });
  });

  describe('Role-Based Access Control - Tier Boundaries', () => {
    it('should correctly identify developer access', () => {
      const developer = AuthStoreTestUtils.createMockUser('developer');
      (developer as any).is_developer = true;
      const token = AuthStoreTestUtils.createTestToken('dev');
      
      AuthStoreTestUtils.performLogin(storeResult, developer, token);

      expect(storeResult.current.isDeveloperOrHigher()).toBe(true);
      expect(storeResult.current.isAdminOrHigher()).toBe(false);
    });

    it('should correctly identify admin access hierarchy', () => {
      const admin = AuthStoreTestUtils.createMockUser('admin');
      const token = AuthStoreTestUtils.createTestToken('admin');
      
      AuthStoreTestUtils.performLogin(storeResult, admin, token);

      AuthStoreTestUtils.verifyRoleAccess(storeResult, true, true);
    });

    it('should maintain role consistency across operations', () => {
      const enterpriseUser = AuthStoreTestUtils.createMockUser('admin', ['admin_access']);
      const token = AuthStoreTestUtils.createTestToken('consistency');
      
      AuthStoreTestUtils.performLogin(storeResult, enterpriseUser, token);
      
      // Role should remain consistent through state changes
      storeResult.current.setLoading(true);
      AuthStoreTestUtils.verifyRoleAccess(storeResult, true, true);
      
      storeResult.current.setLoading(false);
      AuthStoreTestUtils.verifyRoleAccess(storeResult, true, true);
    });
  });

  describe('Permission Edge Cases - Security Validation', () => {
    it('should handle undefined permissions gracefully', () => {
      const userWithoutPermissions = AuthStoreTestUtils.createMockUser('standard_user');
      delete (userWithoutPermissions as any).permissions;
      const token = AuthStoreTestUtils.createTestToken('no-perms');
      
      AuthStoreTestUtils.performLogin(storeResult, userWithoutPermissions, token);

      expect(storeResult.current.hasPermission('any-permission')).toBe(false);
      expect(storeResult.current.hasAnyPermission(['perm1', 'perm2'])).toBe(false);
      expect(storeResult.current.hasAllPermissions(['perm1'])).toBe(false);
    });

    it('should handle null/empty permission arrays', () => {
      const userWithEmptyPermissions = AuthStoreTestUtils.createMockUser('standard_user', []);
      const token = AuthStoreTestUtils.createTestToken('empty-perms');
      
      AuthStoreTestUtils.performLogin(storeResult, userWithEmptyPermissions, token);

      expect(storeResult.current.hasPermission('any-permission')).toBe(false);
      expect(storeResult.current.hasAnyPermission([])).toBe(false);
      expect(storeResult.current.hasAllPermissions([])).toBe(true); // Empty array should return true
    });

    it('should validate permission string matching exactly', () => {
      const user = AuthStoreTestUtils.createMockUser('power_user', ['exact_permission']);
      const token = AuthStoreTestUtils.createTestToken('exact-match');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);

      expect(storeResult.current.hasPermission('exact_permission')).toBe(true);
      expect(storeResult.current.hasPermission('exact_permissio')).toBe(false);
      expect(storeResult.current.hasPermission('exact_permission_extended')).toBe(false);
      expect(storeResult.current.hasPermission('EXACT_PERMISSION')).toBe(false);
    });

    it('should handle case sensitivity in permissions', () => {
      const user = AuthStoreTestUtils.createMockUser('power_user', ['CaseSensitive']);
      const token = AuthStoreTestUtils.createTestToken('case-test');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);

      expect(storeResult.current.hasPermission('CaseSensitive')).toBe(true);
      expect(storeResult.current.hasPermission('casesensitive')).toBe(false);
      expect(storeResult.current.hasPermission('CASESENSITIVE')).toBe(false);
    });

    it('should validate complex permission combinations', () => {
      const user = AuthStoreTestUtils.createMockUser('power_user', ['perm1', 'perm2', 'perm3']);
      const token = AuthStoreTestUtils.createTestToken('complex-perms');
      
      AuthStoreTestUtils.performLogin(storeResult, user, token);

      expect(storeResult.current.hasAnyPermission(['perm1', 'perm4'])).toBe(true);
      expect(storeResult.current.hasAnyPermission(['perm4', 'perm5'])).toBe(false);
      expect(storeResult.current.hasAllPermissions(['perm1', 'perm2'])).toBe(true);
      expect(storeResult.current.hasAllPermissions(['perm1', 'perm4'])).toBe(false);
    });
  });
});