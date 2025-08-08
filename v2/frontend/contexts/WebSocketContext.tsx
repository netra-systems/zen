import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage } from '@/app/types';

interface WebSocketContextType {
  status: WebSocketStatus;
  sendMessage: (message: WebSocketMessage) => void;
  messages: WebSocketMessage[];
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);

  useEffect(() => {
    webSocketService.onStatusChange = setStatus;
    webSocketService.onMessage = (message) => {
      setMessages((prevMessages) => [...prevMessages, message]);
    };
    webSocketService.connect();

    return () => {
      webSocketService.disconnect();
    };
  }, []);

  const sendMessage = (message: WebSocketMessage) => {
    webSocketService.sendMessage(message);
  };

  return (
    <WebSocketContext.Provider value={{ status, sendMessage, messages }}>
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