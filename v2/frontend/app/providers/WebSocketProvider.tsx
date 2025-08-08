
"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { WebSocketStatus } from '@/types';

const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000';

interface WebSocketContextType {
  ws: WebSocket | null;
  status: WebSocketStatus;
  lastJsonMessage: any;
  sendMessage: (message: any) => void;
  connect: (token: string) => void;
  disconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [status, setStatus] = useState<WebSocketStatus>(WebSocketStatus.Closed);
  const [lastJsonMessage, setLastJsonMessage] = useState<any>(null);

  const connect = useCallback((token: string) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected.');
      return;
    }

    const url = `${WEBSOCKET_URL}/ws?token=${token}`;
    setStatus(WebSocketStatus.Connecting);
    console.log('WebSocket connecting to:', url);

    const newWs = new WebSocket(url);

    newWs.onopen = () => {
      console.log('WebSocket connection established.');
      setWs(newWs);
      setStatus(WebSocketStatus.Open);
    };

    newWs.onclose = () => {
      console.log('WebSocket connection closed.');
      setStatus(WebSocketStatus.Closed);
      setWs(null);
    };

    newWs.onerror = (event) => {
      console.error('WebSocket error:', event);
      setStatus(WebSocketStatus.Error);
    };

    newWs.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setLastJsonMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error, 'Received data:', event.data);
      }
    };
  }, [ws]);

  const disconnect = useCallback(() => {
    if (ws) {
      console.log('Disconnecting WebSocket.');
      ws.close();
    }
  }, [ws]);

  const sendMessage = useCallback((message: any) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not open. Cannot send message.');
    }
  }, [ws]);

  return (
    <WebSocketContext.Provider value={{ ws, status, lastJsonMessage, sendMessage, connect, disconnect }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export { useWebSocket } from '@/app/hooks/useWebSocket';
