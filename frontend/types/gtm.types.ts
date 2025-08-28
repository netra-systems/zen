/**
 * Google Tag Manager Integration Types
 * 
 * Provides type-safe interfaces for GTM integration including:
 * - DataLayer interface definitions
 * - Event taxonomy types
 * - Provider configuration
 * - Hook interfaces
 */

export interface GTMConfig {
  /** GTM Container ID */
  containerId: string;
  /** Enable/disable GTM integration */
  enabled: boolean;
  /** Debug mode for development */
  debug?: boolean;
  /** Environment specific configuration */
  environment?: 'development' | 'staging' | 'production';
  /** Custom domain for GTM script (optional) */
  customDomain?: string;
}

export interface DataLayerEvent {
  /** Event name - must match GTM taxonomy */
  event: string;
  /** Event category for grouping */
  event_category?: string;
  /** Event action description */
  event_action?: string;
  /** Event label for additional context */
  event_label?: string;
  /** Numeric value for the event */
  value?: number;
  /** Custom parameters object */
  custom_parameters?: Record<string, any>;
  /** User ID for cross-session tracking */
  user_id?: string;
  /** Session ID for current session */
  session_id?: string;
  /** Page path where event occurred */
  page_path?: string;
  /** Timestamp in ISO format */
  timestamp?: string;
}

export interface AuthenticationEventData extends DataLayerEvent {
  event: 'user_login' | 'user_signup' | 'user_logout' | 'oauth_complete';
  event_category: 'authentication';
  /** Authentication method used */
  auth_method?: 'email' | 'google' | 'oauth';
  /** Whether this is a new user */
  is_new_user?: boolean;
  /** User tier/plan */
  user_tier?: 'free' | 'early' | 'mid' | 'enterprise';
}

export interface EngagementEventData extends DataLayerEvent {
  event: 'chat_started' | 'message_sent' | 'agent_activated' | 'thread_created' | 'feature_used';
  event_category: 'engagement';
  /** Feature or agent type being used */
  feature_type?: string;
  /** Thread ID for chat events */
  thread_id?: string;
  /** Agent type for agent events */
  agent_type?: string;
  /** Message length for message events */
  message_length?: number;
  /** Session duration when applicable */
  session_duration?: number;
}

export interface ConversionEventData extends DataLayerEvent {
  event: 'trial_started' | 'plan_upgraded' | 'payment_completed' | 'demo_requested';
  event_category: 'conversion';
  /** Plan or product being converted to */
  plan_type?: 'early' | 'mid' | 'enterprise';
  /** Transaction value in USD */
  transaction_value?: number;
  /** Transaction ID for revenue tracking */
  transaction_id?: string;
  /** Currency code */
  currency?: string;
  /** Conversion source/campaign */
  conversion_source?: string;
}

export type GTMEventData = AuthenticationEventData | EngagementEventData | ConversionEventData | DataLayerEvent;

export interface GTMProviderProps {
  children: React.ReactNode;
  /** GTM configuration - if not provided, will use environment defaults */
  config?: Partial<GTMConfig>;
  /** Feature flag to enable/disable GTM */
  enabled?: boolean;
}

export interface GTMContextValue {
  /** Whether GTM is loaded and ready */
  isLoaded: boolean;
  /** Whether GTM is enabled */
  isEnabled: boolean;
  /** GTM configuration */
  config: GTMConfig;
  /** Push event to dataLayer */
  pushEvent: (eventData: GTMEventData) => void;
  /** Push custom data to dataLayer */
  pushData: (data: Record<string, any>) => void;
  /** Get current dataLayer state */
  getDataLayer: () => any[];
  /** Debug information */
  debug: {
    /** Last events sent */
    lastEvents: GTMEventData[];
    /** Total events sent */
    totalEvents: number;
    /** Script load time */
    loadTime?: number;
    /** Any errors encountered */
    errors: string[];
  };
}

export interface GTMScriptLoadState {
  /** Script loading status */
  status: 'idle' | 'loading' | 'loaded' | 'error';
  /** Error message if failed to load */
  error?: string;
  /** Load timestamp */
  loadedAt?: number;
}

export interface GTMEventHookReturn {
  /** Track authentication events */
  trackAuth: (eventType: AuthenticationEventData['event'], data?: Partial<AuthenticationEventData>) => void;
  /** Track engagement events */
  trackEngagement: (eventType: EngagementEventData['event'], data?: Partial<EngagementEventData>) => void;
  /** Track conversion events */
  trackConversion: (eventType: ConversionEventData['event'], data?: Partial<ConversionEventData>) => void;
  /** Track custom events */
  trackCustom: (eventData: DataLayerEvent) => void;
  /** Get tracking statistics */
  getStats: () => {
    totalEvents: number;
    eventsByType: Record<string, number>;
    lastEventTime?: number;
  };
}

export interface GTMDebugHookReturn {
  /** Enable debug mode */
  enableDebug: () => void;
  /** Disable debug mode */
  disableDebug: () => void;
  /** Check if debug mode is active */
  isDebugMode: boolean;
  /** Get debug information */
  debugInfo: {
    /** GTM container ID */
    containerId: string;
    /** Script load status */
    scriptStatus: GTMScriptLoadState['status'];
    /** DataLayer events history */
    eventHistory: GTMEventData[];
    /** Performance metrics */
    performance: {
      scriptLoadTime?: number;
      averageEventTime?: number;
      totalEvents: number;
    };
    /** Console logs related to GTM */
    consoleLogs: Array<{
      level: 'log' | 'warn' | 'error';
      message: string;
      timestamp: number;
    }>;
  };
  /** Clear debug history */
  clearDebugHistory: () => void;
}

export interface GTMHookReturn extends GTMContextValue {
  /** Event tracking methods */
  events: GTMEventHookReturn;
  /** Debug utilities */
  debug: GTMDebugHookReturn;
}

// Extend Window interface for GTM globals
declare global {
  interface Window {
    dataLayer: any[];
    gtag?: (...args: any[]) => void;
    google_tag_manager?: {
      [key: string]: any;
    };
  }
}

// Error types for GTM operations
export class GTMError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = 'GTMError';
  }
}

export class GTMScriptLoadError extends GTMError {
  constructor(message: string) {
    super(message, 'SCRIPT_LOAD_ERROR');
    this.name = 'GTMScriptLoadError';
  }
}

export class GTMEventError extends GTMError {
  constructor(message: string) {
    super(message, 'EVENT_ERROR');
    this.name = 'GTMEventError';
  }
}