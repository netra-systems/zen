/**
 * First Load Integration Tests for Netra Apex Frontend
 * Critical for user onboarding and conversion - Phase 2, Agent 4
 * Tests unauthenticated first visit, bundle loading, auth checking, and redirects
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { TestProviders } from '../setup/test-providers';
import { mockAuthServiceResponses } from '../mocks/auth-service-mock';
import { authService } from '@/auth';
import HomePage from '@/app/page';
import LoginPage from '@/app/login/page';
import { 
  setupFirstLoadMocks,
  simulateLoadingSequence,
  simulatePerformanceMetrics,
  checkPageInteractive,
  FirstLoadTestComponent 
} from '../helpers/first-load-helpers';
import { setupFirstLoadMockComponents } from '@/__tests__/helpers/first-load-mock-setup';

setupFirstLoadMockComponents();

describe('First Load Integration Tests', () => {
  beforeEach(() => {
    setupFirstLoadMocks();
    simulatePerformanceMetrics();
  });

  describe('Unauthenticated First Visit', () => {
    it('should load application bundle and show loading state', async () => {
      simulateLoadingSequence({ authLoading: true, authUser: null, configLoaded: true });
      
      render(
        <TestProviders>
          <FirstLoadTestComponent scenario="loading" />
        </TestProviders>
      );
      
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      expect(screen.getByText('Loading Netra Apex...')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(screen.getByTestId('app-loaded')).toBeInTheDocument();
      });
    });

    it('should complete initial page load within 3 seconds', async () => {
      const startTime = Date.now();
      
      render(
        <TestProviders>
          <FirstLoadTestComponent scenario="fast" />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('app-loaded')).toBeInTheDocument();
      });
      
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(3000);
    });

    it('should show page as interactive within performance threshold', async () => {
      render(
        <TestProviders>
          <FirstLoadTestComponent scenario="interactive" />
        </TestProviders>
      );
      
      const isInteractive = await checkPageInteractive(3000);
      expect(isInteractive).toBe(true);
      
      await waitFor(() => {
        expect(screen.getByTestId('interactive-element')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /get started/i })).toBeEnabled();
      });
    });

    it('should handle bundle loading failures gracefully', async () => {
      render(
        <TestProviders>
          <FirstLoadTestComponent scenario="error" />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('load-error')).toBeInTheDocument();
        expect(screen.getByText(/Failed to load application/)).toBeInTheDocument();
        expect(screen.getByTestId('retry-load')).toBeInTheDocument();
      });
    });
  });

  describe('Auth State Checking', () => {
    it('should check authentication status on first load', async () => {
      simulateLoadingSequence({ 
        authLoading: false, 
        authUser: null,
        configLoaded: true 
      });
      
      render(
        <TestProviders>
          <HomePage />
        </TestProviders>
      );
      
      expect(authService.useAuth).toHaveBeenCalled();
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      });
    });

    it('should redirect authenticated users to main app', async () => {
      const mockUser = {
        id: 'user-123',
        email: 'test@example.com',
        name: 'Test User'
      };
      
      jest.mocked(authService.useAuth).mockReturnValue({
        loading: false,
        user: mockUser,
        error: null
      });
      
      render(
        <TestProviders>
          <HomePage />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/chat');
      });
    });

    it('should handle auth service unavailable gracefully', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        loading: false,
        user: null,
        error: 'Auth service unavailable'
      });
      
      render(
        <TestProviders>
          <HomePage />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      });
    });

    it('should show loading during auth check', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        loading: true,
        user: null,
        error: null
      });
      
      render(
        <TestProviders>
          <HomePage />
        </TestProviders>
      );
      
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  describe('Redirect to Login', () => {

    it('should render login page with Google OAuth button', async () => {
      const mockLogin = jest.fn();
      jest.mocked(authService.useAuth).mockReturnValue({
        login: mockLogin,
        loading: false,
        user: null,
        error: null
      });
      
      render(
        <TestProviders>
          <LoginPage />
        </TestProviders>
      );
      
      expect(screen.getByText('Netra')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /login with google/i })).toBeInTheDocument();
      
      const user = userEvent.setup();
      await user.click(screen.getByRole('button', { name: /login with google/i }));
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should show loading state during login process', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        login: jest.fn(),
        loading: true,
        user: null,
        error: null
      });
      
      render(
        <TestProviders>
          <LoginPage />
        </TestProviders>
      );
      
      const loginButton = screen.getByRole('button');
      expect(loginButton).toHaveTextContent('Loading...');
      expect(loginButton).toBeDisabled();
    });
  });

  describe('Error Handling and Performance', () => {
    it('should display proper loading indicators', async () => {
      render(
        <TestProviders>
          <FirstLoadTestComponent scenario="loading" />
        </TestProviders>
      );
      
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      expect(screen.getByText('Loading Netra Apex...')).toBeInTheDocument();
    });

    it('should not show console errors during normal load', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <TestProviders>
          <FirstLoadTestComponent scenario="success" />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('app-loaded')).toBeInTheDocument();
      });
      
      expect(consoleSpy).not.toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('should provide retry mechanism for failed loads', async () => {
      const user = userEvent.setup();
      
      render(
        <TestProviders>
          <FirstLoadTestComponent scenario="error" />
        </TestProviders>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('load-error')).toBeInTheDocument();
      });
      
      const retryButton = screen.getByTestId('retry-load');
      await user.click(retryButton);
      
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });


    it('should handle network failures gracefully', async () => {
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));
      
      render(
        <TestProviders>
          <FirstLoadTestComponent scenario="network-error" />
        </TestProviders>
      );
      
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });
  });
});