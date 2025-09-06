/**
 * Unified Analytics Service
 * 
 * Provides a single interface for tracking events across multiple analytics platforms:
 * - Statsig for product analytics and experimentation
 * - GTM for marketing and conversion tracking
 * 
 * This service ensures consistent event tracking across the application
 * and prevents event duplication or missing events.
 */

import { useStatsigClient } from '@statsig/react-bindings';
import { useGTM } from '@/hooks/useGTM';
import type { DataLayerEvent } from '@/types/gtm.types';

export interface AnalyticsEvent {
  name: string;
  value?: string | number;
  metadata?: Record<string, any>;
}

export interface AnalyticsService {
  /**
   * Track a custom event across all analytics platforms
   */
  trackEvent: (event: AnalyticsEvent) => void;
  
  /**
   * Track user interaction events
   */
  trackInteraction: (action: string, target: string, metadata?: Record<string, any>) => void;
  
  /**
   * Track feature usage
   */
  trackFeatureUsage: (feature: string, action: string, metadata?: Record<string, any>) => void;
  
  /**
   * Track conversion events
   */
  trackConversion: (type: string, value?: number, metadata?: Record<string, any>) => void;
  
  /**
   * Track error events
   */
  trackError: (error: string, context?: Record<string, any>) => void;
}

/**
 * Hook to access the unified analytics service
 */
export function useAnalytics(): AnalyticsService {
  const { client: statsigClient } = useStatsigClient();
  const gtm = useGTM();
  const { trackCustom, trackEngagement, trackConversion: gtmTrackConversion } = gtm.events();

  const trackEvent = (event: AnalyticsEvent) => {
    // Track in Statsig
    if (statsigClient) {
      statsigClient.logEvent(
        event.name,
        event.value?.toString(),
        event.metadata
      );
    }

    // Track in GTM
    const gtmEvent: DataLayerEvent = {
      event: event.name,
      event_category: 'custom',
      event_action: event.name,
      event_label: event.value?.toString(),
      value: typeof event.value === 'number' ? event.value : undefined,
      custom_parameters: event.metadata
    };
    trackCustom(gtmEvent);
  };

  const trackInteraction = (action: string, target: string, metadata?: Record<string, any>) => {
    const eventName = `${action}_${target}`.toLowerCase().replace(/\s+/g, '_');
    
    // Track in Statsig
    if (statsigClient) {
      statsigClient.logEvent(eventName, target, {
        action,
        target,
        ...metadata
      });
    }

    // Track in GTM as engagement event
    trackEngagement('interaction' as any, {
      event_action: action,
      event_label: target,
      custom_parameters: metadata
    });
  };

  const trackFeatureUsage = (feature: string, action: string, metadata?: Record<string, any>) => {
    const eventName = `feature_${feature}_${action}`.toLowerCase().replace(/\s+/g, '_');
    
    // Track in Statsig
    if (statsigClient) {
      statsigClient.logEvent(eventName, feature, {
        feature,
        action,
        ...metadata
      });
    }

    // Track in GTM
    trackEngagement('feature_usage' as any, {
      event_action: action,
      event_label: feature,
      custom_parameters: metadata
    });
  };

  const trackConversion = (type: string, value?: number, metadata?: Record<string, any>) => {
    const eventName = `conversion_${type}`.toLowerCase().replace(/\s+/g, '_');
    
    // Track in Statsig
    if (statsigClient) {
      statsigClient.logEvent(eventName, value?.toString(), {
        conversion_type: type,
        value,
        ...metadata
      });
    }

    // Track in GTM
    gtmTrackConversion('custom_conversion' as any, {
      event_action: type,
      transaction_value: value,
      custom_parameters: metadata
    });
  };

  const trackError = (error: string, context?: Record<string, any>) => {
    const eventName = 'error_occurred';
    
    // Track in Statsig
    if (statsigClient) {
      statsigClient.logEvent(eventName, error, {
        error_message: error,
        ...context
      });
    }

    // Track in GTM
    trackCustom({
      event: 'error_tracking',
      event_category: 'errors',
      event_action: 'error_occurred',
      event_label: error,
      custom_parameters: context
    });
  };

  return {
    trackEvent,
    trackInteraction,
    trackFeatureUsage,
    trackConversion,
    trackError
  };
}

/**
 * Standalone analytics functions for use outside of React components
 * These functions will queue events until the analytics services are initialized
 */
let eventQueue: Array<() => void> = [];
let isInitialized = false;

export const Analytics = {
  /**
   * Initialize the analytics service with clients
   * This should be called once the app is mounted and clients are ready
   */
  initialize: (statsigClient: any) => {
    isInitialized = true;
    
    // Process queued events
    eventQueue.forEach(fn => fn());
    eventQueue = [];
  },

  /**
   * Track event (queues if not initialized)
   */
  trackEvent: (event: AnalyticsEvent) => {
    const track = () => {
      // This will be replaced with actual client when initialized
      console.log('[Analytics] Event tracked:', event);
    };

    if (isInitialized) {
      track();
    } else {
      eventQueue.push(track);
    }
  }
};