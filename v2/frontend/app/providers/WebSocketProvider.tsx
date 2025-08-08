import React, { createContext, useState, useEffect, ReactNode, useContext } from 'react';
import { WebSocketMessage } from '../types';
import { useAuth } from '@/contexts/AuthContext';

interface WebSocketContextType {
  sendMessage: (type: string, payload: any) => void;
  registerMessageHandler: (handler: (message: WebSocketMessage) => void) => void;
  unregisterMessageHandler: (handler: (message: WebSocketMessage) => void) => void;
  lastMessage: WebSocketMessage | null;
}

export const WebSocketContext = createContext<WebSocketContextType | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [messageHandlers, setMessageHandlers] = useState<((message: WebSocketMessage) => void)[]>([]);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const { user, token } = useAuth();

  useEffect(() => {
    if (!user || !token) return;

    const newWs = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

    newWs.onopen = () => {
    };

    newWs.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setLastMessage(message);
      messageHandlers.forEach(handler => handler(message));
    };

    newWs.onclose = () => {
    };

    setWs(newWs);

    return () => {
      newWs.close();
    };
  }, [user, token, messageHandlers]);

  const sendMessage = (type: string, payload: any) => {
    if (ws) {
      ws.send(JSON.stringify({ type, payload }));
    }
  };

  const registerMessageHandler = (handler: (message: WebSocketMessage) => void) => {
    setMessageHandlers(prevHandlers => [...prevHandlers, handler]);
  };

  const unregisterMessageHandler = (handler: (message: WebSocketMessage) => void) => {
    setMessageHandlers(prevHandlers => prevHandlers.filter(h => h !== handler));
  };

  return (
    <WebSocketContext.Provider value={{ sendMessage, registerMessageHandler, unregisterMessageHandler, lastMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};