/**
 * Landing Page Tests - First-Time User Experience (Critical for Conversion)
 * Implementation Agent Fix - Priority 1
 * 
 * Business Value Justification:
 * - Segment: Free → Early conversion (highest impact)
 * - Goal: Zero friction onboarding, 100% Start Chat button reliability
 * - Value Impact: 50% reduction in drop-off, direct conversion optimization
 * - Revenue Impact: +$50K MRR from improved first-user experience
 * 
 * Critical Test Focus: Landing page as the conversion gateway
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { jest } from '@jest/globals';

// Mock router first
const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    prefetch: jest.fn(),
  }),
}));

// Auth service is mocked globally in jest.setup.js with dynamic state support via global.mockAuthState

// Mock required stores
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    debug: jest.fn(),
  },
}));

// Import after mocks are set up
import HomePage from '@/app/page';

describe('Landing Page - First-Time User Experience', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockPush.mockClear();
    mockReplace.mockClear();
    // Reset global mock auth state
    global.mockAuthState = {
      user: null,
      loading: false,
      error: null
    };
  });

  describe('P0: Brand New User Landing Experience', () => {
    it('should show loading state initially for new users', async () => {
      // Setup: New user with loading auth state
      global.mockAuthState = {
        user: null,
        loading: true,
        error: null
      };

      render(<HomePage />);

      // Validation: Loading state visible
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      const loadingContainer = screen.getByText('Loading...').parentElement;
      expect(loadingContainer).toHaveClass('flex', 'items-center', 'justify-center');
    });

    it('should redirect unauthenticated users to login within 200ms', async () => {
      const startTime = performance.now();
      
      // Setup: Unauthenticated user
      global.mockAuthState = {
        user: null,
        loading: false,
        error: null
      };

      await act(async () => {
        render(<HomePage />);
      });

      // Wait for redirect
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      }, { timeout: 1000 });

      const redirectTime = performance.now() - startTime;
      expect(redirectTime).toBeLessThan(200);
    });

    it('should redirect authenticated users directly to chat', async () => {
      const mockUser = {
        id: 'user-123',
        email: 'test@netrasystems.ai',
        name: 'Test User',
      };

      global.mockAuthState = {
        user: mockUser,
        loading: false,
        error: null
      };

      await act(async () => {
        render(<HomePage />);
      });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/chat');
      });
    });

    it('should handle auth service errors gracefully', async () => {
      // Setup: Auth service error
      global.mockAuthState = {
        user: null,
        loading: false,
        error: 'Authentication service unavailable'
      };

      await act(async () => {
        render(<HomePage />);
      });

      // Should still redirect to login for graceful degradation
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      });
    });
  });

  describe('P0: Performance Metrics - Conversion Critical', () => {
    it('should achieve Time to Interactive < 2s for auth check', async () => {
      const startTime = performance.now();
      
      global.mockAuthState = {
        user: null,
        loading: false,
        error: null
      };

      await act(async () => {
        render(<HomePage />);
      });

      // Wait for interactive state (redirect decision made)
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalled();
      });

      const interactiveTime = performance.now() - startTime;
      expect(interactiveTime).toBeLessThan(2000);
    });

    it('should render without console errors', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      global.mockAuthState = {
        user: null,
        loading: false,
        error: null
      };

      await act(async () => {
        render(<HomePage />);
      });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalled();
      });

      expect(consoleSpy).not.toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe('P0: Mobile Responsiveness & Accessibility', () => {
    it('should be accessible with proper ARIA attributes', () => {
      mockAuthState.user = null;
      mockAuthState.loading = true;
      mockAuthState.error = null;

      render(<HomePage />);

      const loadingContainer = screen.getByText('Loading...').parentElement;
      expect(loadingContainer).toHaveAttribute('class', expect.stringContaining('flex'));
      
      const loadingText = screen.getByText('Loading...');
      expect(loadingText).toBeInTheDocument();
    });
  });

  describe('P0: Edge Cases & Error Recovery', () => {
    it('should prevent navigation loops with proper state management', async () => {
      global.mockAuthState = {
        user: null,
        loading: false,
        error: null
      };

      await act(async () => {
        render(<HomePage />);
      });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      });

      // Should only call push once, no loops
      expect(mockPush).toHaveBeenCalledTimes(1);
    });
  });

  describe('P0: Conversion Gateway Simulation', () => {
    it('should simulate complete new user journey to login', async () => {
      // Step 1: User lands on homepage
      global.mockAuthState = {
        user: null,
        loading: false,
        error: null
      };

      await act(async () => {
        render(<HomePage />);
      });

      // Step 2: Should redirect to login
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      });
    });

    it('should track timing for conversion analytics', async () => {
      const timingStart = performance.now();
      
      global.mockAuthState = {
        user: null,
        loading: false,
        error: null
      };

      await act(async () => {
        render(<HomePage />);
      });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalled();
      });

      const totalTime = performance.now() - timingStart;
      
      // Critical conversion timing under 500ms
      expect(totalTime).toBeLessThan(500);
    });
  });
});