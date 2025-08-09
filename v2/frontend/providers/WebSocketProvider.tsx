'use client';
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage } from '../types/websocket';
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
  const { user } = useContext(AuthContext)!;
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);

  useEffect(() => {
    if (user) {
      const fetchConfigAndConnect = async () => {
        try {
          const response = await fetch(`${appConfig.apiUrl}/api/config`);
          const config = await response.json();
          webSocketService.onStatusChange = setStatus;
          webSocketService.onMessage = (newMessage) => {
            setMessages((prevMessages) => [...prevMessages, newMessage]);
          };
          webSocketService.connect(`${config.ws_url}?user_id=${user.id}`);
        } catch (error) {
          console.error('Failed to fetch config and connect to WebSocket', error);
        }
      };

      fetchConfigAndConnect();
    }

    return () => {
      if (user) {
        webSocketService.disconnect();
      }
    };
  }, [user]);

  const sendMessage = (message: WebSocketMessage) => {
    webSocketService.sendMessage(message);
  };

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
