/**
 * GTM Circuit Breaker Tests
 * Tests the circuit breaker functionality for preventing infinite loops
 */

import { GTMCircuitBreaker } from '@/lib/gtm-circuit-breaker';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('GTMCircuitBreaker', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let circuitBreaker: GTMCircuitBreaker;

  beforeEach(() => {
    circuitBreaker = new GTMCircuitBreaker();
    jest.useFakeTimers();
  });

  afterEach(() => {
    circuitBreaker.destroy();
    jest.useRealTimers();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Event Deduplication', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should prevent duplicate events within deduplication window', () => {
      const eventKey = {
        event: 'exception',
        category: 'error',
        action: 'auth_required',
        context: '/dashboard'
      };

      // First event should be allowed
      expect(circuitBreaker.canSendEvent(eventKey)).toBe(true);
      circuitBreaker.recordEventSent(eventKey);

      // Immediate duplicate should be blocked
      expect(circuitBreaker.canSendEvent(eventKey)).toBe(false);

      // After deduplication window (2 seconds), should be allowed again
      jest.advanceTimersByTime(2100);
      expect(circuitBreaker.canSendEvent(eventKey)).toBe(true);
    });

    it('should allow different events even if sent immediately', () => {
      const event1 = {
        event: 'exception',
        category: 'error',
        action: 'auth_required',
        context: '/dashboard'
      };

      const event2 = {
        event: 'page_view',
        category: 'navigation',
        action: 'page_view',
        context: '/dashboard'
      };

      expect(circuitBreaker.canSendEvent(event1)).toBe(true);
      circuitBreaker.recordEventSent(event1);

      // Different event should be allowed immediately
      expect(circuitBreaker.canSendEvent(event2)).toBe(true);
    });
  });

  describe('Rate Limiting', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should enforce rate limits per event type', () => {
      const eventKey = {
        event: 'exception',
        category: 'error',
        action: 'auth_required',
        context: '/dashboard'
      };

      // Send events up to the limit
      for (let i = 0; i < 100; i++) {
        // Advance time slightly to bypass deduplication
        jest.advanceTimersByTime(50);
        
        const allowed = circuitBreaker.canSendEvent({ ...eventKey, context: `/page-${i}` });
        if (allowed) {
          circuitBreaker.recordEventSent({ ...eventKey, context: `/page-${i}` });
        }
      }

      // Next event of same type should be blocked
      jest.advanceTimersByTime(50);
      expect(circuitBreaker.canSendEvent(eventKey)).toBe(false);

      // After cleanup (1 minute), should be allowed again
      jest.advanceTimersByTime(60000);
      expect(circuitBreaker.canSendEvent(eventKey)).toBe(true);
    });
  });

  describe('Circuit Breaker Trip', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should trip circuit after threshold failures', () => {
      const eventKey = {
        event: 'exception',
        category: 'error',
        action: 'auth_required',
        context: '/dashboard'
      };

      // Record failures to trip the circuit
      for (let i = 0; i < 50; i++) {
        circuitBreaker.recordEventFailure(eventKey);
      }

      // Circuit should now be open
      expect(circuitBreaker.isOpen()).toBe(true);
      expect(circuitBreaker.canSendEvent(eventKey)).toBe(false);
    });

    it('should auto-recover after recovery timeout', () => {
      const eventKey = {
        event: 'exception',
        category: 'error',
        action: 'auth_required',
        context: '/dashboard'
      };

      // Trip the circuit
      for (let i = 0; i < 50; i++) {
        circuitBreaker.recordEventFailure(eventKey);
      }

      expect(circuitBreaker.isOpen()).toBe(true);

      // After recovery timeout (30 seconds), circuit should close
      jest.advanceTimersByTime(30000);
      
      expect(circuitBreaker.isOpen()).toBe(false);
      expect(circuitBreaker.canSendEvent(eventKey)).toBe(true);
    });
  });

  describe('Statistics', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track event statistics correctly', () => {
      const event1 = {
        event: 'exception',
        category: 'error',
        action: 'auth_required',
        context: '/dashboard'
      };

      const event2 = {
        event: 'page_view',
        category: 'navigation',
        action: 'page_view',
        context: '/home'
      };

      // Send some events
      circuitBreaker.recordEventSent(event1);
      jest.advanceTimersByTime(3000);
      circuitBreaker.recordEventSent(event2);
      
      const stats = circuitBreaker.getStats();
      
      expect(stats.isOpen).toBe(false);
      expect(stats.recentEventsCount).toBeGreaterThan(0);
      expect(stats.eventTypeCounts).toBeDefined();
    });
  });

  describe('Cleanup', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should clean up old events periodically', () => {
      const eventKey = {
        event: 'exception',
        category: 'error',
        action: 'auth_required',
        context: '/dashboard'
      };

      // Send an event
      circuitBreaker.recordEventSent(eventKey);
      
      let stats = circuitBreaker.getStats();
      expect(stats.recentEventsCount).toBe(1);

      // After cleanup interval (1 minute)
      jest.advanceTimersByTime(61000);
      
      stats = circuitBreaker.getStats();
      expect(stats.recentEventsCount).toBe(0);
      expect(stats.eventTypeCounts).toEqual({});
    });
  });

  describe('AuthGuard Infinite Loop Prevention', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should prevent auth_required event spam', () => {
      const authErrorEvent = {
        event: 'exception',
        category: 'error',
        action: 'auth_required',
        context: '/protected-page'
      };

      // Simulate rapid auth failures (like in an infinite loop)
      const results: boolean[] = [];
      for (let i = 0; i < 20; i++) {
        const allowed = circuitBreaker.canSendEvent(authErrorEvent);
        if (allowed) {
          circuitBreaker.recordEventSent(authErrorEvent);
        }
        results.push(allowed);
        
        // Simulate very rapid re-renders (every 10ms)
        jest.advanceTimersByTime(10);
      }

      // First event should be allowed
      expect(results[0]).toBe(true);
      
      // Subsequent rapid events should be blocked
      const blockedCount = results.filter(r => !r).length;
      expect(blockedCount).toBeGreaterThan(15); // Most should be blocked
    });
  });
});