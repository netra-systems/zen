'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import Script from 'next/script';
import { logger } from '@/lib/logger';
import { getGTMCircuitBreaker } from '@/lib/gtm-circuit-breaker';
import type { 
  GTMConfig, 
  GTMProviderProps, 
  GTMContextValue, 
  GTMEventData, 
  GTMScriptLoadState,
  GTMError,
  GTMScriptLoadError,
  GTMEventError
} from '@/types/gtm.types';

// Default GTM configuration from environment variables
const DEFAULT_GTM_CONFIG: GTMConfig = {
  containerId: process.env.NEXT_PUBLIC_GTM_CONTAINER_ID || 'GTM-WKP28PNQ',
  enabled: process.env.NEXT_PUBLIC_GTM_ENABLED === 'true',
  debug: process.env.NEXT_PUBLIC_GTM_DEBUG === 'true' || process.env.NODE_ENV === 'development',
  environment: (process.env.NEXT_PUBLIC_ENVIRONMENT as GTMConfig['environment']) || 'development'
};

// GTM Context
const GTMContext = createContext<GTMContextValue | null>(null);

export const useGTMContext = (): GTMContextValue => {
  const context = useContext(GTMContext);
  if (!context) {
    throw new Error('useGTMContext must be used within a GTMProvider');
  }
  return context;
};

