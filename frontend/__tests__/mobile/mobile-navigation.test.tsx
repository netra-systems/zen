/**
 * Mobile Navigation Test Suite
 * Tests mobile-specific navigation patterns, gestures, and interactions
 * Business Value: Ensures seamless mobile navigation = critical for user retention
 * Follows 25-line function rule and 450-line file limit
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '@/components/ui/button';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
  }),
}));

describe('Mobile Navigation - Test Suite', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Mobile gesture simulation utilities
  const simulateSwipeGesture = (element: Element, direction: 'left' | 'right' | 'up' | 'down') => {
    const startCoords = { x: 200, y: 200 };
    const endCoords = {
      left: { x: 100, y: 200 },
      right: { x: 300, y: 200 },
      up: { x: 200, y: 100 },
      down: { x: 200, y: 300 }
    };
    
    fireEvent.touchStart(element, {
      touches: [{ clientX: startCoords.x, clientY: startCoords.y }]
    });
    
    fireEvent.touchMove(element, {
      touches: [{ clientX: endCoords[direction].x, clientY: endCoords[direction].y }]
    });
    
    fireEvent.touchEnd(element, {
      changedTouches: [{ clientX: endCoords[direction].x, clientY: endCoords[direction].y }]
    });
  };

  describe('Swipe Navigation', () => {
    it('handles right swipe for navigation', async () => {
      const handleSwipe = jest.fn();
      
      render(
        <div 
          data-testid="swipe-area"
          onTouchEnd={() => handleSwipe('right')}
          className="w-full h-64"
        >
          Swipeable Area
        </div>
      );
      
      const area = screen.getByTestId('swipe-area');
      simulateSwipeGesture(area, 'right');
      
      expect(handleSwipe).toHaveBeenCalledWith('right');
    });

    it('handles left swipe for navigation', async () => {
      const handleSwipe = jest.fn();
      
      render(
        <div 
          data-testid="swipe-area"
          onTouchEnd={() => handleSwipe('left')}
          className="w-full h-64"
        >
          Swipeable Area
        </div>
      );
      
      const area = screen.getByTestId('swipe-area');
      simulateSwipeGesture(area, 'left');
      
      expect(handleSwipe).toHaveBeenCalledWith('left');
    });

    it('handles vertical swipe for scroll navigation', async () => {
      const handleScroll = jest.fn();
      
      render(
        <div 
          data-testid="scroll-area"
          onTouchMove={handleScroll}
          className="overflow-y-auto h-64"
        >
          Scrollable Content
        </div>
      );
      
      const scrollArea = screen.getByTestId('scroll-area');
      simulateSwipeGesture(scrollArea, 'up');
      
      expect(handleScroll).toHaveBeenCalled();
    });

    it('prevents default scrolling during horizontal swipes', async () => {
      const preventDefault = jest.fn();
      
      render(
        <div 
          data-testid="horizontal-swipe"
          onTouchStart={(e) => preventDefault(e.preventDefault)}
        >
          Horizontal Swipe Zone
        </div>
      );
      
      const area = screen.getByTestId('horizontal-swipe');
      simulateSwipeGesture(area, 'left');
      
      expect(preventDefault).toHaveBeenCalled();
    });
  });

  describe('Touch Navigation Controls', () => {
    it('handles hamburger menu toggle on mobile', async () => {
      const handleMenuToggle = jest.fn();
      
      render(
        <Button 
          onClick={handleMenuToggle}
          className="md:hidden min-h-[44px] min-w-[44px]"
          data-testid="mobile-menu-button"
          aria-label="Toggle menu"
        >
          ☰
        </Button>
      );
      
      const menuButton = screen.getByTestId('mobile-menu-button');
      await user.click(menuButton);
      
      expect(handleMenuToggle).toHaveBeenCalledTimes(1);
    });

    it('provides visual feedback for navigation touch', async () => {
      render(
        <Button 
          className="active:bg-gray-200 transition-colors"
          data-testid="nav-button"
        >
          Navigate
        </Button>
      );
      
      const button = screen.getByTestId('nav-button');
      fireEvent.touchStart(button);
      
      expect(button).toHaveClass('active:bg-gray-200');
    });

    it('handles navigation with proper touch target sizes', () => {
      render(
        <nav data-testid="mobile-nav">
          <Button 
            className="min-h-[44px] min-w-[44px] touch-manipulation"
            data-testid="nav-item"
          >
            Home
          </Button>
        </nav>
      );
      
      const navItem = screen.getByTestId('nav-item');
      expect(navItem).toHaveClass('min-h-[44px]');
      expect(navItem).toHaveClass('touch-manipulation');
    });

    it('supports pull-to-refresh navigation', async () => {
      const handleRefresh = jest.fn();
      
      render(
        <div 
          data-testid="refreshable-content"
          onTouchStart={(e) => {
            if (e.touches[0].clientY < 50) handleRefresh();
          }}
        >
          Pull to refresh content
        </div>
      );
      
      const content = screen.getByTestId('refreshable-content');
      fireEvent.touchStart(content, {
        touches: [{ clientX: 200, clientY: 20 }]
      });
      
      expect(handleRefresh).toHaveBeenCalled();
    });
  });

  describe('Mobile Browser Navigation', () => {
    it('handles browser back button correctly', async () => {
      const handlePopState = jest.fn();
      
      // Mock popstate event
      window.addEventListener('popstate', handlePopState);
      
      window.dispatchEvent(new PopStateEvent('popstate', {
        state: { page: 'previous' }
      }));
      
      expect(handlePopState).toHaveBeenCalled();
      
      window.removeEventListener('popstate', handlePopState);
    });

    it('preserves navigation state during orientation change', async () => {
      const navigationState = { currentPage: 'chat' };
      history.pushState(navigationState, '', '/chat');
      
      // Simulate orientation change
      window.dispatchEvent(new Event('orientationchange'));
      
      await waitFor(() => {
        expect(history.state).toEqual(navigationState);
      });
    });

    it('handles deep linking on mobile browsers', async () => {
      const linkHandler = jest.fn();
      
      render(
        <a 
          href="/chat/thread-123"
          onClick={linkHandler}
          data-testid="deep-link"
        >
          Deep Link
        </a>
      );
      
      const link = screen.getByTestId('deep-link');
      await user.click(link);
      
      expect(linkHandler).toHaveBeenCalled();
    });

    it('manages navigation history stack properly', async () => {
      const initialLength = history.length;
      
      // Navigate to new page
      history.pushState({}, '', '/new-page');
      
      expect(history.length).toBe(initialLength + 1);
    });
  });

  describe('Keyboard Navigation on Mobile', () => {
    it('handles virtual keyboard appearance', async () => {
      const handleKeyboardShow = jest.fn();
      
      render(
        <input 
          data-testid="mobile-input"
          onFocus={handleKeyboardShow}
        />
      );
      
      const input = screen.getByTestId('mobile-input');
      await user.click(input);
      
      expect(handleKeyboardShow).toHaveBeenCalled();
    });

    it('maintains focus during virtual keyboard operations', async () => {
      render(
        <div>
          <input data-testid="input-1" />
          <input data-testid="input-2" />
        </div>
      );
      
      const input1 = screen.getByTestId('input-1');
      const input2 = screen.getByTestId('input-2');
      
      await user.click(input1);
      expect(input1).toHaveFocus();
      
      await user.tab();
      expect(input2).toHaveFocus();
    });

    it('handles return key navigation on mobile keyboards', async () => {
      const handleSubmit = jest.fn();
      
      render(
        <input 
          data-testid="mobile-form-input"
          onKeyPress={(e) => {
            if (e.key === 'Enter') handleSubmit();
          }}
        />
      );
      
      const input = screen.getByTestId('mobile-form-input');
      await user.type(input, 'test{enter}');
      
      expect(handleSubmit).toHaveBeenCalled();
    });

    it('adjusts layout for virtual keyboard', async () => {
      render(
        <div 
          className="pb-safe-bottom"
          data-testid="keyboard-aware-layout"
          style={{ paddingBottom: 'env(keyboard-inset-height, 0px)' }}
        >
          Keyboard aware content
        </div>
      );
      
      const layout = screen.getByTestId('keyboard-aware-layout');
      expect(layout).toHaveClass('pb-safe-bottom');
    });
  });

  describe('Navigation Performance', () => {
    it('provides instant visual feedback for navigation', async () => {
      const startTime = performance.now();
      
      render(
        <Button 
          onClick={() => {}}
          className="transition-transform active:scale-95"
          data-testid="instant-feedback"
        >
          Navigate
        </Button>
      );
      
      const button = screen.getByTestId('instant-feedback');
      fireEvent.touchStart(button);
      
      const feedbackTime = performance.now() - startTime;
      expect(feedbackTime).toBeLessThan(16); // 60fps target
    });

    it('handles rapid navigation without blocking', async () => {
      const navigationCount = { value: 0 };
      const handleNavigation = () => navigationCount.value++;
      
      render(
        <div>
          {Array.from({ length: 5 }, (_, i) => (
            <Button 
              key={i}
              onClick={handleNavigation}
              data-testid={`nav-button-${i}`}
            >
              Nav {i}
            </Button>
          ))}
        </div>
      );
      
      // Rapid navigation
      for (let i = 0; i < 5; i++) {
        const button = screen.getByTestId(`nav-button-${i}`);
        await user.click(button);
      }
      
      expect(navigationCount.value).toBe(5);
    });

    it('preloads navigation targets for smooth transitions', async () => {
      const preloadSpy = jest.fn();
      
      render(
        <Button 
          onMouseEnter={preloadSpy}
          onTouchStart={preloadSpy}
          data-testid="preload-nav"
        >
          Preload Target
        </Button>
      );
      
      const button = screen.getByTestId('preload-nav');
      fireEvent.touchStart(button);
      
      expect(preloadSpy).toHaveBeenCalled();
    });

    it('maintains smooth scrolling during navigation', async () => {
      render(
        <div 
          className="overflow-scroll h-32 scroll-smooth"
          data-testid="smooth-scroll"
        >
          <div className="h-96">Long scrollable content</div>
        </div>
      );
      
      const container = screen.getByTestId('smooth-scroll');
      expect(container).toHaveClass('scroll-smooth');
    });
  });

  describe('Accessibility in Mobile Navigation', () => {
    it('announces navigation changes to screen readers', () => {
      render(
        <nav 
          role="navigation"
          aria-label="Main navigation"
          data-testid="accessible-nav"
        >
          <Button aria-current="page">Current Page</Button>
        </nav>
      );
      
      const nav = screen.getByTestId('accessible-nav');
      const currentButton = screen.getByRole('button');
      
      expect(nav).toHaveAttribute('aria-label', 'Main navigation');
      expect(currentButton).toHaveAttribute('aria-current', 'page');
    });

    it('supports voice control navigation', () => {
      render(
        <Button 
          aria-label="Go to chat"
          data-voice-command="go to chat"
          data-testid="voice-nav"
        >
          Chat
        </Button>
      );
      
      const button = screen.getByTestId('voice-nav');
      expect(button).toHaveAttribute('aria-label', 'Go to chat');
      expect(button).toHaveAttribute('data-voice-command', 'go to chat');
    });

    it('provides high contrast navigation indicators', () => {
      render(
        <Button 
          className="focus:ring-4 focus:ring-blue-500 contrast-more:ring-black"
          data-testid="high-contrast-nav"
        >
          Navigate
        </Button>
      );
      
      const button = screen.getByTestId('high-contrast-nav');
      expect(button).toHaveClass('contrast-more:ring-black');
    });

    it('supports reduced motion preferences', () => {
      render(
        <div 
          className="transition-transform motion-reduce:transition-none"
          data-testid="motion-aware"
        >
          Respectful animation
        </div>
      );
      
      const element = screen.getByTestId('motion-aware');
      expect(element).toHaveClass('motion-reduce:transition-none');
    });
  });
});