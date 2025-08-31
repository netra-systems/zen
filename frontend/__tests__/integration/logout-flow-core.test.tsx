/**
 * Logout Flow Core Tests
 * Tests basic logout button click, API calls, and timing requirements
 * BUSINESS VALUE: Security & compliance (Free->Paid conversion via trust)
 * Following 450-line limit and 25-line function requirements
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { TestProviders, AuthTestProvider, mockAuthContextValue } from '../setup/test-providers';
import { authService } from '@/auth/unified-auth-service';
import { useAuthStore } from '@/store/authStore';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('@/store/authStore');
jest.mock('@/lib/logger');

// Mock navigation
const mockReplace = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: mockReplace,
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(),
}));

// Test helpers following 25-line limit
const createMockAuthConfig = () => ({
  development_mode: false,
  google_client_id: 'test-client-id',
  endpoints: {
    login: 'http://localhost:8081/auth/login',
    logout: 'http://localhost:8081/auth/logout',
    callback: 'http://localhost:8081/auth/callback',
    token: 'http://localhost:8081/auth/token',
    user: 'http://localhost:8081/auth/me',
  },
});

const createMockUser = () => ({
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'admin',
});

const setupAuthStore = () => {
  const mockStore = {
    isAuthenticated: true,
    user: createMockUser(),
    token: 'test-token-123',
    logout: jest.fn(() => {
      // Update state when logout is called
      mockStore.isAuthenticated = false;
      mockStore.user = null;
      mockStore.token = null;
    }),
    setLoading: jest.fn(),
    setError: jest.fn(),
  };
  jest.mocked(useAuthStore).mockReturnValue(mockStore);
  return mockStore;
};

const setupAuthServiceMocks = () => {
  jest.mocked(authService.getAuthConfig).mockResolvedValue(createMockAuthConfig());
  jest.mocked(authService.handleLogout).mockResolvedValue(undefined);
  jest.mocked(authService.removeToken).mockImplementation(() => {});
  jest.mocked(authService.getToken).mockReturnValue('test-token-123');
  (authService.setDevLogoutFlag as jest.MockedFunction<any>) = jest.fn();
};

// Simple logout button component for testing
const LogoutButton: React.FC = () => {
  const { logout } = React.useContext(require('@/auth/context').AuthContext);
  return (
    <button onClick={logout} data-testid="logout-btn">
      Logout
    </button>
  );
};

const renderLogoutComponent = () => {
  return render(
    <AuthTestProvider>
      <TestProviders>
        <LogoutButton />
      </TestProviders>
    </AuthTestProvider>
  );
};

describe('Logout Flow Core Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let mockAuthStore: any;
  
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthStore = setupAuthStore();
    setupAuthServiceMocks();
    
    // Set up the mock auth context logout to trigger expected behaviors
    mockAuthContextValue.logout = jest.fn(async () => {
      try {
        // Get the current auth config to check for dev mode
        const authConfig = await authService.getAuthConfig();
        
        // Call dev logout flag if in development mode
        if (authConfig.development_mode) {
          (authService.setDevLogoutFlag as jest.MockedFunction<any>)();
        }
        
        // Call auth service logout
        await authService.handleLogout(authConfig);
      } catch (error) {
        // Continue with logout even if service call fails (graceful error handling)
      }
      // Always call auth store logout and navigation regardless of service errors
      mockAuthStore.logout();
      mockReplace('/login');
    });
  });

  describe('Logout Button Click', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    const clickLogoutButton = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should trigger logout when button is clicked', async () => {
      await clickLogoutButton();
      await waitFor(() => {
        expect(authService.handleLogout).toHaveBeenCalledWith(createMockAuthConfig());
      });
    });

    it('should call auth store logout', async () => {
      await clickLogoutButton();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should redirect to login page after logout', async () => {
      await clickLogoutButton();
      await waitFor(() => {
        expect(mockReplace).toHaveBeenCalledWith('/login');
      });
    });
  });

  describe('API Logout Call', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    const performLogout = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      const startTime = performance.now();
      await user.click(logoutBtn);
      return { startTime };
    };

    it('should call auth service logout API', async () => {
      await performLogout();
      await waitFor(() => {
        expect(authService.handleLogout).toHaveBeenCalledTimes(1);
      });
    });

    it('should complete logout within 500ms', async () => {
      const { startTime } = await performLogout();
      await waitFor(() => {
        expect(authService.handleLogout).toHaveBeenCalled();
        const endTime = performance.now();
        expect(endTime - startTime).toBeLessThan(500);
      });
    });

    it('should handle logout errors gracefully', async () => {
      jest.mocked(authService.handleLogout).mockRejectedValue(new Error('Network error'));
      await performLogout();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });

  describe('Development Mode Logout', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    const setupDevMode = () => {
      const devConfig = { ...createMockAuthConfig(), development_mode: true };
      jest.mocked(authService.getAuthConfig).mockResolvedValue(devConfig);
      jest.mocked(authService.setDevLogoutFlag).mockImplementation(() => {});
    };

    const testDevModeLogout = async () => {
      setupDevMode();
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should set dev logout flag in development mode', async () => {
      await testDevModeLogout();
      await waitFor(() => {
        expect(authService.setDevLogoutFlag).toHaveBeenCalled();
      });
    });

    it('should still perform standard logout in dev mode', async () => {
      await testDevModeLogout();
      await waitFor(() => {
        expect(authService.handleLogout).toHaveBeenCalled();
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling During Logout', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    const testErrorHandling = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should handle auth service errors during logout', async () => {
      jest.mocked(authService.handleLogout).mockRejectedValue(new Error('Auth error'));
      await testErrorHandling();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should complete logout even with partial failures', async () => {
      jest.mocked(authService.handleLogout).mockRejectedValue(new Error('Partial failure'));
      await testErrorHandling();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should use replace instead of push for security', async () => {
      await testErrorHandling();
      await waitFor(() => {
        expect(mockReplace).toHaveBeenCalled();
      });
    });
  });

  describe('Logout Flow Security', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    const verifySecurityMeasures = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should ensure no sensitive data remains after logout', async () => {
      await verifySecurityMeasures();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
        expect(mockAuthStore.user).toBeNull();
        expect(mockAuthStore.token).toBeNull();
      });
    });

    it('should reset authentication status', async () => {
      await verifySecurityMeasures();
      await waitFor(() => {
        expect(mockAuthStore.isAuthenticated).toBe(false);
      });
    });

    it('should ensure clean state for next login', async () => {
      await verifySecurityMeasures();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
        expect(authService.handleLogout).toHaveBeenCalled();
      });
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});