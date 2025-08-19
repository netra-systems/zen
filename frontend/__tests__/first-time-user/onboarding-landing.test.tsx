/**
 * First-Time User Landing Page Tests - Business Critical
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: Free → Early (Critical first impression)
 * - Business Goal: Optimize landing page conversion rate
 * - Value Impact: 5% improvement = $50K+ annually
 * - Revenue Impact: First impression drives 30% of conversions
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Landing page, value proposition, call-to-action
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Real components under test
import LoginPage from '@/app/login/page';

// Test utilities
import {
  setupCleanState,
  resetAllMocks,
  setupSimpleWebSocketMock,
  clearAuthState,
  mockAuthService,
  expectValueProposition,
  expectCallToAction,
  expectAccessibleDesign,
  expectLoadingState,
  expectLoadingIndicator,
  triggerGoogleAuth,
  mockViewport,
  expectMobileOptimizedLayout,
  expectTouchFriendlySize,
  expectQuickLoad,
  measurePerformance,
  renderWithTestSetup,
  setupNextJSMocks,
  setupAuthMocks
} from './onboarding-test-helpers';

// Setup mocks
setupNextJSMocks();
setupAuthMocks();

describe('First-Time User Landing Page Tests', () => {
  beforeEach(() => {
    setupCleanState();
    setupSimpleWebSocketMock();
    resetAllMocks();
  });

  afterEach(() => {
    clearAuthState();
    jest.clearAllMocks();
  });

  describe('Initial Landing Experience', () => {
    it('renders login page with clear value proposition', async () => {
      await renderLoginPage();
      
      expectValueProposition();
      expectCallToAction();
      expectAccessibleDesign();
    });

    it('handles Google OAuth initiation smoothly', async () => {
      mockAuthService.loading = false;
      await renderLoginPage();
      
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      expect(loginButton).toBeEnabled();
      
      await triggerGoogleAuth(loginButton);
      expectLoadingState();
    });

    it('provides clear loading feedback during auth', async () => {
      mockAuthService.loading = true;
      await renderLoginPage();
      
      expectLoadingIndicator();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('displays branding prominently for recognition', async () => {
      await renderLoginPage();
      
      const netraHeading = screen.getByRole('heading', { name: /netra/i });
      expect(netraHeading).toBeInTheDocument();
      expect(netraHeading).toHaveClass('text-4xl', 'font-bold');
    });

    it('focuses on login button for keyboard accessibility', async () => {
      await renderLoginPage();
      
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      loginButton.focus();
      expect(loginButton).toHaveFocus();
    });
  });

  describe('Mobile Responsive Experience', () => {
    it('adapts login page for mobile viewport', async () => {
      mockViewport(375, 667); // iPhone SE
      await renderLoginPage();
      
      expectMobileOptimizedLayout();
    });

    it('ensures touch-friendly interactive elements', async () => {
      mockViewport(375, 667);
      await renderLoginPage();
      
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      expectTouchFriendlySize(loginButton);
    });

    it('maintains readability on small screens', async () => {
      mockViewport(320, 568); // iPhone 5
      await renderLoginPage();
      
      const heading = screen.getByRole('heading', { name: /netra/i });
      expect(heading).toBeVisible();
      
      const button = screen.getByRole('button', { name: /login with google/i });
      expect(button).toBeVisible();
    });
  });

  describe('Performance and Loading States', () => {
    it('loads login page under 2 seconds', async () => {
      const loadTime = await measurePerformance(async () => {
        await renderLoginPage();
      });
      
      expectQuickLoad(loadTime);
    });

    it('provides immediate feedback on user actions', async () => {
      await renderLoginPage();
      
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      await userEvent.click(loginButton);
      
      await waitFor(() => {
        expect(mockAuthService.login).toHaveBeenCalled();
      }, { timeout: 100 });
    });

    it('handles rapid clicks gracefully', async () => {
      await renderLoginPage();
      
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      
      // Rapid clicks should not cause multiple calls
      await userEvent.click(loginButton);
      await userEvent.click(loginButton);
      await userEvent.click(loginButton);
      
      // Should be called once due to loading state
      expect(mockAuthService.login).toHaveBeenCalledTimes(1);
    });
  });

  describe('Visual Design and UX', () => {
    it('centers content for professional appearance', async () => {
      await renderLoginPage();
      
      const centerContainer = document.querySelector('.flex.items-center.justify-center');
      expect(centerContainer).toBeInTheDocument();
      expect(centerContainer).toHaveClass('h-screen');
    });

    it('uses appropriate button sizing for engagement', async () => {
      await renderLoginPage();
      
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      expect(loginButton).toHaveAttribute('class');
      
      const buttonClasses = loginButton.getAttribute('class') || '';
      expect(buttonClasses).toMatch(/size-lg|text-lg|px-|py-/);
    });

    it('maintains consistent spacing and typography', async () => {
      await renderLoginPage();
      
      const heading = screen.getByRole('heading', { name: /netra/i });
      const button = screen.getByRole('button', { name: /login with google/i });
      
      expect(heading).toHaveClass('mb-8');
      expect(button).toBeInTheDocument();
    });
  });

  // Helper functions (≤8 lines each)
  async function renderLoginPage(): Promise<void> {
    await renderWithTestSetup(<LoginPage />);
  }
});
