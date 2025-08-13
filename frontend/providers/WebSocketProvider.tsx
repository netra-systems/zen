'use client';
import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback, useRef } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage } from '../types/backend_schema_auto_generated';
import { config as appConfig } from '@/config';

interface WebSocketContextType {
  status: WebSocketStatus;
  messages: WebSocketMessage[];
  sendMessage: (message: WebSocketMessage) => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: ReactNode;
}

import { AuthContext } from '@/auth/context';

export const WebSocketProvider = ({ children }: WebSocketProviderProps) => {
  const { token } = useContext(AuthContext)!;
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const isConnectingRef = useRef(false);
  const cleanupRef = useRef<() => void>();

  // Memoized message handler to prevent unnecessary re-renders
  const handleMessage = useCallback((newMessage: WebSocketMessage) => {
    setMessages((prevMessages) => {
      // Prevent duplicate messages by checking if message already exists
      const messageExists = prevMessages.some(msg => 
        msg.payload?.message_id === newMessage.payload?.message_id &&
        newMessage.payload?.message_id
      );
      
      if (messageExists) {
        return prevMessages;
      }
      
      return [...prevMessages, newMessage];
    });
  }, []);

  // Memoized status handler
  const handleStatusChange = useCallback((newStatus: WebSocketStatus) => {
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
          console.error('Failed to fetch config and connect to WebSocket', error);
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
