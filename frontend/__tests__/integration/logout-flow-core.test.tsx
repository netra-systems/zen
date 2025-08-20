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
import { TestProviders } from '../setup/test-providers';
import { authService } from '@/auth/service';
import { useAuthStore } from '@/store/authStore';

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
    logout: jest.fn(),
    setLoading: jest.fn(),
    setError: jest.fn(),
  };
  (useAuthStore as jest.Mock).mockReturnValue(mockStore);
  return mockStore;
};

const setupAuthServiceMocks = () => {
  (authService.getAuthConfig as jest.Mock).mockResolvedValue(createMockAuthConfig());
  (authService.handleLogout as jest.Mock).mockResolvedValue(undefined);
  (authService.removeToken as jest.Mock).mockImplementation(() => {});
  (authService.getToken as jest.Mock).mockReturnValue('test-token-123');
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
    <TestProviders>
      <LogoutButton />
    </TestProviders>
  );
};

describe('Logout Flow Core Tests', () => {
  let mockAuthStore: any;
  
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthStore = setupAuthStore();
    setupAuthServiceMocks();
  });

  describe('Logout Button Click', () => {
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
      (authService.handleLogout as jest.Mock).mockRejectedValue(new Error('Network error'));
      await performLogout();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });

  describe('Development Mode Logout', () => {
    const setupDevMode = () => {
      const devConfig = { ...createMockAuthConfig(), development_mode: true };
      (authService.getAuthConfig as jest.Mock).mockResolvedValue(devConfig);
      (authService.setDevLogoutFlag as jest.Mock).mockImplementation(() => {});
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
    const testErrorHandling = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should handle auth service errors during logout', async () => {
      (authService.handleLogout as jest.Mock).mockRejectedValue(new Error('Auth error'));
      await testErrorHandling();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should complete logout even with partial failures', async () => {
      (authService.handleLogout as jest.Mock).mockRejectedValue(new Error('Partial failure'));
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
});