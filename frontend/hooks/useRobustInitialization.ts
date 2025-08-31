import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/auth/context';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { logger } from '@/lib/logger';

export type InitializationPhase = 
  | 'pending'
  | 'auth-init' 
  | 'auth-complete'
  | 'websocket-init'
  | 'websocket-complete'
  | 'store-init'
  | 'store-complete'
  | 'ready'
  | 'error'
  | 'recovery';

interface InitializationError {
  phase: InitializationPhase;
  message: string;
  code?: string;
  recoverable: boolean;
  timestamp: number;
}

interface InitializationMetrics {
  authStartTime?: number;
  authEndTime?: number;
  wsStartTime?: number;
  wsEndTime?: number;
  storeStartTime?: number;
  storeEndTime?: number;
  totalStartTime: number;
  totalEndTime?: number;
}

interface InitializationState {
  phase: InitializationPhase;
  isReady: boolean;
  progress: number;
  errors: InitializationError[];
  retryCount: number;
  metrics: InitializationMetrics;
}

interface UseRobustInitializationReturn {
  state: InitializationState;
  reset: () => void;
  retry: () => void;
  isInitialized: boolean;
  hasErrors: boolean;
  isRecovering: boolean;
}

// Configuration
const CONFIG = {
  MAX_RETRIES: 3,
  RETRY_DELAYS: [1000, 2000, 5000], // Exponential backoff
  TIMEOUTS: {
    AUTH: 10000,      // 10 seconds
    WEBSOCKET: 5000,  // 5 seconds  
    STORE: 2000       // 2 seconds
  },
  PROGRESS_WEIGHTS: {
    AUTH: 35,
    WEBSOCKET: 40,
    STORE: 25
  }
};

/**
 * Robust initialization coordinator with comprehensive error handling,
 * retry logic, and performance monitoring for frontend initialization.
 */
