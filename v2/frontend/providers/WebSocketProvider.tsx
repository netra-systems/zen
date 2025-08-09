'use client';
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage } from '../types/websocket';
import { config as appConfig } from '@/config';

interface WebSocketContextType {
  status: WebSocketStatus;
  lastMessage: WebSocketMessage | null;
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

export const WebSocketProvider = ({ children }: WebSocketProviderProps) => {
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    const fetchConfigAndConnect = async () => {
      try {
        const response = await fetch(`${appConfig.apiUrl}/api/config`);
        const config = await response.json();
        webSocketService.onStatusChange = setStatus;
        webSocketService.onMessage = setLastMessage;
        webSocketService.connect(config.ws_url);
      } catch (error) {
        console.error('Failed to fetch config and connect to WebSocket', error);
      }
    };

    fetchConfigAndConnect();

    return () => {
      webSocketService.disconnect();
    };
  }, []);

  const sendMessage = (message: WebSocketMessage) => {
    webSocketService.sendMessage(message);
  };

  const contextValue = {
    status,
    lastMessage,
    sendMessage,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};
