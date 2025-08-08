import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { WebSocketClient, WebSocketStatus } from './WebSocketClient';
import { useAuth } from '@/app/hooks/useAuth';

interface WebSocketContextType {
  wsClient: WebSocketClient | null;
  wsStatus: WebSocketStatus;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { token } = useAuth();
  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null);
  const [wsStatus, setWsStatus] = useState<WebSocketStatus>(WebSocketStatus.Closed);

  useEffect(() => {
    if (token && !wsClient) {
      const newWsClient = new WebSocketClient();

      newWsClient.onStatusChange = setWsStatus;

      newWsClient.onMessage = (message) => {
        // TODO: Handle incoming messages
        console.log('Received message:', message);
      };

      // TODO: Get runId from somewhere
      newWsClient.connect(token, 'some-run-id');

      setWsClient(newWsClient);

      return () => {
        newWsClient.disconnect();
      };
    }
  }, [token, wsClient]);

  return (
    <WebSocketContext.Provider value={{ wsClient, wsStatus }}>
      {children}
    </WebSocketContext.Provider>
  );
};
