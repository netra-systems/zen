'use client';
import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage, Message } from '@/types/unified';
import { config as appConfig } from '@/config';
import { logger } from '@/lib/logger';
import { logger as debugLogger } from '@/utils/debug-logger';
import { WebSocketContextType, WebSocketProviderProps } from '../types/websocket-context-types';
import { reconciliationService, OptimisticMessage } from '../services/reconciliation';

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

import { AuthContext } from '@/auth/context';
import { unifiedAuthService } from '@/lib/unified-auth-service';

export const WebSocketProvider = ({ children }: WebSocketProviderProps) => {
  const { token } = useContext(AuthContext)!;
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const isConnectingRef = useRef(false);
  const cleanupRef = useRef<() => void>();
  const previousTokenRef = useRef<string | null>(null);

  // Memoized message handler with reconciliation integration
  const handleMessage = useCallback((newMessage: WebSocketMessage) => {
    // Process through reconciliation service first
    const reconciledMessage = reconciliationService.processConfirmation(newMessage);
    
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
      
      // Add new message and limit to last 100 messages for memory cleanup
      const updatedMessages = [...prevMessages, newMessage];
      return updatedMessages.length > 100 ? updatedMessages.slice(-100) : updatedMessages;
    });
  }, []);

  // Memoized status handler
  const handleStatusChange = useCallback((newStatus: WebSocketStatus) => {
    debugLogger.debug('[WebSocketProvider] Status changed to:', newStatus);
    setStatus(newStatus);
  }, []);

  useEffect(() => {
    if (token && !isConnectingRef.current) {
      isConnectingRef.current = true;
      
      const connectToWebSocket = async () => {
        try {
          // Set up event handlers
          webSocketService.onStatusChange = handleStatusChange;
          webSocketService.onMessage = handleMessage;
          
          // Connect to WebSocket using secure endpoint - ensure immediate connection on app load
          const baseWsUrl = appConfig.wsUrl || `${appConfig.apiUrl.replace(/^http/, 'ws')}/ws`;
          const wsUrl = webSocketService.getSecureUrl(baseWsUrl);
          
          debugLogger.debug('[WebSocketProvider] Establishing secure WebSocket connection on app load', {
            baseWsUrl: baseWsUrl,
            finalWsUrl: wsUrl.replace(/jwt\.[^&]+/, 'jwt.***'), // Hide token in logs
            hasToken: !!token,
            tokenLength: token ? token.length : 0,
            isSecure: true,
            authMethod: 'subprotocol',
            configWsUrl: appConfig.wsUrl,
            configApiUrl: appConfig.apiUrl
          });
          
          webSocketService.connect(wsUrl, {
            token,
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
              debugLogger.debug('[WebSocketProvider] Secure WebSocket connection established');
            },
            onError: (error) => {
              logger.error('WebSocket connection error', undefined, {
                component: 'WebSocketProvider',
                action: 'connection_error',
                metadata: { 
                  error: error.message,
                  type: error.type,
                  recoverable: error.recoverable,
                  code: error.code
                }
              });
              
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
              debugLogger.debug('[WebSocketProvider] WebSocket reconnecting with fresh authentication');
            },
            heartbeatInterval: 30000, // 30 second heartbeat
            rateLimit: {
              messages: 60,
              window: 60000 // 60 messages per minute
            }
          });
          
          // Store cleanup function
          cleanupRef.current = () => {
            webSocketService.onStatusChange = null;
            webSocketService.onMessage = null;
            webSocketService.disconnect();
          };
          
        } catch (error) {
          logger.error('Failed to connect to WebSocket', error as Error, {
            component: 'WebSocketProvider',
            action: 'connect_websocket'
          });
        } finally {
          isConnectingRef.current = false;
        }
      };

      // Establish connection immediately on app load
      connectToWebSocket();
    }

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = undefined;
      }
      isConnectingRef.current = false;
    };
  }, [token, handleMessage, handleStatusChange]);

  // Token synchronization effect - update WebSocket when token changes
  useEffect(() => {
    if (token && previousTokenRef.current && token !== previousTokenRef.current) {
      logger.debug('Auth token changed, updating WebSocket connection', {
        component: 'WebSocketProvider',
        action: 'token_sync',
        metadata: {
          hadPreviousToken: !!previousTokenRef.current,
          hasNewToken: !!token
        }
      });
      
      // Update the WebSocket service with the new token
      webSocketService.updateToken(token).catch(error => {
        logger.error('Failed to update WebSocket token', error as Error, {
          component: 'WebSocketProvider',
          action: 'token_sync_failed'
        });
      });
    }
    
    previousTokenRef.current = token;
  }, [token]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    webSocketService.sendMessage(message);
  }, []);

  // Enhanced sendMessage with optimistic update support
  const sendOptimisticMessage = useCallback((messageContent: string, messageType: 'user' | 'assistant' = 'user') => {
    // Create optimistic message for immediate UI update
    const optimisticMsg = reconciliationService.addOptimisticMessage({
      id: `temp_${Date.now()}`,
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

  const contextValue = {
    status,
    messages,
    sendMessage,
    sendOptimisticMessage,
    reconciliationStats: reconciliationService.getStats(),
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};
