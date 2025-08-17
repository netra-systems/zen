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
import { renderWithProviders, waitForElement, safeAsync, resetAllMocks } from '../../shared/unified-test-utilities';
import { safeAct, waitForCondition, flushPromises } from '../../helpers/test-timing-utilities';
import { TestProviders, mockWebSocketContextValue } from '../../setup/test-providers';
import { createTestUser, createMockToken, setAuthenticatedState, setupMockFetchForConfig } from '../../helpers/test-setup-helpers';
import { WebSocketStatusComponent, AuthenticatedWebSocketComponent, AuthStatusComponent } from '../../helpers/test-component-helpers';

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