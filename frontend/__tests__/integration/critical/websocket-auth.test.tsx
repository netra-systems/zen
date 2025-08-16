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

// Import test utilities
import { TestProviders, WebSocketContext, mockWebSocketContextValue } from '../../test-utils/providers';
import { setupTestEnvironment, cleanupTestEnvironment, resetTestStores, clearTestStorage, createTestUser, createMockToken, setAuthenticatedState } from '../../helpers/test-setup-helpers';
import { createMockOAuthResponse, createExpiredToken } from '../../helpers/test-mock-helpers';
import { simulateOAuthCallback, simulateSessionRestore } from '../../helpers/test-async-helpers';
import { WebSocketStatusComponent, AuthenticatedWebSocketComponent, AuthStatusComponent } from '../../helpers/test-component-helpers';
import { assertWebSocketStatus, assertUserIsAuthenticated, assertElementText } from '../../helpers/test-assertion-helpers';

// Mock environment
const mockEnv = {
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
  NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
};

describe('WebSocket and Authentication Integration', () => {
  let server: WS;
  
  beforeEach(() => {
    process.env = { ...process.env, ...mockEnv };
    setupTestEnvironment();
    server = new WS('ws://localhost:8000/ws');
    clearTestStorage();
    resetTestStores();
    setupMockFetchForConfig();
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('WebSocket Provider Integration', () => {
    it('should integrate WebSocket with authentication state', async () => {
      setAuthenticatedState();
      
      const { rerender } = render(
        <TestProviders wsValue={{ ...mockWebSocketContextValue, status: 'CLOSED' }}>
          <WebSocketStatusComponent />
        </TestProviders>
      );
      
      assertWebSocketStatus('Disconnected');
      rerender(
        <TestProviders wsValue={{ ...mockWebSocketContextValue, status: 'OPEN' }}>
          <WebSocketStatusComponent />
        </TestProviders>
      );
      assertWebSocketStatus('Connected');
    });

    it('should reconnect WebSocket when authentication changes', async () => {
      const { getByText } = render(
        <TestProviders>
          <AuthenticatedWebSocketComponent />
        </TestProviders>
      );
      
      fireEvent.click(getByText('Login'));
      
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