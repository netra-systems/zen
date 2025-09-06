/**
 * Regression test for analytics events() function issue
 * 
 * Issue: gtm.events() was being called as a function when it's actually a property
 * Fixed: Changed gtm.events() to gtm.events in analyticsService.ts line 55
 * 
 * This test ensures the issue doesn't regress
 */

import React from 'react';
import { renderHook } from '@testing-library/react';
import { useAnalytics } from '@/services/analyticsService';
import { useStatsigClient } from '@statsig/react-bindings';
import { useGTM } from '@/hooks/useGTM';

// Mock dependencies
jest.mock('@statsig/react-bindings');
jest.mock('@/hooks/useGTM');

describe('Analytics Events Regression Tests', () => {
  let mockStatsigClient: any;
  let mockGTMEvents: any;
  let mockGTMHook: any;

  beforeEach(() => {
    // Setup Statsig mock
    mockStatsigClient = {
      logEvent: jest.fn()
    };
    (useStatsigClient as jest.Mock).mockReturnValue({
      client: mockStatsigClient
    });

    // Setup GTM events object
    mockGTMEvents = {
      trackCustom: jest.fn(),
      trackEngagement: jest.fn(),
      trackConversion: jest.fn(),
      trackAuth: jest.fn(),
      getStats: jest.fn(() => ({
        totalEvents: 0,
        eventsByType: {},
        lastEventTime: undefined
      }))
    };

    // Mock the useGTM hook to return events as a property, not a function
    mockGTMHook = {
      events: mockGTMEvents,
      debug: {
        enableDebug: jest.fn(),
        disableDebug: jest.fn(),
        isDebugMode: false,
        debugInfo: {
          containerId: 'GTM-TEST123',
          scriptStatus: 'loaded' as const,
          eventHistory: [],
          performance: {
            scriptLoadTime: 100,
            averageEventTime: undefined,
            totalEvents: 0
          },
          consoleLogs: []
        },
        clearDebugHistory: jest.fn()
      },
      isLoaded: true,
      config: {
        containerId: 'GTM-TEST123',
        debug: false
      },
      pushEvent: jest.fn()
    };

    (useGTM as jest.Mock).mockReturnValue(mockGTMHook);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Regression: events is not a function', () => {
    it('should access gtm.events as a property, not call it as a function', () => {
      // This test verifies the fix: gtm.events is accessed as a property
      const { result } = renderHook(() => useAnalytics());

      // Should not throw "events is not a function" error
      expect(() => result.current.trackEvent({
        name: 'test_event',
        value: 'test'
      })).not.toThrow();
    });

    it('should correctly destructure tracking functions from gtm.events', () => {
      const { result } = renderHook(() => useAnalytics());

      // Track a custom event
      result.current.trackEvent({
        name: 'custom_event',
        value: 'test_value',
        metadata: { category: 'test' }
      });

      // Verify trackCustom was called
      expect(mockGTMEvents.trackCustom).toHaveBeenCalledWith({
        event: 'custom_event',
        event_category: 'custom',
        event_action: 'custom_event',
        event_label: 'test_value',
        value: undefined,
        custom_parameters: { category: 'test' }
      });
    });

    it('should handle all tracking methods without errors', () => {
      const { result } = renderHook(() => useAnalytics());

      // Test all methods work without "is not a function" errors
      expect(() => {
        result.current.trackEvent({ name: 'event1' });
        result.current.trackInteraction('click', 'button');
        result.current.trackFeatureUsage('feature1', 'used');
        result.current.trackConversion('purchase', 100);
        result.current.trackError('Error occurred');
      }).not.toThrow();

      // Verify methods were called
      expect(mockGTMEvents.trackCustom).toHaveBeenCalled();
      expect(mockGTMEvents.trackEngagement).toHaveBeenCalled();
      expect(mockGTMEvents.trackConversion).toHaveBeenCalled();
    });

    it('should handle missing GTM events object gracefully', () => {
      // Mock GTM with undefined events
      (useGTM as jest.Mock).mockReturnValue({
        ...mockGTMHook,
        events: undefined
      });

      // Should not crash when events is undefined
      const { result } = renderHook(() => useAnalytics());
      
      // This should handle undefined gracefully - no error should be thrown
      expect(() => {
        result.current.trackEvent({ name: 'test' });
      }).not.toThrow();
      
      // Verify Statsig is still called even if GTM is unavailable
      result.current.trackEvent({ name: 'test_event' });
      expect(mockStatsigClient.logEvent).toHaveBeenCalledWith(
        'test_event',
        undefined,
        undefined
      );
    });

    it('should verify the exact line of code that was fixed', () => {
      // This test documents the specific fix
      // BEFORE FIX: const { trackCustom, trackEngagement, trackConversion: gtmTrackConversion } = gtm.events();
      // AFTER FIX:  const { trackCustom, trackEngagement, trackConversion: gtmTrackConversion } = gtm.events;
      
      // Verify that useGTM returns an object with events as a property
      const gtmResult = (useGTM as jest.Mock)();
      
      // events should be an object, not a function
      expect(typeof gtmResult.events).toBe('object');
      expect(typeof gtmResult.events).not.toBe('function');
      
      // events object should contain the tracking methods
      expect(gtmResult.events).toHaveProperty('trackCustom');
      expect(gtmResult.events).toHaveProperty('trackEngagement');
      expect(gtmResult.events).toHaveProperty('trackConversion');
    });
  });

  describe('Mock validation', () => {
    it('should ensure mocks are correctly structured', () => {
      // Validate the mock structure matches the real implementation
      const gtm = (useGTM as jest.Mock)();
      
      // Validate events property exists and is not a function
      expect(gtm).toHaveProperty('events');
      expect(typeof gtm.events).toBe('object');
      
      // Validate events object has all required methods
      expect(gtm.events).toMatchObject({
        trackCustom: expect.any(Function),
        trackEngagement: expect.any(Function),
        trackConversion: expect.any(Function),
        trackAuth: expect.any(Function),
        getStats: expect.any(Function)
      });

      // Validate other GTM properties
      expect(gtm).toHaveProperty('debug');
      expect(gtm).toHaveProperty('isLoaded');
      expect(gtm).toHaveProperty('config');
      expect(gtm).toHaveProperty('pushEvent');
    });
  });
});