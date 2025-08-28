'use client';

import { useCallback } from 'react';
import { useGTM } from './useGTM';
import type { 
  AuthenticationEventData,
  EngagementEventData,
  ConversionEventData,
  DataLayerEvent
} from '@/types/gtm.types';

/**
 * Simplified GTM event tracking hook
 * 
 * Provides convenient methods for tracking common business events
 * with sensible defaults and type safety.
 * 
 * @returns Event tracking methods
 */
export const useGTMEvent = () => {
  const { events, isEnabled, config } = useGTM();

  // Authentication Events
  const trackLogin = useCallback((method?: 'email' | 'google' | 'oauth', isNewUser?: boolean) => {
    if (!isEnabled) return;
    
    events.trackAuth('user_login', {
      auth_method: method,
      is_new_user: isNewUser,
      event_label: method ? `login_${method}` : 'login'
    });
  }, [events, isEnabled]);

  const trackSignup = useCallback((method?: 'email' | 'google' | 'oauth', userTier?: 'free' | 'early' | 'mid' | 'enterprise') => {
    if (!isEnabled) return;
    
    events.trackAuth('user_signup', {
      auth_method: method,
      is_new_user: true,
      user_tier: userTier || 'free',
      event_label: method ? `signup_${method}` : 'signup'
    });
  }, [events, isEnabled]);

  const trackLogout = useCallback(() => {
    if (!isEnabled) return;
    
    events.trackAuth('user_logout', {
      event_label: 'user_logout'
    });
  }, [events, isEnabled]);

  const trackOAuthComplete = useCallback((provider: string, isNewUser?: boolean) => {
    if (!isEnabled) return;
    
    events.trackAuth('oauth_complete', {
      auth_method: 'oauth',
      is_new_user: isNewUser,
      event_label: `oauth_${provider}`,
      custom_parameters: {
        oauth_provider: provider
      }
    });
  }, [events, isEnabled]);

  // Engagement Events
  const trackChatStarted = useCallback((threadId?: string) => {
    if (!isEnabled) return;
    
    events.trackEngagement('chat_started', {
      thread_id: threadId,
      event_label: 'new_chat'
    });
  }, [events, isEnabled]);

  const trackMessageSent = useCallback((threadId?: string, messageLength?: number, agentType?: string) => {
    if (!isEnabled) return;
    
    events.trackEngagement('message_sent', {
      thread_id: threadId,
      message_length: messageLength,
      agent_type: agentType,
      event_label: 'user_message',
      value: messageLength
    });
  }, [events, isEnabled]);

  const trackAgentActivated = useCallback((agentType: string, threadId?: string) => {
    if (!isEnabled) return;
    
    events.trackEngagement('agent_activated', {
      agent_type: agentType,
      thread_id: threadId,
      feature_type: agentType,
      event_label: `agent_${agentType}`
    });
  }, [events, isEnabled]);

  const trackThreadCreated = useCallback((threadId?: string, agentType?: string) => {
    if (!isEnabled) return;
    
    events.trackEngagement('thread_created', {
      thread_id: threadId,
      agent_type: agentType,
      event_label: 'new_thread'
    });
  }, [events, isEnabled]);

  const trackFeatureUsed = useCallback((featureType: string, additionalData?: Record<string, any>) => {
    if (!isEnabled) return;
    
    events.trackEngagement('feature_used', {
      feature_type: featureType,
      event_label: `feature_${featureType}`,
      custom_parameters: additionalData
    });
  }, [events, isEnabled]);

  // Conversion Events
  const trackTrialStarted = useCallback((planType?: 'early' | 'mid' | 'enterprise') => {
    if (!isEnabled) return;
    
    events.trackConversion('trial_started', {
      plan_type: planType,
      event_label: `trial_${planType || 'unknown'}`,
      custom_parameters: {
        conversion_type: 'trial'
      }
    });
  }, [events, isEnabled]);

  const trackPlanUpgraded = useCallback((
    planType: 'early' | 'mid' | 'enterprise', 
    transactionValue?: number,
    transactionId?: string,
    source?: string
  ) => {
    if (!isEnabled) return;
    
    events.trackConversion('plan_upgraded', {
      plan_type: planType,
      transaction_value: transactionValue,
      transaction_id: transactionId,
      currency: 'USD',
      conversion_source: source,
      event_label: `upgrade_to_${planType}`,
      value: transactionValue
    });
  }, [events, isEnabled]);

  const trackPaymentCompleted = useCallback((
    transactionValue: number,
    transactionId: string,
    planType?: 'early' | 'mid' | 'enterprise'
  ) => {
    if (!isEnabled) return;
    
    events.trackConversion('payment_completed', {
      plan_type: planType,
      transaction_value: transactionValue,
      transaction_id: transactionId,
      currency: 'USD',
      event_label: `payment_${planType || 'unknown'}`,
      value: transactionValue
    });
  }, [events, isEnabled]);

  const trackDemoRequested = useCallback((source?: string, planType?: 'enterprise') => {
    if (!isEnabled) return;
    
    events.trackConversion('demo_requested', {
      plan_type: planType,
      conversion_source: source,
      event_label: `demo_request_${planType || 'general'}`,
      custom_parameters: {
        demo_type: planType || 'general',
        request_source: source
      }
    });
  }, [events, isEnabled]);

  // Custom event tracking
  const trackCustomEvent = useCallback((
    eventName: string,
    category: string,
    action?: string,
    label?: string,
    value?: number,
    customParameters?: Record<string, any>
  ) => {
    if (!isEnabled) return;
    
    const eventData: DataLayerEvent = {
      event: eventName,
      event_category: category,
      event_action: action || eventName,
      event_label: label,
      value: value,
      custom_parameters: customParameters
    };
    
    events.trackCustom(eventData);
  }, [events, isEnabled]);

  // Page view tracking (for SPA navigation)
  const trackPageView = useCallback((pagePath?: string, pageTitle?: string) => {
    if (!isEnabled) return;
    
    const eventData: DataLayerEvent = {
      event: 'page_view',
      event_category: 'navigation',
      event_action: 'page_view',
      page_path: pagePath || (typeof window !== 'undefined' ? window.location.pathname : undefined),
      event_label: pageTitle || (typeof document !== 'undefined' ? document.title : undefined),
      custom_parameters: {
        page_title: pageTitle || (typeof document !== 'undefined' ? document.title : undefined),
        page_location: typeof window !== 'undefined' ? window.location.href : undefined
      }
    };
    
    events.trackCustom(eventData);
  }, [events, isEnabled]);

  // Utility to track errors
  const trackError = useCallback((
    errorType: string,
    errorMessage: string,
    errorContext?: string,
    fatal?: boolean
  ) => {
    if (!isEnabled) return;
    
    const eventData: DataLayerEvent = {
      event: 'exception',
      event_category: 'error',
      event_action: errorType,
      event_label: errorMessage,
      custom_parameters: {
        error_type: errorType,
        error_message: errorMessage,
        error_context: errorContext,
        fatal: fatal || false
      }
    };
    
    events.trackCustom(eventData);
  }, [events, isEnabled]);

  return {
    // Auth events
    trackLogin,
    trackSignup,
    trackLogout,
    trackOAuthComplete,
    
    // Engagement events
    trackChatStarted,
    trackMessageSent,
    trackAgentActivated,
    trackThreadCreated,
    trackFeatureUsed,
    
    // Conversion events
    trackTrialStarted,
    trackPlanUpgraded,
    trackPaymentCompleted,
    trackDemoRequested,
    
    // Utility events
    trackCustomEvent,
    trackPageView,
    trackError,
    
    // State
    isEnabled,
    config
  };
};