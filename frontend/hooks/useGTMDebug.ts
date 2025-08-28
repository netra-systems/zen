'use client';

import { useCallback, useEffect, useState } from 'react';
import { useGTM } from './useGTM';
import type { GTMEventData } from '@/types/gtm.types';

interface GTMDebugConsoleLog {
  level: 'log' | 'warn' | 'error';
  message: string;
  timestamp: number;
  data?: any;
}

interface GTMPerformanceMetrics {
  scriptLoadTime?: number;
  averageEventTime?: number;
  totalEvents: number;
  eventsPerSecond?: number;
  dataLayerSize: number;
  lastEventTime?: number;
}

/**
 * GTM Debug hook for development and monitoring
 * 
 * Provides debugging utilities, performance metrics, and console logging
 * for GTM integration. Only active in development or when debug is enabled.
 * 
 * @returns Debug utilities and metrics
 */
export const useGTMDebug = () => {
  const { debug: gtmDebug, config, isLoaded, getDataLayer } = useGTM();
  
  const [consoleLogs, setConsoleLogs] = useState<GTMDebugConsoleLog[]>([]);
  const [isDebugMode, setIsDebugMode] = useState(config.debug || false);
  const [performanceMetrics, setPerformanceMetrics] = useState<GTMPerformanceMetrics>({
    totalEvents: 0,
    dataLayerSize: 0
  });

  // Console log interceptor for GTM-related messages
  useEffect(() => {
    if (!config.debug && !isDebugMode) return;

    const originalConsole = {
      log: console.log,
      warn: console.warn,
      error: console.error
    };

    const interceptConsole = (level: 'log' | 'warn' | 'error') => {
      return (...args: any[]) => {
        const message = args.map(arg => 
          typeof arg === 'string' ? arg : JSON.stringify(arg)
        ).join(' ');

        // Check if message is GTM-related
        if (message.includes('GTM') || message.includes('dataLayer') || message.includes('google_tag_manager')) {
          setConsoleLogs(prev => [...prev, {
            level,
            message,
            timestamp: Date.now(),
            data: args.length > 1 ? args.slice(1) : undefined
          }].slice(-50)); // Keep last 50 logs
        }

        // Call original console method
        originalConsole[level](...args);
      };
    };

    console.log = interceptConsole('log');
    console.warn = interceptConsole('warn');
    console.error = interceptConsole('error');

    return () => {
      console.log = originalConsole.log;
      console.warn = originalConsole.warn;
      console.error = originalConsole.error;
    };
  }, [config.debug, isDebugMode]);

  // Update performance metrics
  useEffect(() => {
    const updateMetrics = () => {
      const dataLayer = getDataLayer();
      const events = gtmDebug.lastEvents;
      
      let averageEventTime: number | undefined;
      let eventsPerSecond: number | undefined;
      
      if (events.length > 1) {
        const timestamps = events
          .map(event => new Date(event.timestamp || '').getTime())
          .filter(time => !isNaN(time))
          .sort((a, b) => b - a); // Most recent first
        
        if (timestamps.length > 1) {
          const timeDiffs = [];
          for (let i = 0; i < timestamps.length - 1; i++) {
            timeDiffs.push(timestamps[i] - timestamps[i + 1]);
          }
          averageEventTime = timeDiffs.reduce((sum, diff) => sum + diff, 0) / timeDiffs.length;
          
          // Calculate events per second over the last minute
          const oneMinuteAgo = Date.now() - 60000;
          const recentEvents = timestamps.filter(time => time > oneMinuteAgo);
          eventsPerSecond = recentEvents.length / 60;
        }
      }

      setPerformanceMetrics({
        scriptLoadTime: gtmDebug.loadTime,
        averageEventTime,
        totalEvents: gtmDebug.totalEvents,
        eventsPerSecond,
        dataLayerSize: dataLayer.length,
        lastEventTime: events.length > 0 ? new Date(events[0].timestamp || '').getTime() : undefined
      });
    };

    const interval = setInterval(updateMetrics, 5000); // Update every 5 seconds
    updateMetrics(); // Initial update

    return () => clearInterval(interval);
  }, [gtmDebug.lastEvents, gtmDebug.totalEvents, gtmDebug.loadTime, getDataLayer]);

  const enableDebug = useCallback(() => {
    setIsDebugMode(true);
    
    if (typeof window !== 'undefined' && window.dataLayer) {
      window.dataLayer.push({
        event: 'gtm.debug.enable',
        debug_mode: true,
        timestamp: new Date().toISOString()
      });
    }
    
    console.log('[GTM Debug] Debug mode enabled');
  }, []);

  const disableDebug = useCallback(() => {
    setIsDebugMode(false);
    
    if (typeof window !== 'undefined' && window.dataLayer) {
      window.dataLayer.push({
        event: 'gtm.debug.disable',
        debug_mode: false,
        timestamp: new Date().toISOString()
      });
    }
    
    console.log('[GTM Debug] Debug mode disabled');
  }, []);

  const clearDebugHistory = useCallback(() => {
    setConsoleLogs([]);
    console.log('[GTM Debug] Debug history cleared');
  }, []);

  const inspectDataLayer = useCallback(() => {
    const dataLayer = getDataLayer();
    console.group('[GTM Debug] DataLayer Inspection');
    console.log('Total items:', dataLayer.length);
    console.log('Items:', dataLayer);
    console.groupEnd();
    return dataLayer;
  }, [getDataLayer]);

  const validateEvent = useCallback((eventData: GTMEventData): { isValid: boolean; errors: string[] } => {
    const errors: string[] = [];
    
    if (!eventData.event) {
      errors.push('Event must have an "event" property');
    }
    
    if (!eventData.event_category) {
      errors.push('Event should have an "event_category" property');
    }
    
    if (eventData.event_category === 'conversion' && !eventData.value && !eventData.custom_parameters?.transaction_value) {
      errors.push('Conversion events should have a "value" or "transaction_value"');
    }
    
    // Validate event name format
    if (eventData.event && !/^[a-z_]+$/.test(eventData.event)) {
      errors.push('Event name should use snake_case format (lowercase with underscores)');
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }, []);

  const testEvent = useCallback((eventData: GTMEventData) => {
    const validation = validateEvent(eventData);
    
    console.group(`[GTM Debug] Testing event: ${eventData.event}`);
    console.log('Event data:', eventData);
    console.log('Validation:', validation);
    
    if (validation.isValid) {
      console.log('✅ Event is valid and ready to send');
      
      if (config.debug) {
        // In debug mode, show what would be sent
        console.log('Would push to dataLayer:', {
          ...eventData,
          timestamp: new Date().toISOString(),
          environment: config.environment
        });
      }
    } else {
      console.warn('❌ Event validation failed:', validation.errors);
    }
    
    console.groupEnd();
    return validation;
  }, [validateEvent, config.debug, config.environment]);

  const getDebugReport = useCallback(() => {
    const report = {
      configuration: {
        containerId: config.containerId,
        environment: config.environment,
        debugMode: isDebugMode,
        scriptLoaded: isLoaded
      },
      performance: performanceMetrics,
      events: {
        recent: gtmDebug.lastEvents,
        total: gtmDebug.totalEvents,
        errors: gtmDebug.errors
      },
      dataLayer: {
        size: getDataLayer().length,
        items: getDataLayer()
      },
      console: {
        logs: consoleLogs,
        recentErrors: consoleLogs.filter(log => log.level === 'error')
      }
    };
    
    console.group('[GTM Debug] Debug Report');
    console.log(report);
    console.groupEnd();
    
    return report;
  }, [config, isDebugMode, isLoaded, performanceMetrics, gtmDebug, getDataLayer, consoleLogs]);

  const exportDebugData = useCallback(() => {
    const debugData = getDebugReport();
    const dataStr = JSON.stringify(debugData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `gtm-debug-${config.containerId}-${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    console.log('[GTM Debug] Debug data exported to:', exportFileDefaultName);
  }, [getDebugReport, config.containerId]);

  return {
    // Debug mode control
    enableDebug,
    disableDebug,
    isDebugMode,
    
    // Inspection tools
    inspectDataLayer,
    validateEvent,
    testEvent,
    getDebugReport,
    exportDebugData,
    
    // Debug information
    debugInfo: {
      containerId: config.containerId,
      scriptStatus: isLoaded ? 'loaded' as const : 'loading' as const,
      eventHistory: gtmDebug.lastEvents,
      performance: performanceMetrics,
      consoleLogs
    },
    
    // Utilities
    clearDebugHistory,
    
    // Metrics
    metrics: performanceMetrics,
    consoleLogs,
    
    // Status
    isEnabled: config.enabled,
    isLoaded
  };
};