import React, { createContext, useContext } from 'react';
import { WebSocketStatus } from '../../services/webSocketService';
import { WebSocketMessage } from '../../types/backend_schema_auto_generated';

// Define the context type to match real WebSocketProvider
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

// Create context
const WebSocketContext = createContext<WebSocketContextType | null>(mockWebSocketContextValue);

// Export the hook that matches real WebSocketProvider
export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    // For tests, return mock value instead of throwing
    return mockWebSocketContextValue;
  }
  return context;
};

// Mock WebSocketProvider
export const WebSocketProvider: React.FC<{ 
  children: React.ReactNode;
}> = ({ children }) => {
  return (
    <WebSocketContext.Provider value={mockWebSocketContextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};