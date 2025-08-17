import React, { createContext, useContext } from 'react';
import { WebSocketContextType, MockWebSocketProviderProps } from '../types/websocket-context-types';
import { WebSocketStatus } from '../services/webSocketService';

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
export const MockWebSocketProvider: React.FC<MockWebSocketProviderProps> = ({ children, value }) => {
  const contextValue = { ...mockWebSocketContextValue, ...value };
  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};