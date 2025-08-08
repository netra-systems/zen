
// frontend/contexts/WebSocketContext.tsx

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { WebSocketMessage } from '@/types';
import { useAuth } from './AuthContext';

interface WebSocketContextType {
  sendMessage: (message: Omit<WebSocketMessage, 'type'>) => void;
  lastMessage: WebSocketMessage | null;
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (!user || socket) return;

    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setSocket(ws);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setLastMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setSocket(null);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
      setSocket(null);
    };

  }, [user, socket]);

  useEffect(() => {
    if (user && !socket) {
      connect();
    }

    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, [user, socket, connect]);

  const sendMessage = useCallback((message: Omit<WebSocketMessage, 'type'>) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify({ type: 'analysis_request', ...message }));
    } else {
      console.error('WebSocket is not connected.');
    }
  }, [socket, isConnected]);

  return (
    <WebSocketContext.Provider value={{ sendMessage, lastMessage, isConnected }}>
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
