import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { WebSocketContextType, WebSocketProviderProps } from '../../types/websocket-context-types';
import { WebSocketStatus } from '../../services/webSocketService';
import { MessageType } from '../../types/shared/enums';
import { useAuth } from '../../auth/context';

// Create context first
const WebSocketContext = createContext<WebSocketContextType | null>(null);

// Mock WebSocketProvider that responds to auth state
export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { token, initialized: authInitialized } = useAuth();
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  
  // Mock the connection logic based on auth state  
  useEffect(() => {
    if (!authInitialized) {
      setStatus('CLOSED');
      return;
    }
    
    if (token) {
      // Simulate connection when authenticated
      setStatus('CONNECTING');
      setTimeout(() => setStatus('OPEN'), 50);
      
      // Call the mocked connect function to satisfy test expectations
      const webSocketService = require('../../services/webSocketService').webSocketService;
      if (webSocketService.connect && typeof webSocketService.connect === 'function') {
        webSocketService.connect('ws://localhost:8000/ws', {});
      }
    } else {
      setStatus('CLOSED');
      
      // Call disconnect when logged out
      const webSocketService = require('../../services/webSocketService').webSocketService;
      if (webSocketService.disconnect && typeof webSocketService.disconnect === 'function') {
        webSocketService.disconnect();
      }
    }
  }, [token, authInitialized]);
  
  const mockSendMessage = useCallback(jest.fn(), []);
  const mockSendOptimisticMessage = useCallback(jest.fn(() => ({
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
  })), []);

  const contextValue: WebSocketContextType = {
    status,
    messages: [],
    sendMessage: mockSendMessage,
    sendOptimisticMessage: mockSendOptimisticMessage,
    reconciliationStats: {
      totalOptimistic: 0,
      totalConfirmed: 0,
      totalFailed: 0,
      totalTimeout: 0,
      averageReconciliationTime: 0,
      currentPendingCount: 0
    }
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Export the hook that matches real WebSocketProvider
export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};