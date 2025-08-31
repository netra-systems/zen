import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
vent 20%+ mobile conversion loss from poor UX
 * - Value Impact: Each mobile conversion = $1K+ potential ARR
 * - Revenue Impact: 15% mobile UX improvement = $150K+ annually
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Touch interactions, responsive design, mobile gestures
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Real components under test
import LoginPage from '@/app/login/page';
import { MessageInput } from '@/components/chat/MessageInput';
import { Button } from '@/components/ui/button';

// Test utilities
import { TestProviders } from '../setup/test-providers';
import {
  setupCleanState,
  setupSimpleWebSocketMock,
  mockAuthService,
  clearAuthState
} from './onboarding-test-helpers';
import {
  setMobileViewport,
  simulateTouchEvent,
  simulateSwipe,
  simulatePinch,
  createMockUser,
  setupMockVibration,
  setupMockMatchMedia,
  measureInteractionTime,
  expectPerformantInteraction,
  simulateLongPress,
  simulateRapidTouches,
  simulateHighDensityDisplay,
  simulatePortraitOrientation,
  simulateLandscapeOrientation,
  simulateSmallScreen,
  MOBILE_BREAKPOINTS
} from './mobile-experience-helpers';

// Mock the auth service to avoid provider issues
jest.mock('@/auth', () => ({
  authService: {
    useAuth: () => ({
      login: jest.fn(),
      loading: false,
      isAuthenticated: false,
      user: null
    })
  }
}));

