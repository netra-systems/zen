
import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import { webSocketService } from '@/services/webSocketService';
import { useAuth } from '@/contexts/AuthContext';

interface WebSocketContextType {
  sendMessage: (payload: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      webSocketService.connect();
    }

    return () => {
      if (user) {
        webSocketService.close();
      }
    };
  }, [user]);

  const sendMessage = (payload: any) => {
    webSocketService.sendMessage(payload);
  };

  return (
    <WebSocketContext.Provider value={{ sendMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
