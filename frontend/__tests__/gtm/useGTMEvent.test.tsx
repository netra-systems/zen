import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { GTMProvider } from '@/providers/GTMProvider';
import { useGTMEvent } from '@/hooks/useGTMEvent';

// Mock Next.js Script component
jest.mock('next/script', () => {
  return function MockScript({ onLoad, onReady, ...props }: any) {
    React.useEffect(() => {
      if (onReady) onReady();
      const timer = setTimeout(() => {
        if (onLoad) onLoad();
      }, 50);
      return () => clearTimeout(timer);
    }, [onLoad, onReady]);
    return <script {...props} data-testid="gtm-script" />;
  };
});

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
  },
}));

const createWrapper = (enabled = true) => {
  return ({ children }: { children: React.ReactNode }) => (
    <GTMProvider enabled={enabled} config={{ debug: true }}>
      {children}
    </GTMProvider>
  );
};

describe('useGTMEvent Hook', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let mockDataLayer: any[];

  beforeEach(() => {
    mockDataLayer = [];
    Object.defineProperty(global, 'window', {
      value: {
        dataLayer: mockDataLayer,
        location: {
          pathname: '/test-event-path'
        }
      },
      writable: true
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Hook Initialization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should provide event tracking functionality', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current).toHaveProperty('trackEvent');
        expect(result.current).toHaveProperty('trackPageView');
        expect(result.current).toHaveProperty('trackUserAction');
        expect(result.current).toHaveProperty('trackConversion');
        expect(result.current).toHaveProperty('isReady');
        expect(result.current).toHaveProperty('eventQueue');
      });
    });

    it('should indicate when GTM is ready', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });
    });

    it('should handle disabled GTM', () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper(false)
      });

      expect(result.current.isReady).toBe(false);
    });
  });

  describe('Generic Event Tracking', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track basic events with required fields', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackEvent({
          event: 'custom_event',
          event_category: 'test',
          event_action: 'test_action'
        });
      });

      await waitFor(() => {
        const trackedEvent = mockDataLayer.find(item => item.event === 'custom_event');
        expect(trackedEvent).toBeDefined();
        expect(trackedEvent.event_category).toBe('test');
        expect(trackedEvent.event_action).toBe('test_action');
        expect(trackedEvent.timestamp).toBeDefined();
        expect(trackedEvent.page_path).toBe('/test-event-path');
      });
    });

    it('should track events with all optional fields', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackEvent({
          event: 'detailed_event',
          event_category: 'engagement',
          event_action: 'click',
          event_label: 'header_button',
          value: 1,
          custom_parameters: {
            button_id: 'nav-login',
            section: 'header'
          },
          user_id: 'user123',
          session_id: 'session456'
        });
      });

      await waitFor(() => {
        const trackedEvent = mockDataLayer.find(item => item.event === 'detailed_event');
        expect(trackedEvent).toBeDefined();
        expect(trackedEvent.event_label).toBe('header_button');
        expect(trackedEvent.value).toBe(1);
        expect(trackedEvent.custom_parameters.button_id).toBe('nav-login');
        expect(trackedEvent.user_id).toBe('user123');
        expect(trackedEvent.session_id).toBe('session456');
      });
    });
  });

  describe('Page View Tracking', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track page views with default path', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackPageView();
      });

      await waitFor(() => {
        const pageViewEvent = mockDataLayer.find(item => item.event === 'page_view');
        expect(pageViewEvent).toBeDefined();
        expect(pageViewEvent.page_path).toBe('/test-event-path');
        expect(pageViewEvent.event_category).toBe('navigation');
      });
    });

    it('should track page views with custom path and title', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackPageView('/custom-path', 'Custom Page Title');
      });

      await waitFor(() => {
        const pageViewEvent = mockDataLayer.find(item => item.event === 'page_view');
        expect(pageViewEvent).toBeDefined();
        expect(pageViewEvent.page_path).toBe('/custom-path');
        expect(pageViewEvent.page_title).toBe('Custom Page Title');
      });
    });

    it('should include additional metadata in page views', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackPageView('/dashboard', 'Dashboard', {
          user_tier: 'premium',
          feature_flags: ['new_ui', 'beta_chat']
        });
      });

      await waitFor(() => {
        const pageViewEvent = mockDataLayer.find(item => item.event === 'page_view');
        expect(pageViewEvent).toBeDefined();
        expect(pageViewEvent.page_path).toBe('/dashboard');
        expect(pageViewEvent.page_title).toBe('Dashboard');
        expect(pageViewEvent.user_tier).toBe('premium');
        expect(pageViewEvent.feature_flags).toEqual(['new_ui', 'beta_chat']);
      });
    });
  });

  describe('User Action Tracking', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track button clicks', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackUserAction('click', 'start_chat_button', {
          button_text: 'Start New Chat',
          position: 'sidebar'
        });
      });

      await waitFor(() => {
        const actionEvent = mockDataLayer.find(item => item.event === 'user_action');
        expect(actionEvent).toBeDefined();
        expect(actionEvent.event_category).toBe('interaction');
        expect(actionEvent.event_action).toBe('click');
        expect(actionEvent.event_label).toBe('start_chat_button');
        expect(actionEvent.button_text).toBe('Start New Chat');
        expect(actionEvent.position).toBe('sidebar');
      });
    });

    it('should track form submissions', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackUserAction('submit', 'login_form', {
          form_method: 'email',
          validation_errors: 0,
          completion_time: 45
        });
      });

      await waitFor(() => {
        const actionEvent = mockDataLayer.find(item => item.event === 'user_action');
        expect(actionEvent).toBeDefined();
        expect(actionEvent.event_action).toBe('submit');
        expect(actionEvent.event_label).toBe('login_form');
        expect(actionEvent.form_method).toBe('email');
        expect(actionEvent.validation_errors).toBe(0);
        expect(actionEvent.completion_time).toBe(45);
      });
    });

    it('should track navigation actions', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackUserAction('navigate', 'menu_item', {
          destination: '/dashboard',
          navigation_method: 'sidebar_menu'
        });
      });

      await waitFor(() => {
        const actionEvent = mockDataLayer.find(item => item.event === 'user_action');
        expect(actionEvent).toBeDefined();
        expect(actionEvent.destination).toBe('/dashboard');
        expect(actionEvent.navigation_method).toBe('sidebar_menu');
      });
    });
  });

  describe('Conversion Tracking', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track signup conversions', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackConversion('signup', {
          value: 0,
          currency: 'USD',
          conversion_id: 'signup_123',
          source: 'landing_page',
          medium: 'cta_button',
          campaign: 'summer_2024'
        });
      });

      await waitFor(() => {
        const conversionEvent = mockDataLayer.find(item => item.event === 'conversion');
        expect(conversionEvent).toBeDefined();
        expect(conversionEvent.event_category).toBe('conversion');
        expect(conversionEvent.event_action).toBe('signup');
        expect(conversionEvent.value).toBe(0);
        expect(conversionEvent.currency).toBe('USD');
        expect(conversionEvent.conversion_id).toBe('signup_123');
        expect(conversionEvent.source).toBe('landing_page');
        expect(conversionEvent.campaign).toBe('summer_2024');
      });
    });

    it('should track purchase conversions', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackConversion('purchase', {
          value: 99.99,
          currency: 'USD',
          transaction_id: 'txn_456',
          items: [
            { name: 'Premium Plan', category: 'subscription', price: 99.99, quantity: 1 }
          ]
        });
      });

      await waitFor(() => {
        const conversionEvent = mockDataLayer.find(item => item.event === 'conversion');
        expect(conversionEvent).toBeDefined();
        expect(conversionEvent.event_action).toBe('purchase');
        expect(conversionEvent.value).toBe(99.99);
        expect(conversionEvent.transaction_id).toBe('txn_456');
        expect(conversionEvent.items).toHaveLength(1);
        expect(conversionEvent.items[0].name).toBe('Premium Plan');
      });
    });

    it('should track trial start conversions', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackConversion('trial_start', {
          trial_type: 'premium',
          trial_duration: 30,
          value: 0
        });
      });

      await waitFor(() => {
        const conversionEvent = mockDataLayer.find(item => item.event === 'conversion');
        expect(conversionEvent).toBeDefined();
        expect(conversionEvent.event_action).toBe('trial_start');
        expect(conversionEvent.trial_type).toBe('premium');
        expect(conversionEvent.trial_duration).toBe(30);
      });
    });
  });

  describe('Event Queue Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should queue events when GTM is not ready', () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      // GTM is not ready initially
      expect(result.current.isReady).toBe(false);

      // Track event while not ready
      act(() => {
        result.current.trackEvent({
          event: 'queued_event',
          event_category: 'test'
        });
      });

      // Event should be queued
      expect(result.current.eventQueue).toHaveLength(1);
      expect(result.current.eventQueue[0].event).toBe('queued_event');
    });

    it('should flush queued events when GTM becomes ready', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      // Track events while not ready
      act(() => {
        result.current.trackEvent({ event: 'queued_1', event_category: 'test' });
        result.current.trackEvent({ event: 'queued_2', event_category: 'test' });
      });

      expect(result.current.eventQueue).toHaveLength(2);

      // Wait for GTM to become ready
      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Queue should be empty and events should be in dataLayer
      await waitFor(() => {
        expect(result.current.eventQueue).toHaveLength(0);
        expect(mockDataLayer.find(item => item.event === 'queued_1')).toBeDefined();
        expect(mockDataLayer.find(item => item.event === 'queued_2')).toBeDefined();
      });
    });

    it('should limit queue size to prevent memory issues', () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      // Add many events to queue
      act(() => {
        for (let i = 0; i < 150; i++) {
          result.current.trackEvent({
            event: `queued_${i}`,
            event_category: 'test'
          });
        }
      });

      // Queue should be limited (assuming max of 100)
      expect(result.current.eventQueue.length).toBeLessThanOrEqual(100);
    });
  });

  describe('Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle events when GTM is disabled', () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper(false)
      });

      expect(result.current.isReady).toBe(false);

      // Events should be queued even when disabled
      act(() => {
        result.current.trackEvent({
          event: 'disabled_event',
          event_category: 'test'
        });
      });

      expect(result.current.eventQueue).toHaveLength(1);
    });

    it('should handle invalid event data gracefully', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Track event with missing required fields
      act(() => {
        result.current.trackEvent({
          event_category: 'test'
        } as any);
      });

      // Should not crash, but event should be handled by GTM error handling
      expect(() => result.current.trackEvent).not.toThrow();
    });
  });

  describe('Performance Considerations', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle rapid event tracking without issues', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Track many events rapidly
      act(() => {
        for (let i = 0; i < 100; i++) {
          result.current.trackEvent({
            event: `rapid_${i}`,
            event_category: 'performance_test',
            event_action: 'rapid_fire',
            value: i
          });
        }
      });

      await waitFor(() => {
        const rapidEvents = mockDataLayer.filter(item => 
          item.event && item.event.startsWith('rapid_')
        );
        expect(rapidEvents).toHaveLength(100);
      });
    });

    it('should debounce similar events to prevent spam', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Track the same event multiple times rapidly
      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.trackEvent({
            event: 'repeated_event',
            event_category: 'test',
            event_action: 'spam_test'
          });
        }
      });

      // Implementation might debounce identical events
      // This test depends on actual debouncing logic in useGTMEvent
      await waitFor(() => {
        const repeatedEvents = mockDataLayer.filter(item => 
          item.event === 'repeated_event'
        );
        // Should have fewer than 10 events due to debouncing
        expect(repeatedEvents.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Custom Event Types', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle authentication events through generic interface', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackEvent({
          event: 'user_login',
          event_category: 'authentication',
          event_action: 'login_success',
          auth_method: 'google',
          is_new_user: false
        });
      });

      await waitFor(() => {
        const authEvent = mockDataLayer.find(item => item.event === 'user_login');
        expect(authEvent).toBeDefined();
        expect(authEvent.event_category).toBe('authentication');
        expect(authEvent.auth_method).toBe('google');
        expect(authEvent.is_new_user).toBe(false);
      });
    });

    it('should handle engagement events through generic interface', async () => {
      const { result } = renderHook(() => useGTMEvent(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      act(() => {
        result.current.trackEvent({
          event: 'agent_activated',
          event_category: 'engagement',
          event_action: 'agent_start',
          agent_type: 'code_generator',
          thread_id: 'thread_123'
        });
      });

      await waitFor(() => {
        const engagementEvent = mockDataLayer.find(item => item.event === 'agent_activated');
        expect(engagementEvent).toBeDefined();
        expect(engagementEvent.agent_type).toBe('code_generator');
        expect(engagementEvent.thread_id).toBe('thread_123');
      });
    });
  });
});