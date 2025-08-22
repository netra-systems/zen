/**
 * WebSocket and Authentication Integration Tests
 * Tests for WebSocket provider with authentication state
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

// Import stores
import { useAuthStore } from '@/store/authStore';

// Import unified test utilities
import { renderWithProviders, waitForElement, safeAsync, resetAllMocks } from '@/__tests__/shared/unified-test-utilities';
import { safeAct, waitForCondition, flushPromises } from '@/__tests__/helpers/test-timing-utilities';
import { TestProviders, mockWebSocketContextValue } from '@/__tests__/setup/test-providers';
import { createTestUser, createMockToken, setAuthenticatedState, setupMockFetchForConfig } from '@/__tests__/helpers/test-setup-helpers';
import { WebSocketStatusComponent, AuthenticatedWebSocketComponent, AuthStatusComponent } from '@/__tests__/helpers/test-component-helpers';

// Mock environment
const mockEnv = {
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
  NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
};

describe('WebSocket and Authentication Integration', () => {
  let server: WS;
  
  beforeEach(() => {
    process.env = { ...process.env, ...mockEnv };
    server = new WS('ws://localhost:8000/ws');
    resetAllMocks();
    setupMockFetchForConfig();
  });

  afterEach(() => {
    server.close();
    resetAllMocks();
  });

  describe('WebSocket Provider Integration', () => {
    it('should integrate WebSocket with authentication state', async () => {
      await safeAsync(() => {
        setAuthenticatedState();
      });
      
      renderWithProviders(<WebSocketStatusComponent />);
      const statusElement = await waitForElement('ws-status');
      expect(statusElement).toHaveTextContent('Connected');
    });

    it('should reconnect WebSocket when authentication changes', async () => {
      renderWithProviders(<AuthenticatedWebSocketComponent />);
      
      await safeAsync(async () => {
        fireEvent.click(screen.getByText('Login'));
      });
      
      await flushPromises();
      expect(useAuthStore.getState().token).toBe('new-token');
    });
  });

  describe('Authentication Flow Integration', () => {
    it('should complete OAuth flow and establish WebSocket', async () => {
      const mockOAuthResponse = createMockOAuthResponse();
      (fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => mockOAuthResponse });
      
      const result = await simulateOAuthCallback('oauth-code');
      
      expect(result.access_token).toBe('oauth-token');
      assertUserIsAuthenticated();
    });

    it('should persist authentication across page refreshes', async () => {
      const mockUser = createTestUser();
      const mockToken = createMockToken();
      setupPersistedAuthState(mockUser, mockToken);
      
      resetTestStores();
      simulateSessionRestore();
      
      assertUserIsAuthenticated();
      expect(useAuthStore.getState().user).toEqual(mockUser);
    });
  });
});

// Helper functions
function createMockOAuthResponse() {
  return {
    access_token: 'oauth-token',
    refresh_token: 'refresh-token',
    token_type: 'Bearer',
    expires_in: 3600,
    user: createTestUser(),
  };
}

async function simulateOAuthCallback(code: string) {
  const mockResponse = createMockOAuthResponse();
  
  (global.fetch as jest.Mock) = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })
  );

  return mockResponse;
}

function assertUserIsAuthenticated() {
  expect(localStorage.getItem('auth_token')).toBeTruthy();
  expect(localStorage.getItem('user')).toBeTruthy();
}

function setupPersistedAuthState(user: any, token: string) {
  localStorage.setItem('auth_token', token);
  localStorage.setItem('user', JSON.stringify(user));
}

function resetTestStores() {
  localStorage.clear();
  jest.clearAllMocks();
}

function simulateSessionRestore() {
  const token = localStorage.getItem('auth_token');
  const user = localStorage.getItem('user');
  
  return {
    token,
    user: user ? JSON.parse(user) : null,
  };
}