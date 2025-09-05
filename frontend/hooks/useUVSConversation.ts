/**
 * UVS Conversation Hook - Primary hook for multiturn conversations
 * 
 * CRITICAL: Provides simplified interface to UVS conversation management
 * with automatic factory pattern usage and error handling.
 * 
 * Business Value: Makes UVS integration simple for developers
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { FrontendComponentFactory } from '@/services/uvs/FrontendComponentFactory';
import { ConversationManager, ConversationState, Message } from '@/services/uvs/ConversationManager';
import { WebSocketBridgeClient } from '@/services/uvs/WebSocketBridgeClient';
import { UVSReport } from '@/components/uvs/UVSReportDisplay';
import { logger } from '@/lib/logger';

export interface UseUVSConversationOptions {
  userId: string;
  autoConnect?: boolean;
  onError?: (error: Error) => void;
  onReportReceived?: (report: UVSReport) => void;
}

export interface UseUVSConversationReturn {
  // State
  messages: Message[];
  isProcessing: boolean;
  isConnected: boolean;
  currentReport: UVSReport | null;
  queueStatus: {
    queueLength: number;
    isProcessing: boolean;
  };
  
  // Actions
  sendMessage: (text: string) => Promise<void>;
  clearConversation: () => void;
  retryConnection: () => Promise<void>;
  cancelCurrentMessage: () => void;
  
  // Status
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastError: Error | null;
}

/**
 * Main UVS Conversation Hook
 */
export function useUVSConversation(
  options: UseUVSConversationOptions
): UseUVSConversationReturn {
  const { userId, autoConnect = true, onError, onReportReceived } = options;
  
  // Component instances from factory
  const conversationManagerRef = useRef<ConversationManager | null>(null);
  const wsClientRef = useRef<WebSocketBridgeClient | null>(null);
  
  // State
  const [state, setState] = useState<ConversationState>({
    threadId: null,
    messages: [],
    currentAgentRunId: null,
    isProcessing: false,
    lastActivity: Date.now()
  });
  
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<UseUVSConversationReturn['connectionStatus']>('disconnected');
  const [currentReport, setCurrentReport] = useState<UVSReport | null>(null);
  const [lastError, setLastError] = useState<Error | null>(null);
  const [queueStatus, setQueueStatus] = useState({ queueLength: 0, isProcessing: false });
  
  /**
   * Initialize conversation manager and WebSocket client
   */
  const initialize = useCallback(async () => {
    try {
      logger.info('Initializing UVS conversation', { userId });
      setConnectionStatus('connecting');
      
      // Get instances from factory (ensures user isolation)
      conversationManagerRef.current = FrontendComponentFactory.getConversationManager(userId);
      wsClientRef.current = FrontendComponentFactory.getWebSocketClient(userId);
      
      // Subscribe to state changes
      const unsubscribe = conversationManagerRef.current.onStateChange((newState) => {
        setState(newState);
        
        // Extract UVS report if present
        if (newState.uvsContext) {
          const report: UVSReport = {
            report_type: newState.uvsContext.reportType,
            message: newState.messages[newState.messages.length - 1]?.text || '',
            has_data: newState.uvsContext.hasData,
            has_optimizations: newState.uvsContext.hasOptimizations,
            triage_result: newState.uvsContext.triageResult,
            data_result: newState.uvsContext.dataResult,
            optimizations_result: newState.uvsContext.optimizationsResult,
            exploration_questions: newState.uvsContext.explorationQuestions,
            next_steps: newState.uvsContext.nextSteps
          };
          
          setCurrentReport(report);
          onReportReceived?.(report);
        }
      });
      
      // Connect WebSocket
      if (autoConnect) {
        await wsClientRef.current.ensureIntegration();
        setIsConnected(wsClientRef.current.isConnected());
        setConnectionStatus('connected');
      }
      
      // Update queue status periodically
      const queueInterval = setInterval(() => {
        if (conversationManagerRef.current) {
          const status = conversationManagerRef.current.getQueueStatus();
          setQueueStatus({
            queueLength: status.queueLength,
            isProcessing: status.isProcessing
          });
        }
      }, 100);
      
      // Cleanup function
      return () => {
        unsubscribe();
        clearInterval(queueInterval);
      };
      
    } catch (error) {
      logger.error('🚨 Failed to initialize UVS conversation', { error });
      setConnectionStatus('error');
      setLastError(error as Error);
      onError?.(error as Error);
    }
  }, [userId, autoConnect, onError, onReportReceived]);
  
  /**
   * Send message
   */
  const sendMessage = useCallback(async (text: string) => {
    if (!conversationManagerRef.current) {
      const error = new Error('Conversation manager not initialized');
      setLastError(error);
      throw error;
    }
    
    try {
      setLastError(null);
      await conversationManagerRef.current.sendMessage(text);
    } catch (error) {
      logger.error('🚨 Failed to send message', { error });
      setLastError(error as Error);
      onError?.(error as Error);
      throw error;
    }
  }, [onError]);
  
  /**
   * Clear conversation
   */
  const clearConversation = useCallback(() => {
    if (conversationManagerRef.current) {
      conversationManagerRef.current.clearConversation();
      setCurrentReport(null);
      logger.info('Conversation cleared');
    }
  }, []);
  
  /**
   * Retry connection
   */
  const retryConnection = useCallback(async () => {
    try {
      setConnectionStatus('connecting');
      setLastError(null);
      
      if (!wsClientRef.current) {
        wsClientRef.current = FrontendComponentFactory.getWebSocketClient(userId);
      }
      
      await wsClientRef.current.ensureIntegration();
      setIsConnected(wsClientRef.current.isConnected());
      setConnectionStatus('connected');
      
      logger.info('Connection retry successful');
    } catch (error) {
      logger.error('🚨 Connection retry failed', { error });
      setConnectionStatus('error');
      setLastError(error as Error);
      onError?.(error as Error);
      throw error;
    }
  }, [userId, onError]);
  
  /**
   * Cancel current message
   */
  const cancelCurrentMessage = useCallback(() => {
    if (conversationManagerRef.current) {
      conversationManagerRef.current.cancelCurrentMessage();
      logger.info('Current message cancelled');
    }
  }, []);
  
  /**
   * Initialize on mount
   */
  useEffect(() => {
    const cleanup = initialize();
    
    return () => {
      cleanup.then(fn => fn?.());
    };
  }, [initialize]);
  
  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      // Components are managed by factory, no need to dispose here
      // Factory handles cleanup automatically
    };
  }, []);
  
  return {
    // State
    messages: state.messages,
    isProcessing: state.isProcessing,
    isConnected,
    currentReport,
    queueStatus,
    
    // Actions
    sendMessage,
    clearConversation,
    retryConnection,
    cancelCurrentMessage,
    
    // Status
    connectionStatus,
    lastError
  };
}

