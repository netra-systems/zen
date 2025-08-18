'use client';
import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage } from '@/types/registry';
import { config as appConfig } from '@/config';
import { logger } from '@/lib/logger';
import { WebSocketContextType, WebSocketProviderProps } from '../types/websocket-context-types';

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

import { AuthContext } from '@/auth/context';

export const WebSocketProvider = ({ children }: WebSocketProviderProps) => {
  const { token } = useContext(AuthContext)!;
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const isConnectingRef = useRef(false);
  const cleanupRef = useRef<() => void>();

  // Memoized message handler to prevent unnecessary re-renders
  const handleMessage = useCallback((newMessage: WebSocketMessage) => {
    // Only update local state - let useEventProcessor handle unified events
    // This prevents duplicate processing and race conditions
    setMessages((prevMessages) => {
      // Prevent duplicate messages by checking if message already exists
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
      
      logger.debug('WebSocket message received and queued', {
        component: 'WebSocketProvider',
        action: 'message_received',
        metadata: { 
          eventType: newMessage.type,
          messageId: newMessage.payload?.message_id,
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
    console.log('[WebSocketProvider] Status changed to:', newStatus);
    setStatus(newStatus);
  }, []);

  useEffect(() => {
    if (token && !isConnectingRef.current) {
      isConnectingRef.current = true;
      
      const fetchConfigAndConnect = async () => {
        try {
          const response = await fetch(`${appConfig.apiUrl}/api/config`);
          const config = await response.json();
          
          // Set up event handlers
          webSocketService.onStatusChange = handleStatusChange;
          webSocketService.onMessage = handleMessage;
          
          // Connect to WebSocket
          webSocketService.connect(`${config.ws_url}?token=${token}`);
          
          // Store cleanup function
          cleanupRef.current = () => {
            webSocketService.onStatusChange = null;
            webSocketService.onMessage = null;
            webSocketService.disconnect();
          };
          
        } catch (error) {
          logger.error('Failed to fetch config and connect to WebSocket', error as Error, {
            component: 'WebSocketProvider',
            action: 'fetch_config_and_connect'
          });
        } finally {
          isConnectingRef.current = false;
        }
      };

      fetchConfigAndConnect();
    }

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = undefined;
      }
      isConnectingRef.current = false;
    };
  }, [token, handleMessage, handleStatusChange]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    webSocketService.sendMessage(message);
  }, []);

  const contextValue = {
    status,
    messages,
    sendMessage,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};