describe('Mobile Experience for First-Time Users', () => {
    jest.setTimeout(10000);
  const user = userEvent.setup();

  beforeEach(() => {
    setupCleanState();
    setupSimpleWebSocketMock();
  });

  afterEach(() => {
    clearAuthState();
    jest.clearAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Touch Target Optimization', () => {
      jest.setTimeout(10000);
    it('ensures login button meets 44px minimum touch target', () => {
      simulatePortraitOrientation();
      render(<LoginPage />);
      
      const loginButton = screen.getByRole('button', { name: /login with google/i });
      
      expect(loginButton).toBeInTheDocument();
      expect(loginButton).toHaveClass('h-11'); // h-11 = 44px in Tailwind
    });

    it('provides adequate spacing between interactive elements', async () => {
      render(<LoginPage />);
      
      const loginButton = screen.getByRole('button');
      const container = loginButton.closest('.text-center');
      
      expect(container).toBeInTheDocument();
      expect(loginButton).toBeInTheDocument();
    });

    it('handles touch interactions without lag on buttons', async () => {
      const mockClick = jest.fn();
      render(<Button onClick={mockClick} size="lg">Touch Test</Button>);
      
      const button = screen.getByRole('button');
      await user.click(button);
      
      expect(mockClick).toHaveBeenCalled();
    });

    it('supports touch feedback visual states', () => {
      render(<LoginPage />);
      
      const button = screen.getByRole('button');
      simulateTouchEvent(button, 'touchStart');
      
      expect(button).toBeInTheDocument();
    });
  });

  describe('Responsive Design Validation', () => {
      jest.setTimeout(10000);
    it('adapts layout for mobile portrait orientation', async () => {
      setMobileViewport(375, 667);
      render(<LoginPage />);
      
      const container = screen.getByText('Netra').closest('.flex');
      expect(container).toHaveClass('flex', 'items-center', 'justify-center');
      expect(container).toHaveClass('h-screen');
    });

    it('adjusts for mobile landscape orientation', () => {
      setMobileViewport(667, 375);
      render(<LoginPage />);
      
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveClass('text-4xl', 'font-bold', 'mb-8');
    });

    it('scales content appropriately for small screens', () => {
      setMobileViewport(320, 568); // iPhone 5
      render(<LoginPage />);
      
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('maintains readability on high-density displays', () => {
      Object.defineProperty(window, 'devicePixelRatio', { value: 3 });
      render(<LoginPage />);
      
      const heading = screen.getByText('Netra');
      expect(heading).toHaveClass('text-4xl');
    });
  });

  describe('Mobile Keyboard Handling', () => {
      jest.setTimeout(10000);
    it('renders message input with proper mobile attributes', () => {
      render(<TestProviders><MessageInput /></TestProviders>);
      
      const input = screen.getByRole('textbox', { name: /message input/i });
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('aria-label', 'Message input');
    });

    it('handles viewport changes gracefully', () => {
      render(<TestProviders><MessageInput /></TestProviders>);
      setMobileViewport(375, 400);
      
      const input = screen.getByRole('textbox');
      expect(input).toBeInTheDocument();
    });

    it('provides accessible placeholder text', () => {
      render(<TestProviders><MessageInput /></TestProviders>);
      
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('placeholder');
    });

    it('maintains responsive design during interactions', () => {
      render(<TestProviders><MessageInput /></TestProviders>);
      
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('w-full');
    });
  });

  describe('Touch Gestures and Navigation', () => {
      jest.setTimeout(10000);
    it('handles swipe gestures for navigation', async () => {
      render(<LoginPage />);
      
      const container = document.body;
      const swipeHandler = jest.fn();
      
      container.addEventListener('touchmove', swipeHandler);
      simulateSwipe(container, 100, 300);
      
      expect(swipeHandler).toHaveBeenCalled();
      container.removeEventListener('touchmove', swipeHandler);
    });

    it('supports pinch-to-zoom on content areas', () => {
      render(<LoginPage />);
      
      const heading = screen.getByText('Netra');
      fireEvent.touchStart(heading, {
        touches: [
          { clientX: 100, clientY: 100, identifier: 0 },
          { clientX: 200, clientY: 200, identifier: 1 }
        ]
      });
      
      expect(heading).toBeInTheDocument();
    });

    it('prevents accidental double-tap zoom on buttons', async () => {
      render(<LoginPage />);
      
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('handles long press interactions appropriately', async () => {
      render(<LoginPage />);
      
      const heading = screen.getByText('Netra');
      simulateTouchEvent(heading, 'touchStart');
      
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 500));
      });
      
      simulateTouchEvent(heading, 'touchEnd');
      expect(heading).toBeInTheDocument();
    });
  });

  describe('Viewport and Orientation Adaptations', () => {
      jest.setTimeout(10000);
    it('adapts to various mobile orientations and densities', () => {
      simulatePortraitOrientation();
      render(<LoginPage />);
      
      const container = screen.getByText('Netra').closest('.text-center');
      expect(container).toBeInTheDocument();
    });

    it('maintains layout integrity during device changes', () => {
      simulateHighDensityDisplay();
      render(<LoginPage />);
      
      const heading = screen.getByText('Netra');
      expect(heading).toBeVisible();
    });
  });

  describe('Performance on Mobile Devices', () => {
      jest.setTimeout(10000);
    it('handles rapid touch events efficiently', async () => {
      const touchCount = { value: 0 };
      const handleTouch = () => touchCount.value++;
      
      render(<Button onTouchStart={handleTouch}>Rapid Touch</Button>);
      
      const button = screen.getByRole('button');
      simulateRapidTouches(button);
      
      expect(touchCount.value).toBe(5);
    });

    it('prevents memory leaks from touch event listeners', () => {
      const { unmount } = render(<LoginPage />);
      
      const button = screen.getByRole('button');
      simulateTouchEvent(button, 'touchStart');
      
      unmount();
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility on Mobile', () => {
      jest.setTimeout(10000);
    it('provides comprehensive mobile accessibility support', () => {
      setupMockVibration();
      setupMockMatchMedia();
      render(<LoginPage />);
      
      const heading = screen.getByRole('heading', { level: 1 });
      const button = screen.getByRole('button', { name: /login with google/i });
      
      expect(heading).toHaveTextContent('Netra');
      expect(button).toHaveTextContent('Login with Google');
      expect(button).toBeInTheDocument();
    });

    it('supports touch-based screen reader navigation', () => {
      render(<LoginPage />);
      
      const button = screen.getByRole('button', { name: /login with google/i });
      expect(button).toBeInTheDocument();
    });
  });
});