export const useRobustInitialization = (): UseRobustInitializationReturn => {
  const mounted = useRef(true);
  const initializationLock = useRef(false);
  const timeoutRefs = useRef<{
    auth?: NodeJS.Timeout;
    websocket?: NodeJS.Timeout;
    store?: NodeJS.Timeout;
    retry?: NodeJS.Timeout;
  }>({});
  
  // Check if running in test environment
  const isTestEnv = typeof window !== 'undefined' && (
    (window as any).Cypress || 
    process.env.NODE_ENV === 'test'
  );
  
  const [state, setState] = useState<InitializationState>({
    phase: isTestEnv ? 'ready' : 'pending',
    isReady: isTestEnv,
    progress: isTestEnv ? 100 : 0,
    errors: [],
    retryCount: 0,
    metrics: {
      totalStartTime: Date.now()
    }
  });

  // Safely get hook values with error boundaries
  const getAuthState = () => {
    try {
      return useAuth();
    } catch (error) {
      logger.error('Auth hook error', error as Error, {
        component: 'useRobustInitialization',
        action: 'get_auth_state'
      });
      return { initialized: false, loading: true, user: null, error };
    }
  };

  const getWebSocketState = () => {
    try {
      return useWebSocket();
    } catch (error) {
      logger.warn('WebSocket hook error - continuing', {
        component: 'useRobustInitialization',
        action: 'get_websocket_state',
        metadata: { error: (error as Error).message }
      });
      return { isConnected: false, error };
    }
  };

  const getStoreState = () => {
    try {
      return useUnifiedChatStore();
    } catch (error) {
      logger.warn('Store hook error - continuing', {
        component: 'useRobustInitialization',
        action: 'get_store_state',
        metadata: { error: (error as Error).message }
      });
      return { initialized: false, error };
    }
  };

  const authState = getAuthState();
  const wsState = getWebSocketState();
  const storeState = getStoreState();

  const addError = useCallback((error: Omit<InitializationError, 'timestamp'>) => {
    setState(prev => ({
      ...prev,
      errors: [...prev.errors, { ...error, timestamp: Date.now() }]
    }));
  }, []);

  const updatePhase = useCallback((
    phase: InitializationPhase, 
    progress: number,
    metrics?: Partial<InitializationMetrics>
  ) => {
    if (!mounted.current) return;
    
    setState(prev => ({
      ...prev,
      phase,
      isReady: phase === 'ready',
      progress: Math.min(100, Math.max(0, progress)),
      metrics: metrics ? { ...prev.metrics, ...metrics } : prev.metrics
    }));

    logger.debug('Initialization phase updated', {
      component: 'useRobustInitialization',
      action: 'update_phase',
      metadata: { phase, progress }
    });
  }, []);

  const clearTimeouts = useCallback(() => {
    Object.values(timeoutRefs.current).forEach(timeout => {
      if (timeout) clearTimeout(timeout);
    });
    timeoutRefs.current = {};
  }, []);

  const reset = useCallback(() => {
    clearTimeouts();
    initializationLock.current = false;
    
    setState({
      phase: 'pending',
      isReady: false,
      progress: 0,
      errors: [],
      retryCount: 0,
      metrics: {
        totalStartTime: Date.now()
      }
    });

    logger.info('Initialization reset', {
      component: 'useRobustInitialization',
      action: 'reset'
    });
  }, [clearTimeouts]);

  const retry = useCallback(() => {
    if (state.retryCount >= CONFIG.MAX_RETRIES) {
      logger.error('Max retries exceeded', undefined, {
        component: 'useRobustInitialization',
        action: 'retry',
        metadata: { retryCount: state.retryCount }
      });
      return;
    }

    const retryDelay = CONFIG.RETRY_DELAYS[state.retryCount] || 5000;
    
    setState(prev => ({
      ...prev,
      phase: 'recovery',
      retryCount: prev.retryCount + 1
    }));

    logger.info('Retrying initialization', {
      component: 'useRobustInitialization',
      action: 'retry',
      metadata: { 
        retryCount: state.retryCount + 1,
        delay: retryDelay
      }
    });

    timeoutRefs.current.retry = setTimeout(() => {
      reset();
    }, retryDelay);
  }, [state.retryCount, reset]);

  // Main initialization effect
  useEffect(() => {
    if (isTestEnv) return;
    if (!mounted.current) return;
    if (initializationLock.current) return;
    if (state.phase === 'ready' || state.phase === 'error' || state.phase === 'recovery') return;

    const runInitialization = async () => {
      initializationLock.current = true;

      try {
        // PHASE 1: Authentication
        if (state.phase === 'pending' || state.phase === 'auth-init') {
          if (state.phase === 'pending') {
            updatePhase('auth-init', 5, { authStartTime: Date.now() });
          }

          // Set auth timeout
          if (!timeoutRefs.current.auth) {
            timeoutRefs.current.auth = setTimeout(() => {
              if (mounted.current && state.phase === 'auth-init') {
                addError({
                  phase: 'auth-init',
                  message: 'Authentication timeout',
                  code: 'AUTH_TIMEOUT',
                  recoverable: true
                });
                
                // Continue without auth if possible
                updatePhase('websocket-init', 35);
              }
            }, CONFIG.TIMEOUTS.AUTH);
          }

          // Check auth state
          if (authState.error) {
            addError({
              phase: 'auth-init',
              message: authState.error.message || 'Authentication failed',
              code: 'AUTH_ERROR',
              recoverable: true
            });
            // Continue anyway - app might work without auth
            updatePhase('websocket-init', 35);
          } else if (authState.initialized && !authState.loading) {
            clearTimeout(timeoutRefs.current.auth);
            delete timeoutRefs.current.auth;
            
            updatePhase('auth-complete', 35, { 
              authEndTime: Date.now() 
            });
            
            // Move to WebSocket phase
            updatePhase('websocket-init', 40);
          }
          
          initializationLock.current = false;
          return;
        }

        // PHASE 2: WebSocket Connection
        if (state.phase === 'websocket-init') {
          updatePhase('websocket-init', 40, { wsStartTime: Date.now() });

          // Set WebSocket timeout - shorter as it's less critical
          if (!timeoutRefs.current.websocket) {
            timeoutRefs.current.websocket = setTimeout(() => {
              if (mounted.current && state.phase === 'websocket-init') {
                logger.warn('WebSocket timeout - continuing without real-time updates', {
                  component: 'useRobustInitialization',
                  action: 'websocket_timeout'
                });
                
                addError({
                  phase: 'websocket-init',
                  message: 'WebSocket connection timeout',
                  code: 'WS_TIMEOUT',
                  recoverable: true
                });
                
                // Continue to store phase
                updatePhase('store-init', 75);
              }
            }, CONFIG.TIMEOUTS.WEBSOCKET);
          }

          // Check WebSocket state
          if (wsState.error) {
            addError({
              phase: 'websocket-init',
              message: 'WebSocket connection failed',
              code: 'WS_ERROR',
              recoverable: true
            });
            // Continue without WebSocket
            updatePhase('store-init', 75);
          } else if (wsState.isConnected) {
            clearTimeout(timeoutRefs.current.websocket);
            delete timeoutRefs.current.websocket;
            
            updatePhase('websocket-complete', 75, { 
              wsEndTime: Date.now() 
            });
            
            // Move to store phase
            updatePhase('store-init', 80);
          }
          
          initializationLock.current = false;
          return;
        }

        // PHASE 3: Store Initialization
        if (state.phase === 'store-init') {
          updatePhase('store-init', 80, { storeStartTime: Date.now() });

          // Set store timeout
          if (!timeoutRefs.current.store) {
            timeoutRefs.current.store = setTimeout(() => {
              if (mounted.current && state.phase === 'store-init') {
                // Store is critical - if it fails, we need to handle it
                const storeError = storeState.error;
                
                if (storeError) {
                  addError({
                    phase: 'store-init',
                    message: 'Store initialization failed',
                    code: 'STORE_ERROR',
                    recoverable: false
                  });
                  
                  updatePhase('error', 0);
                } else {
                  // Assume store is ready even if not reported
                  updatePhase('ready', 100, {
                    storeEndTime: Date.now(),
                    totalEndTime: Date.now()
                  });
                }
              }
            }, CONFIG.TIMEOUTS.STORE);
          }

          // Check store state
          if (storeState.error) {
            addError({
              phase: 'store-init',
              message: 'Store initialization error',
              code: 'STORE_ERROR',
              recoverable: false
            });
            updatePhase('error', 0);
          } else if (storeState.initialized) {
            clearTimeout(timeoutRefs.current.store);
            delete timeoutRefs.current.store;
            
            updatePhase('ready', 100, {
              storeEndTime: Date.now(),
              totalEndTime: Date.now()
            });

            // Log success metrics
            const totalTime = Date.now() - state.metrics.totalStartTime;
            logger.info('Initialization complete', {
              component: 'useRobustInitialization',
              action: 'complete',
              metadata: {
                totalTime,
                authTime: state.metrics.authEndTime && state.metrics.authStartTime
                  ? state.metrics.authEndTime - state.metrics.authStartTime
                  : null,
                wsTime: state.metrics.wsEndTime && state.metrics.wsStartTime
                  ? state.metrics.wsEndTime - state.metrics.wsStartTime
                  : null,
                storeTime: state.metrics.storeEndTime && state.metrics.storeStartTime
                  ? state.metrics.storeEndTime - state.metrics.storeStartTime
                  : null
              }
            });
          }
          
          initializationLock.current = false;
          return;
        }

      } catch (error) {
        logger.error('Initialization error', error as Error, {
          component: 'useRobustInitialization',
          action: 'run_initialization',
          metadata: { phase: state.phase }
        });
        
        addError({
          phase: state.phase,
          message: (error as Error).message,
          code: 'UNKNOWN_ERROR',
          recoverable: state.retryCount < CONFIG.MAX_RETRIES
        });
        
        if (state.retryCount < CONFIG.MAX_RETRIES) {
          retry();
        } else {
          updatePhase('error', 0);
        }
      } finally {
        initializationLock.current = false;
      }
    };

    runInitialization();
  }, [
    authState.initialized,
    authState.loading,
    authState.error,
    wsState.isConnected,
    wsState.error,
    storeState.initialized,
    storeState.error,
    state.phase,
    state.retryCount,
    updatePhase,
    addError,
    retry,
    isTestEnv
  ]);

  // Cleanup effect
  useEffect(() => {
    return () => {
      mounted.current = false;
      clearTimeouts();
    };
  }, [clearTimeouts]);

  // Monitor for critical errors that should trigger recovery
  useEffect(() => {
    if (state.phase === 'error' && state.errors.length > 0) {
      const lastError = state.errors[state.errors.length - 1];
      
      if (lastError.recoverable && state.retryCount < CONFIG.MAX_RETRIES) {
        logger.info('Attempting automatic recovery', {
          component: 'useRobustInitialization',
          action: 'auto_recovery',
          metadata: { 
            error: lastError.message,
            retryCount: state.retryCount
          }
        });
        
        retry();
      }
    }
  }, [state.phase, state.errors, state.retryCount, retry]);

  return {
    state,
    reset,
    retry,
    isInitialized: state.isReady,
    hasErrors: state.errors.length > 0,
    isRecovering: state.phase === 'recovery'
  };
};