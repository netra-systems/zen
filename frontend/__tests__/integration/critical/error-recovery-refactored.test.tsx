/**
 * Error Recovery Integration Tests - REFACTORED
 * Tests for WebSocket disconnection, API retry logic, and session expiration
 * All functions ≤8 lines as per architecture requirements
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import stores
import { useAuthStore } from '@/store/authStore';

// Import test utilities
import { TestProviders } from '@/__tests__/setup/test-providers';
import { setupTestEnvironment, cleanupTestEnvironment, resetTestStores, clearTestStorage } from '../../helpers/test-setup-helpers';
import { createExpiredToken, setupRetryFetchMock } from '../../helpers/test-mock-helpers';
import { retryWithBackoff } from '../../helpers/test-async-helpers';
import { ConnectionRecoveryComponent, AuthStatusComponent } from '../../helpers/test-component-helpers';
import { assertConnectionStatus, assertElementText } from '../../helpers/test-assertion-helpers';

describe('Error Recovery Integration', () => {
  beforeEach(() => {
    setupTestEnvironment();
    clearTestStorage();
    resetTestStores();
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Connection Recovery', () => {
    it('should recover from WebSocket disconnection', async () => {
      const { getByText } = render(
        <TestProviders>
          <ConnectionRecoveryComponent />
        </TestProviders>
      );
      
      assertConnectionStatus('Disconnected');
      fireEvent.click(getByText('Reconnect'));
      assertConnectionStatus('Connected');
      fireEvent.click(getByText('Disconnect'));
      assertConnectionStatus('Disconnected');
    });

    it('should retry failed API calls with exponential backoff', async () => {
      const mockFetch = setupRetryFetchMock();
      global.fetch = mockFetch;
      
      const result = await retryWithBackoff(() => 
        fetch('/api/test').then(r => r.json())
      );
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('should handle session expiration gracefully', async () => {
      const expiredToken = createExpiredToken();
      localStorage.setItem('auth_token', expiredToken);
      useAuthStore.setState({ token: expiredToken, isAuthenticated: true });
      
      render(<AuthStatusComponent />);
      
      assertElementText('auth-status', 'Session Expired');
    });
  });
});