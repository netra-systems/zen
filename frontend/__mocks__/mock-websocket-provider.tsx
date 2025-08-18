import React, { createContext, useContext } from 'react';
import { WebSocketContextType, MockWebSocketProviderProps } from '../types/websocket-context-types';
import { WebSocketStatus } from '../services/webSocketService';
import { MessageType } from '../types/shared/enums';

// Mock WebSocket context value
export const mockWebSocketContextValue: WebSocketContextType = {
  status: 'OPEN' as WebSocketStatus,
  messages: [],
  sendMessage: jest.fn(),
  sendOptimisticMessage: jest.fn(() => ({
    id: 'mock-optimistic-id',
    content: 'mock-content',
    type: MessageType.USER,
    role: 'user' as const,
    timestamp: Date.now(),
    tempId: 'mock-temp-id',
    optimisticTimestamp: Date.now(),
    contentHash: 'mock-hash',
    reconciliationStatus: 'pending' as const,
    sequenceNumber: 1,
    retryCount: 0
  })),
  reconciliationStats: {
    totalOptimistic: 0,
    totalConfirmed: 0,
    totalFailed: 0,
    totalTimeout: 0,
    averageReconciliationTime: 0,
    currentPendingCount: 0
  }
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