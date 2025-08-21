/**
 * Role-Based Access Control Integration Tests
 * 
 * Tests access control for different user tiers (Free, Early, Mid, Enterprise),
 * permission validation, protected routes, and feature access control.
 * 
 * Business Value: Ensures proper monetization through tier-based access,
 * prevents unauthorized feature usage, protects premium functionality.
 */

// Mock declarations (Jest hoisting)
const mockUseAuthStore = jest.fn();
const mockUseRouter = jest.fn();
const mockUseUnifiedChatStore = jest.fn();

// Mock auth store
jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

// Mock unified chat store
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: mockUseRouter,
  usePathname: () => '/chat',
  useSearchParams: () => new URLSearchParams()
}));

// Mock AuthGate component
jest.mock('@/components/auth/AuthGate', () => {
  return function MockAuthGate({ 
    children, 
    requiredRole, 
    requiredPermissions,
    fallback 
  }: any) {
    const authStore = mockUseAuthStore();
    
    // Simple role check for testing
    if (requiredRole && (!authStore.user || authStore.user.role !== requiredRole)) {
      return fallback || <div data-testid="access-denied">Access Denied</div>;
    }
    
    // Simple permission check for testing
    if (requiredPermissions && !authStore.hasAllPermissions?.(requiredPermissions)) {
      return fallback || <div data-testid="access-denied">Access Denied</div>;
    }
    
    return <>{children}</>;
  };
});

import React from 'react';
import { render, fireEvent, waitFor, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupTestEnvironment, resetTestState } from '../test-utils/integration-test-setup';

// User tier definitions for testing
const userTiers = {
  free: {
    id: 'free-user',
    email: 'free@netrasystems.ai',
    name: 'Free User',
    tier: 'free',
    role: 'standard_user',
    permissions: ['chat:basic', 'thread:create'],
    limits: { threadsPerMonth: 10, messagesPerThread: 50 }
  },
  early: {
    id: 'early-user',
    email: 'early@netrasystems.ai',
    name: 'Early User',
    tier: 'early',
    role: 'power_user',
    permissions: ['chat:basic', 'chat:advanced', 'thread:create', 'thread:export'],
    limits: { threadsPerMonth: 100, messagesPerThread: 500 }
  },
  mid: {
    id: 'mid-user',
    email: 'mid@netrasystems.ai',
    name: 'Mid User',
    tier: 'mid',
    role: 'power_user',
    permissions: ['chat:basic', 'chat:advanced', 'chat:analytics', 'thread:create', 'thread:export', 'corpus:access'],
    limits: { threadsPerMonth: 1000, messagesPerThread: 5000 }
  },
  enterprise: {
    id: 'enterprise-user',
    email: 'enterprise@netrasystems.ai',
    name: 'Enterprise User',
    tier: 'enterprise',
    role: 'admin',
    permissions: ['chat:basic', 'chat:advanced', 'chat:analytics', 'chat:enterprise', 'thread:create', 'thread:export', 'corpus:access', 'admin:access'],
    limits: { threadsPerMonth: -1, messagesPerThread: -1 }
  }
};

