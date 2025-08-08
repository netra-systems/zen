"use client";

import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { WebSocketMessage } from '../types';

interface WebSocketContextType {
  sendMessage: (type: string, payload: any) => void;
  registerMessageHandler: (handler: (message: WebSocketMessage) => void) => void;
  unregisterMessageHandler: (handler: (message: WebSocketMessage) => void) => void;
}

export const WebSocketContext = createContext<WebSocketContextType | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [messageHandlers, setMessageHandlers] = useState<((message: WebSocketMessage) => void)[]>([]);

  useEffect(() => {
    const newWs = new WebSocket('ws://localhost:8000/ws');

    newWs.onopen = () => {
      console.log('WebSocket connected');
    };

    newWs.onmessage = (event) => {
      const message = JSON.parse(event.data);
      messageHandlers.forEach(handler => handler(message));
    };

    newWs.onclose = () => {
      console.log('WebSocket disconnected');
    };

    setWs(newWs);

    return () => {
      newWs.close();
    };
  }, [messageHandlers]);

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
    <WebSocketContext.Provider value={{ sendMessage, registerMessageHandler, unregisterMessageHandler }}>
      {children}
    </WebSocketContext.Provider>
  );
};