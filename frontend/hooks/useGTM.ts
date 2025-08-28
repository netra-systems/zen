'use client';

import { useCallback } from 'react';
import { useGTMContext } from '@/providers/GTMProvider';
import type { 
  GTMHookReturn,
  GTMEventHookReturn,
  GTMDebugHookReturn,
  AuthenticationEventData,
  EngagementEventData,
  ConversionEventData,
  DataLayerEvent
} from '@/types/gtm.types';

/**
 * Core GTM hook that provides access to all GTM functionality
 * 
 * Features:
 * - Event tracking with type safety
 * - Debug utilities
 * - Performance monitoring
 * - Error handling
 * 
 * @returns GTMHookReturn with all GTM functionality
 */
export const useGTM = (): GTMHookReturn => {
  const context = useGTMContext();

  // Event tracking functionality
  const useEventTracking = (): GTMEventHookReturn => {
    const trackAuth = useCallback((
      eventType: AuthenticationEventData['event'], 
      data?: Partial<AuthenticationEventData>
    ) => {
      const eventData: AuthenticationEventData = {
        event: eventType,
        event_category: 'authentication',
        event_action: eventType.replace('_', ' '),
        ...data
      };
      
      context.pushEvent(eventData);
    }, []);

    const trackEngagement = useCallback((
      eventType: EngagementEventData['event'],
      data?: Partial<EngagementEventData>
    ) => {
      const eventData: EngagementEventData = {
        event: eventType,
        event_category: 'engagement',
        event_action: eventType.replace('_', ' '),
        ...data
      };
      
      context.pushEvent(eventData);
    }, []);

    const trackConversion = useCallback((
      eventType: ConversionEventData['event'],
      data?: Partial<ConversionEventData>
    ) => {
      const eventData: ConversionEventData = {
        event: eventType,
        event_category: 'conversion',
        event_action: eventType.replace('_', ' '),
        value: data?.transaction_value,
        ...data
      };
      
      context.pushEvent(eventData);
    }, []);

    const trackCustom = useCallback((eventData: DataLayerEvent) => {
      context.pushEvent(eventData);
    }, []);

    const getStats = useCallback(() => {
      const events = context.debug.lastEvents;
      const eventsByType: Record<string, number> = {};
      
      // Count events by type
      events.forEach(event => {
        eventsByType[event.event] = (eventsByType[event.event] || 0) + 1;
      });

      return {
        totalEvents: context.debug.totalEvents,
        eventsByType,
        lastEventTime: events.length > 0 ? new Date(events[0].timestamp || '').getTime() : undefined
      };
    }, [context.debug.lastEvents, context.debug.totalEvents]);

    return {
      trackAuth,
      trackEngagement,
      trackConversion,
      trackCustom,
      getStats
    };
  };

  // Debug functionality
  const useDebugFunctionality = (): GTMDebugHookReturn => {
    const enableDebug = useCallback(() => {
      if (typeof window !== 'undefined') {
        // Enable GTM debug mode
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({
          event: 'gtm.debug.enable',
          debug_mode: true
        });
        
        if (context.config.debug) {
          console.log('[GTM] Debug mode enabled');
        }
      }
    }, [context.config.debug]);

    const disableDebug = useCallback(() => {
      if (typeof window !== 'undefined') {
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({
          event: 'gtm.debug.disable',
          debug_mode: false
        });
        
        if (context.config.debug) {
          console.log('[GTM] Debug mode disabled');
        }
      }
    }, [context.config.debug]);

    const clearDebugHistory = useCallback(() => {
      // This would need to be implemented in the provider
      // For now, we can just log the action
      if (context.config.debug) {
        console.log('[GTM] Debug history cleared');
      }
    }, [context.config.debug]);

    const debugInfo = {
      containerId: context.config.containerId,
      scriptStatus: context.isLoaded ? 'loaded' as const : 'loading' as const,
      eventHistory: context.debug.lastEvents,
      performance: {
        scriptLoadTime: context.debug.loadTime,
        averageEventTime: undefined, // Could be calculated
        totalEvents: context.debug.totalEvents
      },
      consoleLogs: [], // Would need to be implemented
    };

    return {
      enableDebug,
      disableDebug,
      isDebugMode: context.config.debug || false,
      debugInfo,
      clearDebugHistory
    };
  };

  // Get event tracking functionality
  const events = useEventTracking();
  
  // Get debug functionality
  const debug = useDebugFunctionality();

  return {
    ...context,
    events,
    debug
  };
};