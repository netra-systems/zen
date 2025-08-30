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
  const wsTimeoutRef = useRef<NodeJS.Timeout>();
  const storeTimeoutRef = useRef<NodeJS.Timeout>();
  
  const [state, setState] = useState<InitializationState>({
    phase: 'auth',
    isReady: false,
    error: null,
    progress: 0
  });

  // Wrap hook calls in try-catch to handle errors
  let authInitialized = false;
  let authLoading = true;
  let user = null;
  let wsConnected = false;
  let storeInitialized = false;
  
  try {
    const authResult = useAuth();
    authInitialized = authResult.initialized;
    authLoading = authResult.loading;
    user = authResult.user;
  } catch (error) {
    // Auth hook threw an error
    if (mounted.current && state.phase !== 'error') {
      console.error('Initialization error:', error);
      setState({
        phase: 'error',
        isReady: false,
        error: error as Error,
        progress: 0
      });
    }
  }
  
  try {
    const wsResult = useWebSocket();
    wsConnected = wsResult.isConnected;
  } catch (error) {
    // WebSocket hook error is less critical, log but continue
    console.warn('WebSocket initialization warning:', error);
  }
  
  try {
    const storeResult = useUnifiedChatStore();
    storeInitialized = storeResult.initialized;
  } catch (error) {
    // Store hook error is less critical, log but continue
    console.warn('Store initialization warning:', error);
  }

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
    // Clear any pending timeouts
    if (wsTimeoutRef.current) clearTimeout(wsTimeoutRef.current);
    if (storeTimeoutRef.current) clearTimeout(storeTimeoutRef.current);
    
    setState({
      phase: 'auth',
      isReady: false,
      error: null,
      progress: 0
    });
  }, []);

  useEffect(() => {
    // Prevent multiple initialization runs  
    if (!mounted.current) return;
    if (state.phase === 'ready' || state.phase === 'error') return;
    
    const runInitialization = async () => {
      try {
        // Phase 1: Auth initialization (0-33%)
        if (state.phase === 'auth') {
          if (!authInitialized || authLoading) {
            // Keep initial progress at 0 until auth starts
            return; // Wait for auth to complete
          }
          
          if (!user) {
            // No user means not authenticated, but initialization is complete
            updatePhase('ready', 100);
            return;
          }
          
          // Auth completed, move to WebSocket phase
          updatePhase('websocket', 40);
          return;
        }
        
        // Phase 2: WebSocket connection (33-66%)
        if (state.phase === 'websocket') {
          if (!wsConnected) {
            // Set up timeout for WebSocket connection
            if (!wsTimeoutRef.current) {
              wsTimeoutRef.current = setTimeout(() => {
                if (mounted.current && state.phase === 'websocket') {
                  console.warn('WebSocket connection timeout, proceeding anyway');
                  updatePhase('store', 70);
                  wsTimeoutRef.current = undefined;
                }
              }, 3000);
            }
            return;
          }
          
          // WebSocket connected, clear timeout and move to store phase
          if (wsTimeoutRef.current) {
            clearTimeout(wsTimeoutRef.current);
            wsTimeoutRef.current = undefined;
          }
          updatePhase('store', 70);
          return;
        }
        
        // Phase 3: Store initialization (66-100%)
        if (state.phase === 'store') {
          if (!storeInitialized) {
            // Give store time to initialize
            if (!storeTimeoutRef.current) {
              storeTimeoutRef.current = setTimeout(() => {
                if (mounted.current && state.phase === 'store') {
                  updatePhase('ready', 100);
                  storeTimeoutRef.current = undefined;
                }
              }, 500);
            }
            return;
          }
          
          // Everything ready, clear timeout
          if (storeTimeoutRef.current) {
            clearTimeout(storeTimeoutRef.current);
            storeTimeoutRef.current = undefined;
          }
          updatePhase('ready', 100);
        }
        
      } catch (error) {
        console.error('Initialization error:', error);
        updatePhase('error', 0, error as Error);
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
      // Clear any pending timeouts on unmount
      if (wsTimeoutRef.current) clearTimeout(wsTimeoutRef.current);
      if (storeTimeoutRef.current) clearTimeout(storeTimeoutRef.current);
    };
  }, []);

  return {
    state,
    reset,
    isInitialized: state.isReady
  };
};