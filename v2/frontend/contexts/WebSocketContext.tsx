import React, { createContext, useContext, useEffect, useState } from 'react';
import { webSocketService } from '@/services/websocket';
import { WebSocketMessage } from '@/types';

interface WebSocketContextType {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: WebSocketMessage) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: React.ReactNode; userId: string }> = ({ children, userId }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    if (userId) {
      webSocketService.connect(
        userId,
        () => setIsConnected(true),
        (message) => setLastMessage(message),
        (error) => console.error('WebSocket error:', error)
      );
    }

    return () => {
      webSocketService.disconnect();
      setIsConnected(false);
    };
  }, [userId]);

  const sendMessage = (message: WebSocketMessage) => {
    webSocketService.sendMessage(message);
  };

  return (
    <WebSocketContext.Provider value={{ isConnected, lastMessage, sendMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
