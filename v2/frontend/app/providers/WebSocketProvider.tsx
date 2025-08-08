import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import { useWebSocket } from '@/app/services/websocket';
import { useAuth } from '@/contexts/AuthContext';

interface WebSocketContextType {
  sendMessage: (payload: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const { connect, disconnect, sendMessage } = useWebSocket();

  useEffect(() => {
    if (user?.token) {
      connect(user.token);
    }

    return () => {
      if (user) {
        disconnect();
      }
    };
  }, [user, connect, disconnect]);

  return (
    <WebSocketContext.Provider value={{ sendMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};