import React, { createContext, useContext } from 'react';
import { WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage } from '../types/backend_schema_auto_generated';

// Define the context type to match WebSocketProvider
interface WebSocketContextType {
  status: WebSocketStatus;
  messages: WebSocketMessage[];
  sendMessage: (message: WebSocketMessage) => void;
}

// Mock WebSocket context value
export const mockWebSocketContextValue: WebSocketContextType = {
  status: 'OPEN' as WebSocketStatus,
  messages: [],
  sendMessage: jest.fn(),
};

// Create the same context as WebSocketProvider uses
const WebSocketContext = createContext<WebSocketContextType | null>(mockWebSocketContextValue);

// Export the hook that matches WebSocketProvider
export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  // In tests, always return the mock value
  return context || mockWebSocketContextValue;
};

// Mock WebSocketProvider that doesn't actually connect
export const MockWebSocketProvider: React.FC<{ 
  children: React.ReactNode;
  value?: Partial<WebSocketContextType>;
}> = ({ children, value }) => {
  const contextValue = { ...mockWebSocketContextValue, ...value };
  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};