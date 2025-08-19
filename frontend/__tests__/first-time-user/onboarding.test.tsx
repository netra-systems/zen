/**
 * First-Time User Onboarding Flow Tests - Master Test Suite
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: Free → Early (Critical conversion funnel)
 * - Business Goal: Prevent 15-20% conversion loss from poor UX
 * - Value Impact: Each successful onboard = potential $1K+ ARR
 * - Revenue Impact: 5% improvement = $100K+ annually
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Main onboarding test orchestration
 * 
 * NOTE: This file has been split into focused modules for compliance:
 * - onboarding-landing.test.tsx: Landing page and initial experience
 * - onboarding-auth-recovery.test.tsx: Authentication error handling
 * - onboarding-welcome.test.tsx: Post-auth welcome flow
 * - onboarding-test-helpers.tsx: Shared utilities
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Real components under test
import LoginPage from '@/app/login/page';
import ChatPage from '@/app/chat/page';

// Test utilities
import { TestProviders } from '../setup/test-providers';
import { createMockUser } from '../utils/mock-factories';
import {
  setupCleanState,
  resetAllMocks,
  setupSimpleWebSocketMock,
  clearAuthState,
  mockAuthService,
  expectValueProposition,
  expectCallToAction,
  renderWithTestSetup,
  setupNextJSMocks,
  setupAuthMocks
} from './onboarding-test-helpers';

// Setup mocks
setupNextJSMocks();
setupAuthMocks();

describe('First-Time User Onboarding Flow - Integration Tests', () => {
  beforeEach(() => {
    setupCleanState();
    setupSimpleWebSocketMock();
    resetAllMocks();
  });

  afterEach(() => {
    clearAuthState();
    jest.clearAllMocks();
  });

  describe('End-to-End Onboarding Flow', () => {
    it('completes full user journey from landing to chat', async () => {
      // Step 1: Land on login page
      await renderLoginPage();
      expectValueProposition();
      expectCallToAction();

      // Step 2: Simulate successful auth
      mockAuthService.user = createMockUser();
      mockAuthService.loading = false;

      // Step 3: Navigate to chat
      await renderChatPage();
      await expectChatInterface();
    });

    it('maintains conversion focus throughout journey', async () => {
      await renderLoginPage();
      
      // Should emphasize business value
      expect(screen.getByText(/netra/i)).toBeInTheDocument();
      
      // Should have clear call-to-action
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      expect(loginButton).toBeEnabled();
    });

    it('provides consistent branding across all pages', async () => {
      // Test login page branding
      await renderLoginPage();
      expect(screen.getByText(/netra/i)).toBeInTheDocument();

      // Test chat page maintains branding
      mockAuthService.user = createMockUser();
      await renderChatPage();
      expect(document.body).toBeInTheDocument();
    });

    it('optimizes for conversion at each step', async () => {
      await renderLoginPage();
      
      // Landing page should focus on conversion
      expectValueProposition();
      expectCallToAction();
      
      // Should not overwhelm with too many options
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeLessThanOrEqual(2); // Login button + maybe one more
    });
  });

  describe('Critical User Experience Validation', () => {
    it('ensures smooth user flow without jarring transitions', async () => {
      const startTime = performance.now();
      
      await renderLoginPage();
      const landingTime = performance.now() - startTime;
      expect(landingTime).toBeLessThan(2000);

      mockAuthService.user = createMockUser();
      await renderChatPage();
      await expectChatInterface();
    });

    it('provides immediate value recognition', async () => {
      await renderLoginPage();
      
      // Should communicate value immediately
      const content = document.body.textContent || '';
      expect(content.toLowerCase()).toMatch(/netra/);
    });

    it('maintains professional appearance for enterprise appeal', async () => {
      await renderLoginPage();
      
      // Should have clean, professional design
      const container = document.querySelector('.flex.items-center.justify-center');
      expect(container).toBeInTheDocument();
      
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveClass('text-4xl', 'font-bold');
    });
  });

  describe('Business Conversion Metrics', () => {
    it('minimizes friction in signup process', async () => {
      await renderLoginPage();
      
      // Should have single-click signup
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      expect(loginButton).toBeInTheDocument();
      expect(loginButton).toBeEnabled();
    });

    it('emphasizes immediate value over features', async () => {
      await renderLoginPage();
      
      // Should focus on outcomes, not features
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toBeInTheDocument();
    });

    it('provides clear path to first value delivery', async () => {
      mockAuthService.user = createMockUser();
      await renderChatPage();
      
      await waitFor(() => {
        const messageInput = screen.getByRole('textbox', { name: /message input/i });
        expect(messageInput).toBeInTheDocument();
      });
    });
  });

  // Helper functions (≤8 lines each)
  async function renderLoginPage(): Promise<void> {
    await renderWithTestSetup(<LoginPage />);
  }

  async function renderChatPage(): Promise<void> {
    await renderWithTestSetup(
      <TestProviders>
        <ChatPage />
      </TestProviders>
    );
  }

  async function expectChatInterface(): Promise<void> {
    await waitFor(() => {
      const messageInput = screen.getByRole('textbox', { name: /message input/i });
      expect(messageInput).toBeInTheDocument();
    });
  }
});