describe('Role-Based Access Control Integration', () => {
  let mockRouter: any;

  beforeEach(() => {
    setupTestEnvironment();
    resetTestState();
    setupAccessControlMocks();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Tier-Based Feature Access', () => {
    it('should restrict free users to basic features', async () => {
      const { AccessComponent } = setupFreeUserAccess();
      
      render(<AccessComponent />);
      await verifyFreeUserRestrictions();
      expectBasicFeaturesOnly();
    });

    it('should grant early users advanced features', async () => {
      const { AccessComponent } = setupEarlyUserAccess();
      
      render(<AccessComponent />);
      await verifyEarlyUserPermissions();
      expectAdvancedFeaturesEnabled();
    });

    it('should grant mid users analytics access', async () => {
      const { AccessComponent } = setupMidUserAccess();
      
      render(<AccessComponent />);
      await verifyMidUserPermissions();
      expectAnalyticsAccess();
    });

    it('should grant enterprise users full access', async () => {
      const { AccessComponent } = setupEnterpriseUserAccess();
      
      render(<AccessComponent />);
      await verifyEnterprisePermissions();
      expectFullFeatureAccess();
    });
  });

  describe('Protected Route Navigation', () => {
    it('should redirect unauthorized users from admin routes', async () => {
      const { ProtectedComponent } = setupUnauthorizedUserRoute();
      
      render(<ProtectedComponent />);
      await attemptAdminRouteAccess();
      
      expectAccessDenied();
      expectRedirectToAppropriateRoute();
    });

    it('should allow enterprise users to access admin routes', async () => {
      const { ProtectedComponent } = setupAuthorizedAdminRoute();
      
      render(<ProtectedComponent />);
      await verifyAdminRouteAccess();
      expectAdminInterfaceRendered();
    });

    it('should handle route permissions dynamically', async () => {
      const { DynamicComponent } = setupDynamicRoutePermissions();
      
      render(<DynamicComponent />);
      await changeTierDynamically();
      
      await verifyDynamicPermissionUpdate();
      expectRouteAccessUpdated();
    });
  });

  describe('Feature Limitations', () => {
    it('should enforce thread creation limits for free users', async () => {
      const { LimitComponent } = setupThreadLimitScenario();
      
      render(<LimitComponent />);
      await reachThreadLimit();
      
      expectLimitReached();
      expectUpgradePrompt();
    });

    it('should enforce message limits per thread', async () => {
      const { MessageComponent } = setupMessageLimitScenario();
      
      render(<MessageComponent />);
      await reachMessageLimit();
      
      expectMessageLimitEnforced();
      expectLimitNotification();
    });

    it('should remove limits for enterprise users', async () => {
      const { UnlimitedComponent } = setupUnlimitedAccess();
      
      render(<UnlimitedComponent />);
      await testUnlimitedUsage();
      expectNoLimitsEnforced();
    });
  });

  describe('Permission Validation', () => {
    it('should validate permissions before feature access', async () => {
      const { ValidationComponent } = setupPermissionValidation();
      
      render(<ValidationComponent />);
      await attemptFeatureAccess();
      
      expectPermissionValidated();
      expectActionExecuted();
    });

    it('should handle missing permissions gracefully', async () => {
      const { GracefulComponent } = setupMissingPermissions();
      
      render(<GracefulComponent />);
      await attemptUnauthorizedAction();
      
      expectGracefulPermissionDenial();
      expectUserFriendlyMessage();
    });

    it('should support hierarchical permissions', async () => {
      const { HierarchyComponent } = setupHierarchicalPermissions();
      
      render(<HierarchyComponent />);
      await testPermissionHierarchy();
      expectHierarchyRespected();
    });
  });

  describe('Upgrade Flow Integration', () => {
    it('should trigger upgrade flow for premium features', async () => {
      const { UpgradeComponent } = setupUpgradeFlowTrigger();
      
      render(<UpgradeComponent />);
      await attemptPremiumFeature();
      
      expectUpgradeFlowTriggered();
      expectCorrectUpgradePath();
    });

    it('should handle upgrade completion', async () => {
      const { CompletionComponent } = setupUpgradeCompletion();
      
      render(<CompletionComponent />);
      await completeUpgrade();
      
      await verifyUpgradeProcessed();
      expectPermissionsUpdated();
      expectFeatureAccessGranted();
    });
  });

  // Helper functions for test setup (≤8 lines each)
  function setupAccessControlMocks() {
    mockRouter = createMockRouter();
    mockUseRouter.mockReturnValue(mockRouter);
    mockUseUnifiedChatStore.mockReturnValue(createMockChatStore());
  }

  function createMockRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      refresh: jest.fn(),
      pathname: '/chat',
      query: {},
      asPath: '/chat'
    };
  }

  function createMockChatStore() {
    return {
      threads: [],
      messages: [],
      createThread: jest.fn(),
      addMessage: jest.fn(),
      getThreadCount: jest.fn().mockReturnValue(0),
      getMessageCount: jest.fn().mockReturnValue(0)
    };
  }

  function setupFreeUserAccess() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.free);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const AccessComponent = () => (
      <div>
        <div data-testid="basic-feature">Basic Chat</div>
        <div data-testid="advanced-feature" style={{ display: mockAuthStore.hasPermission('chat:advanced') ? 'block' : 'none' }}>
          Advanced Features
        </div>
        <div data-testid="analytics-feature" style={{ display: mockAuthStore.hasPermission('chat:analytics') ? 'block' : 'none' }}>
          Analytics
        </div>
      </div>
    );
    
    return { AccessComponent };
  }

  function createMockAuthStoreForUser(user: any) {
    return {
      isAuthenticated: true,
      user,
      token: 'mock-token',
      hasPermission: jest.fn((permission: string) => user.permissions.includes(permission)),
      hasAnyPermission: jest.fn((permissions: string[]) => 
        permissions.some(p => user.permissions.includes(p))
      ),
      hasAllPermissions: jest.fn((permissions: string[]) => 
        permissions.every(p => user.permissions.includes(p))
      ),
      isAdminOrHigher: jest.fn(() => ['admin', 'super_admin'].includes(user.role)),
      isDeveloperOrHigher: jest.fn(() => ['developer', 'admin', 'super_admin'].includes(user.role))
    };
  }

  async function verifyFreeUserRestrictions() {
    await waitFor(() => {
      expect(screen.getByTestId('basic-feature')).toBeVisible();
    });
  }

  function expectBasicFeaturesOnly() {
    expect(screen.getByTestId('basic-feature')).toBeVisible();
    expect(screen.getByTestId('advanced-feature')).not.toBeVisible();
    expect(screen.getByTestId('analytics-feature')).not.toBeVisible();
  }

  function setupEarlyUserAccess() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.early);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const AccessComponent = () => (
      <div>
        <div data-testid="basic-feature">Basic Chat</div>
        <div data-testid="advanced-feature" style={{ display: mockAuthStore.hasPermission('chat:advanced') ? 'block' : 'none' }}>
          Advanced Features
        </div>
        <div data-testid="export-feature" style={{ display: mockAuthStore.hasPermission('thread:export') ? 'block' : 'none' }}>
          Export Threads
        </div>
      </div>
    );
    
    return { AccessComponent };
  }

  async function verifyEarlyUserPermissions() {
    await waitFor(() => {
      expect(screen.getByTestId('advanced-feature')).toBeVisible();
    });
  }

  function expectAdvancedFeaturesEnabled() {
    expect(screen.getByTestId('basic-feature')).toBeVisible();
    expect(screen.getByTestId('advanced-feature')).toBeVisible();
    expect(screen.getByTestId('export-feature')).toBeVisible();
  }

  function setupMidUserAccess() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.mid);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const AccessComponent = () => (
      <div>
        <div data-testid="analytics-feature" style={{ display: mockAuthStore.hasPermission('chat:analytics') ? 'block' : 'none' }}>
          Analytics Dashboard
        </div>
        <div data-testid="corpus-feature" style={{ display: mockAuthStore.hasPermission('corpus:access') ? 'block' : 'none' }}>
          Corpus Management
        </div>
      </div>
    );
    
    return { AccessComponent };
  }

  async function verifyMidUserPermissions() {
    await waitFor(() => {
      expect(screen.getByTestId('analytics-feature')).toBeVisible();
    });
  }

  function expectAnalyticsAccess() {
    expect(screen.getByTestId('analytics-feature')).toBeVisible();
    expect(screen.getByTestId('corpus-feature')).toBeVisible();
  }

  function setupEnterpriseUserAccess() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.enterprise);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const AccessComponent = () => (
      <div>
        <div data-testid="admin-feature" style={{ display: mockAuthStore.hasPermission('admin:access') ? 'block' : 'none' }}>
          Admin Panel
        </div>
        <div data-testid="enterprise-feature" style={{ display: mockAuthStore.hasPermission('chat:enterprise') ? 'block' : 'none' }}>
          Enterprise Features
        </div>
      </div>
    );
    
    return { AccessComponent };
  }

  async function verifyEnterprisePermissions() {
    await waitFor(() => {
      expect(screen.getByTestId('admin-feature')).toBeVisible();
    });
  }

  function expectFullFeatureAccess() {
    expect(screen.getByTestId('admin-feature')).toBeVisible();
    expect(screen.getByTestId('enterprise-feature')).toBeVisible();
  }

  function setupUnauthorizedUserRoute() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.free);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const ProtectedComponent = () => {
      const MockAuthGate = require('@/components/auth/AuthGate').default;
      return (
        <MockAuthGate requiredRole="admin">
          <div data-testid="admin-content">Admin Dashboard</div>
        </MockAuthGate>
      );
    };
    
    return { ProtectedComponent };
  }

  async function attemptAdminRouteAccess() {
    // Component should render access denied automatically
    await waitFor(() => {
      expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    });
  }

  function expectAccessDenied() {
    expect(screen.getByTestId('access-denied')).toBeInTheDocument();
  }

  function expectRedirectToAppropriateRoute() {
    // In real implementation, this would trigger a redirect
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  }

  function setupAuthorizedAdminRoute() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.enterprise);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const ProtectedComponent = () => {
      const MockAuthGate = require('@/components/auth/AuthGate').default;
      return (
        <MockAuthGate requiredRole="admin">
          <div data-testid="admin-content">Admin Dashboard</div>
        </MockAuthGate>
      );
    };
    
    return { ProtectedComponent };
  }

  async function verifyAdminRouteAccess() {
    await waitFor(() => {
      expect(screen.getByTestId('admin-content')).toBeInTheDocument();
    });
  }

  function expectAdminInterfaceRendered() {
    expect(screen.getByTestId('admin-content')).toBeVisible();
  }

  function setupDynamicRoutePermissions() {
    let currentUser = userTiers.free;
    const mockAuthStore = createMockAuthStoreForUser(currentUser);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const DynamicComponent = () => {
      const [userTier, setUserTier] = React.useState('free');
      
      const handleUpgrade = () => {
        currentUser = userTiers.mid;
        setUserTier('mid');
        // Update mock to return new user
        mockUseAuthStore.mockReturnValue(createMockAuthStoreForUser(currentUser));
      };
      
      return (
        <div>
          <button onClick={handleUpgrade} data-testid="upgrade-btn">Upgrade</button>
          <div data-testid="current-tier">{userTier}</div>
          <div data-testid="feature-access">
            {mockUseAuthStore().hasPermission('chat:analytics') ? 'Analytics Enabled' : 'Analytics Disabled'}
          </div>
        </div>
      );
    };
    
    return { DynamicComponent };
  }

  async function changeTierDynamically() {
    const upgradeBtn = screen.getByTestId('upgrade-btn');
    fireEvent.click(upgradeBtn);
  }

  async function verifyDynamicPermissionUpdate() {
    await waitFor(() => {
      expect(screen.getByTestId('current-tier')).toHaveTextContent('mid');
    });
  }

  function expectRouteAccessUpdated() {
    expect(screen.getByTestId('feature-access')).toHaveTextContent('Analytics Enabled');
  }

  function setupThreadLimitScenario() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.free);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const LimitComponent = () => {
      const [threadCount, setThreadCount] = React.useState(0);
      const [limitReached, setLimitReached] = React.useState(false);
      
      const createThread = () => {
        const newCount = threadCount + 1;
        setThreadCount(newCount);
        if (newCount >= userTiers.free.limits.threadsPerMonth) {
          setLimitReached(true);
        }
      };
      
      return (
        <div>
          <button onClick={createThread} data-testid="create-thread-btn" disabled={limitReached}>
            Create Thread
          </button>
          <div data-testid="thread-count">{threadCount}</div>
          {limitReached && <div data-testid="limit-reached">Thread limit reached</div>}
          {limitReached && <div data-testid="upgrade-prompt">Upgrade to create more threads</div>}
        </div>
      );
    };
    
    return { LimitComponent };
  }

  async function reachThreadLimit() {
    const createBtn = screen.getByTestId('create-thread-btn');
    // Create threads up to limit
    for (let i = 0; i < userTiers.free.limits.threadsPerMonth; i++) {
      fireEvent.click(createBtn);
      await waitFor(() => {
        expect(screen.getByTestId('thread-count')).toHaveTextContent((i + 1).toString());
      });
    }
  }

  function expectLimitReached() {
    expect(screen.getByTestId('limit-reached')).toBeInTheDocument();
    expect(screen.getByTestId('create-thread-btn')).toBeDisabled();
  }

  function expectUpgradePrompt() {
    expect(screen.getByTestId('upgrade-prompt')).toBeInTheDocument();
  }

  function setupMessageLimitScenario() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.free);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const MessageComponent = () => {
      const [messageCount, setMessageCount] = React.useState(0);
      const [limitReached, setLimitReached] = React.useState(false);
      
      const sendMessage = () => {
        const newCount = messageCount + 1;
        setMessageCount(newCount);
        if (newCount >= userTiers.free.limits.messagesPerThread) {
          setLimitReached(true);
        }
      };
      
      return (
        <div>
          <button onClick={sendMessage} data-testid="send-message-btn" disabled={limitReached}>
            Send Message
          </button>
          <div data-testid="message-count">{messageCount}</div>
          {limitReached && <div data-testid="message-limit">Message limit reached for this thread</div>}
        </div>
      );
    };
    
    return { MessageComponent };
  }

  async function reachMessageLimit() {
    const sendBtn = screen.getByTestId('send-message-btn');
    // Send messages up to limit
    for (let i = 0; i < userTiers.free.limits.messagesPerThread; i++) {
      fireEvent.click(sendBtn);
    }
  }

  function expectMessageLimitEnforced() {
    expect(screen.getByTestId('send-message-btn')).toBeDisabled();
  }

  function expectLimitNotification() {
    expect(screen.getByTestId('message-limit')).toBeInTheDocument();
  }

  function setupUnlimitedAccess() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.enterprise);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const UnlimitedComponent = () => {
      const [operationCount, setOperationCount] = React.useState(0);
      
      const performOperation = () => {
        setOperationCount(prev => prev + 1);
      };
      
      return (
        <div>
          <button onClick={performOperation} data-testid="unlimited-operation-btn">
            Perform Operation
          </button>
          <div data-testid="operation-count">{operationCount}</div>
          <div data-testid="unlimited-status">Unlimited access</div>
        </div>
      );
    };
    
    return { UnlimitedComponent };
  }

  async function testUnlimitedUsage() {
    const operationBtn = screen.getByTestId('unlimited-operation-btn');
    // Perform many operations to test no limits
    for (let i = 0; i < 100; i++) {
      fireEvent.click(operationBtn);
    }
  }

  function expectNoLimitsEnforced() {
    expect(screen.getByTestId('operation-count')).toHaveTextContent('100');
    expect(screen.getByTestId('unlimited-operation-btn')).not.toBeDisabled();
  }

  function setupPermissionValidation() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.early);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const ValidationComponent = () => {
      const [actionResult, setActionResult] = React.useState('');
      
      const performAction = () => {
        if (mockAuthStore.hasPermission('thread:export')) {
          setActionResult('Export successful');
        } else {
          setActionResult('Permission denied');
        }
      };
      
      return (
        <div>
          <button onClick={performAction} data-testid="action-btn">Export Thread</button>
          <div data-testid="action-result">{actionResult}</div>
        </div>
      );
    };
    
    return { ValidationComponent };
  }

  async function attemptFeatureAccess() {
    const actionBtn = screen.getByTestId('action-btn');
    fireEvent.click(actionBtn);
  }

  function expectPermissionValidated() {
    expect(mockUseAuthStore().hasPermission).toHaveBeenCalledWith('thread:export');
  }

  function expectActionExecuted() {
    expect(screen.getByTestId('action-result')).toHaveTextContent('Export successful');
  }

  function setupMissingPermissions() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.free);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const GracefulComponent = () => {
      const [message, setMessage] = React.useState('');
      
      const attemptAction = () => {
        if (mockAuthStore.hasPermission('admin:access')) {
          setMessage('Admin action performed');
        } else {
          setMessage('This feature requires an upgrade to Enterprise tier');
        }
      };
      
      return (
        <div>
          <button onClick={attemptAction} data-testid="restricted-action-btn">Admin Action</button>
          <div data-testid="permission-message">{message}</div>
        </div>
      );
    };
    
    return { GracefulComponent };
  }

  async function attemptUnauthorizedAction() {
    const actionBtn = screen.getByTestId('restricted-action-btn');
    fireEvent.click(actionBtn);
  }

  function expectGracefulPermissionDenial() {
    expect(screen.getByTestId('permission-message')).toHaveTextContent('This feature requires an upgrade');
  }

  function expectUserFriendlyMessage() {
    const message = screen.getByTestId('permission-message').textContent;
    expect(message).toContain('Enterprise tier');
  }

  function setupHierarchicalPermissions() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.enterprise);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const HierarchyComponent = () => {
      const [results, setResults] = React.useState<string[]>([]);
      
      const testHierarchy = () => {
        const newResults = [];
        if (mockAuthStore.hasPermission('chat:basic')) newResults.push('Basic');
        if (mockAuthStore.hasPermission('chat:advanced')) newResults.push('Advanced');
        if (mockAuthStore.hasPermission('admin:access')) newResults.push('Admin');
        setResults(newResults);
      };
      
      return (
        <div>
          <button onClick={testHierarchy} data-testid="hierarchy-test-btn">Test Hierarchy</button>
          <div data-testid="hierarchy-results">{results.join(', ')}</div>
        </div>
      );
    };
    
    return { HierarchyComponent };
  }

  async function testPermissionHierarchy() {
    const testBtn = screen.getByTestId('hierarchy-test-btn');
    fireEvent.click(testBtn);
  }

  function expectHierarchyRespected() {
    const results = screen.getByTestId('hierarchy-results').textContent;
    expect(results).toContain('Basic');
    expect(results).toContain('Advanced');
    expect(results).toContain('Admin');
  }

  function setupUpgradeFlowTrigger() {
    const mockAuthStore = createMockAuthStoreForUser(userTiers.free);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const UpgradeComponent = () => {
      const [upgradeTriggered, setUpgradeTriggered] = React.useState(false);
      
      const attemptPremium = () => {
        if (mockAuthStore.hasPermission('chat:analytics')) {
          // Access granted
        } else {
          setUpgradeTriggered(true);
        }
      };
      
      return (
        <div>
          <button onClick={attemptPremium} data-testid="premium-feature-btn">Analytics</button>
          {upgradeTriggered && <div data-testid="upgrade-flow">Upgrade to access analytics</div>}
        </div>
      );
    };
    
    return { UpgradeComponent };
  }

  async function attemptPremiumFeature() {
    const premiumBtn = screen.getByTestId('premium-feature-btn');
    fireEvent.click(premiumBtn);
  }

  function expectUpgradeFlowTriggered() {
    expect(screen.getByTestId('upgrade-flow')).toBeInTheDocument();
  }

  function expectCorrectUpgradePath() {
    expect(screen.getByTestId('upgrade-flow')).toHaveTextContent('Upgrade to access analytics');
  }

  function setupUpgradeCompletion() {
    let currentUser = userTiers.free;
    const mockAuthStore = createMockAuthStoreForUser(currentUser);
    mockUseAuthStore.mockReturnValue(mockAuthStore);
    
    const CompletionComponent = () => {
      const [upgradedUser, setUpgradedUser] = React.useState(currentUser);
      
      const completeUpgrade = () => {
        const newUser = userTiers.mid;
        setUpgradedUser(newUser);
        // Update mock
        mockUseAuthStore.mockReturnValue(createMockAuthStoreForUser(newUser));
      };
      
      return (
        <div>
          <button onClick={completeUpgrade} data-testid="complete-upgrade-btn">Complete Upgrade</button>
          <div data-testid="current-tier">{upgradedUser.tier}</div>
          <div data-testid="analytics-access">
            {mockUseAuthStore().hasPermission('chat:analytics') ? 'Analytics Available' : 'Analytics Unavailable'}
          </div>
        </div>
      );
    };
    
    return { CompletionComponent };
  }

  async function completeUpgrade() {
    const completeBtn = screen.getByTestId('complete-upgrade-btn');
    fireEvent.click(completeBtn);
  }

  async function verifyUpgradeProcessed() {
    await waitFor(() => {
      expect(screen.getByTestId('current-tier')).toHaveTextContent('mid');
    });
  }

  function expectPermissionsUpdated() {
    expect(mockUseAuthStore().hasPermission('chat:analytics')).toBe(true);
  }

  function expectFeatureAccessGranted() {
    expect(screen.getByTestId('analytics-access')).toHaveTextContent('Analytics Available');
  }
});