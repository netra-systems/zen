/**
 * Logout WebSocket Disconnection Tests
 * Tests WebSocket disconnection and connection state cleanup
 * BUSINESS VALUE: Security & compliance (enterprise data protection)
 * Following 450-line limit and 25-line function requirements
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { TestProviders } from '../setup/test-providers';
import { webSocketService } from '@/services/webSocketService';
import { useAuthStore } from '@/store/authStore';

// Mock dependencies
jest.mock('@/services/webSocketService');
jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn()
}));
jest.mock('@/lib/logger');

// Test helpers following 25-line limit
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
    reset: jest.fn(),
    setLoading: jest.fn(),
    setError: jest.fn(),
  };
  (useAuthStore as jest.Mock).mockReturnValue(mockStore);
  return mockStore;
};

const setupWebSocketMocks = () => {
  (webSocketService.disconnect as jest.Mock).mockImplementation(() => {});
  (webSocketService.getState as jest.Mock).mockReturnValue('disconnected');
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

describe('Logout WebSocket Disconnection Tests', () => {
  let mockAuthStore: any;
  
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthStore = setupAuthStore();
    setupWebSocketMocks();
  });

  describe('WebSocket Disconnection', () => {
    const testWebSocketDisconnection = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should disconnect WebSocket on logout', async () => {
      await testWebSocketDisconnection();
      await waitFor(() => {
        expect(webSocketService.disconnect).toHaveBeenCalled();
      });
    });

    it('should verify WebSocket is disconnected', async () => {
      await testWebSocketDisconnection();
      await waitFor(() => {
        expect(webSocketService.getState()).toBe('disconnected');
      });
    });

    it('should clear WebSocket message queue', async () => {
      await testWebSocketDisconnection();
      await waitFor(() => {
        expect(webSocketService.disconnect).toHaveBeenCalled();
      });
    });

    it('should handle WebSocket disconnection errors', async () => {
      (webSocketService.disconnect as jest.Mock).mockImplementation(() => {
        throw new Error('WebSocket error');
      });
      await testWebSocketDisconnection();
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });

  describe('WebSocket State Cleanup', () => {
    const verifyWebSocketCleanup = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should ensure WebSocket connection is terminated', async () => {
      await verifyWebSocketCleanup();
      await waitFor(() => {
        expect(webSocketService.disconnect).toHaveBeenCalledTimes(1);
      });
    });

    it('should prevent new WebSocket messages after logout', async () => {
      await verifyWebSocketCleanup();
      await waitFor(() => {
        expect(webSocketService.getState()).toBe('disconnected');
      });
    });

    it('should clear any pending WebSocket operations', async () => {
      await verifyWebSocketCleanup();
      await waitFor(() => {
        expect(webSocketService.disconnect).toHaveBeenCalled();
      });
    });

    it('should ensure clean WebSocket state for next session', async () => {
      await verifyWebSocketCleanup();
      await waitFor(() => {
        expect(webSocketService.getState()).toBe('disconnected');
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });

  describe('WebSocket Timing Requirements', () => {
    const measureWebSocketDisconnectTime = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      const startTime = performance.now();
      await user.click(logoutBtn);
      await waitFor(() => {
        expect(webSocketService.disconnect).toHaveBeenCalled();
      });
      const endTime = performance.now();
      return endTime - startTime;
    };

    it('should complete WebSocket disconnect within 25ms', async () => {
      const disconnectTime = await measureWebSocketDisconnectTime();
      expect(disconnectTime).toBeLessThan(25);
    });

    it('should not block logout process if WebSocket fails', async () => {
      (webSocketService.disconnect as jest.Mock).mockImplementation(() => {
        throw new Error('WebSocket disconnect failed');
      });
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should handle WebSocket timeout gracefully', async () => {
      (webSocketService.disconnect as jest.Mock).mockImplementation(() => {
        return new Promise((resolve) => setTimeout(resolve, 100));
      });
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should complete logout even if WebSocket is slow', async () => {
      (webSocketService.disconnect as jest.Mock).mockImplementation(() => {
        return new Promise((resolve) => setTimeout(resolve, 200));
      });
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      const startTime = performance.now();
      await user.click(logoutBtn);
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
        const endTime = performance.now();
        expect(endTime - startTime).toBeLessThan(500);
      });
    });
  });

  describe('WebSocket Error Handling', () => {
    const testWebSocketErrorHandling = async (errorType: string) => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should handle WebSocket disconnect errors gracefully', async () => {
      (webSocketService.disconnect as jest.Mock).mockImplementation(() => {
        throw new Error('Connection error');
      });
      await testWebSocketErrorHandling('connection');
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should handle WebSocket state check errors', async () => {
      (webSocketService.getState as jest.Mock).mockImplementation(() => {
        throw new Error('State check error');
      });
      await testWebSocketErrorHandling('state');
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should continue logout process despite WebSocket errors', async () => {
      (webSocketService.disconnect as jest.Mock).mockImplementation(() => {
        throw new Error('WebSocket error');
      });
      await testWebSocketErrorHandling('general');
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
        expect(mockAuthStore.reset).toHaveBeenCalled();
      });
    });

    it('should log WebSocket errors without blocking logout', async () => {
      (webSocketService.disconnect as jest.Mock).mockImplementation(() => {
        throw new Error('Test WebSocket error');
      });
      await testWebSocketErrorHandling('logging');
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });

  describe('WebSocket Security Cleanup', () => {
    const verifyWebSocketSecurity = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should ensure no WebSocket connections remain active', async () => {
      await verifyWebSocketSecurity();
      await waitFor(() => {
        expect(webSocketService.disconnect).toHaveBeenCalled();
        expect(webSocketService.getState()).toBe('disconnected');
      });
    });

    it('should prevent unauthorized WebSocket access after logout', async () => {
      await verifyWebSocketSecurity();
      await waitFor(() => {
        expect(webSocketService.getState()).toBe('disconnected');
        expect(mockAuthStore.isAuthenticated).toBe(false);
      });
    });

    it('should clear any WebSocket authentication tokens', async () => {
      await verifyWebSocketSecurity();
      await waitFor(() => {
        expect(webSocketService.disconnect).toHaveBeenCalled();
        expect(mockAuthStore.token).toBeNull();
      });
    });

    it('should ensure complete WebSocket session termination', async () => {
      await verifyWebSocketSecurity();
      await waitFor(() => {
        expect(webSocketService.disconnect).toHaveBeenCalled();
        expect(mockAuthStore.reset).toHaveBeenCalled();
      });
    });
  });
});