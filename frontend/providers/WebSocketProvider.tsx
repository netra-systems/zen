'use client';
import React, { createContext, useContext, useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage, Message } from '@/types/unified';
import { config as appConfig } from '@/config';
import { logger } from '@/lib/logger';
import { WebSocketContextType, WebSocketProviderProps } from '../types/websocket-context-types';
import { reconciliationService, OptimisticMessage } from '../services/reconciliation';
import { chatStatePersistence } from '../services/chatStatePersistence';
import { generateMessageId, generateTemporaryId } from '../utils/unique-id-generator';

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

import { AuthContext } from '@/auth/context';
import { useAuth } from '@/auth/context';
import { unifiedAuthService } from '@/lib/unified-auth-service';

// Environment-aware heartbeat interval configuration
const getEnvironmentHeartbeatInterval = (): number => {
  const isStaging = typeof window !== 'undefined' && 
    (window.location.hostname.includes('staging') || 
     process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' ||
     process.env.NODE_ENV === 'staging');
  
  // Staging needs longer heartbeat intervals due to GCP network latency
  return isStaging ? 30000 : 15000; // 30s for staging, 15s for dev
};

export const WebSocketProvider = ({ children }: WebSocketProviderProps) => {
  const { token, initialized: authInitialized } = useAuth();
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const isConnectingRef = useRef(false);
  const cleanupRef = useRef<() => void>();
  const previousTokenRef = useRef<string | null>(null);
  const hasRestoredStateRef = useRef(false);
  const currentThreadIdRef = useRef<string | null>(null);
  
  // Connection state management to prevent duplicate connections
  const connectionStateRef = useRef<'disconnected' | 'connecting' | 'connected' | 'updating'>('disconnected');
  const lastProcessedTokenRef = useRef<string | null>(null);
  const debounceTimeoutRef = useRef<NodeJS.Timeout>();

  // Memoized message handler with reconciliation integration
  const handleMessage = useCallback((newMessage: WebSocketMessage) => {
    // Process through reconciliation service first
    const reconciledMessage = reconciliationService.processConfirmation(newMessage);
    
    // Handle thread-related messages for state persistence
    if (newMessage.type === 'thread_created' || newMessage.type === 'thread_loaded') {
      const threadId = newMessage.payload?.thread_id || newMessage.payload?.threadId;
      if (threadId) {
        currentThreadIdRef.current = threadId;
        chatStatePersistence.updateThread(threadId);
        // Save session state to WebSocket service
        webSocketService.saveSessionState(threadId, newMessage.payload?.message_id);
      }
    }
    
    setMessages((prevMessages) => {
      // Check for duplicates using message_id
      const messageExists = prevMessages.some(msg => 
        msg.payload?.message_id === newMessage.payload?.message_id &&
        newMessage.payload?.message_id
      );
      
      if (messageExists) {
        logger.debug('Duplicate WebSocket message ignored', {
          component: 'WebSocketProvider',
          action: 'duplicate_message',
          metadata: { 
            messageId: newMessage.payload?.message_id,
            eventType: newMessage.type 
          }
        });
        return prevMessages;
      }
      
      logger.debug('WebSocket message received and processed', {
        component: 'WebSocketProvider',
        action: 'message_received',
        metadata: { 
          eventType: newMessage.type,
          messageId: newMessage.payload?.message_id,
          reconciled: !!reconciledMessage,
          totalMessages: prevMessages.length + 1
        }
      });
      
      // Add new message and limit to last 500 messages for better data retention
      const updatedMessages = [...prevMessages, newMessage];
      
      // Persist chat messages if they are user or assistant messages
      if (newMessage.type === 'user_message' || newMessage.type === 'assistant_message' || 
          newMessage.type === 'agent_completed' || newMessage.type === 'final_report') {
        const chatMessages = updatedMessages
          .filter(msg => ['user_message', 'assistant_message', 'agent_completed', 'final_report'].includes(msg.type))
          .map(msg => ({
            id: msg.payload?.message_id || generateMessageId(),
            content: msg.payload?.content || msg.payload?.result || '',
            role: msg.type === 'user_message' ? 'user' : 'assistant',
            timestamp: msg.payload?.timestamp || Date.now()
          } as Message));
        
        chatStatePersistence.updateMessages(chatMessages);
      }
      
      return updatedMessages.length > 500 ? updatedMessages.slice(-500) : updatedMessages;
    });
  }, []);

  // Memoized status handler
  const handleStatusChange = useCallback((newStatus: WebSocketStatus) => {
    logger.debug('[WebSocketProvider] Status changed to:', newStatus);
    setStatus(newStatus);
  }, []);

  // Helper function to perform initial WebSocket connection
  const performInitialConnection = useCallback(async (currentToken: string | null, isDevelopment: boolean) => {
    if (isConnectingRef.current || connectionStateRef.current === 'connecting') {
      logger.debug('[WebSocketProvider] Connection already in progress, skipping');
      return;
    }
    
    connectionStateRef.current = 'connecting';
    isConnectingRef.current = true;
    
    try {
      // Set up event handlers
      webSocketService.onStatusChange = handleStatusChange;
      webSocketService.onMessage = handleMessage;
      
      // Connect to WebSocket using secure endpoint
      const baseWsUrl = appConfig.wsUrl || `${appConfig.apiUrl.replace(/^http/, 'ws')}/ws`;
      const wsUrl = webSocketService.getSecureUrl(baseWsUrl);
      
      logger.debug('[WebSocketProvider] Establishing secure WebSocket connection', {
        baseWsUrl: baseWsUrl,
        finalWsUrl: wsUrl.replace(/jwt\.[^&]+/, 'jwt.***'), // Hide token in logs
        hasToken: !!currentToken,
        tokenLength: currentToken ? currentToken.length : 0,
        isSecure: !isDevelopment || !!currentToken,
        isDevelopment,
        authMethod: currentToken ? 'subprotocol' : 'none',
        configWsUrl: appConfig.wsUrl,
        configApiUrl: appConfig.apiUrl
      });
      
      webSocketService.connect(wsUrl, {
        token: currentToken || undefined,
        refreshToken: async () => {
          try {
            // Use the unified auth service for token refresh
            const authConfig = unifiedAuthService.getWebSocketAuthConfig();
            const refreshedToken = await authConfig.refreshToken();
            
            if (refreshedToken) {
              logger.debug('WebSocket token refreshed successfully via unified auth service');
              return refreshedToken;
            }
            
            logger.warn('Token refresh returned null - may indicate auth failure');
            return null;
          } catch (error) {
            logger.error('Token refresh failed in WebSocketProvider', error as Error, {
              component: 'WebSocketProvider',
              action: 'token_refresh_failed'
            });
            return null;
          }
        },
        onOpen: () => {
          logger.debug('[WebSocketProvider] Secure WebSocket connection established');
          connectionStateRef.current = 'connected';
        },
        onError: (error) => {
          connectionStateRef.current = 'disconnected';
          
          // Log auth errors appropriately based on context
          const errorMessage = error.type === 'auth' 
            ? 'Authentication failure' 
            : 'WebSocket connection error';
          
          const errorAction = error.type === 'auth'
            ? 'authentication_error'
            : 'connection_error';
          
          // Use warning level for recoverable errors, error level for critical ones
          const logContext = {
            component: 'WebSocketProvider',
            action: errorAction,
            metadata: { 
              error: error.message,
              type: error.type,
              recoverable: error.recoverable,
              code: error.code
            }
          };
          
          // Call logger methods directly to maintain proper 'this' context
          if (error.recoverable) {
            logger.warn(errorMessage, logContext);
          } else {
            logger.error(errorMessage, undefined, logContext);
          }
          
          // Handle different error types
          if (error.type === 'auth') {
            if (error.code === 1008) {
              if (error.message.includes('Security violation')) {
                logger.error('WebSocket security violation - using deprecated authentication method');
                // This is a critical security issue - don't retry
              } else {
                logger.warn('WebSocket authentication failed - token may be expired or invalid');
                // Token refresh might help here
              }
            } else {
              logger.warn('WebSocket authentication error', undefined, {
                component: 'WebSocketProvider',
                metadata: { code: error.code, message: error.message }
              });
            }
          }
        },
        onReconnect: () => {
          logger.debug('[WebSocketProvider] WebSocket reconnecting with fresh authentication');
          connectionStateRef.current = 'connecting';
        },
        heartbeatInterval: getEnvironmentHeartbeatInterval(), // Environment-aware heartbeat interval
        rateLimit: {
          messages: 60,
          window: 60000 // 60 messages per minute
        }
      });
      
      // Store cleanup function
      cleanupRef.current = () => {
        connectionStateRef.current = 'disconnected';
        webSocketService.onStatusChange = null;
        webSocketService.onMessage = null;
        webSocketService.disconnect();
      };
      
    } catch (error) {
      connectionStateRef.current = 'disconnected';
      logger.error('Failed to connect to WebSocket', error as Error, {
        component: 'WebSocketProvider',
        action: 'connect_websocket'
      });
    } finally {
      isConnectingRef.current = false;
    }
  }, [handleMessage, handleStatusChange]);

  // Helper function to perform token update without reconnection
  const performTokenUpdate = useCallback(async (newToken: string | null) => {
    if (connectionStateRef.current !== 'connected') {
      logger.debug('[WebSocketProvider] Not updating token - not connected');
      return;
    }
    
    connectionStateRef.current = 'updating';
    
    try {
      logger.debug('Auth token changed, updating WebSocket connection', {
        component: 'WebSocketProvider',
        action: 'token_sync',
        metadata: {
          hadPreviousToken: !!previousTokenRef.current,
          hasNewToken: !!newToken
        }
      });
      
      // Update the WebSocket service with the new token
      if (newToken) {
        await webSocketService.updateToken(newToken);
        logger.debug('[WebSocketProvider] Token updated successfully');
      }
      
    } catch (error) {
      logger.error('Failed to update WebSocket token', error as Error, {
        component: 'WebSocketProvider',
        action: 'token_sync_failed'
      });
    } finally {
      connectionStateRef.current = 'connected';
    }
  }, []);

  // Consolidated WebSocket connection and token management effect
  useEffect(() => {
    // Clear any pending debounce
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
      debounceTimeoutRef.current = undefined;
    }

    // In development mode, allow connection without token
    const isDevelopment = process.env.NODE_ENV === 'development';
    
    // Wait for auth to initialize before attempting connection
    if (!authInitialized) {
      logger.debug('[WebSocketProvider] Waiting for auth initialization');
      return;
    }
    
    // Skip if no token available (unless in development mode)
    if (!token && !isDevelopment) {
      logger.debug('[WebSocketProvider] WebSocket connection skipped - no token available');
      // Update connection state to disconnected
      connectionStateRef.current = 'disconnected';
      return;
    }
    
    // Determine the action to take based on current state and token changes
    const currentToken = token;
    const wasTokenProcessed = lastProcessedTokenRef.current === currentToken;
    const tokenChanged = previousTokenRef.current && previousTokenRef.current !== currentToken;
    const currentState = connectionStateRef.current;
    
    logger.debug('[WebSocketProvider] Connection state evaluation', {
      component: 'WebSocketProvider',
      action: 'state_evaluation',
      metadata: {
        currentState,
        hasToken: !!currentToken,
        tokenChanged,
        wasTokenProcessed,
        authInitialized
      }
    });
    
    // If we're already connecting or updating, don't start another operation
    if (currentState === 'connecting' || currentState === 'updating') {
      logger.debug('[WebSocketProvider] Skipping action - operation in progress', { currentState });
      return;
    }
    
    // If token already processed and no change, skip
    if (wasTokenProcessed && !tokenChanged && currentState === 'connected') {
      logger.debug('[WebSocketProvider] Skipping action - token already processed and connected');
      return;
    }
    
    // Restore chat state on initial mount if available and not yet restored
    if (!hasRestoredStateRef.current && authInitialized) {
      const restorable = chatStatePersistence.getRestorableState();
      if (restorable) {
        logger.debug('[WebSocketProvider] Restoring chat state after refresh', {
          component: 'WebSocketProvider',
          action: 'restore_state',
          metadata: {
            threadId: restorable.threadId,
            messageCount: restorable.messages.length,
            hasDraft: !!restorable.draftMessage
          }
        });
        
        // Restore thread ID
        if (restorable.threadId) {
          currentThreadIdRef.current = restorable.threadId;
        }
        
        // Restore messages to state
        const wsMessages = restorable.messages.map(msg => ({
          type: msg.role === 'user' ? 'user_message' : 'assistant_message',
          payload: {
            message_id: msg.id,
            content: msg.content,
            timestamp: msg.timestamp
          }
        } as WebSocketMessage));
        
        setMessages(wsMessages);
      }
      hasRestoredStateRef.current = true;
    }
    
    // Debounce rapid token changes to prevent excessive operations
    debounceTimeoutRef.current = setTimeout(() => {
      // Decide what action to take
      if (currentState === 'disconnected' || !wasTokenProcessed) {
        // Need to establish initial connection
        performInitialConnection(currentToken, isDevelopment);
      } else if (tokenChanged && currentState === 'connected') {
        // Need to update existing connection with new token
        performTokenUpdate(currentToken);
      }
      
      // Update processed token reference
      lastProcessedTokenRef.current = currentToken;
      previousTokenRef.current = currentToken;
    }, 50); // 50ms debounce to handle rapid token changes

    // Comprehensive cleanup function to prevent memory leaks
    return () => {
      // Clear all timeouts to prevent memory leaks
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
        debounceTimeoutRef.current = undefined;
      }
      
      // Execute WebSocket cleanup if available
      if (cleanupRef.current) {
        try {
          cleanupRef.current();
        } catch (error) {
          logger.debug('Error during WebSocket cleanup:', error);
        } finally {
          cleanupRef.current = undefined;
        }
      }
      
      // Reset connection state
      isConnectingRef.current = false;
      connectionStateRef.current = 'disconnected';
      
      // Clear status handler to prevent memory leaks
      webSocketService.onStatusChange = null;
      webSocketService.onMessage = null;
      
      logger.debug('[WebSocketProvider] Effect cleanup completed');
    };
  }, [token, authInitialized, handleMessage, handleStatusChange, performInitialConnection, performTokenUpdate]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    webSocketService.sendMessage(message);
  }, []);

  // Enhanced sendMessage with optimistic update support
  const sendOptimisticMessage = useCallback((messageContent: string, messageType: 'user' | 'assistant' = 'user') => {
    // Create optimistic message for immediate UI update
    const optimisticMsg = reconciliationService.addOptimisticMessage({
      id: generateTemporaryId('message'),
      content: messageContent,
      role: messageType,
      timestamp: Date.now()
    });
    
    // Send actual WebSocket message
    const wsMessage: WebSocketMessage = {
      type: 'user_message',
      payload: {
        content: messageContent,
        timestamp: new Date().toISOString(),
        correlation_id: optimisticMsg.tempId
      }
    };
    
    webSocketService.sendMessage(wsMessage);
    return optimisticMsg;
  }, []);

  // Comprehensive cleanup on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      try {
        // Clear all event handlers to prevent memory leaks
        webSocketService.onStatusChange = null;
        webSocketService.onMessage = null;
        
        // Disconnect WebSocket service
        webSocketService.disconnect();
        
        // Destroy chat state persistence
        chatStatePersistence.destroy();
        
        // Clear all refs to help garbage collection
        isConnectingRef.current = false;
        cleanupRef.current = undefined;
        previousTokenRef.current = null;
        hasRestoredStateRef.current = false;
        currentThreadIdRef.current = null;
        connectionStateRef.current = 'disconnected';
        lastProcessedTokenRef.current = null;
        
        // Clear any pending timeouts
        if (debounceTimeoutRef.current) {
          clearTimeout(debounceTimeoutRef.current);
          debounceTimeoutRef.current = undefined;
        }
        
        logger.debug('[WebSocketProvider] Component cleanup completed');
      } catch (error) {
        logger.debug('Error during component cleanup:', error);
      }
    };
  }, []);
  
  const contextValue = useMemo(() => ({
    status,
    messages,
    sendMessage,
    sendOptimisticMessage,
    reconciliationStats: reconciliationService.getStats(),
  }), [status, messages, sendMessage, sendOptimisticMessage]);

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};
