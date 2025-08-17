
import React from 'react';

// Mock WebSocket context value matching the real interface
const mockWebSocketContextValue = {
  status: 'OPEN' as const,
  messages: [],
  sendMessage: jest.fn()
};

// Create mock context
export const WebSocketContext = React.createContext(mockWebSocketContextValue);

export const WebSocketProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <WebSocketContext.Provider value={mockWebSocketContextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = () => mockWebSocketContextValue;
