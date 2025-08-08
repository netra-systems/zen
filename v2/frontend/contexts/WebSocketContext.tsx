import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage } from '../types/websockets';

interface WebSocketContextType {
  status: WebSocketStatus;
  sendMessage: (message: WebSocketMessage) => void;
  lastMessage: WebSocketMessage | null;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    webSocketService.onStatusChange = setStatus;
    webSocketService.onMessage = setLastMessage;
    webSocketService.connect();

    return () => {
      webSocketService.disconnect();
    };
  }, []);

  const sendMessage = (message: WebSocketMessage) => {
    webSocketService.sendMessage(message);
  };

  return (
    <WebSocketContext.Provider value={{ status, sendMessage, lastMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};