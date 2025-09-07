/**
 * Tests for the unified analytics service
 */

import React from 'react';
import { renderHook } from '@testing-library/react';
import { useAnalytics } from '@/services/analyticsService';
import { useStatsigClient } from '@statsig/react-bindings';
import { useGTM } from '@/hooks/useGTM';

// Mock dependencies
jest.mock('@statsig/react-bindings');
jest.mock('@/hooks/useGTM');

describe('Analytics Service', () => {
  let mockStatsigClient: any;
  let mockGTMEvents: any;

  beforeEach(() => {
    // Setup Statsig mock
    mockStatsigClient = {
      logEvent: jest.fn()
    };
    (useStatsigClient as jest.Mock).mockReturnValue({
      client: mockStatsigClient
    });

    // Setup GTM mock
    mockGTMEvents = {
      trackCustom: jest.fn(),
      trackEngagement: jest.fn(),
      trackConversion: jest.fn()
    };
    (useGTM as jest.Mock).mockReturnValue({
      events: mockGTMEvents
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('trackEvent', () => {
    it('should track custom events to both Statsig and GTM', () => {
      const { result } = renderHook(() => useAnalytics());

      const event = {
        name: 'test_event',
        value: 'test_value',
        metadata: { foo: 'bar' }
      };

      result.current.trackEvent(event);

      // Check Statsig was called
      expect(mockStatsigClient.logEvent).toHaveBeenCalledWith(
        'test_event',
        'test_value',
        { foo: 'bar' }
      );

      // Check GTM was called
      expect(mockGTMEvents.trackCustom).toHaveBeenCalledWith({
        event: 'test_event',
        event_category: 'custom',
        event_action: 'test_event',
        event_label: 'test_value',
        value: undefined,
        custom_parameters: { foo: 'bar' }
      });
    });

    it('should handle numeric values correctly', () => {
      const { result } = renderHook(() => useAnalytics());

      const event = {
        name: 'purchase',
        value: 99.99,
        metadata: { currency: 'USD' }
      };

      result.current.trackEvent(event);

      // Check Statsig gets string value
      expect(mockStatsigClient.logEvent).toHaveBeenCalledWith(
        'purchase',
        '99.99',
        { currency: 'USD' }
      );

      // Check GTM gets numeric value
      expect(mockGTMEvents.trackCustom).toHaveBeenCalledWith(
        expect.objectContaining({
          value: 99.99,
          event_label: '99.99'
        })
      );
    });
  });

  describe('trackInteraction', () => {
    it('should track user interactions', () => {
      const { result } = renderHook(() => useAnalytics());

      result.current.trackInteraction('click', 'submit_button', {
        page: 'checkout'
      });

      // Check Statsig
      expect(mockStatsigClient.logEvent).toHaveBeenCalledWith(
        'click_submit_button',
        'submit_button',
        {
          action: 'click',
          target: 'submit_button',
          page: 'checkout'
        }
      );

      // Check GTM
      expect(mockGTMEvents.trackEngagement).toHaveBeenCalledWith(
        'interaction',
        {
          event_action: 'click',
          event_label: 'submit_button',
          custom_parameters: { page: 'checkout' }
        }
      );
    });
  });

  describe('trackFeatureUsage', () => {
    it('should track feature usage events', () => {
      const { result } = renderHook(() => useAnalytics());

      result.current.trackFeatureUsage('chat', 'message_sent', {
        thread_id: '123',
        message_length: 42
      });

      // Check Statsig
      expect(mockStatsigClient.logEvent).toHaveBeenCalledWith(
        'feature_chat_message_sent',
        'chat',
        {
          feature: 'chat',
          action: 'message_sent',
          thread_id: '123',
          message_length: 42
        }
      );

      // Check GTM
      expect(mockGTMEvents.trackEngagement).toHaveBeenCalledWith(
        'feature_usage',
        {
          event_action: 'message_sent',
          event_label: 'chat',
          custom_parameters: {
            thread_id: '123',
            message_length: 42
          }
        }
      );
    });
  });

  describe('trackConversion', () => {
    it('should track conversion events', () => {
      const { result } = renderHook(() => useAnalytics());

      result.current.trackConversion('subscription_upgrade', 49.99, {
        plan: 'pro',
        billing_cycle: 'monthly'
      });

      // Check Statsig
      expect(mockStatsigClient.logEvent).toHaveBeenCalledWith(
        'conversion_subscription_upgrade',
        '49.99',
        {
          conversion_type: 'subscription_upgrade',
          value: 49.99,
          plan: 'pro',
          billing_cycle: 'monthly'
        }
      );

      // Check GTM
      expect(mockGTMEvents.trackConversion).toHaveBeenCalledWith(
        'custom_conversion',
        {
          event_action: 'subscription_upgrade',
          transaction_value: 49.99,
          custom_parameters: {
            plan: 'pro',
            billing_cycle: 'monthly'
          }
        }
      );
    });
  });

  describe('trackError', () => {
    it('should track error events', () => {
      const { result } = renderHook(() => useAnalytics());

      result.current.trackError('API request failed', {
        endpoint: '/api/data',
        status_code: 500
      });

      // Check Statsig
      expect(mockStatsigClient.logEvent).toHaveBeenCalledWith(
        'error_occurred',
        'API request failed',
        {
          error_message: 'API request failed',
          endpoint: '/api/data',
          status_code: 500
        }
      );

      // Check GTM
      expect(mockGTMEvents.trackCustom).toHaveBeenCalledWith({
        event: 'error_tracking',
        event_category: 'errors',
        event_action: 'error_occurred',
        event_label: 'API request failed',
        custom_parameters: {
          endpoint: '/api/data',
          status_code: 500
        }
      });
    });
  });

  describe('Message content tracking', () => {
    it('should include message content in tracking data', () => {
      const { result } = renderHook(() => useAnalytics());

      const userMessage = "How can I optimize my cloud costs?";
      
      result.current.trackInteraction('send_message', 'chat', {
        message_content: userMessage,
        message_length: userMessage.length,
        thread_id: 'thread-123',
        timestamp: '2024-01-01T00:00:00.000Z'
      });

      // Verify message content is tracked
      expect(mockStatsigClient.logEvent).toHaveBeenCalledWith(
        'send_message_chat',
        'chat',
        expect.objectContaining({
          message_content: userMessage
        })
      );

      expect(mockGTMEvents.trackEngagement).toHaveBeenCalledWith(
        'interaction',
        expect.objectContaining({
          custom_parameters: expect.objectContaining({
            message_content: userMessage
          })
        })
      );
    });
  });

  describe('Null client handling', () => {
    it('should handle null Statsig client gracefully', () => {
      (useStatsigClient as jest.Mock).mockReturnValue({
        client: null
      });

      const { result } = renderHook(() => useAnalytics());

      // Should not throw
      expect(() => {
        result.current.trackEvent({
          name: 'test_event',
          value: 'test'
        });
      }).not.toThrow();

      // GTM should still be called
      expect(mockGTMEvents.trackCustom).toHaveBeenCalled();
    });
  });
});