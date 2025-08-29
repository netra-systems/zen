import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/auth/context';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';

export type InitializationPhase = 'auth' | 'websocket' | 'store' | 'ready' | 'error';

interface InitializationState {
  phase: InitializationPhase;
  isReady: boolean;
  error: Error | null;
  progress: number;
}

interface UseInitializationCoordinatorReturn {
  state: InitializationState;
  reset: () => void;
  isInitialized: boolean;
}

/**
 * Coordinates the initialization sequence of auth, websocket, and store
 * to prevent multiple re-renders and race conditions during first load
 */
export const useInitializationCoordinator = (): UseInitializationCoordinatorReturn => {
  const mounted = useRef(true);
  const initStarted = useRef(false);
  
  const [state, setState] = useState<InitializationState>({
    phase: 'auth',
    isReady: false,
    error: null,
    progress: 0
  });

  const { initialized: authInitialized, loading: authLoading, user } = useAuth();
  const { isConnected: wsConnected } = useWebSocket();
  const { initialized: storeInitialized } = useUnifiedChatStore();

  const updatePhase = useCallback((phase: InitializationPhase, progress: number, error?: Error) => {
    if (!mounted.current) return;
    
    setState(prev => ({
      phase,
      isReady: phase === 'ready',
      error: error || null,
      progress
    }));
  }, []);

  const reset = useCallback(() => {
    initStarted.current = false;
    setState({
      phase: 'auth',
      isReady: false,
      error: null,
      progress: 0
    });
  }, []);

  useEffect(() => {
    // Prevent multiple initialization runs
    if (!mounted.current || initStarted.current) return;
    if (state.phase === 'ready' || state.phase === 'error') return;
    
    const runInitialization = async () => {
      try {
        initStarted.current = true;
        
        // Phase 1: Auth initialization (0-33%)
        if (!authInitialized || authLoading) {
          updatePhase('auth', 10);
          return; // Wait for auth to complete
        }
        
        if (!user) {
          // No user means not authenticated, but initialization is complete
          updatePhase('ready', 100);
          return;
        }
        
        updatePhase('auth', 33);
        
        // Phase 2: WebSocket connection (33-66%)
        if (state.phase === 'auth') {
          updatePhase('websocket', 40);
          
          // Give WebSocket time to establish connection
          const wsTimeout = setTimeout(() => {
            if (mounted.current && !wsConnected) {
              console.warn('WebSocket connection timeout, proceeding anyway');
              updatePhase('store', 66);
            }
          }, 3000);
          
          if (wsConnected) {
            clearTimeout(wsTimeout);
            updatePhase('websocket', 66);
          } else {
            return; // Wait for WebSocket
          }
        }
        
        // Phase 3: Store initialization (66-100%)
        if (state.phase === 'websocket' || wsConnected) {
          updatePhase('store', 75);
          
          // Allow store to initialize with WebSocket data
          const storeTimeout = setTimeout(() => {
            if (mounted.current) {
              updatePhase('ready', 100);
              initStarted.current = false;
            }
          }, 500);
          
          if (storeInitialized) {
            clearTimeout(storeTimeout);
            updatePhase('ready', 100);
            initStarted.current = false;
          }
        }
        
      } catch (error) {
        console.error('Initialization error:', error);
        updatePhase('error', 0, error as Error);
        initStarted.current = false;
      }
    };
    
    runInitialization();
  }, [
    authInitialized,
    authLoading,
    user,
    wsConnected,
    storeInitialized,
    state.phase,
    updatePhase
  ]);

  useEffect(() => {
    return () => {
      mounted.current = false;
    };
  }, []);

  return {
    state,
    reset,
    isInitialized: state.isReady
  };
};