export const GTMProvider: React.FC<GTMProviderProps> = ({ 
  children, 
  config: providedConfig,
  enabled = true
}) => {
  // Merge provided config with defaults
  const config: GTMConfig = {
    ...DEFAULT_GTM_CONFIG,
    ...providedConfig,
    enabled: enabled && (providedConfig?.enabled ?? DEFAULT_GTM_CONFIG.enabled)
  };

  const [scriptState, setScriptState] = useState<GTMScriptLoadState>({
    status: 'idle'
  });

  const [debugState, setDebugState] = useState({
    lastEvents: [] as GTMEventData[],
    totalEvents: 0,
    loadTime: undefined as number | undefined,
    errors: [] as string[]
  });

  const dataLayerInitialized = useRef(false);
  const scriptLoadStart = useRef<number>();

  // Initialize dataLayer before any scripts load
  useEffect(() => {
    if (!config.enabled || dataLayerInitialized.current) return;

    try {
      // Initialize dataLayer if it doesn't exist
      if (typeof window !== 'undefined' && !window.dataLayer) {
        window.dataLayer = [];
        
        // Add initial GTM configuration
        window.dataLayer.push({
          'gtm.start': new Date().getTime(),
          event: 'gtm.js',
          // Add environment context
          environment: config.environment,
          debug_mode: config.debug
        });

        dataLayerInitialized.current = true;

        logger.debug('GTM DataLayer initialized', {
          component: 'GTMProvider',
          action: 'dataLayer_init',
          metadata: { 
            containerId: config.containerId,
            environment: config.environment,
            debug: config.debug
          }
        });
      }
    } catch (error) {
      const errorMessage = 'Failed to initialize GTM DataLayer';
      logger.error(errorMessage, error as Error, {
        component: 'GTMProvider',
        action: 'dataLayer_init_failed'
      });

      setDebugState(prev => ({
        ...prev,
        errors: [...prev.errors, errorMessage]
      }));
    }
  }, [config.enabled, config.containerId, config.environment, config.debug]);

  // Push event to dataLayer with error handling and circuit breaker
  const pushEvent = useCallback((eventData: GTMEventData) => {
    if (!config.enabled || typeof window === 'undefined' || !window.dataLayer) {
      if (config.debug) {
        console.warn('[GTM] Cannot push event - GTM not available:', eventData);
      }
      return;
    }

    try {
      // Validate required event properties
      if (!eventData.event) {
        throw new GTMEventError('Event data must include an "event" property');
      }

      // Check circuit breaker before pushing event
      const circuitBreaker = getGTMCircuitBreaker();
      const eventKey = {
        event: eventData.event,
        category: eventData.event_category || 'unknown',
        action: eventData.event_action || eventData.event,
        context: eventData.page_path || window.location.pathname
      };

      if (!circuitBreaker.canSendEvent(eventKey)) {
        if (config.debug) {
          console.warn('[GTM] Event blocked by circuit breaker:', eventData);
        }
        return;
      }

      // Add timestamp and environment context
      const enrichedEventData = {
        ...eventData,
        timestamp: eventData.timestamp || new Date().toISOString(),
        environment: config.environment,
        // Add page context
        page_path: eventData.page_path || (typeof window !== 'undefined' ? window.location.pathname : undefined)
      };

      // Push to dataLayer
      window.dataLayer.push(enrichedEventData);

      // Record successful event with circuit breaker
      circuitBreaker.recordEventSent(eventKey);

      // Update debug state
      setDebugState(prev => ({
        ...prev,
        lastEvents: [enrichedEventData, ...prev.lastEvents].slice(0, 10), // Keep last 10 events
        totalEvents: prev.totalEvents + 1
      }));

      if (config.debug) {
        console.log('[GTM] Event pushed to dataLayer:', enrichedEventData);
      }

      logger.debug('GTM event pushed to dataLayer', {
        component: 'GTMProvider',
        action: 'event_pushed',
        metadata: { 
          eventType: eventData.event,
          category: eventData.event_category,
          containerId: config.containerId
        }
      });

    } catch (error) {
      const errorMessage = `Failed to push GTM event: ${(error as Error).message}`;
      logger.error('GTM event push failed', error as Error, {
        component: 'GTMProvider',
        action: 'event_push_failed',
        metadata: { eventType: eventData.event }
      });

      // Record failure with circuit breaker
      const circuitBreaker = getGTMCircuitBreaker();
      const eventKey = {
        event: eventData.event,
        category: eventData.event_category || 'unknown',
        action: eventData.event_action || eventData.event,
        context: eventData.page_path || window.location.pathname
      };
      circuitBreaker.recordEventFailure(eventKey, error as Error);

      setDebugState(prev => ({
        ...prev,
        errors: [...prev.errors, errorMessage]
      }));

      if (config.debug) {
        console.error('[GTM] Failed to push event:', error, eventData);
      }
    }
  }, [config.enabled, config.environment, config.debug, config.containerId]);

  // Push arbitrary data to dataLayer
  const pushData = useCallback((data: Record<string, any>) => {
    if (!config.enabled || typeof window === 'undefined' || !window.dataLayer) {
      if (config.debug) {
        console.warn('[GTM] Cannot push data - GTM not available:', data);
      }
      return;
    }

    try {
      window.dataLayer.push(data);
      
      if (config.debug) {
        console.log('[GTM] Data pushed to dataLayer:', data);
      }

      logger.debug('GTM data pushed to dataLayer', {
        component: 'GTMProvider',
        action: 'data_pushed',
        metadata: { dataKeys: Object.keys(data) }
      });

    } catch (error) {
      const errorMessage = `Failed to push GTM data: ${(error as Error).message}`;
      logger.error('GTM data push failed', error as Error, {
        component: 'GTMProvider',
        action: 'data_push_failed'
      });

      setDebugState(prev => ({
        ...prev,
        errors: [...prev.errors, errorMessage]
      }));

      if (config.debug) {
        console.error('[GTM] Failed to push data:', error, data);
      }
    }
  }, [config.enabled, config.debug]);

  // Get current dataLayer state
  const getDataLayer = useCallback((): any[] => {
    if (typeof window === 'undefined' || !window.dataLayer) {
      return [];
    }
    return [...window.dataLayer];
  }, []);

  // Script loading handlers
  const handleScriptLoad = useCallback(() => {
    const loadTime = scriptLoadStart.current ? Date.now() - scriptLoadStart.current : undefined;
    
    setScriptState({
      status: 'loaded',
      loadedAt: Date.now()
    });

    setDebugState(prev => ({
      ...prev,
      loadTime
    }));

    logger.debug('GTM script loaded successfully', {
      component: 'GTMProvider',
      action: 'script_loaded',
      metadata: { 
        containerId: config.containerId,
        loadTime: loadTime
      }
    });

    if (config.debug) {
      console.log(`[GTM] Script loaded in ${loadTime}ms`);
    }
  }, [config.containerId, config.debug]);

  const handleScriptError = useCallback((error: Error) => {
    const errorMessage = `GTM script failed to load: ${error.message}`;
    
    setScriptState({
      status: 'error',
      error: errorMessage
    });

    setDebugState(prev => ({
      ...prev,
      errors: [...prev.errors, errorMessage]
    }));

    logger.error('GTM script load error', error, {
      component: 'GTMProvider',
      action: 'script_load_error',
      metadata: { containerId: config.containerId }
    });

    if (config.debug) {
      console.error('[GTM] Script load error:', error);
    }
  }, [config.containerId, config.debug]);

  const handleScriptReady = useCallback(() => {
    scriptLoadStart.current = Date.now();
    setScriptState({ status: 'loading' });
    
    if (config.debug) {
      console.log('[GTM] Script loading started');
    }
  }, [config.debug]);

  // Context value
  const contextValue: GTMContextValue = {
    isLoaded: scriptState.status === 'loaded',
    isEnabled: config.enabled,
    config,
    pushEvent,
    pushData,
    getDataLayer,
    debug: debugState
  };

  return (
    <GTMContext.Provider value={contextValue}>
      {/* Load GTM script only if enabled */}
      {config.enabled && (
        <>
          {/* Google Tag Manager Script */}
          <Script
            id="gtm-script"
            src={`https://www.googletagmanager.com/gtm.js?id=${config.containerId}`}
            strategy="afterInteractive"
            onLoad={handleScriptLoad}
            onError={handleScriptError}
            onReady={handleScriptReady}
          />

          {/* GTM noscript fallback */}
          <noscript>
            <iframe
              src={`https://www.googletagmanager.com/ns.html?id=${config.containerId}`}
              height="0"
              width="0"
              style={{ display: 'none', visibility: 'hidden' }}
            />
          </noscript>
        </>
      )}
      
      {children}
    </GTMContext.Provider>
  );
};