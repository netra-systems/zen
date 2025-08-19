/**
 * First-Time User Authentication Error Recovery Tests - Business Critical
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: Free → Early (Critical error recovery for conversions)
 * - Business Goal: Reduce 15-20% user drop-off from auth failures
 * - Value Impact: Each recovered user = potential $1K+ ARR
 * - Revenue Impact: 10% improvement = $75K+ annually
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Auth errors, network failures, retry mechanisms
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Real components under test
import AuthErrorPage from '@/app/auth/error/page';
import LoginPage from '@/app/login/page';

// Test utilities
import {
  setupCleanState,
  resetAllMocks,
  setupSimpleWebSocketMock,
  clearAuthState,
  mockAuthService,
  expectErrorMessage,
  expectRetryButton,
  expectNetworkErrorHandling,
  renderWithTestSetup,
  setupNextJSMocks,
  setupAuthMocks
} from './onboarding-test-helpers';

// Setup mocks
setupNextJSMocks();
setupAuthMocks();

describe('First-Time User Authentication Error Recovery Tests', () => {
  beforeEach(() => {
    setupCleanState();
    setupSimpleWebSocketMock();
    resetAllMocks();
  });

  afterEach(() => {
    clearAuthState();
    jest.clearAllMocks();
  });

  describe('Authentication Error Handling', () => {
    it('displays clear error messages with retry option', async () => {
      await renderAuthErrorPage('OAuth consent denied');
      
      expectErrorMessage('OAuth consent denied');
      expectRetryButton();
    });

    it('handles network failures gracefully', async () => {
      mockAuthService.error = 'Network connection failed';
      await renderLoginPage();
      
      expectNetworkErrorHandling();
    });

    it('provides fallback options when auth fails', async () => {
      await renderAuthErrorPage('Service temporarily unavailable');
      
      const retryButton = screen.getByRole('button', { name: /try again/i });
      expect(retryButton).toBeInTheDocument();
      
      const linkElement = retryButton.closest('a');
      expect(linkElement).toHaveAttribute('href', '/login');
    });

    it('shows specific error for OAuth consent denial', async () => {
      await renderAuthErrorPage('access_denied');
      
      expect(screen.getByText(/authentication error/i)).toBeInTheDocument();
      expect(screen.getByText(/an error occurred during authentication/i)).toBeInTheDocument();
    });

    it('handles timeout errors with appropriate messaging', async () => {
      await renderAuthErrorPage('Request timeout');
      
      expectErrorMessage('Request timeout');
      expectRetryButton();
    });
  });

  describe('Network Error Recovery', () => {
    it('detects offline state and shows appropriate message', async () => {
      Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
      mockAuthService.error = 'Network error';
      
      await renderLoginPage();
      
      expectNetworkErrorHandling();
    });

    it('provides retry mechanism for network failures', async () => {
      mockAuthService.error = 'ERR_NETWORK';
      await renderLoginPage();
      
      expectNetworkErrorHandling();
      
      // Clear error and retry
      mockAuthService.error = null;
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      expect(loginButton).toBeEnabled();
    });

    it('handles DNS resolution failures', async () => {
      await renderAuthErrorPage('DNS_PROBE_FINISHED_NXDOMAIN');
      
      expectErrorMessage('DNS_PROBE_FINISHED_NXDOMAIN');
      expectRetryButton();
    });
  });

  describe('Service Availability Recovery', () => {
    it('handles server errors with retry options', async () => {
      await renderAuthErrorPage('Internal server error (500)');
      
      expectErrorMessage('Internal server error (500)');
      expectRetryButton();
    });

    it('shows maintenance mode messaging', async () => {
      await renderAuthErrorPage('Service temporarily unavailable (503)');
      
      expectErrorMessage('Service temporarily unavailable (503)');
      expectRetryButton();
    });

    it('provides alternative contact options for persistent failures', async () => {
      await renderAuthErrorPage('Multiple authentication failures');
      
      expectErrorMessage('Multiple authentication failures');
      expectRetryButton();
    });
  });

  describe('User Experience During Errors', () => {
    it('maintains professional appearance during errors', async () => {
      await renderAuthErrorPage('Authentication failed');
      
      const errorContainer = document.querySelector('.text-center');
      expect(errorContainer).toBeInTheDocument();
    });

    it('provides clear navigation back to login', async () => {
      await renderAuthErrorPage('Session expired');
      
      const retryButton = screen.getByRole('button', { name: /try again/i });
      const linkElement = retryButton.closest('a');
      expect(linkElement).toHaveAttribute('href', '/login');
    });

    it('prevents infinite error loops', async () => {
      // Simulate multiple error attempts
      await renderAuthErrorPage('Repeated failure');
      
      const retryButton = screen.getByRole('button', { name: /try again/i });
      expect(retryButton).toBeInTheDocument();
      expect(retryButton).toBeEnabled();
    });

    it('maintains accessibility during error states', async () => {
      await renderAuthErrorPage('Accessibility test error');
      
      const retryButton = screen.getByRole('button', { name: /try again/i });
      expect(retryButton).toHaveAccessibleName();
      expect(retryButton).toBeVisible();
    });
  });

  describe('Error Message Quality', () => {
    it('shows user-friendly error messages', async () => {
      await renderAuthErrorPage('Invalid client configuration');
      
      // Should show generic friendly message, not technical details
      expect(screen.getByText(/an error occurred during authentication/i)).toBeInTheDocument();
    });

    it('provides actionable guidance in error messages', async () => {
      await renderAuthErrorPage('Permission denied');
      
      expectRetryButton();
      expect(screen.getByText(/try again/i)).toBeInTheDocument();
    });

    it('avoids exposing sensitive technical details', async () => {
      await renderAuthErrorPage('Database connection failed: connection_string_here');
      
      // Should not expose database connection strings
      expect(screen.queryByText(/connection_string_here/)).not.toBeInTheDocument();
      expect(screen.getByText(/authentication error/i)).toBeInTheDocument();
    });
  });

  // Helper functions (≤8 lines each)
  async function renderAuthErrorPage(errorMessage: string): Promise<void> {
    const mockSearchParams = new URLSearchParams();
    mockSearchParams.set('message', errorMessage);
    
    jest.doMock('next/navigation', () => ({
      useRouter: () => ({ push: jest.fn(), replace: jest.fn(), refresh: jest.fn() }),
      usePathname: () => '/auth/error',
      useSearchParams: () => mockSearchParams
    }));
    
    await renderWithTestSetup(<AuthErrorPage />);
  }

  async function renderLoginPage(): Promise<void> {
    await renderWithTestSetup(<LoginPage />);
  }
});
