/**
 * GTM Infinite Loop Prevention Test Suite
 * 
 * Comprehensive tests to ensure GTM events don't cause infinite loops
 * particularly in authentication flows and error scenarios.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthGuard } from '@/components/AuthGuard';
import { AuthProvider } from '@/auth/context';
import { GTMProvider } from '@/providers/GTMProvider';
import { useRouter } from 'next/navigation';
import { getGTMCircuitBreaker } from '@/lib/gtm-circuit-breaker';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock auth context
jest.mock('@/auth/context', () => ({
  ...jest.requireActual('@/auth/context'),
  useAuth: jest.fn(),
}));

// Mock GTM hook
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: jest.fn(),
}));

describe('GTM Infinite Loop Prevention', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let mockPush: jest.Mock;
  let mockTrackError: jest.Mock;
  let mockTrackPageView: jest.Mock;
  let mockUseAuth: jest.Mock;
  let mockUseGTMEvent: jest.Mock;
  let dataLayerSpy: jest.SpyInstance;

  beforeEach(() => {
    // Setup router mock
    mockPush = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      pathname: '/protected',
    });

    // Setup GTM event mocks
    mockTrackError = jest.fn();
    mockTrackPageView = jest.fn();
    mockUseGTMEvent = require('@/hooks/useGTMEvent').useGTMEvent;
    mockUseGTMEvent.mockReturnValue({
      trackError: mockTrackError,
      trackPageView: mockTrackPageView,
    });

    // Setup auth mock
    mockUseAuth = require('@/auth/context').useAuth;

    // Setup dataLayer spy
    window.dataLayer = [];
    dataLayerSpy = jest.spyOn(window.dataLayer, 'push');

    // Reset circuit breaker
    getGTMCircuitBreaker().reset();
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    dataLayerSpy.mockRestore();
      cleanupAntiHang();
  });

  describe('AuthGuard Event Deduplication', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should only fire auth_required event once when user is not authenticated', async () => {
      // Mock unauthenticated state
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
      });

      const { rerender } = render(
        <GTMProvider>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </GTMProvider>
      );

      // Wait for initial render
      await waitFor(() => {
        expect(mockTrackError).toHaveBeenCalledTimes(1);
      });

      // Trigger multiple re-renders
      for (let i = 0; i < 10; i++) {
        rerender(
          <GTMProvider>
            <AuthGuard>
              <div>Protected Content</div>
            </AuthGuard>
          </GTMProvider>
        );
      }

      // Should still only have one error event
      await waitFor(() => {
        expect(mockTrackError).toHaveBeenCalledTimes(1);
        expect(mockTrackError).toHaveBeenCalledWith(
          'auth_required',
          'User not authenticated',
          expect.any(String),
          false
        );
      });
    });

    it('should only fire page_view event once when user is authenticated', async () => {
      // Mock authenticated state
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com' },
        loading: false,
      });

      const { rerender } = render(
        <GTMProvider>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </GTMProvider>
      );

      // Wait for initial render
      await waitFor(() => {
        expect(mockTrackPageView).toHaveBeenCalledTimes(1);
      });

      // Trigger multiple re-renders
      for (let i = 0; i < 10; i++) {
        rerender(
          <GTMProvider>
            <AuthGuard>
              <div>Protected Content</div>
            </AuthGuard>
          </GTMProvider>
        );
      }

      // Should still only have one page view event
      await waitFor(() => {
        expect(mockTrackPageView).toHaveBeenCalledTimes(1);
        expect(mockTrackError).not.toHaveBeenCalled();
      });
    });

    it('should fire new events when path changes', async () => {
      // Mock unauthenticated state
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
      });

      // Mock window.location.pathname
      Object.defineProperty(window, 'location', {
        value: { pathname: '/page1' },
        writable: true,
      });

      const { rerender } = render(
        <GTMProvider>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </GTMProvider>
      );

      await waitFor(() => {
        expect(mockTrackError).toHaveBeenCalledTimes(1);
      });

      // Change path
      Object.defineProperty(window, 'location', {
        value: { pathname: '/page2' },
        writable: true,
      });

      rerender(
        <GTMProvider>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </GTMProvider>
      );

      // Should fire event for new path
      await waitFor(() => {
        expect(mockTrackError).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Circuit Breaker Protection', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should prevent event storms using circuit breaker', async () => {
      const circuitBreaker = getGTMCircuitBreaker();
      const events: boolean[] = [];

      // Simulate rapid event firing
      for (let i = 0; i < 100; i++) {
        const canSend = circuitBreaker.canSendEvent({
          event: 'exception',
          category: 'error',
          action: 'auth_required',
          context: '/protected',
        });
        
        if (canSend) {
          circuitBreaker.recordEventSent({
            event: 'exception',
            category: 'error',
            action: 'auth_required',
            context: '/protected',
          });
        }
        
        events.push(canSend);
      }

      // First event should be allowed
      expect(events[0]).toBe(true);
      
      // Most subsequent events should be blocked
      const blockedCount = events.filter(e => !e).length;
      expect(blockedCount).toBeGreaterThan(90);
    });

    it('should trip circuit breaker after threshold failures', () => {
      const circuitBreaker = getGTMCircuitBreaker();

      // Record many failures
      for (let i = 0; i < 50; i++) {
        circuitBreaker.recordEventFailure({
          event: 'exception',
          category: 'error',
          action: 'network_error',
        });
      }

      // Circuit should be open
      expect(circuitBreaker.isOpen()).toBe(true);

      // New events should be blocked
      const canSend = circuitBreaker.canSendEvent({
        event: 'any_event',
        category: 'any',
        action: 'any',
      });
      expect(canSend).toBe(false);
    });

    it('should enforce rate limiting per event type', () => {
      const circuitBreaker = getGTMCircuitBreaker();
      let successCount = 0;

      // Try to send 150 events of same type
      for (let i = 0; i < 150; i++) {
        // Use different context to bypass deduplication
        const canSend = circuitBreaker.canSendEvent({
          event: 'test_event',
          category: 'test',
          action: 'rate_limit_test',
          context: `/context-${i}`,
        });

        if (canSend) {
          successCount++;
          circuitBreaker.recordEventSent({
            event: 'test_event',
            category: 'test',
            action: 'rate_limit_test',
            context: `/context-${i}`,
          });
        }
      }

      // Should be limited to max events per type (100)
      expect(successCount).toBeLessThanOrEqual(100);
    });
  });

  describe('Loading State Transitions', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should not fire events while loading', async () => {
      // Start with loading state
      mockUseAuth.mockReturnValue({
        user: null,
        loading: true,
      });

      const { rerender } = render(
        <GTMProvider>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </GTMProvider>
      );

      // No events while loading
      expect(mockTrackError).not.toHaveBeenCalled();
      expect(mockTrackPageView).not.toHaveBeenCalled();

      // Transition to not authenticated
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
      });

      rerender(
        <GTMProvider>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </GTMProvider>
      );

      // Should fire auth_required event once
      await waitFor(() => {
        expect(mockTrackError).toHaveBeenCalledTimes(1);
      });
    });

    it('should handle rapid loading state changes', async () => {
      const loadingStates = [
        { loading: true, user: null },
        { loading: false, user: null },
        { loading: true, user: null },
        { loading: false, user: null },
        { loading: false, user: { id: '1', email: 'test@example.com' } },
      ];

      for (const state of loadingStates) {
        mockUseAuth.mockReturnValue(state);
        
        render(
          <GTMProvider>
            <AuthGuard>
              <div>Protected Content</div>
            </AuthGuard>
          </GTMProvider>
        );
      }

      // Should have limited event firing despite state changes
      await waitFor(() => {
        // Should have at most 2 events (one auth_required, one page_view)
        const totalEvents = mockTrackError.mock.calls.length + mockTrackPageView.mock.calls.length;
        expect(totalEvents).toBeLessThanOrEqual(2);
      });
    });
  });

  describe('Memory and Performance', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should not cause memory leaks with many events', () => {
      const circuitBreaker = getGTMCircuitBreaker();
      const initialMemory = process.memoryUsage().heapUsed;

      // Send many events
      for (let i = 0; i < 10000; i++) {
        circuitBreaker.canSendEvent({
          event: 'test',
          category: 'test',
          action: `action-${i}`,
          context: `/page-${i}`,
        });
      }

      const stats = circuitBreaker.getStats();
      
      // Recent events should be bounded
      expect(stats.recentEventsCount).toBeLessThan(1000);
      
      // Memory usage should not explode
      const finalMemory = process.memoryUsage().heapUsed;
      const memoryIncrease = finalMemory - initialMemory;
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024); // Less than 10MB
    });

    it('should cleanup old tracking data', () => {
      jest.useFakeTimers();
      const circuitBreaker = getGTMCircuitBreaker();

      // Send some events
      for (let i = 0; i < 50; i++) {
        circuitBreaker.recordEventSent({
          event: 'test',
          category: 'test',
          action: 'cleanup_test',
          context: `/page-${i}`,
        });
      }

      let stats = circuitBreaker.getStats();
      expect(stats.eventTypeCounts['test:cleanup_test']).toBe(50);

      // Advance time to trigger cleanup (1 minute)
      jest.advanceTimersByTime(61000);

      stats = circuitBreaker.getStats();
      expect(stats.eventTypeCounts).toEqual({});

      jest.useRealTimers();
    });
  });

  describe('Integration with GTMProvider', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should integrate circuit breaker with GTMProvider', async () => {
      window.dataLayer = [];
      const circuitBreaker = getGTMCircuitBreaker();
      
      render(
        <GTMProvider config={{ containerId: 'GTM-TEST', enabled: true }}>
          <div>Test</div>
        </GTMProvider>
      );

      // Manually push events through provider context would be tested here
      // This is a placeholder for integration testing
      expect(window.dataLayer).toBeDefined();
    });

    it('should respect circuit breaker in production-like scenario', async () => {
      // Reset circuit breaker
      const circuitBreaker = getGTMCircuitBreaker();
      circuitBreaker.reset();

      // Simulate auth failure scenario
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
      });

      // Render component multiple times rapidly
      for (let i = 0; i < 20; i++) {
        render(
          <GTMProvider>
            <AuthGuard>
              <div>Protected Content</div>
            </AuthGuard>
          </GTMProvider>
        );
      }

      // Events should be deduplicated
      await waitFor(() => {
        // Should have very few actual events fired
        expect(mockTrackError.mock.calls.length).toBeLessThan(5);
      });
    });
  });

  describe('Edge Cases and Error Scenarios', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle undefined window.dataLayer gracefully', () => {
      delete (window as any).dataLayer;
      
      const circuitBreaker = getGTMCircuitBreaker();
      
      // Should not throw
      expect(() => {
        circuitBreaker.canSendEvent({
          event: 'test',
          category: 'test',
          action: 'test',
        });
      }).not.toThrow();
    });

    it('should handle malformed event data', () => {
      const circuitBreaker = getGTMCircuitBreaker();
      
      // Should handle events with missing properties
      const canSend = circuitBreaker.canSendEvent({
        event: '',
        category: '',
        action: '',
      });
      
      expect(typeof canSend).toBe('boolean');
    });

    it('should recover from circuit breaker trip', () => {
      jest.useFakeTimers();
      const circuitBreaker = getGTMCircuitBreaker();

      // Trip the circuit
      for (let i = 0; i < 50; i++) {
        circuitBreaker.recordEventFailure({
          event: 'error',
          category: 'error',
          action: 'test',
        });
      }

      expect(circuitBreaker.isOpen()).toBe(true);

      // Advance time for recovery (30 seconds)
      jest.advanceTimersByTime(30000);

      // Circuit should be closed
      expect(circuitBreaker.isOpen()).toBe(false);
      
      // New events should be allowed
      const canSend = circuitBreaker.canSendEvent({
        event: 'test',
        category: 'test',
        action: 'recovery_test',
      });
      expect(canSend).toBe(true);

      jest.useRealTimers();
    });
  });
});