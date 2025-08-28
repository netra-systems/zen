import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { GTMProvider } from '@/providers/GTMProvider';
import { useGTM } from '@/hooks/useGTM';
import type { AuthenticationEventData, EngagementEventData, ConversionEventData } from '@/types/gtm.types';

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

const createWrapper = (enabled = true, debug = true) => {
  return ({ children }: { children: React.ReactNode }) => (
    <GTMProvider enabled={enabled} config={{ debug }}>
      {children}
    </GTMProvider>
  );
};

describe('useGTM Hook', () => {
  let mockDataLayer: any[];

  beforeEach(() => {
    mockDataLayer = [];
    Object.defineProperty(global, 'window', {
      value: {
        dataLayer: mockDataLayer,
        location: {
          pathname: '/test-hook-path'
        }
      },
      writable: true
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Hook Initialization', () => {
    it('should provide all GTM functionality', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      expect(result.current).toHaveProperty('isLoaded');
      expect(result.current).toHaveProperty('isEnabled');
      expect(result.current).toHaveProperty('config');
      expect(result.current).toHaveProperty('pushEvent');
      expect(result.current).toHaveProperty('pushData');
      expect(result.current).toHaveProperty('getDataLayer');
      expect(result.current).toHaveProperty('events');
      expect(result.current).toHaveProperty('debug');
    });

    it('should provide event tracking methods', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      expect(result.current.events).toHaveProperty('trackAuth');
      expect(result.current.events).toHaveProperty('trackEngagement');
      expect(result.current.events).toHaveProperty('trackConversion');
      expect(result.current.events).toHaveProperty('trackCustom');
      expect(result.current.events).toHaveProperty('getStats');
    });

    it('should provide debug functionality', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      expect(result.current.debug).toHaveProperty('enableDebug');
      expect(result.current.debug).toHaveProperty('disableDebug');
      expect(result.current.debug).toHaveProperty('isDebugMode');
      expect(result.current.debug).toHaveProperty('debugInfo');
      expect(result.current.debug).toHaveProperty('clearDebugHistory');
    });
  });

  describe('Authentication Event Tracking', () => {
    it('should track user login events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackAuth('user_login', {
          auth_method: 'email',
          is_new_user: false,
          user_tier: 'free'
        });
      });

      await waitFor(() => {
        const loginEvent = mockDataLayer.find(item => item.event === 'user_login');
        expect(loginEvent).toBeDefined();
        expect(loginEvent.event_category).toBe('authentication');
        expect(loginEvent.event_action).toBe('user login');
        expect(loginEvent.auth_method).toBe('email');
        expect(loginEvent.is_new_user).toBe(false);
        expect(loginEvent.user_tier).toBe('free');
        expect(loginEvent.timestamp).toBeDefined();
      });
    });

    it('should track user signup events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackAuth('user_signup', {
          auth_method: 'google',
          is_new_user: true,
          user_tier: 'early'
        });
      });

      await waitFor(() => {
        const signupEvent = mockDataLayer.find(item => item.event === 'user_signup');
        expect(signupEvent).toBeDefined();
        expect(signupEvent.event_category).toBe('authentication');
        expect(signupEvent.auth_method).toBe('google');
        expect(signupEvent.is_new_user).toBe(true);
      });
    });

    it('should track OAuth completion events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackAuth('oauth_complete', {
          auth_method: 'oauth',
          user_id: 'user123'
        });
      });

      await waitFor(() => {
        const oauthEvent = mockDataLayer.find(item => item.event === 'oauth_complete');
        expect(oauthEvent).toBeDefined();
        expect(oauthEvent.user_id).toBe('user123');
      });
    });
  });

  describe('Engagement Event Tracking', () => {
    it('should track chat started events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackEngagement('chat_started', {
          thread_id: 'thread123',
          session_duration: 0
        });
      });

      await waitFor(() => {
        const chatEvent = mockDataLayer.find(item => item.event === 'chat_started');
        expect(chatEvent).toBeDefined();
        expect(chatEvent.event_category).toBe('engagement');
        expect(chatEvent.thread_id).toBe('thread123');
      });
    });

    it('should track message sent events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackEngagement('message_sent', {
          thread_id: 'thread123',
          message_length: 150,
          agent_type: 'supervisor_agent'
        });
      });

      await waitFor(() => {
        const messageEvent = mockDataLayer.find(item => item.event === 'message_sent');
        expect(messageEvent).toBeDefined();
        expect(messageEvent.message_length).toBe(150);
        expect(messageEvent.agent_type).toBe('supervisor_agent');
      });
    });

    it('should track agent activation events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackEngagement('agent_activated', {
          agent_type: 'code_agent',
          feature_type: 'code_generation'
        });
      });

      await waitFor(() => {
        const agentEvent = mockDataLayer.find(item => item.event === 'agent_activated');
        expect(agentEvent).toBeDefined();
        expect(agentEvent.agent_type).toBe('code_agent');
        expect(agentEvent.feature_type).toBe('code_generation');
      });
    });

    it('should track feature usage events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackEngagement('feature_used', {
          feature_type: 'file_upload',
          session_duration: 300
        });
      });

      await waitFor(() => {
        const featureEvent = mockDataLayer.find(item => item.event === 'feature_used');
        expect(featureEvent).toBeDefined();
        expect(featureEvent.feature_type).toBe('file_upload');
        expect(featureEvent.session_duration).toBe(300);
      });
    });
  });

  describe('Conversion Event Tracking', () => {
    it('should track trial started events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackConversion('trial_started', {
          plan_type: 'early',
          conversion_source: 'landing_page'
        });
      });

      await waitFor(() => {
        const trialEvent = mockDataLayer.find(item => item.event === 'trial_started');
        expect(trialEvent).toBeDefined();
        expect(trialEvent.event_category).toBe('conversion');
        expect(trialEvent.plan_type).toBe('early');
        expect(trialEvent.conversion_source).toBe('landing_page');
      });
    });

    it('should track plan upgrade events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackConversion('plan_upgraded', {
          plan_type: 'enterprise',
          transaction_value: 299.99,
          transaction_id: 'txn123',
          currency: 'USD'
        });
      });

      await waitFor(() => {
        const upgradeEvent = mockDataLayer.find(item => item.event === 'plan_upgraded');
        expect(upgradeEvent).toBeDefined();
        expect(upgradeEvent.transaction_value).toBe(299.99);
        expect(upgradeEvent.value).toBe(299.99); // Should map to value field
        expect(upgradeEvent.transaction_id).toBe('txn123');
        expect(upgradeEvent.currency).toBe('USD');
      });
    });

    it('should track payment completion events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.events.trackConversion('payment_completed', {
          transaction_value: 99.99,
          transaction_id: 'pay123',
          plan_type: 'mid'
        });
      });

      await waitFor(() => {
        const paymentEvent = mockDataLayer.find(item => item.event === 'payment_completed');
        expect(paymentEvent).toBeDefined();
        expect(paymentEvent.transaction_value).toBe(99.99);
        expect(paymentEvent.plan_type).toBe('mid');
      });
    });
  });

  describe('Custom Event Tracking', () => {
    it('should track custom events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      const customEvent = {
        event: 'custom_interaction',
        event_category: 'ui',
        event_action: 'button_click',
        event_label: 'export_data',
        value: 1,
        custom_parameters: {
          export_format: 'csv',
          file_size: 1024
        }
      };

      act(() => {
        result.current.events.trackCustom(customEvent);
      });

      await waitFor(() => {
        const trackedEvent = mockDataLayer.find(item => item.event === 'custom_interaction');
        expect(trackedEvent).toBeDefined();
        expect(trackedEvent.event_category).toBe('ui');
        expect(trackedEvent.custom_parameters.export_format).toBe('csv');
      });
    });
  });

  describe('Statistics and Analytics', () => {
    it('should provide event statistics', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      // Track several events
      act(() => {
        result.current.events.trackAuth('user_login');
        result.current.events.trackAuth('user_login');
        result.current.events.trackEngagement('chat_started');
      });

      await waitFor(() => {
        const stats = result.current.events.getStats();
        expect(stats.totalEvents).toBe(3);
        expect(stats.eventsByType.user_login).toBe(2);
        expect(stats.eventsByType.chat_started).toBe(1);
        expect(stats.lastEventTime).toBeDefined();
      });
    });

    it('should handle empty event history', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      const stats = result.current.events.getStats();
      expect(stats.totalEvents).toBe(0);
      expect(stats.eventsByType).toEqual({});
      expect(stats.lastEventTime).toBeUndefined();
    });
  });

  describe('Debug Functionality', () => {
    it('should enable debug mode', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.debug.enableDebug();
      });

      await waitFor(() => {
        const debugEvent = mockDataLayer.find(item => item.event === 'gtm.debug.enable');
        expect(debugEvent).toBeDefined();
        expect(debugEvent.debug_mode).toBe(true);
      });
    });

    it('should disable debug mode', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.debug.disableDebug();
      });

      await waitFor(() => {
        const debugEvent = mockDataLayer.find(item => item.event === 'gtm.debug.disable');
        expect(debugEvent).toBeDefined();
        expect(debugEvent.debug_mode).toBe(false);
      });
    });

    it('should provide debug information', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper(true, true)
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      expect(result.current.debug.isDebugMode).toBe(true);
      expect(result.current.debug.debugInfo).toHaveProperty('containerId');
      expect(result.current.debug.debugInfo).toHaveProperty('scriptStatus');
      expect(result.current.debug.debugInfo).toHaveProperty('eventHistory');
      expect(result.current.debug.debugInfo).toHaveProperty('performance');
      expect(result.current.debug.debugInfo).toHaveProperty('consoleLogs');

      expect(result.current.debug.debugInfo.scriptStatus).toBe('loaded');
      expect(result.current.debug.debugInfo.containerId).toBe('GTM-WKP28PNQ');
    });

    it('should clear debug history', async () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
      
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper(true, true)
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      act(() => {
        result.current.debug.clearDebugHistory();
      });

      expect(consoleSpy).toHaveBeenCalledWith('[GTM] Debug history cleared');
      
      consoleSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    it('should handle events when GTM is disabled', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper(false, true)
      });

      // GTM should be disabled but hook should still work
      expect(result.current.isEnabled).toBe(false);

      // Events should be handled gracefully
      act(() => {
        result.current.events.trackAuth('user_login');
      });

      // No events should be in dataLayer
      expect(mockDataLayer.find(item => item.event === 'user_login')).toBeUndefined();
    });
  });

  describe('Performance', () => {
    it('should handle multiple rapid events', async () => {
      const { result } = renderHook(() => useGTM(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isLoaded).toBe(true);
      });

      // Track many events rapidly
      act(() => {
        for (let i = 0; i < 50; i++) {
          result.current.events.trackEngagement('message_sent', {
            message_length: i * 10
          });
        }
      });

      await waitFor(() => {
        const messageEvents = mockDataLayer.filter(item => item.event === 'message_sent');
        expect(messageEvents.length).toBe(50);
        
        // Verify events are properly structured
        messageEvents.forEach((event, index) => {
          expect(event.message_length).toBe(index * 10);
          expect(event.timestamp).toBeDefined();
        });
      });
    });
  });
});