import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import useWebSocket from '@/hooks/useWebSocket';
import { useAuth } from '@/hooks/useAuth';
import { WebSocketStatus } from '@/types';

interface WebSocketContextType {
  status: WebSocketStatus;
  lastJsonMessage: any;
  sendMessage: (message: object) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocketContext = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { token } = useAuth();
  const { status, lastJsonMessage, sendMessage, connect } = useWebSocket();

  useEffect(() => {
    if (token) {
      connect(token);
    }
  }, [token, connect]);

  return (
    <WebSocketContext.Provider value={{ status, lastJsonMessage, sendMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};