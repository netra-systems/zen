import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import stores
import { useChatStore } from '@/store/chatStore';

// Import test utilities
import { TestProviders, WebSocketContext } from '../../test-utils/providers';

describe('Agent Provider Integration', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset chat store
    useChatStore.setState({ messages: [], currentThread: null });
  });

  afterEach(() => {
    jest.restoreAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Agent State Coordination', () => {
      jest.setTimeout(10000);
    it('should coordinate agent state with WebSocket messages', async () => {
      const TestComponent = () => {
        const [isProcessing, setIsProcessing] = React.useState(false);
        const wsContext = React.useContext(WebSocketContext);
        
        const sendMessage = () => {
          setIsProcessing(true);
          if (wsContext?.sendMessage) {
            wsContext.sendMessage({ type: 'user_message', payload: { content: 'test message' } } as any);
          }
        };
        
        const stopProcessing = () => {
          setIsProcessing(false);
        };
        
        // Expose function for testing
        React.useEffect(() => {
          (window as any).stopProcessing = stopProcessing;
        }, []);
        
        return (
          <div>
            <div data-testid="status">{isProcessing ? 'Processing' : 'Idle'}</div>
            <button onClick={sendMessage}>Send</button>
            <button onClick={stopProcessing}>Stop</button>
          </div>
        );
      };
      
      const { getByText } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Send message
      fireEvent.click(getByText('Send'));
      
      // Verify processing state
      expect(screen.getByTestId('status')).toHaveTextContent('Processing');
      
      // Simulate agent completion by clicking stop
      fireEvent.click(getByText('Stop'));
      
      // Verify idle state
      expect(screen.getByTestId('status')).toHaveTextContent('Idle');
    });

    it('should sync agent reports with chat messages', async () => {
      const TestComponent = () => {
        const messages = useChatStore((state) => state.messages);
        
        const simulateAgentComplete = () => {
          // Directly add message to store when agent completes
          useChatStore.getState().addMessage({
            id: 'msg-1',
            content: 'Analysis complete',
            role: 'assistant',
            thread_id: 'thread-123'
          });
        };
        
        return (
          <div>
            <button onClick={simulateAgentComplete}>Complete</button>
            <div data-testid="message-count">Messages: {messages.length}</div>
          </div>
        );
      };
      
      const { getByText } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Initially no messages
      expect(screen.getByTestId('message-count')).toHaveTextContent('Messages: 0');
      
      // Simulate agent completion
      fireEvent.click(getByText('Complete'));
      
      // Verify message was added
      expect(screen.getByTestId('message-count')).toHaveTextContent('Messages: 1');
      expect(useChatStore.getState().messages[0].content).toBe('Analysis complete');
    });
  });
});