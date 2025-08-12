import React from 'react';

// Mock WebSocket context value
export const mockWebSocketContextValue = {
  sendMessage: jest.fn(),
  connect: jest.fn(),
  disconnect: jest.fn(),
  isConnected: true,
  connectionState: 'connected' as const,
  error: null,
  lastMessage: null,
  reconnectAttempts: 0,
  messageQueue: [],
  status: 'OPEN' as const,
  messages: [],
  ws: null,
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
};

// Export the same context that WebSocketProvider uses
export const WebSocketContext = React.createContext(mockWebSocketContextValue);

// Mock WebSocketProvider that doesn't actually connect
export const MockWebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <WebSocketContext.Provider value={mockWebSocketContextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};