/**
 * Hook for handling message queue separately
 */
export function useMessageQueue(conversationManager: ConversationManager | null) {
  const [queueStatus, setQueueStatus] = useState({
    queueLength: 0,
    isProcessing: false,
    messages: [] as Array<{ id: string; text: string; attempts: number; queuedFor: number }>
  });
  
  useEffect(() => {
    if (!conversationManager) return;
    
    const interval = setInterval(() => {
      const status = conversationManager.getQueueStatus();
      setQueueStatus({
        queueLength: status.queueLength,
        isProcessing: status.isProcessing,
        messages: status.messages
      });
    }, 100);
    
    return () => clearInterval(interval);
  }, [conversationManager]);
  
  return queueStatus;
}

/**
 * Hook for WebSocket connection status
 */
export function useWebSocketStatus(wsClient: WebSocketBridgeClient | null) {
  const [status, setStatus] = useState({
    isConnected: false,
    circuitBreakerState: 'CLOSED' as 'CLOSED' | 'OPEN' | 'HALF_OPEN',
    lastPing: null as number | null
  });
  
  useEffect(() => {
    if (!wsClient) return;
    
    const interval = setInterval(() => {
      setStatus({
        isConnected: wsClient.isConnected(),
        circuitBreakerState: wsClient.getCircuitBreakerState(),
        lastPing: Date.now()
      });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [wsClient]);
  
  return status;
}

/**
 * Hook for handling UVS reports
 */
export function useUVSReports() {
  const [reports, setReports] = useState<UVSReport[]>([]);
  const [latestReport, setLatestReport] = useState<UVSReport | null>(null);
  
  const addReport = useCallback((report: UVSReport) => {
    setReports(prev => [...prev, report]);
    setLatestReport(report);
  }, []);
  
  const clearReports = useCallback(() => {
    setReports([]);
    setLatestReport(null);
  }, []);
  
  return {
    reports,
    latestReport,
    addReport,
    clearReports
  };
}